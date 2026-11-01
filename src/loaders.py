"""
ClaimRecon AI — File Loaders & Normalizers
Pure-Python xlsx reader (zipfile + xml.etree) — works without openpyxl.
Falls back to openpyxl if installed (more robust date handling).
"""
from __future__ import annotations


import json
import os
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# ─── xlsx reader ─────────────────────────────────────────────────────────────

def _read_xlsx_pure(path: str) -> list[dict]:
    """Parse an xlsx file to list[dict] using only stdlib (zipfile + xml)."""
    NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()

        # Shared strings table (may not exist)
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in names:
            sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst.findall(f"{NS}si"):
                parts = si.findall(f".//{NS}t")
                shared_strings.append("".join(p.text or "" for p in parts))

        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))

    rows: list[list] = []
    for row_el in sheet.findall(f".//{NS}row"):
        row = []
        for c in row_el.findall(f"{NS}c"):
            cell_type = c.get("t", "")
            is_el = c.find(f"{NS}is/{NS}t")   # inlineStr
            v_el = c.find(f"{NS}v")            # value

            if is_el is not None:
                row.append(is_el.text or "")
            elif v_el is not None:
                if cell_type == "s":
                    row.append(shared_strings[int(v_el.text)])
                else:
                    # Try int → float → string
                    raw = v_el.text or ""
                    try:
                        val = int(raw) if "." not in raw else float(raw)
                    except ValueError:
                        val = raw
                    row.append(val)
            else:
                row.append("")
        rows.append(row)

    if not rows:
        return []

    headers = [str(h) for h in rows[0]]
    return [dict(zip(headers, r)) for r in rows[1:] if any(str(v).strip() for v in r)]


def load_xlsx(path: str) -> list[dict]:
    """Load an xlsx file. Uses openpyxl if available, otherwise pure stdlib."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h) for h in rows[0]]
        return [
            dict(zip(headers, row))
            for row in rows[1:]
            if any(v is not None and str(v).strip() for v in row)
        ]
    except ImportError:
        return _read_xlsx_pure(path)


def load_json(path: str) -> dict:
    """Load a JSON file and return as dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Claim normalizer ─────────────────────────────────────────────────────────

def normalize_claim(raw: dict) -> dict:
    """Ensure the claim dict has all required fields with correct types."""
    return {
        "claim_profile": raw.get("claim_profile", "UNKNOWN"),
        "checklist_id": raw.get("checklist_id", ""),
        "insured": raw.get("insured", ""),
        "loss_date": raw.get("loss_date", ""),
        "claimed_stock_amount": str(raw.get("claimed_stock_amount", "0")),
        "status": raw.get("status", ""),
        "currency": raw.get("currency", "USD"),  # default USD
    }


# ─── File inventory ───────────────────────────────────────────────────────────

def read_file_inventory(folder: str) -> list[dict]:
    """Return a list of file metadata dicts for all files in the folder."""
    inventory = []
    for entry in sorted(Path(folder).iterdir()):
        if entry.is_file() and not entry.name.startswith("."):
            inventory.append(
                {
                    "filename": entry.name,
                    "path": str(entry.resolve()),
                    "extension": entry.suffix.lower(),
                    "size_bytes": entry.stat().st_size,
                }
            )
    return inventory


# ─── Sample rows helper ───────────────────────────────────────────────────────

def get_sample_rows(rows: list[dict], n: int = 7) -> list[dict]:
    """Return up to n rows with None/empty values converted to empty strings."""
    samples = []
    for row in rows[:n]:
        samples.append(
            {k: ("" if v is None else v) for k, v in row.items()}
        )
    return samples
