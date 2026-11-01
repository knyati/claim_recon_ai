"""
DUPLICATE_INVOICE_V1 — Duplicate Invoice Check
Detects the same invoice_number appearing more than once in the purchase ledger.
Designed finding: INV-5521 appears in PL-1001 and PL-1092 → $38,000 deduction.
"""
from __future__ import annotations


from src.state import ClaimState

RULE_ID = "DUPLICATE_INVOICE_V1"


def check_duplicate_invoices(state: ClaimState) -> dict:
    """
    Scan the purchase ledger for duplicate invoice numbers.
    Returns a result dict with status, findings, and check metadata.
    """
    ledger_doc = state["documents"].get("PURCHASE_LEDGER", {})
    ledger_rows: list[dict] = ledger_doc.get("data", [])

    seen: dict[str, dict] = {}   # invoice_number → first ledger row
    findings: list[dict] = []
    finding_counter = len(state.get("integrity_findings", [])) + 1

    for row in ledger_rows:
        inv_num = str(row.get("invoice_number", "")).strip()
        if not inv_num:
            continue

        if inv_num in seen:
            first_row = seen[inv_num]
            amount = float(row.get("amount", 0) or 0)

            finding = {
                "finding_id": f"FND-{finding_counter:03d}",
                "rule_id": RULE_ID,
                "claim_line_key": inv_num,
                "financial_treatment": "DEDUCT_FULL_LINE",
                "financial_impact": f"{amount:.2f}",
                "facts": {
                    "first_occurrence": first_row.get("ledger_id", ""),
                    "duplicate_occurrence": row.get("ledger_id", ""),
                    "invoice_number": inv_num,
                    "amount": amount,
                },
                "evidence": [
                    f"purchase_ledger.xlsx:{first_row.get('ledger_id', '')}",
                    f"purchase_ledger.xlsx:{row.get('ledger_id', '')}",
                ],
                "description": (
                    f"Invoice {inv_num} appears more than once in the purchase ledger. "
                    f"The duplicate entry ({row.get('ledger_id', '')}) is flagged for deduction."
                ),
            }
            findings.append(finding)
            finding_counter += 1
        else:
            seen[inv_num] = row

    status = "COMPLETED"
    return {
        "status": status,
        "rule_id": RULE_ID,
        "findings": findings,
        "check_metadata": {
            "tool": "check_duplicate_invoices",
            "rule_id": RULE_ID,
            "records_scanned": len(ledger_rows),
            "duplicates_found": len(findings),
        },
    }
