"""
Node 4 — check_completeness (Python / Deterministic)
Compares accepted document types against the required checklist.
Also computes the list of available tools (dependencies met).
"""
from __future__ import annotations


from src.state import ClaimState
from src.config import CHECKLIST, TOOL_CATALOG


def check_completeness(state: ClaimState) -> dict:
    """Evaluate which required documents are present and which tools can run."""
    documents = state.get("documents", {})
    found_types = set(documents.keys())
    required = set(CHECKLIST["required_documents"])

    missing = sorted(required - found_types)
    present = sorted(required & found_types)

    is_complete = len(missing) == 0
    completeness_pct = round(len(present) / len(required) * 100, 1) if required else 100.0

    completeness_result = {
        "is_complete": is_complete,
        "completeness_pct": completeness_pct,
        "required_documents": sorted(required),
        "found_documents": sorted(found_types),
        "present_required": present,
        "missing_documents": missing,
    }

    # Compute which tools have all their dependencies satisfied
    available_tools = []
    blocked_tools = []
    for tool_name, tool_cfg in TOOL_CATALOG.items():
        deps = set(tool_cfg["requires"])
        missing_deps = sorted(deps - found_types)
        if missing_deps:
            blocked_tools.append(
                {
                    "tool": tool_name,
                    "rule_id": tool_cfg["rule_id"],
                    "missing_dependencies": missing_deps,
                    "reason": f"Missing: {', '.join(missing_deps)}",
                }
            )
        else:
            available_tools.append(
                {
                    "name": tool_name,
                    "rule_id": tool_cfg["rule_id"],
                    "requires": tool_cfg["requires"],
                    "description": tool_cfg["description"],
                }
            )

    status = "COMPLETE" if is_complete else "INCOMPLETE"

    return {
        "completeness_result": completeness_result,
        "available_tools": available_tools,
        "blocked_checks": blocked_tools,
        "status": status,
    }
