"""
"College at a glance" + downloadable brochure (2026-10-15).

When a parent asks for everything at once ("tell me all the details about the
college — fees, branches, placements, scholarships..."), IntelliVoice answers with
one organised overview instead of a single topic:
  - build_overview()  -> sections for the chat card (from the live database)
  - brochure_pdf()    -> the same information as a printable PDF

Everything comes from MongoDB (through the Knowledge Engine's cache, so it is fast
and shows admin uploads within a minute) plus the verified facts in
college_profile.py. Nothing is invented: a section with no data is simply left out.
"""

from datetime import datetime

from fpdf import FPDF

from database.connection import get_database
from engines.college_profile import ABOUT, COLLEGE_NAME, CONTACT, HOURS
from engines.knowledge_engine import _find

MAX_ITEM_CHARS = 240          # on the chat card; the PDF shows the full text


# ── helpers ────────────────────────────────────────────────────────────────
def inr(value) -> str:
    """120000 -> 'Rs 1,20,000' (Indian grouping). Text is returned unchanged."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    n = int(round(value))
    s = str(abs(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return f"Rs {'-' if n < 0 else ''}{s}"


def _num(value) -> str:
    return f"{value:,}" if isinstance(value, int) and not isinstance(value, bool) else str(value)


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(_text(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):
        return "; ".join(f"{k.replace('_', ' ')}: {_text(v)}" for k, v in value.items())
    return str(value).strip()


def _item(label: str, value) -> dict | None:
    text = _text(value)
    return {"label": label, "value": text} if text else None


async def _docs(db, collection: str, limit: int = 300) -> list:
    try:
        return await _find(db, collection, {}, limit=limit) if db is not None else []
    except Exception as e:
        print(f"⚠️  Overview: could not read '{collection}': {e}")
        return []


def _first(docs: list, **match) -> dict:
    for d in docs:
        if all(d.get(k) == v for k, v in match.items()):
            return d
    return {}


# ── sections ───────────────────────────────────────────────────────────────
def _about() -> dict:
    items = [
        _item("Established", f"{ABOUT.get('established')} by {ABOUT.get('established_by')}"),
        _item("Location", ABOUT.get("location")),
        _item("Accreditation", ABOUT.get("accreditation")),
        _item("Status", ABOUT.get("autonomous")),
        _item("Approved by", ABOUT.get("approved_by")),
        _item("College codes", ABOUT.get("college_codes")),
    ]
    return {"id": "about", "title": "About SVIT", "icon": "account_balance", "items": items}


def _courses(docs: list) -> dict:
    c = next((d for d in docs if d.get("ug_programs_2026_27")), {})
    items = [
        _item("B.E. programmes", c.get("ug_programs_2026_27") or ABOUT.get("programmes_2026_27")),
        _item("New in 2026-27", c.get("new_ug_programs")),
        _item("Seats", c.get("seats_per_branch")),
        _item("Postgraduate", c.get("pg_programs")),
        _item("ISE", c.get("ise_status")),
    ]
    return {"id": "courses", "title": "Branches & seats", "icon": "school", "items": items}


def _fees(docs: list) -> dict:
    by_branch: dict[str, dict[str, object]] = {}
    for d in docs:
        branch = d.get("branch")
        fee = d.get("annual_fee")
        if not branch or fee is None:
            continue
        route = d.get("exam") or d.get("quota") or "Fee"
        by_branch.setdefault(branch, {}).setdefault(route, fee)
    order = ["KCET", "COMEDK", "Management"]
    items = []
    for branch, routes in by_branch.items():
        parts = [f"{r} {inr(routes[r])}" for r in order if r in routes]
        parts += [f"{r} {inr(v)}" for r, v in routes.items() if r not in order]
        items.append(_item(branch, " · ".join(parts) + " per year"))
    year = next((d.get("academic_year") for d in docs if d.get("academic_year")), None)
    return {"id": "fees", "title": "Tuition fees" + (f" ({year})" if year else ""), "icon": "payments", "items": items,
            "note": "Annual tuition. Hostel and bus fees are listed separately."}


def _cutoffs(docs: list) -> dict:
    by_branch: dict[str, dict[str, object]] = {}
    for d in docs:
        branch, exam, closing = d.get("branch"), d.get("exam"), d.get("closing_rank")
        if not branch or not exam or closing is None:
            continue
        if d.get("category") not in (None, "", "General", "GM"):
            continue
        by_branch.setdefault(branch, {}).setdefault(exam, closing)
    items = [_item(b, " · ".join(f"{e} {_num(r)}" for e, r in ex.items())) for b, ex in by_branch.items()]
    return {"id": "cutoffs", "title": "Cutoff ranks (closing)", "icon": "leaderboard", "items": items,
            "note": "Last year's closing ranks for General merit — a guide, not a guarantee."}


def _placements(docs: list) -> dict:
    overall = next((d for d in docs if str(d.get("scope", "")).lower().startswith("whole")), {})
    items = [
        _item("Year", overall.get("year")),
        _item("Total offers", overall.get("total_placement_offers")),
        _item("Highest package", overall.get("highest_ctc")),
        _item("Average package", overall.get("average_ctc")),
        _item("Companies visited", overall.get("companies_visited")),
    ]
    branch_offers = [f"{d['branch']} {d['placement_offers']}" for d in docs
                     if d is not overall and isinstance(d.get("branch"), str) and d.get("placement_offers") is not None]
    if branch_offers:
        items.append(_item("Offers by branch", " · ".join(branch_offers)))
    for key in ("top_recruiters", "recruiters", "notable_recruiters"):
        if overall.get(key):
            items.append(_item("Top recruiters", overall[key]))
            break
    return {"id": "placements", "title": "Placements", "icon": "work", "items": items}


def _internships(collections: dict) -> dict:
    """Any field mentioning internships, wherever it is stored."""
    items, seen = [], set()
    for name in ("internships", "placements", "placement_training", "campus_life", "academics"):
        for d in collections.get(name, []):
            for key, value in d.items():
                if "intern" in key.lower() and key not in seen:
                    seen.add(key)
                    items.append(_item(key.replace("_", " ").capitalize(), value))
    return {"id": "internships", "title": "Internships & training", "icon": "badge", "items": items}


def _training(docs: list) -> list:
    d = docs[0] if docs else {}
    return [_item("Placement training", d.get("training")), _item("Placement head", d.get("placement_head"))]


def _scholarships(docs: list) -> dict:
    names = [d.get("scholarship_name") for d in docs if d.get("scholarship_name")]
    items = [_item("Available", names)]
    how = next((d.get("how_to_apply") for d in docs if d.get("how_to_apply")), None)
    items.append(_item("How to apply", how))
    return {"id": "scholarships", "title": "Scholarships", "icon": "volunteer_activism", "items": items}


def _hostel(docs: list) -> dict:
    common = next((d for d in docs if d.get("overview")), {})
    boys = next((d for d in docs if str(d.get("hostel_for", "")).lower() == "boys"), {})
    girls = next((d for d in docs if str(d.get("hostel_for", "")).lower() == "girls"), {})
    girls_fee = None
    if girls.get("fee_2026_27_old_hostel") is not None:
        girls_fee = f"Old hostel {inr(girls['fee_2026_27_old_hostel'])}, new hostel {inr(girls.get('fee_2026_27_new_hostel'))} a year"
    items = [
        _item("Overview", common.get("overview")),
        _item("Boys hostel", boys.get("fee_existing_building") and f"{boys.get('fee_existing_building')}; new building: {boys.get('fee_new_building')}"),
        _item("Girls hostel", girls_fee),
        _item("Food", common.get("food")),
    ]
    return {"id": "hostel", "title": "Hostel", "icon": "apartment", "items": items}


def _transport(docs: list) -> dict:
    t = docs[0] if docs else {}
    fees = [f"{label} {inr(t[k])}" for k, label in (("fee_bengaluru_city_limits", "Bengaluru city"),
                                                     ("fee_yelahanka_limits", "Yelahanka"),
                                                     ("fee_doddaballapura", "Doddaballapura")) if t.get(k) is not None]
    items = [_item("Buses", t.get("buses")), _item("Bus fee (per year)", " · ".join(fees)), _item("Routes", t.get("route_areas"))]
    return {"id": "transport", "title": "Transport", "icon": "directions_bus", "items": items}


def _faculty(docs: list) -> dict:
    f = docs[0] if docs else {}
    items = [
        _item("Principal", f.get("principal") or ABOUT.get("principal")),
        _item("Deans", f.get("deans")),
        _item("Heads of departments", f.get("heads_of_departments")),
        _item("Mentoring", f.get("approachability")),
    ]
    return {"id": "faculty", "title": "Faculty & leadership", "icon": "groups", "items": items}


def _contact() -> dict:
    items = [
        _item("Phone", ", ".join(CONTACT["telephone"][:1] + CONTACT["mobile"][:1])),
        _item("Email", CONTACT["email"][0]),
        _item("Office hours", f"Mon-Fri {HOURS['monday_to_friday']}; Sat {HOURS['saturday']}"),
        _item("Address", CONTACT["admissions_office_address"]),
    ]
    return {"id": "contact", "title": "Admission office", "icon": "call", "items": items}


def _clean(section: dict, trim: bool) -> dict | None:
    items = [i for i in section.get("items", []) if i]
    if trim:
        items = [{**i, "value": i["value"] if len(i["value"]) <= MAX_ITEM_CHARS
                  else i["value"][:MAX_ITEM_CHARS].rsplit(" ", 1)[0] + "…"} for i in items]
    return {**section, "items": items} if items else None


async def build_overview(trim: bool = True) -> dict:
    """All sections, in reading order. trim=False keeps the full text (for the PDF)."""
    db = get_database()
    names = ["courses", "fees", "cutoffs", "placements", "placement_training", "internships", "campus_life",
             "academics", "scholarships", "hostel", "transport", "faculty"]
    collections = {n: await _docs(db, n) for n in names}

    placements = _placements(collections["placements"])
    internships = _internships(collections)
    internships["items"] = internships["items"] + _training(collections["placement_training"])

    sections = [
        _about(),
        _courses(collections["courses"]),
        _fees(collections["fees"]),
        _cutoffs(collections["cutoffs"]),
        placements,
        internships,
        _scholarships(collections["scholarships"]),
        _hostel(collections["hostel"]),
        _transport(collections["transport"]),
        _faculty(collections["faculty"]),
        _contact(),
    ]
    sections = [s for s in (_clean(s, trim) for s in sections) if s]
    return {
        "title": f"{COLLEGE_NAME} at a glance",
        "sections": sections,
        "brochure_url": "/api/brochure",
        "generated_at": datetime.now().strftime("%d %b %Y"),
    }


# ── brochure PDF ───────────────────────────────────────────────────────────
def _latin(text: str) -> str:
    # The built-in PDF fonts only cover Latin-1 characters.
    return ((text or "").replace("₹", "Rs ").replace("–", "-").replace("—", "-").replace("·", "|")
            .replace("…", "...").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            .encode("latin-1", "replace").decode("latin-1"))


def brochure_pdf(overview: dict) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()

    # title band
    pdf.set_fill_color(38, 44, 32)
    pdf.rect(0, 0, 210, 34, "F")
    pdf.set_xy(18, 9)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 17)
    pdf.cell(0, 8, _latin(COLLEGE_NAME), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(18)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(206, 216, 170)
    pdf.cell(0, 6, _latin(f"Admission brochure - prepared by IntelliVoice on {overview.get('generated_at', '')}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(42)

    label_w = 46
    for section in overview.get("sections", []):
        if pdf.get_y() > 255:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(79, 93, 54)
        pdf.cell(0, 8, _latin(section["title"]), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(206, 216, 170)
        pdf.line(pdf.l_margin, pdf.get_y(), 210 - pdf.r_margin, pdf.get_y())
        pdf.ln(2)
        for item in section["items"]:
            y = pdf.get_y()
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(label_w, 5.6, _latin(item["label"]), new_x="RIGHT", new_y="TOP")
            pdf.set_xy(pdf.l_margin + label_w + 2, y)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(25, 25, 25)
            pdf.multi_cell(0, 5.6, _latin(item["value"]), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        if section.get("note"):
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(110, 110, 110)
            pdf.multi_cell(0, 5, _latin(section["note"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(110, 60, 0)
    pdf.multi_cell(0, 5, _latin("Figures are from the SVIT admissions database at the time of download and can change. "
                                "Please confirm with the SVIT admission office before making payments."),
                   new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
