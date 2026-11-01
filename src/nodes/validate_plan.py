"""
Node 6 — validate_plan (Python / Deterministic)
Validates the Supervisor's tool selections against the tool catalog,
dependency availability, and completed-check list.
Section 9 of the blueprint.
"""
from __future__ import annotations


from src.state import ClaimState
from src.config import TOOL_CATALOG


def _dependencies_present(tool_name: str, documents: dict) -> bool:
    """Return True if all dependencies for the tool are in the documents dict."""
    tool_cfg = TOOL_CATALOG.get(tool_name)
    if not tool_cfg:
        return False
    return all(dep in documents for dep in tool_cfg["requires"])


def validate_plan(state: ClaimState) -> dict:
    """
    Validate the Supervisor's selected tools:
    1. Reject unknown tools not in TOOL_CATALOG
    2. Reject tools with missing dependencies
    3. Remove already-completed checks
    4. Update supervisor_plan with the approved_tools list
    """
    plan = state.get("supervisor_plan", {})
    selected = plan.get("selected_tools", [])
    documents = state.get("documents", {})
    completed_checks = state.get("completed_checks", [])

    # Map rule_id → tool_name for completed-check filtering
    rule_to_tool = {v["rule_id"]: k for k, v in TOOL_CATALOG.items()}
    completed_tool_names = {
        rule_to_tool[rid] for rid in completed_checks if rid in rule_to_tool
    }

    approved_tools: list[str] = []
    rejected: list[dict] = []

    for selection in selected:
        tool_name = selection.get("tool", "")

        # 1. Unknown tool
        if tool_name not in TOOL_CATALOG:
            rejected.append({"tool": tool_name, "reason": "Not in approved catalog"})
            continue

        # 2. Already completed
        if tool_name in completed_tool_names:
            rejected.append({"tool": tool_name, "reason": "Already completed"})
            continue

        # 3. Dependencies not met
        if not _dependencies_present(tool_name, documents):
            missing = [
                dep
                for dep in TOOL_CATALOG[tool_name]["requires"]
                if dep not in documents
            ]
            rejected.append(
                {"tool": tool_name, "reason": f"Missing dependencies: {missing}"}
            )
            continue

        approved_tools.append(tool_name)

    updated_plan = {**plan, "approved_tools": approved_tools, "rejected_tools": rejected}

    return {"supervisor_plan": updated_plan, "status": "PLAN_VALIDATED"}
