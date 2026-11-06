"""
ClaimRecon AI — Run History & Portfolio Analytics Manager
Persists and retrieves run outputs, aggregates portfolio-level metrics
(total submitted, supported, unsupported), and provides claim ranking.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional


RUNS_DIR = Path("runs")


def _to_decimal(val: Any) -> Decimal:
    """Safe Decimal conversion."""
    try:
        if val is None:
            return Decimal("0.00")
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def get_runs_dir() -> Path:
    """Ensure and return the runs directory path."""
    if not RUNS_DIR.exists():
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
    return RUNS_DIR


def save_run(result: Dict[str, Any]) -> str:
    """
    Persist an execution result into the runs/ directory as JSON.
    Returns the file path of the saved record.
    """
    runs_dir = get_runs_dir()
    claim = result.get("claim", {})
    claim_id = claim.get("claim_profile", "UNKNOWN").replace("/", "_").replace("\\", "_")
    run_id = result.get("run_id", "run")
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    filename = f"run_{timestamp}_{claim_id}_{run_id[:8]}.json"
    file_path = runs_dir / filename

    # Extract serializable summary record
    record = {
        "run_id": result.get("run_id"),
        "timestamp_utc": datetime.utcnow().isoformat(),
        "claim_folder": result.get("claim_folder"),
        "status": result.get("status"),
        "claim": {
            "claim_profile": claim.get("claim_profile", "UNKNOWN"),
            "insured": claim.get("insured", "Unknown Insured"),
            "loss_date": claim.get("loss_date", ""),
            "claimed_stock_amount": str(claim.get("claimed_stock_amount", "0")),
            "currency": claim.get("currency", "USD"),
        },
        "financial_summary": result.get("financial_summary", {}),
        "check_evaluation": result.get("check_evaluation", {}),
        "completeness_result": result.get("completeness_result", {}),
        "integrity_findings": result.get("integrity_findings", []),
        "supervisor_plan": result.get("supervisor_plan", {}),
        "investigator_summary": result.get("investigator_summary", {}),
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, default=str)

    return str(file_path)


def load_all_runs() -> List[Dict[str, Any]]:
    """
    Load all stored run records from the runs/ folder, sorted newest first.
    """
    runs_dir = get_runs_dir()
    records = []

    for path in sorted(runs_dir.glob("run_*.json"), reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file_path"] = str(path)
                records.append(data)
        except Exception:
            continue

    return records


def get_latest_runs_by_claim() -> List[Dict[str, Any]]:
    """
    Returns the most recent run for each distinct claim_profile,
    ensuring metrics don't duplicate when a claim is re-run multiple times.
    """
    all_runs = load_all_runs()
    latest_by_claim: Dict[str, Dict[str, Any]] = {}

    for r in all_runs:
        claim_profile = r.get("claim", {}).get("claim_profile", "UNKNOWN")
        if claim_profile not in latest_by_claim:
            latest_by_claim[claim_profile] = r

    return list(latest_by_claim.values())


def compute_portfolio_metrics(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute aggregate portfolio totals across claims:
    - Total Submitted / Claimed
    - Total Supported
    - Total Unsupported
    - Total Findings Count
    - List of formatted claim summary records
    """
    total_claimed = Decimal("0.00")
    total_supported = Decimal("0.00")
    total_unsupported = Decimal("0.00")
    total_findings_count = 0

    claim_rows = []

    for r in runs:
        claim = r.get("claim", {})
        fs = r.get("financial_summary", {})
        findings = r.get("integrity_findings", [])
        ce = r.get("check_evaluation", {})

        claimed = _to_decimal(fs.get("claimed_amount", claim.get("claimed_stock_amount", "0")))
        is_complete = bool(fs.get("calculation_complete", False))

        if is_complete and fs.get("supported_amount") is not None:
            supported = _to_decimal(fs.get("supported_amount", "0"))
            unsupported = _to_decimal(fs.get("unsupported_amount", "0"))
        else:
            supported = None
            unsupported = _to_decimal(fs.get("identified_unsupported_amount", "0"))

        total_claimed += claimed
        if supported is not None:
            total_supported += supported
        total_unsupported += unsupported
        total_findings_count += len(findings)

        # Completeness details
        comp_res = r.get("completeness_result", {})
        completeness_pct = comp_res.get("completeness_pct")
        if completeness_pct is None:
            # Infer from completeness or calculation status
            completeness_pct = 100.0 if is_complete else 80.0
        else:
            completeness_pct = float(completeness_pct)

        missing_docs = comp_res.get("missing_documents", [])
        present_docs = comp_res.get("present_required", comp_res.get("found_documents", []))

        claim_rows.append({
            "run_id": r.get("run_id"),
            "timestamp": r.get("timestamp_utc", ""),
            "claim_profile": claim.get("claim_profile", "UNKNOWN"),
            "insured": claim.get("insured", "Unknown Insured"),
            "loss_date": claim.get("loss_date", ""),
            "claimed_amount": float(claimed),
            "supported_amount": float(supported) if supported is not None else None,
            "unsupported_amount": float(unsupported),
            "calculation_complete": is_complete,
            "completeness_pct": round(completeness_pct, 1),
            "missing_docs": missing_docs,
            "present_docs": present_docs,
            "status": r.get("status", "COMPLETED"),
            "findings_count": len(findings),
            "findings": findings,
            "summary": r.get("investigator_summary", {}),
            "raw_record": r,
        })

    return {
        "total_claimed": float(total_claimed),
        "total_supported": float(total_supported),
        "total_unsupported": float(total_unsupported),
        "total_findings_count": total_findings_count,
        "total_claims_evaluated": len(runs),
        "claims": claim_rows,
    }

