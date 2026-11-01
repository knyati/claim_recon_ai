"""
Node 10 — generate_summary (LLM)
Generates a human-readable investigator summary from verified structured output.
Uses plain JSON output for reliability. Falls back to deterministic template.
"""
from __future__ import annotations

import json
import re
from src.state import ClaimState
from src.llm_factory import get_llm


SYSTEM_PROMPT = """You are a claims investigation assistant generating a factual summary
for a human investigator reviewing a commercial property fire stock claim.

Return ONLY a valid JSON object — no markdown fences, no explanation. Schema:
{
  "executive_summary": "<2-3 sentence factual summary>",
  "recommended_actions": ["<action 1>", "<action 2>", "<action 3>"],
  "disclaimer": "This output supports investigation and does not approve, deny, or determine coverage."
}

STRICT RULES:
1. Do NOT modify any amounts, statuses, finding IDs, or evidence.
2. Do NOT use the word "fraud" or make any fraud determination.
3. Do NOT approve, deny, or determine coverage or payability.
4. Do NOT add findings not in the structured input.
5. The disclaimer must be exactly: "This output supports investigation and does not approve, deny, or determine coverage."
6. Return ONLY the JSON object. No markdown, no extra text.
"""

FALLBACK_DISCLAIMER = (
    "This output supports investigation and does not approve, deny, or determine coverage."
)


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def _build_fallback_summary(state: ClaimState) -> dict:
    """Deterministic template used when LLM is unavailable."""
    fs = state.get("financial_summary", {})
    findings = state.get("integrity_findings", [])
    claim = state.get("claim", {})
    is_complete = fs.get("calculation_complete", False)

    if is_complete:
        summary = (
            f"Review of claim {claim.get('claim_profile', '')} for "
            f"{claim.get('insured', '')} is complete. "
            f"{len(findings)} integrity finding(s) identified. "
            f"Claimed: ${float(fs.get('claimed_amount', 0)):,.2f}. "
            f"Supported: ${float(fs.get('supported_amount', 0)):,.2f}. "
            f"Unsupported: ${float(fs.get('unsupported_amount', 0)):,.2f}."
        )
    else:
        summary = (
            f"Partial review of claim {claim.get('claim_profile', '')} completed. "
            f"{len(findings)} finding(s) from completed checks. "
            f"Definitive supported amount cannot be calculated — some checks blocked."
        )

    actions = [
        f"Review {f.get('finding_id')} for invoice {f.get('claim_line_key')}: {f.get('description', '')}"
        for f in findings
    ] or ["No integrity findings. Proceed with standard claim processing."]

    return {
        "executive_summary": summary,
        "recommended_actions": actions,
        "disclaimer": FALLBACK_DISCLAIMER,
        "generated_by": "fallback_template",
    }


def generate_summary(state: ClaimState) -> dict:
    """Generate the investigator summary using LLM with a deterministic fallback."""
    financial_summary = state.get("financial_summary", {})
    check_evaluation = state.get("check_evaluation", {})
    findings = state.get("integrity_findings", [])
    claim = state.get("claim", {})

    llm_input = {
        "claim_profile": claim.get("claim_profile"),
        "insured": claim.get("insured"),
        "loss_date": claim.get("loss_date"),
        "claimed_amount": financial_summary.get("claimed_amount"),
        "supported_amount": financial_summary.get("supported_amount"),
        "identified_unsupported_amount": financial_summary.get(
            "identified_unsupported_amount",
            financial_summary.get("unsupported_amount"),
        ),
        "calculation_complete": financial_summary.get("calculation_complete"),
        "check_summary": check_evaluation.get("check_summary", {}),
        "integrity_findings": [
            {
                "finding_id": f.get("finding_id"),
                "rule_id": f.get("rule_id"),
                "claim_line_key": f.get("claim_line_key"),
                "financial_impact": f.get("financial_impact"),
                "description": f.get("description"),
            }
            for f in findings
        ],
        "blocked_checks": check_evaluation.get("blocked_checks", []),
    }

    human_prompt = (
        "Generate an investigator summary for this claim review:\n"
        + json.dumps(llm_input, indent=2, default=str)
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
        summary = _parse_json_response(raw_text)
        summary["generated_by"] = "llm"
    except Exception as e:
        summary = _build_fallback_summary(state)
        summary["llm_error"] = str(e)

    return {"investigator_summary": summary, "status": "SUMMARY_READY"}
