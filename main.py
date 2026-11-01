"""
ClaimRecon AI — CLI Entry Point
Usage:
    python main.py [claim_folder]

    claim_folder defaults to: data/complete_claim_package_clm_2026_0042
"""

import sys
import os
import warnings

# Suppress all deprecation, future, and runtime warnings before third-party imports
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["GRPC_VERBOSITY"] = "NONE"
warnings.filterwarnings("ignore")
try:
    from langchain_core._api.deprecation import LangChainPendingDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
except Exception:
    pass

import json
from dotenv import load_dotenv

load_dotenv()

from src.graph import build_graph


def print_separator(char="─", width=60):
    print(char * width)


def format_amount(val) -> str:
    try:
        return f"${float(val):>12,.2f}"
    except (TypeError, ValueError):
        return "          N/A"


def main():
    folder = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "data/complete_claim_package_clm_2026_0042"
    )

    print()
    print_separator("═")
    print("  ClaimRecon AI — Bounded Agentic Claim Validation")
    print_separator("═")
    print(f"  Package: {folder}")
    print_separator()

    graph = build_graph()

    print("  Running pipeline...\n")
    result = graph.invoke({"claim_folder": folder})

    claim = result.get("claim", {})
    fs = result.get("financial_summary", {})
    ce = result.get("check_evaluation", {})
    summary = result.get("investigator_summary", {})
    findings = result.get("integrity_findings", [])

    # ── Header ────────────────────────────────────────────────────────────────
    print_separator("═")
    print(f"  {claim.get('claim_profile', '')} | {claim.get('insured', '')} | {result.get('status', '')}")
    print_separator("═")

    # ── Financial KPIs ────────────────────────────────────────────────────────
    print()
    print(f"  Claimed Amount    : {format_amount(fs.get('claimed_amount'))}")
    if fs.get("calculation_complete"):
        print(f"  Supported Amount  : {format_amount(fs.get('supported_amount'))}")
        print(f"  Unsupported Amount: {format_amount(fs.get('unsupported_amount'))}")
        print(f"  Supported %       : {fs.get('supported_pct', 0):.1f}%")
    else:
        print(f"  Identified Unsupported: {format_amount(fs.get('identified_unsupported_amount'))}")
        print(f"  ⚠  Calculation incomplete — {fs.get('reason', '')}")

    # ── Check Summary ─────────────────────────────────────────────────────────
    print()
    print_separator()
    cs = ce.get("check_summary", {})
    print(
        f"  Checks: {cs.get('completed', 0)} completed  "
        f"{cs.get('blocked', 0)} blocked  "
        f"{cs.get('failed', 0)} failed  "
        f"{cs.get('pending', 0)} pending"
    )

    # ── Integrity Findings ────────────────────────────────────────────────────
    print()
    print_separator()
    print(f"  {'Finding':<8} {'Invoice':<12} {'Rule':<32} {'Impact':>12}")
    print_separator()
    for f in findings:
        print(
            f"  {f.get('finding_id', ''):<8} "
            f"{f.get('claim_line_key', ''):<12} "
            f"{f.get('rule_id', ''):<32} "
            f"{format_amount(f.get('financial_impact', '0')):>12}"
        )
    if not findings:
        print("  No integrity findings.")

    # ── Golden Invariant Check ────────────────────────────────────────────────
    if fs.get("calculation_complete"):
        print()
        print_separator()
        claimed = float(fs.get("claimed_amount", 0))
        supported = float(fs.get("supported_amount", 0))
        unsupported = float(fs.get("unsupported_amount", 0))
        invariant_ok = abs((supported + unsupported) - claimed) < 0.01
        status = "✅ INVARIANT PASSES" if invariant_ok else "❌ INVARIANT FAILED"
        print(f"  {supported:,.2f} + {unsupported:,.2f} = {supported + unsupported:,.2f}  →  {status}")

    # ── Investigator Summary ──────────────────────────────────────────────────
    if summary:
        print()
        print_separator()
        print("  INVESTIGATOR SUMMARY")
        print_separator()
        print(f"  {summary.get('executive_summary', '')}")
        print()
        print("  Recommended Actions:")
        for i, action in enumerate(summary.get("recommended_actions", []), 1):
            print(f"  {i}. {action}")
        print()
        print(f"  [{summary.get('disclaimer', '')}]")

    print()
    print_separator("═")
    print()


if __name__ == "__main__":
    main()

