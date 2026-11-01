"""
Node 7 — execute_checks (Python / Deterministic)
Runs the approved integrity check tools from the TOOL_REGISTRY.
Accumulates findings into state.
"""
from __future__ import annotations


from src.state import ClaimState
from src.config import TOOL_CATALOG
from src.tools.duplicate_invoice import check_duplicate_invoices
from src.tools.delivery_after_loss import check_delivery_after_loss
from src.tools.amount_mismatch import check_invoice_amount_mismatch


TOOL_REGISTRY = {
    "check_duplicate_invoices": check_duplicate_invoices,
    "check_delivery_after_loss": check_delivery_after_loss,
    "check_invoice_amount_mismatch": check_invoice_amount_mismatch,
}


def execute_checks(state: ClaimState) -> dict:
    """Execute each approved tool and collect findings into state."""
    plan = state.get("supervisor_plan", {})
    approved_tools: list[str] = plan.get("approved_tools", [])

    # Load existing state lists (accumulate across iterations)
    all_findings: list[dict] = list(state.get("integrity_findings", []))
    completed_checks: list[str] = list(state.get("completed_checks", []))
    failed_checks: list[dict] = list(state.get("failed_checks", []))
    blocked_checks: list[dict] = list(state.get("blocked_checks", []))

    # Merge any blocked checks identified during completeness or supervisor plan
    existing_blocked_rules = {b["rule_id"] for b in blocked_checks if "rule_id" in b}
    for blocked in plan.get("blocked_tools", []):
        rule_id = TOOL_CATALOG.get(blocked.get("tool", ""), {}).get("rule_id")
        if rule_id and rule_id not in existing_blocked_rules:
            blocked_checks.append(
                {
                    "rule_id": rule_id,
                    "tool": blocked.get("tool"),
                    "reason": blocked.get("reason", ""),
                    "missing_dependencies": [],
                }
            )
            existing_blocked_rules.add(rule_id)

    for tool_name in approved_tools:
        fn = TOOL_REGISTRY.get(tool_name)
        if not fn:
            failed_checks.append(
                {"rule_id": tool_name, "error": "Tool not found in registry"}
            )
            continue

        try:
            result = fn(state)
            tool_status = result.get("status", "FAILED")
            rule_id = result.get("rule_id", TOOL_CATALOG.get(tool_name, {}).get("rule_id", tool_name))

            if tool_status == "COMPLETED":
                all_findings.extend(result.get("findings", []))
                if rule_id not in completed_checks:
                    completed_checks.append(rule_id)
            elif tool_status == "FAILED":
                failed_checks.append(
                    {"rule_id": rule_id, "error": result.get("error", "Unknown error")}
                )

        except Exception as e:
            rule_id = TOOL_CATALOG.get(tool_name, {}).get("rule_id", tool_name)
            failed_checks.append({"rule_id": rule_id, "error": str(e)})

    return {
        "integrity_findings": all_findings,
        "completed_checks": completed_checks,
        "failed_checks": failed_checks,
        "blocked_checks": blocked_checks,
        "status": "CHECKS_EXECUTED",
    }
