"""
ClaimRecon AI — Shared LangGraph State Definition
Matches Section 5 of the Technical Blueprint exactly.
"""

from __future__ import annotations
from typing import TypedDict, Union, List, Dict, Any, Optional


class ClaimState(TypedDict, total=False):
    run_id: str
    claim_folder: str
    checklist_id: str
    claim: Dict[str, Any]
    file_inventory: List[Dict[str, Any]]
    document_classifications: List[Dict[str, Any]]
    documents: Dict[str, Dict[str, Any]]   # keyed by doc type e.g. "PURCHASE_LEDGER"
    normalized_data: Dict[str, Any]        # tabular → list[dict], json → dict
    completeness_result: Dict[str, Any]
    available_tools: List[Dict[str, Any]]
    supervisor_plan: Dict[str, Any]
    completed_checks: List[str]            # rule_ids that finished successfully
    blocked_checks: List[Dict[str, Any]]   # [{rule_id, missing_dependencies}]
    failed_checks: List[Dict[str, Any]]    # [{rule_id, error}]
    integrity_findings: List[Dict[str, Any]]  # FND-001, FND-002, FND-003 …
    check_evaluation: Dict[str, Any]
    financial_summary: Dict[str, Any]
    investigator_summary: Dict[str, Any]
    planning_iteration: int
    status: str
