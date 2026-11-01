"""
ClaimRecon AI — LangGraph Pipeline
Wires all 10 nodes into the StateGraph with conditional routing.
Section 4 & 15 of the blueprint.
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

from langgraph.graph import StateGraph, END

from src.state import ClaimState
from src.nodes.load_package import load_claim_package
from src.nodes.classify_documents import classify_documents
from src.nodes.validate_classification import validate_classification
from src.nodes.check_completeness import check_completeness
from src.nodes.supervisor_plan import supervisor_plan
from src.nodes.validate_plan import validate_plan
from src.nodes.execute_checks import execute_checks
from src.nodes.evaluate_completion import evaluate_completion
from src.nodes.calculate_amounts import (
    calculate_supported_amount,
    calculate_partial_result,
)
from src.nodes.generate_summary import generate_summary


# ─── Conditional router ────────────────────────────────────────────────────────

def route_after_evaluation(state: ClaimState) -> str:
    """Map next_action from evaluate_completion to a node name."""
    next_action = state.get("check_evaluation", {}).get("next_action", "PROCESSING_REVIEW")
    routes = {
        "CONTINUE_INVESTIGATION":      "supervisor_plan",
        "CALCULATE_SUPPORTED_AMOUNT":  "calculate_supported_amount",
        "CALCULATE_PARTIAL_RESULT":    "calculate_partial_result",
        "PROCESSING_REVIEW":           "generate_summary",
        "SKIP_ALL":                    "generate_summary",  # guard-triggered
    }
    return routes.get(next_action, "generate_summary")


# ─── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and compile the ClaimRecon AI LangGraph pipeline."""
    builder = StateGraph(ClaimState)

    # ── Register all nodes ────────────────────────────────────────────────────
    builder.add_node("load_claim_package",       load_claim_package)
    builder.add_node("classify_documents",       classify_documents)
    builder.add_node("validate_classification",  validate_classification)
    builder.add_node("check_completeness",       check_completeness)
    builder.add_node("supervisor_plan",          supervisor_plan)
    builder.add_node("validate_plan",            validate_plan)
    builder.add_node("execute_checks",           execute_checks)
    builder.add_node("evaluate_completion",      evaluate_completion)
    builder.add_node("calculate_supported_amount", calculate_supported_amount)
    builder.add_node("calculate_partial_result",   calculate_partial_result)
    builder.add_node("generate_summary",           generate_summary)

    # ── Entry point ───────────────────────────────────────────────────────────
    builder.set_entry_point("load_claim_package")

    # ── Linear edges ──────────────────────────────────────────────────────────
    builder.add_edge("load_claim_package",      "classify_documents")
    builder.add_edge("classify_documents",      "validate_classification")
    builder.add_edge("validate_classification", "check_completeness")
    builder.add_edge("check_completeness",      "supervisor_plan")
    builder.add_edge("supervisor_plan",         "validate_plan")
    builder.add_edge("validate_plan",           "execute_checks")
    builder.add_edge("execute_checks",          "evaluate_completion")

    # ── Conditional routing from evaluate_completion ──────────────────────────
    builder.add_conditional_edges(
        "evaluate_completion",
        route_after_evaluation,
        {
            "supervisor_plan":            "supervisor_plan",
            "calculate_supported_amount": "calculate_supported_amount",
            "calculate_partial_result":   "calculate_partial_result",
            "generate_summary":           "generate_summary",
        },
    )

    # ── Terminal edges ─────────────────────────────────────────────────────────
    builder.add_edge("calculate_supported_amount", "generate_summary")
    builder.add_edge("calculate_partial_result",   "generate_summary")
    builder.add_edge("generate_summary",           END)

    return builder.compile()
