"""
utils/datasets.py — which MongoDB collections the admin can update by Excel,
and the rules each row must follow.

Each dataset says:
  collection   MongoDB collection name (must match intents.json knowledge_collection)
  key_fields   columns that identify ONE record (used to find "same record, new value")
  columns      every column in the Excel sheet, its type and rules
  row_check    extra rules that involve several columns (optional)

Column types:
  "choice" -> must be one of the allowed values (aliases from entities.json accepted,
              e.g. "computer science" becomes "CSE")
  "int"    -> whole number; "3,25,000", "₹325000" and 325000.0 are all accepted
  "text"   -> any text; optional regex `pattern`

To add a new dataset later (e.g. cutoffs), copy the "fees" block, change the
collection, key_fields and columns to match that collection's documents, and
the template / upload / preview / undo all work for it automatically.
"""

import json
import os

_ENTITIES_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "seed_data", "entities.json")
with open(_ENTITIES_PATH, encoding="utf-8") as f:
    ENTITIES = json.load(f)


def entity_choices(entity_type: str) -> dict:
    """{canonical_value: [aliases]} for one entity type from entities.json."""
    values = ENTITIES.get(entity_type, {})
    return {k: v for k, v in values.items() if k != "note" and isinstance(v, list)}


# ── extra multi-column rules ───────────────────────────────────────────────
def _fees_row_check(row: dict) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings) for one fees row."""
    errors, warnings = [], []

    has_exam, has_quota = bool(row.get("exam")), bool(row.get("quota"))
    if has_exam == has_quota:
        errors.append("Fill exactly one of 'exam' (KCET/COMEDK) or 'quota' (Management/NRI/Government), not both or neither")

    annual, sem, inst = row.get("annual_fee"), row.get("semester_fee"), row.get("installments")
    if annual and sem and inst and sem * inst != annual:
        warnings.append(f"semester_fee × installments = {sem * inst:,}, but annual_fee is {annual:,}. Please double-check")

    early = row.get("early_bird_fee")
    if early and annual and early > annual:
        warnings.append(f"early_bird_fee ({early:,}) is higher than annual_fee ({annual:,})")
    return errors, warnings


DATASETS = {
    "fees": {
        "collection": "fees",
        "title": "Fee Structure",
        "key_fields": ["branch", "exam", "quota", "academic_year"],
        "columns": [
            {"field": "branch", "type": "choice", "required": True,
             "choices": entity_choices("branch"), "help": "e.g. CSE, CSE-AIML, ECE"},
            {"field": "exam", "type": "choice", "required": False,
             "choices": entity_choices("exam"), "help": "KCET or COMEDK (leave empty for management/NRI seats)"},
            {"field": "quota", "type": "choice", "required": False,
             "choices": entity_choices("quota"), "help": "Management / NRI / Government (leave empty for KCET/COMEDK rows)"},
            {"field": "academic_year", "type": "text", "required": True,
             "pattern": r"^\d{4}-\d{2}$", "help": "Format 2026-27"},
            {"field": "annual_fee", "type": "int", "required": True, "min": 1000, "max": 5000000,
             "help": "Rupees per year, numbers only"},
            {"field": "semester_fee", "type": "int", "required": True, "min": 1000, "max": 5000000,
             "help": "Amount per installment"},
            {"field": "early_bird_fee", "type": "int", "required": False, "min": 1000, "max": 5000000,
             "help": "Optional discounted fee"},
            {"field": "payment_mode", "type": "choice", "required": True,
             "choices": {"Semester-wise": ["semester wise", "semesterwise"], "One-time": ["one time", "onetime"]},
             "help": "Semester-wise or One-time"},
            {"field": "installments", "type": "int", "required": True, "min": 1, "max": 12,
             "help": "Number of payments per year"},
        ],
        "row_check": _fees_row_check,
    },
}

# Numbers that change by more than this fraction get a "please check" warning
BIG_CHANGE_RATIO = 0.30


def get_dataset(name: str) -> dict | None:
    return DATASETS.get(name)
