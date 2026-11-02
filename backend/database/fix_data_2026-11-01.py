"""
database/fix_data_2026-11-01.py — make the database match the college website (2026-11-01).

Team rule: when our data and the college website disagree, the website wins.
Checked on 1 Nov 2026 against the saved website copy (115 pages):

  Physics HOD ........... database = website (Dr. Yogananda H S)        -> nothing to change
  Dean Student Affairs .. database = website "VP & Deans" page
                          (Dr. T G Manjunatha)                         -> nothing to change
  Number of buses ....... database = website (8 buses)                 -> nothing to change
  PIN code .............. database 560119, website 560064              -> KEPT 560119 (team decision, San)
  Seats (intake) ........ database had ONE sample record (CSE: 300 seats, 210 filled, 90 left);
                          the website lists each department's intake    -> REPLACED with the website intake

Run from the backend folder, with the venv active:

    python database/fix_data_2026-11-01.py            -> DRY RUN: shows what would change, writes nothing
    python database/fix_data_2026-11-01.py --apply    -> makes the changes

Before changing anything, --apply saves the old records to
database/fix_data_2026-11-01_before.json, so they can be put back by hand.
The keys (.env) are read from your own .env file; this script never prints them.
The knowledge engine's cache refreshes within 60 s (no restart needed).
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient

# Intake per branch, from the department / faculty pages of saividya.ac.in (copied 31 Oct 2026).
# ISE is left out: it is closed for new admissions from 2026-27 (merged into CSE).
# CSE (Cyber Security), CS (Business Systems) and MBA: intake not given on the website.
WEBSITE_INTAKE = {
    "CSE": (180, "saividya.ac.in/faculty/computer-science-and-engineering"),
    "CSE-AIML": (120, "saividya.ac.in/faculty/artificial-intelligence-and-machine-learning"),
    "CSE-DS": (120, "saividya.ac.in/department/data-science"),
    "ECE": (120, "saividya.ac.in/department/electronics-and-communication-engineering"),
    "Civil": (30, "saividya.ac.in/department/civil-engineering"),
    "Mechanical": (30, "saividya.ac.in/department/mechanical-engineering"),
}
SEATS_NOTE = ("Sanctioned intake as listed on the college website. How many seats are still "
              "available changes during admissions: please ask the admission office.")
BACKUP_FILE = os.path.join(os.path.dirname(__file__), "fix_data_2026-11-01_before.json")


def connect():
    load_dotenv()
    url = os.getenv("MONGODB_URL")
    if not url:
        sys.exit("MONGODB_URL is not set in .env")
    client = MongoClient(url, serverSelectionTimeoutMS=15000)
    return client[os.getenv("DATABASE_NAME", "intellivoice")]


def _jsonable(doc):
    return json.loads(json.dumps(doc, default=lambda v: str(v) if isinstance(v, (ObjectId, datetime)) else v))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="make the changes (default: dry run)")
    args = parser.parse_args()
    db = connect()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    before = {"admissions_seats": []}

    # Seats: replace the sample record(s) with the website intake
    print("\nSeats (intake)")
    old_seats = list(db.admissions.find({"topic": "seats"}))
    for doc in old_seats:
        print(f"   remove old: {doc.get('branch')}  total {doc.get('total_seats')}, "
              f"filled {doc.get('seats_filled')}, available {doc.get('seats_available')}")
        before["admissions_seats"].append(_jsonable(doc))
    new_docs = []
    for branch, (intake, source) in WEBSITE_INTAKE.items():
        new_docs.append({
            "topic": "seats", "branch": branch, "total_seats": intake, "intake": intake, "note": SEATS_NOTE,
            "_meta": {"seed_tag": "website_fix_2026_11_01", "data_status": "verified",
                      "sources": [source], "loaded_at": now},
        })
        print(f"   add: {branch:<11} intake {intake}   ({source})")

    if not args.apply:
        print("\nDRY RUN - nothing was written. Run again with --apply to make these changes.")
        return
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(before, f, ensure_ascii=False, indent=1)
    if old_seats:
        db.admissions.delete_many({"_id": {"$in": [d["_id"] for d in old_seats]}})
    db.admissions.insert_many(new_docs)
    print(f"\nDone. Old records saved in {BACKUP_FILE}. IntelliVoice shows the new data within a minute.")


if __name__ == "__main__":
    main()
