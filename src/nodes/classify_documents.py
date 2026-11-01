"""
Node 2 — classify_documents (LLM with thread-timeout + rule-based fallback)

The LLM call runs in a daemon thread with a 25s timeout.
If it times out or fails for any reason, a fast rule-based classifier
(filename + column keywords) takes over — guaranteeing the pipeline
always completes, even with a slow/unavailable LLM.
"""
from __future__ import annotations

import json
import re
import threading
from src.state import ClaimState
from src.config import ALLOWED_DOCUMENT_TYPES
from src.loaders import get_sample_rows
from src.llm_factory import get_llm

LLM_TIMEOUT_SECONDS = 25

# ─── Rule-based fallback ──────────────────────────────────────────────────────
KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["claim_information", "claim_info", "checklist_id", "claimed_stock"], "CLAIM_FORM"),
    (["fire_report", "fire", "incident_date", "cause"],                    "FIRE_REPORT"),
    (["purchase_ledger", "ledger", "ledger_id", "date_entered"],           "PURCHASE_LEDGER"),
    (["supplier_invoice", "invoice_number", "supplier_name", "issue_date"],"SUPPLIER_INVOICES"),
    (["delivery_record", "delivery", "dispatch_reference", "delivered_on"],"DELIVERY_RECORDS"),
    (["goods_receipt", "receipt", "receipt_id", "receipt_date"],           "GOODS_RECEIPT"),
]

def _rule_based_classify(fname: str, columns: list, keys: list) -> tuple[str, float, str]:
    haystack = (fname + " " + " ".join(columns) + " " + " ".join(keys)).lower()
    for keywords, doc_type in KEYWORD_RULES:
        matches = [kw for kw in keywords if kw in haystack]
        if matches:
            conf = min(0.5 + 0.1 * len(matches), 0.95)
            return doc_type, conf, f"Rule-based: matched {matches}"
    return "UNKNOWN", 0.0, "No keyword rules matched"

# ─── LLM prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a document classifier for insurance claim packages.
Classify EACH file. Return ONLY a valid JSON array, no markdown.
ALLOWED TYPES: {json.dumps(ALLOWED_DOCUMENT_TYPES)}
Each element: {{"filename":"<exact>","document_type":"<type>","confidence":<0-1>,"reason":"<one sentence>","column_mapping":{{}},"requires_human_review":<bool>}}
Same order as input. Return ONLY the JSON array."""

def _build_context(file_info: dict, norm_data: dict) -> dict:
    fname = file_info["filename"]
    ext   = file_info["extension"]
    stem  = fname.replace(ext, "")
    raw   = norm_data.get(stem, {})
    if ext == ".xlsx" and isinstance(raw, list):
        cols = list(raw[0].keys()) if raw else []
        return {"filename": fname, "type": "xlsx", "columns": cols,
                "sample_rows": get_sample_rows(raw, n=2)}
    elif ext == ".json" and isinstance(raw, dict):
        return {"filename": fname, "type": "json", "keys": list(raw.keys()),
                "sample": {k: v for k, v in list(raw.items())[:3]}}
    return {"filename": fname, "type": ext}

def _parse(text: str) -> list:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())

def _llm_classify(contexts: list, result_holder: list, error_holder: list) -> None:
    """Run in a daemon thread — puts result in result_holder or error in error_holder."""
    try:
        llm = get_llm()
        human = (f"Classify these {len(contexts)} files. "
                 f"Return a JSON array with {len(contexts)} entries.\n\n"
                 + json.dumps(contexts, indent=2, default=str))
        resp = llm.invoke([{"role": "system", "content": SYSTEM_PROMPT},
                           {"role": "user",   "content": human}])
        raw_text = resp.content if hasattr(resp, "content") else str(resp)
        result_holder.append(_parse(raw_text))
    except Exception as e:
        error_holder.append(str(e))


def classify_documents(state: ClaimState) -> dict:
    inventory = state["file_inventory"]
    norm_data = state["normalized_data"]
    path_map  = {f["filename"]: f["path"] for f in inventory}
    contexts  = [_build_context(f, norm_data) for f in inventory]

    # ── LLM attempt (thread-based timeout) ───────────────────────────────────
    result_holder: list = []
    error_holder:  list = []

    t = threading.Thread(
        target=_llm_classify,
        args=(contexts, result_holder, error_holder),
        daemon=True,
    )
    t.start()
    t.join(timeout=LLM_TIMEOUT_SECONDS)

    llm_results: list[dict] = []
    classified_by = "rule_based"

    if result_holder:
        # LLM returned in time — validate entries
        classified_by = "llm"
        for item in result_holder[0]:
            if not isinstance(item, dict):
                continue
            fname    = item.get("filename", "")
            doc_type = item.get("document_type", "UNKNOWN")
            if doc_type not in ALLOWED_DOCUMENT_TYPES:
                doc_type = "UNKNOWN"
            llm_results.append({
                "filename":             fname,
                "document_type":        doc_type,
                "confidence":           float(item.get("confidence", 0.0)),
                "reason":               str(item.get("reason", "")),
                "column_mapping":       item.get("column_mapping", {}),
                "requires_human_review": bool(item.get("requires_human_review",
                                                       doc_type == "UNKNOWN")),
                "path":                 path_map.get(fname, ""),
                "classified_by":        "llm",
            })

    # ── Rule-based fallback for any file not in LLM results ──────────────────
    llm_fnames = {c["filename"] for c in llm_results}
    rule_results: list[dict] = []

    for f_info in inventory:
        fname = f_info["filename"]
        if fname in llm_fnames:
            continue
        ext  = f_info["extension"]
        stem = fname.replace(ext, "")
        raw  = norm_data.get(stem, {})
        cols = list(raw[0].keys()) if isinstance(raw, list) and raw else []
        keys = list(raw.keys())    if isinstance(raw, dict) else []

        doc_type, conf, reason = _rule_based_classify(fname, cols, keys)
        rule_results.append({
            "filename":             fname,
            "document_type":        doc_type,
            "confidence":           conf,
            "reason":               reason,
            "column_mapping":       {},
            "requires_human_review": conf < 0.5 or doc_type == "UNKNOWN",
            "path":                 f_info["path"],
            "classified_by":        classified_by,
        })

    classifications = llm_results + rule_results
    return {"document_classifications": classifications, "status": "CLASSIFIED"}
