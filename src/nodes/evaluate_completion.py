"""
Node 8 — evaluate_completion (Python / Deterministic)
State machine that compares configured checks vs completed/blocked/failed/pending.
Determines the next_action for conditional routing.
Section 11 of the blueprint.
"""
from __future__ import annotations


from src.state import ClaimState
from src.config import CONFIGURED_RULE_IDS


def evaluate_completion(state: ClaimState) -> dict:
    """
    Compute check completion status and determine what happens next.

    next_action values:
      CONTINUE_INVESTIGATION    → loop back to supervisor_plan
      CALCULATE_SUPPORTED_AMOUNT → all checks done; compute final amount
      CALCULATE_PARTIAL_RESULT  → some blocked; compute partial amount
      PROCESSING_REVIEW         → at least one check failed; needs human review
    """
    configured = CONFIGURED_RULE_IDS  # from config — not LLM-defined

    completed = set(state.get("completed_checks", []))
    failed_checks = state.get("failed_checks", [])
    blocked_checks = state.get("blocked_checks", [])

    failed = {x["rule_id"] for x in failed_checks}
    blocked = {x["rule_id"] for x in blocked_checks}
    pending = configured - completed - failed - blocked

    # Determine next action (exact logic from Section 11)
    if failed:
        next_action = "PROCESSING_REVIEW"
        status = "PROCESSING_REVIEW"
    elif blocked:
        # If any check is blocked due to missing documents, calculate partial result
        next_action = "CALCULATE_PARTIAL_RESULT"
        status = "PARTIALLY_COMPLETED"
    elif pending:
        next_action = "CONTINUE_INVESTIGATION"
        status = "CHECKS_PENDING"
    else:
        next_action = "CALCULATE_SUPPORTED_AMOUNT"
        status = "COMPLETED"

    check_evaluation = {
        "status": status,
        "configured_checks": sorted(configured),
        "completed_checks": sorted(completed),
        "blocked_checks": sorted(blocked),
        "failed_checks": sorted(failed),
        "pending_checks": sorted(pending),
        "all_checks_completed": len(pending) == 0 and len(failed) == 0 and len(blocked) == 0,
        "next_action": next_action,
        # Summary counts for UI
        "check_summary": {
            "configured": len(configured),
            "completed": len(completed),
            "blocked": len(blocked),
            "failed": len(failed),
            "pending": len(pending),
        },
    }

    return {"check_evaluation": check_evaluation, "status": status}
