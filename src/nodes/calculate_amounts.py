"""
Node 9 — calculate_amounts (Python / Deterministic)
Two functions:
  - calculate_supported_amount: all checks done → final definitive result
  - calculate_partial_result:   some checks blocked → partial / indicative result

Uses Python Decimal throughout to avoid floating-point errors.
Safeguard: max-impact-per-line prevents double-counting.
Section 12 of the blueprint.
"""
from __future__ import annotations


from decimal import Decimal, InvalidOperation
from src.state import ClaimState


def _to_decimal(val) -> Decimal:
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _aggregate_findings(findings: list[dict]) -> tuple[dict[str, Decimal], Decimal]:
    """
    Aggregate financial impacts by claim line key.
    Safeguard: per-line maximum (prevents double-deduction when two findings
    affect the same invoice line).
    Returns (impact_by_line, total_unsupported).
    """
    impact_by_line: dict[str, Decimal] = {}
    for finding in findings:
        key = finding.get("claim_line_key", "UNKNOWN")
        impact = _to_decimal(finding.get("financial_impact", "0"))
        impact_by_line[key] = max(impact_by_line.get(key, Decimal("0")), impact)

    total_unsupported = sum(impact_by_line.values(), Decimal("0"))
    return impact_by_line, total_unsupported


def calculate_supported_amount(state: ClaimState) -> dict:
    """
    All financial checks completed → compute the definitive supported amount.
    Asserts the invariant: supported + unsupported == claimed.
    """
    check_eval = state.get("check_evaluation", {})
    assert check_eval.get("all_checks_completed"), (
        "calculate_supported_amount called before all checks completed"
    )

    claimed = _to_decimal(state["claim"]["claimed_stock_amount"])
    findings = state.get("integrity_findings", [])
    currency = state["claim"].get("currency", "USD")

    impact_by_line, unsupported = _aggregate_findings(findings)
    supported = claimed - unsupported

    # Golden invariant assertion
    assert supported + unsupported == claimed, (
        f"INVARIANT FAILED: {supported} + {unsupported} != {claimed}"
    )

    # Build breakdown list for UI
    breakdown = []
    for finding in findings:
        key = finding.get("claim_line_key", "")
        # Only include the max-impact finding per line
        if _to_decimal(finding.get("financial_impact", "0")) == impact_by_line.get(key):
            breakdown.append(
                {
                    "finding_id": finding.get("finding_id"),
                    "reason": finding.get("rule_id", "").replace("_V1", "").replace("_", " "),
                    "invoice": key,
                    "amount": f"{_to_decimal(finding.get('financial_impact', '0')):.2f}",
                    "description": finding.get("description", ""),
                    "evidence": finding.get("evidence", []),
                }
            )

    supported_pct = float(supported / claimed * 100) if claimed else 0.0
    unsupported_pct = float(unsupported / claimed * 100) if claimed else 0.0

    financial_summary = {
        "claimed_amount": f"{claimed:.2f}",
        "supported_amount": f"{supported:.2f}",
        "unsupported_amount": f"{unsupported:.2f}",
        "difference_amount": f"{claimed - supported:.2f}",
        "supported_pct": round(supported_pct, 2),
        "unsupported_pct": round(unsupported_pct, 2),
        "currency": currency,
        "calculation_complete": True,
        "breakdown": breakdown,
    }

    return {
        "financial_summary": financial_summary,
        "status": "READY_FOR_SUMMARY",
    }


def calculate_partial_result(state: ClaimState) -> dict:
    """
    Some checks blocked → compute partial/indicative unsupported amount only.
    supported_amount is explicitly null — do not display as final.
    """
    claimed = _to_decimal(state["claim"]["claimed_stock_amount"])
    findings = state.get("integrity_findings", [])
    currency = state["claim"].get("currency", "USD")
    blocked = state.get("blocked_checks", [])

    _impact_by_line, identified_unsupported = _aggregate_findings(findings)

    blocked_rule_ids = [b.get("rule_id") for b in blocked]
    blocked_descriptions = [b.get("reason", b.get("rule_id", "")) for b in blocked]

    financial_summary = {
        "claimed_amount": f"{claimed:.2f}",
        "supported_amount": None,          # ← deliberately null
        "identified_unsupported_amount": f"{identified_unsupported:.2f}",
        "difference_amount": None,
        "currency": currency,
        "calculation_complete": False,
        "reason": (
            f"The following checks could not complete due to missing documents: "
            f"{', '.join(blocked_rule_ids)}. "
            f"A definitive supported amount cannot be calculated."
        ),
        "blocked_checks": blocked_rule_ids,
        "blocked_check_reasons": blocked_descriptions,
        "breakdown": [
            {
                "finding_id": f.get("finding_id"),
                "reason": f.get("rule_id", "").replace("_V1", "").replace("_", " "),
                "invoice": f.get("claim_line_key"),
                "amount": f"{_to_decimal(f.get('financial_impact', '0')):.2f}",
                "description": f.get("description", ""),
                "evidence": f.get("evidence", []),
            }
            for f in findings
        ],
    }

    return {
        "financial_summary": financial_summary,
        "status": "PARTIALLY_COMPLETED",
    }
