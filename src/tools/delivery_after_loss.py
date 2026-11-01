"""
DELIVERY_AFTER_LOSS_V1 — Post-Loss Delivery Check
Flags goods delivered after the loss date. Cross-references:
  - fire_report.json → loss_date
  - delivery_records.xlsx → delivered_on / related_invoice
  - purchase_ledger.xlsx → amount for the flagged invoice

Designed finding: INV-9102 delivered 2026-08-17, loss was 2026-08-15 → $24,000
"""
from __future__ import annotations


from datetime import date
from src.state import ClaimState

RULE_ID = "DELIVERY_AFTER_LOSS_V1"


def _parse_date(val) -> date | None:
    """Parse a date string or date object safely."""
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val).strip())
    except (ValueError, TypeError):
        return None


def check_delivery_after_loss(state: ClaimState) -> dict:
    """
    Flag deliveries that occurred after the loss date.
    The financial impact is the ledger amount for the affected invoice.
    """
    # Load required documents
    fire_doc = state["documents"].get("FIRE_REPORT", {})
    fire_data: dict = fire_doc.get("data", {})
    loss_date = _parse_date(fire_data.get("loss_date"))

    delivery_doc = state["documents"].get("DELIVERY_RECORDS", {})
    delivery_rows: list[dict] = delivery_doc.get("data", [])

    ledger_doc = state["documents"].get("PURCHASE_LEDGER", {})
    ledger_rows: list[dict] = ledger_doc.get("data", [])

    if not loss_date:
        return {
            "status": "FAILED",
            "rule_id": RULE_ID,
            "findings": [],
            "error": "Could not parse loss_date from fire report",
        }

    # Build a lookup: invoice_number → ledger rows (may have multiple)
    ledger_map: dict[str, list[dict]] = {}
    for row in ledger_rows:
        inv = str(row.get("invoice_number", "")).strip()
        if inv:
            ledger_map.setdefault(inv, []).append(row)

    findings: list[dict] = []
    finding_counter = len(state.get("integrity_findings", [])) + 1

    for delivery in delivery_rows:
        delivered_on = _parse_date(delivery.get("delivered_on"))
        related_inv = str(delivery.get("related_invoice", "")).strip()

        if not delivered_on or not related_inv:
            continue

        if delivered_on > loss_date:
            # Find the corresponding ledger amount
            ledger_entries = ledger_map.get(related_inv, [])
            amount = float(ledger_entries[0].get("amount", 0)) if ledger_entries else 0.0
            dispatch_ref = str(delivery.get("dispatch_reference", "")).strip()

            finding = {
                "finding_id": f"FND-{finding_counter:03d}",
                "rule_id": RULE_ID,
                "claim_line_key": related_inv,
                "financial_treatment": "DEDUCT_FULL_LINE",
                "financial_impact": f"{amount:.2f}",
                "facts": {
                    "loss_date": str(loss_date),
                    "delivery_date": str(delivered_on),
                    "days_after_loss": (delivered_on - loss_date).days,
                    "dispatch_reference": dispatch_ref,
                    "invoice_number": related_inv,
                    "amount": amount,
                },
                "evidence": [
                    "fire_report.json:loss_date",
                    f"delivery_records.xlsx:{dispatch_ref}",
                ],
                "description": (
                    f"Invoice {related_inv} has a delivery date ({delivered_on}) "
                    f"that is {(delivered_on - loss_date).days} day(s) after "
                    f"the loss date ({loss_date}). The full line amount of "
                    f"${amount:,.2f} is flagged for deduction."
                ),
            }
            findings.append(finding)
            finding_counter += 1

    return {
        "status": "COMPLETED",
        "rule_id": RULE_ID,
        "findings": findings,
        "check_metadata": {
            "tool": "check_delivery_after_loss",
            "rule_id": RULE_ID,
            "loss_date": str(loss_date),
            "deliveries_scanned": len(delivery_rows),
            "post_loss_deliveries": len(findings),
        },
    }
