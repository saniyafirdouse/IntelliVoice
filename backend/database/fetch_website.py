"""
database/fetch_website.py — copy the college website into IntelliVoice (2026-10-30).

    cd backend
    venv\\Scripts\\activate
    python database/fetch_website.py

Reads every page of saividya.ac.in and every PDF link on it (calendar of
events, timetables, exam circulars, syllabus, brochures, bus routes...) and
saves them in MongoDB (website_pages, website_documents). Prints what is new,
changed and removed. The admin panel's "Fetch updated data from website"
button does exactly the same.

Run it on a network where saividya.ac.in opens (takes about a minute).
The backend does not need to be running.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from database import connection  # noqa: E402
from engines import website_engine  # noqa: E402


async def main() -> int:
    await connection.connect_to_mongo()
    db = connection.get_database()
    if db is None:
        print("❌ MongoDB is not connected — check MONGODB_URL in .env and the internet.")
        return 1
    print("Reading saividya.ac.in … (about a minute)")
    summary = await website_engine.refresh(db)
    if summary.get("error"):
        print(f"❌ {summary['error']}")
        return 1
    print(f"✅ {summary['pages']} pages and {summary['pdfs']} PDFs saved "
          f"({summary['pdfs_for_parents']} PDFs that parents and students may ask for).")
    print(f"   New pages: {summary['new_pages']} · changed: {summary['changed_pages']} · removed: {summary['removed_pages']}")
    print(f"   New PDFs: {summary['new_pdfs']} · removed: {summary['removed_pdfs']}")
    for title in summary.get("new_pdf_titles", []):
        print(f"     + {title}")
    if summary.get("errors"):
        print(f"   ⚠️  {len(summary['errors'])} page(s) could not be read, e.g. {summary['errors'][0]}")
    print("Restart is NOT needed: IntelliVoice uses the new copy within about 10 minutes "
          "(immediately if you use the admin panel button instead).")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(asyncio.run(main()))
