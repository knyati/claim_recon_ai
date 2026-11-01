"""
Node 5 — supervisor_plan (LLM)
The Supervisor observes evidence availability and prior check status,
then selects tools from the fixed approved catalog.
Uses plain JSON output for reliability across all providers.
"""
from __future__ import annotations

import json
import re
from src.state import ClaimState
from src.config import MAX_PLANNING_ITERATIONS
from src.llm_factory import get_llm


SYSTEM_PROMPT = """You are the Claims Investigation Supervisor for ClaimRecon AI.
Select which approved integrity checks to run based on available evidence.

Return ONLY a valid JSON object — no markdown fences, no explanation. Schema:
{
  "selected_tools": [{"tool": "<tool_name>", "reason": "<one sentence>"}],
  "blocked_tools":  [{"tool": "<tool_name>", "reason": "<one sentence>"}],
  "next_action": "EXECUTE_AVAILABLE_CHECKS" | "SKIP_ALL"
}

Rules:
- Only select tools from the available_tools list provided.
- Do not select tools whose dependencies are not met.
- Do not re-select checks already in completed_checks.
- Set next_action to EXECUTE_AVAILABLE_CHECKS if there are selected_tools, else SKIP_ALL.
- You may NOT create new tools, modify evidence, or make coverage decisions.
- Return ONLY the JSON object. No markdown, no extra text.
"""


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def supervisor_plan(state: ClaimState) -> dict:
    """LLM Supervisor selects approved tools based on available evidence."""
    iteration = state.get("planning_iteration", 0)

    # ── Loop guard ────────────────────────────────────────────────────────────
    if iteration >= MAX_PLANNING_ITERATIONS:
        plan = {
            "selected_tools": [],
            "blocked_tools": [],
            "next_action": "SKIP_ALL",
            "iteration": iteration,
            "guard_triggered": True,
        }
        return {
            "supervisor_plan": plan,
            "planning_iteration": iteration + 1,
            "status": "SUPERVISOR_GUARD_TRIGGERED",
        }

    documents = state.get("documents", {})
    available_tools = state.get("available_tools", [])
    completed_checks = state.get("completed_checks", [])

    llm_input = {
        "available_documents": sorted(documents.keys()),
        "completed_checks": completed_checks,
        "available_tools": [
            {
                "name": t["name"],
                "requires": t["requires"],
                "description": t.get("description", ""),
            }
            for t in available_tools
            if t["rule_id"] not in completed_checks
        ],
    }

    human_prompt = (
        "Select integrity checks to run:\n"
        + json.dumps(llm_input, indent=2)
    )

    llm = get_llm()

    try:
        response = llm.invoke(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": human_prompt},
            ]
        )
        raw_text = response.content if hasattr(response, "content") else str(response)
        plan = _parse_json_response(raw_text)
        # Ensure required keys exist
        plan.setdefault("selected_tools", [])
        plan.setdefault("blocked_tools", [])
        plan.setdefault("next_action", "EXECUTE_AVAILABLE_CHECKS" if plan["selected_tools"] else "SKIP_ALL")
    except Exception as e:
        # Fallback: run all available tools
        plan = {
            "selected_tools": [
                {"tool": t["name"], "reason": "LLM unavailable — auto-selected"}
                for t in available_tools
                if t["rule_id"] not in completed_checks
            ],
            "blocked_tools": [],
            "next_action": "EXECUTE_AVAILABLE_CHECKS",
            "fallback_reason": str(e),
        }

    plan["iteration"] = iteration

    return {
        "supervisor_plan": plan,
        "planning_iteration": iteration + 1,
        "status": "PLANNED",
    }
