"""
Node 3 — validate_classification (Python / Deterministic)
Validates LLM classifications against the allowed type list and
confidence threshold. Builds the `documents` dict keyed by doc type.
"""
from __future__ import annotations


from src.state import ClaimState
from src.config import ALLOWED_DOCUMENT_TYPES, MIN_CLASSIFICATION_CONFIDENCE


def validate_classification(state: ClaimState) -> dict:
    """
    Accept high-confidence classifications, reject unknowns and low-confidence
    results, and build the `documents` dict for downstream nodes.
    """
    classifications = state["document_classifications"]
    normalized_data = state["normalized_data"]

    documents: dict = {}
    validated: list[dict] = []

    for cls in classifications:
        doc_type = cls.get("document_type", "UNKNOWN")
        confidence = cls.get("confidence", 0.0)
        fname = cls.get("filename", "")
        ext = "." + fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        stem = fname.replace(ext, "")

        # Reject types not in the allowed list
        if doc_type not in ALLOWED_DOCUMENT_TYPES or doc_type == "UNKNOWN":
            cls["validation_status"] = "REJECTED_UNKNOWN_TYPE"
            cls["requires_human_review"] = True
            validated.append(cls)
            continue

        # Reject low-confidence classifications
        if confidence < MIN_CLASSIFICATION_CONFIDENCE:
            cls["validation_status"] = "REJECTED_LOW_CONFIDENCE"
            cls["requires_human_review"] = True
            validated.append(cls)
            continue

        # Accept — add to documents dict
        # If multiple files map to the same type, keep the highest confidence one
        if doc_type not in documents or confidence > documents[doc_type]["confidence"]:
            raw_data = normalized_data.get(stem)
            documents[doc_type] = {
                "filename": fname,
                "path": cls.get("path", ""),
                "confidence": confidence,
                "column_mapping": cls.get("column_mapping", {}),
                "data": raw_data,
            }

        cls["validation_status"] = "ACCEPTED"
        validated.append(cls)

    return {
        "document_classifications": validated,
        "documents": documents,
        "status": "VALIDATED",
    }
