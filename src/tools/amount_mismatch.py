"""
INVOICE_AMOUNT_MISMATCH_V1 — Invoice Amount Mismatch Check
Compares amounts in the purchase ledger vs. the supplier invoices.
Deducts the positive difference (ledger > invoice) only.

Designed finding: INV-7742 ledger=$52,000, invoice=$50,000 → $2,000 mismatch
"""
from __future__ import annotations


from decimal import Decimal, InvalidOperation
from src.state import ClaimState

RULE_ID = "INVOICE_AMOUNT_MISMATCH_V1"


def _to_decimal(val) -> Decimal | None:
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return None


def check_invoice_amount_mismatch(state: ClaimState) -> dict:
    """
    For each invoice in both the ledger and supplier invoices,
    flag cases where ledger_amount > invoice_amount (over-claimed).
    """
    ledger_doc = state["documents"].get("PURCHASE_LEDGER", {})
    ledger_rows: list[dict] = ledger_doc.get("data", [])

    invoice_doc = state["documents"].get("SUPPLIER_INVOICES", {})
    invoice_rows: list[dict] = invoice_doc.get("data", [])

    # Build lookups by invoice_number
    # Take the first occurrence in each — duplicate check handles repeats
    ledger_map: dict[str, dict] = {}
    for row in ledger_rows:
        inv = str(row.get("invoice_number", "")).strip()
        if inv and inv not in ledger_map:
            ledger_map[inv] = row

    invoice_map: dict[str, dict] = {}
    for row in invoice_rows:
        inv = str(row.get("invoice_number", "")).strip()
        if inv and inv not in invoice_map:
            invoice_map[inv] = row

    findings: list[dict] = []
    finding_counter = len(state.get("integrity_findings", [])) + 1

    # Only compare invoices that appear in both documents
    common_invoices = set(ledger_map.keys()) & set(invoice_map.keys())

    for inv_num in sorted(common_invoices):
        ledger_amount = _to_decimal(ledger_map[inv_num].get("amount"))
        invoice_amount = _to_decimal(invoice_map[inv_num].get("amount"))

        if ledger_amount is None or invoice_amount is None:
            continue

        if ledger_amount != invoice_amount:
            diff = ledger_amount - invoice_amount

            # Only deduct positive differences (ledger shows more than invoiced)
            if diff > Decimal("0"):
                finding = {
                    "finding_id": f"FND-{finding_counter:03d}",
                    "rule_id": RULE_ID,
                    "claim_line_key": inv_num,
                    "financial_treatment": "DEDUCT_DIFFERENCE",
                    "financial_impact": f"{diff:.2f}",
                    "facts": {
                        "invoice_number": inv_num,
                        "ledger_amount": f"{ledger_amount:.2f}",
                        "invoice_amount": f"{invoice_amount:.2f}",
                        "difference": f"{diff:.2f}",
                        "ledger_id": ledger_map[inv_num].get("ledger_id", ""),
                        "supplier_name": invoice_map[inv_num].get("supplier_name", ""),
                    },
                    "evidence": [
                        f"purchase_ledger.xlsx:{ledger_map[inv_num].get('ledger_id', '')}",
                        f"supplier_invoices.xlsx:{inv_num}",
                    ],
                    "description": (
                        f"Invoice {inv_num} shows ${ledger_amount:,.2f} in the purchase ledger "
                        f"but only ${invoice_amount:,.2f} on the supplier invoice. "
                        f"The ${diff:,.2f} difference is flagged for deduction."
                    ),
                }
                findings.append(finding)
                finding_counter += 1

    return {
        "status": "COMPLETED",
        "rule_id": RULE_ID,
        "findings": findings,
        "check_metadata": {
            "tool": "check_invoice_amount_mismatch",
            "rule_id": RULE_ID,
            "invoices_compared": len(common_invoices),
            "mismatches_found": len(findings),
        },
    }
