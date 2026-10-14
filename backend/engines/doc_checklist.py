"""
Personalised admission document checklist (PDF) — 2026-10-13.

The student says how they are joining (KCET / COMEDK / management quota,
lateral entry, MBA) and their category; this builds a one-page PDF with
tick boxes: the documents to bring, then the next admission steps
(this replaces a separate "journey tracker").

The document rules below are typical Karnataka engineering admission
requirements, entered as DEMO data (approved by San). Every PDF says
"please confirm with the admission office". Update DOCUMENT_RULES when the
college gives its official list.

Needs:  pip install fpdf2
"""

from datetime import datetime

from fpdf import FPDF

from engines.college_profile import COLLEGE_NAME, CONTACT, HOURS

ADMISSION_TYPES = {
    "KCET": "B.E. through KCET (Government quota)",
    "COMEDK": "B.E. through COMEDK",
    "Management": "B.E. through Management quota",
    "Lateral": "B.E. lateral entry (2nd year, through DCET)",
    "MBA": "MBA (through PGCET)",
}
CATEGORIES = ("General", "SC", "ST", "OBC")

COMMON = [
    "SSLC / 10th marks card (original + 2 copies)",
    "Aadhaar card (copy)",
    "Transfer certificate from the last institution",
    "Conduct / study certificate",
    "6 recent passport-size photographs",
]
DOCUMENT_RULES = {
    "KCET": ["2nd PUC / 12th marks card (original + 2 copies)", "KCET admission order", "KCET fee receipt",
             "KCET verification slip"],
    "COMEDK": ["2nd PUC / 12th marks card (original + 2 copies)", "COMEDK allotment letter", "COMEDK fee receipt",
               "COMEDK rank card", "Migration certificate (if your 12th board is outside Karnataka)"],
    "Management": ["2nd PUC / 12th marks card (original + 2 copies)", "Provisional admission letter from SVIT",
                   "Seat-blocking / fee payment receipt",
                   "Migration certificate (if your 12th board is outside Karnataka)"],
    "Lateral": ["Diploma marks cards (all semesters)", "Diploma certificate / provisional certificate",
                "DCET admission order", "DCET fee receipt"],
    "MBA": ["2nd PUC / 12th marks card", "Degree marks cards (all semesters)", "Provisional degree certificate",
            "PGCET admission order", "PGCET fee receipt"],
}
CATEGORY_RULES = {
    "SC": ["Caste certificate", "Income certificate", "Documents for SC/ST scholarship / fee reimbursement"],
    "ST": ["Caste certificate", "Income certificate", "Documents for SC/ST scholarship / fee reimbursement"],
    "OBC": ["Caste certificate (Category I / II / III)", "Income certificate",
            "Documents for the Category I-III fee concession"],
}
NEXT_STEPS = [
    "Admission confirmed by the SVIT admission office",
    "College fee paid (online through the Contineo payment gateway, or DD)",
    "Hostel registered (if needed)",
    "College bus registered (if needed)",
    "Scholarship application submitted in August (if eligible)",
]


def build_checklist(admission_type: str, category: str = "General", student_name: str | None = None) -> list:
    """The checklist items (for tests or other uses), in order."""
    items = list(COMMON) + list(DOCUMENT_RULES.get(admission_type, []))
    items += CATEGORY_RULES.get(category, [])
    return items


def _latin(text: str) -> str:
    # The built-in PDF fonts only cover Latin-1 characters.
    return (text or "").replace("₹", "Rs ").replace("–", "-").replace("—", "-").encode("latin-1", "replace").decode("latin-1")


def checklist_pdf(admission_type: str, category: str = "General", student_name: str | None = None) -> bytes:
    if admission_type not in ADMISSION_TYPES:
        raise ValueError(f"admission_type must be one of: {', '.join(ADMISSION_TYPES)}")
    if category not in CATEGORIES:
        category = "General"

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(18, 16, 18)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(47, 58, 107)
    pdf.cell(0, 9, _latin(COLLEGE_NAME), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 6, "Admission document checklist - prepared by IntelliVoice", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_text_color(20, 20, 20)
    pdf.set_font("Helvetica", "", 11)
    rows = [("Student", student_name or "-"), ("Admission", ADMISSION_TYPES[admission_type]),
            ("Category", category), ("Prepared on", datetime.now().strftime("%d %b %Y"))]
    for label, value in rows:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(32, 7, _latin(label))
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, _latin(value), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def section(title, items):
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(47, 58, 107)
        pdf.cell(0, 9, _latin(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(20, 20, 20)
        pdf.set_font("Helvetica", "", 11)
        for item in items:
            y = pdf.get_y()
            pdf.rect(pdf.l_margin, y + 1.5, 4.5, 4.5)        # tick box
            pdf.set_x(pdf.l_margin + 8)
            pdf.multi_cell(0, 7, _latin(item), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    section("Documents to bring", build_checklist(admission_type, category))
    section("Next steps", NEXT_STEPS)

    pdf.set_font("Helvetica", "I", 9.5)
    pdf.set_text_color(110, 60, 0)
    pdf.multi_cell(0, 5.5, _latin(
        "This is a general checklist. Requirements can change every year - please confirm the final list "
        "with the SVIT admission office before your visit. Carry originals and photocopies."),
        new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(60, 60, 60)
    phones = ", ".join(CONTACT["mobile"])
    pdf.multi_cell(0, 5.5, _latin(
        f"Admission office: {phones} | {CONTACT['email'][0]} | "
        f"Mon-Fri {HOURS['monday_to_friday']}, Sat {HOURS['saturday']}"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
