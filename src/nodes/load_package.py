"""
Node 1 — load_claim_package (Python / Deterministic)
Reads all files from the claim folder, builds the file inventory,
and loads + normalizes data into shared state.
"""
from __future__ import annotations


import uuid
from src.state import ClaimState
from src.config import CHECKLIST
from src.loaders import (
    load_json,
    load_xlsx,
    normalize_claim,
    read_file_inventory,
)


def load_claim_package(state: ClaimState) -> dict:
    """Load all documents from the claim folder into normalized state."""
    folder = state["claim_folder"]

    # 1. Scan the folder for all files
    inventory = read_file_inventory(folder)

    # 2. Separate by extension for loading
    json_files = {f["filename"]: f["path"] for f in inventory if f["extension"] == ".json"}
    xlsx_files = {f["filename"]: f["path"] for f in inventory if f["extension"] == ".xlsx"}

    # 3. Load claim info JSON (the OCR form)
    claim_raw = {}
    for fname, path in json_files.items():
        if "claim_information" in fname.lower() or "claim_info" in fname.lower():
            claim_raw = load_json(path)
            break

    claim = normalize_claim(claim_raw)

    # 4. Load all data files into normalized_data keyed by filename stem
    normalized_data: dict = {}

    for fname, path in json_files.items():
        stem = fname.replace(".json", "")
        raw = load_json(path)
        normalized_data[stem] = raw   # dicts stay as dicts

    for fname, path in xlsx_files.items():
        stem = fname.replace(".xlsx", "")
        rows = load_xlsx(path)
        normalized_data[stem] = rows  # list[dict]

    return {
        "run_id": str(uuid.uuid4()),
        "claim_folder": folder,
        "checklist_id": CHECKLIST["checklist_id"],
        "claim": claim,
        "file_inventory": inventory,
        "normalized_data": normalized_data,
        "planning_iteration": 0,
        "completed_checks": [],
        "blocked_checks": [],
        "failed_checks": [],
        "integrity_findings": [],
        "status": "LOADED",
    }
