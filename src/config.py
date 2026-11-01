"""
ClaimRecon AI — Business Configuration
Hardcoded checklist and tool catalog from Sections 3 & 8 of the Blueprint.
These are business rules — not LLM decisions.
"""

# ─── Required Document Checklist ─────────────────────────────────────────────
CHECKLIST = {
    "checklist_id": "COMMERCIAL_PROPERTY_FIRE_STOCK_V1",
    "required_documents": [
        "CLAIM_FORM",
        "FIRE_REPORT",
        "PURCHASE_LEDGER",
        "SUPPLIER_INVOICES",
        "DELIVERY_RECORDS",
    ],
}

# ─── Approved Document Types ──────────────────────────────────────────────────
# The LLM may only classify files into these types.
# GOODS_RECEIPT is optional evidence — not in the required checklist.
ALLOWED_DOCUMENT_TYPES = [
    "CLAIM_FORM",
    "FIRE_REPORT",
    "PURCHASE_LEDGER",
    "SUPPLIER_INVOICES",
    "DELIVERY_RECORDS",
    "GOODS_RECEIPT",   # optional
    "UNKNOWN",
]

# ─── Approved Tool Catalog ────────────────────────────────────────────────────
# Section 3 — rule dependencies.
# Section 8 — available_tools list passed to the Supervisor.
TOOL_CATALOG = {
    "check_duplicate_invoices": {
        "rule_id": "DUPLICATE_INVOICE_V1",
        "requires": ["PURCHASE_LEDGER"],
        "description": "Detects the same invoice appearing more than once in the purchase ledger.",
    },
    "check_delivery_after_loss": {
        "rule_id": "DELIVERY_AFTER_LOSS_V1",
        "requires": ["FIRE_REPORT", "DELIVERY_RECORDS", "PURCHASE_LEDGER"],
        "description": "Flags goods delivered after the loss date.",
    },
    "check_invoice_amount_mismatch": {
        "rule_id": "INVOICE_AMOUNT_MISMATCH_V1",
        "requires": ["PURCHASE_LEDGER", "SUPPLIER_INVOICES"],
        "description": "Flags invoices where the ledger amount differs from the supplier invoice amount.",
    },
}

# ─── Configured Rule IDs ──────────────────────────────────────────────────────
# Derived from the catalog — used by evaluate_completion.
CONFIGURED_RULE_IDS = {v["rule_id"] for v in TOOL_CATALOG.values()}

# ─── Classification confidence threshold ─────────────────────────────────────
MIN_CLASSIFICATION_CONFIDENCE = 0.50

# ─── Supervisor loop guard ────────────────────────────────────────────────────
MAX_PLANNING_ITERATIONS = 2

