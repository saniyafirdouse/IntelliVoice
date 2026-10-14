"""
Verified facts about SVIT, given by the team (Saniya, 2026-10-13; updated the same
afternoon with the principal, accreditation, autonomy, codes and PIN 560119).

Why this file exists
--------------------
Some questions ("tell me about this college", "where is it", "college
timings", "admission office number") have no MongoDB data yet. Without
facts, the model once invented an answer ("SVIT ... Pune, Maharashtra").
These facts are always available, so those questions get a true answer.

If the admin uploads a record for the same topic to MongoDB, the database
record is used instead (see knowledge_engine.fetch_knowledge).

Only put CONFIRMED facts here. Anything not listed is "not known".
"""

COLLEGE_NAME = "Sai Vidya Institute of Technology (SVIT)"
COLLEGE_LOCATION = "Rajanukunte, via Yelahanka, Bengaluru, Karnataka 560119"

# One line added to every prompt so the model never mixes SVIT up with
# another college that has similar initials.
IDENTITY_LINE = (
    f"SVIT means {COLLEGE_NAME}, located at {COLLEGE_LOCATION}, India. "
    "It is not any other college with similar initials."
)

ABOUT = {
    "name": COLLEGE_NAME,
    "location": COLLEGE_LOCATION,
    "established": "2008",
    "established_by": "Sri Sai Vidya Vikas Shikshana Samithi",
    "founded_by": "a group of eminent academicians with a strong vision for excellence in engineering education",
    "motto": "Learn to Lead",
    "principal": "Dr. Manjunath T N",
    "affiliated_to": "Visvesvaraya Technological University (VTU), Belagavi, for students admitted before 2026",
    "autonomous": "Students joining from 2026 onwards study under SVIT's own autonomous scheme",
    "accreditation": "NAAC 'A' grade; NBA accredited programmes: CSE, ECE and ISE",
    "college_codes": "KCET E173, COMEDK E113, PGCET (MBA) B269",
    "programmes_2026_27": "B.E. in CSE, CSE (AI & ML), CSE (Data Science), CSE (Cyber Security), CS (Business Systems), ECE, Civil and Mechanical; MBA. ISE has been merged into CSE for new admissions.",
    "sister_institution": "Sai Vidya First Grade College (B.Com, BBA, BCA)",
    "approved_by": "All India Council for Technical Education (AICTE), New Delhi",
    "recognized_by": "Government of Karnataka",
    "total_enrollment": "1,686 students (2026)",
    "guided_by": "Prof. M. R. Holla, a distinguished academician and administrator with over 50 years of academic and administrative experience",
    "core_leadership_team": [
        "Dr. Y. Jayasimha (Eminent Electronics Professor)",
        "Prof. R. C. Shanmukha Swamy (Eminent Electrical Professor)",
        "Dr. A. M. Padma Reddy (Eminent Computer Science Professor)",
        "Sri R. Srinivas Raju (Practicing Civil Engineer)",
        "Sri M. K. Manohar (Renowned Chartered Accountant)",
        "Late Sri Narayana Raju (Renowned Academic Administrator)",
    ],
    "academic_focus": (
        "A dynamic learning environment with highly qualified and dedicated teaching "
        "and non-teaching staff; emphasis on academic rigor, innovation and holistic "
        "development to prepare students for professional success."
    ),
    "educational_philosophy": [
        "a strong sense of ethics, values and moral responsibility",
        "an understanding of history, ideals and societal responsibilities",
        "analytical thinking, creativity and intellectual curiosity",
    ],
}

HOURS = {
    "monday_to_friday": "8:30 am to 4:10 pm",
    "saturday": "8:30 am to 12:50 pm",
    "sunday": "closed",
}

CONTACT = {
    "admissions_office_address": "Admissions Section, Sai Vidya Institute of Technology, Rajanukunte, via Yelahanka, Bengaluru, Karnataka 560119",
    "email": ["admissions@saividya.ac.in", "info@saividya.ac.in"],
    "admissions_portal": "admissions.saividya.ac.in",
    "telephone": ["080-2846-8191", "080-2846-8196", "080-2846-8198"],
    "mobile": ["+91 91085 75191", "+91 93649 12981"],
}

# Intent -> the facts that answer it. The model gets only the slice it needs.
PROFILE_FACTS = {
    "ask_about_college": {**ABOUT},
    "ask_university_affiliation": {
        "name": COLLEGE_NAME,
        "affiliated_to": ABOUT["affiliated_to"],
        "autonomous": ABOUT["autonomous"],
        "approved_by": ABOUT["approved_by"],
        "recognized_by": ABOUT["recognized_by"],
    },
    "ask_working_hours": {"name": COLLEGE_NAME, "college_hours": HOURS},
    "ask_contact_admission_office": {**CONTACT, "office_hours": HOURS},
}


def profile_knowledge(intent_id: str):
    """Engine 3 result built from the verified facts, or None if this intent has none."""
    facts = PROFILE_FACTS.get(intent_id)
    if not facts:
        return None
    return {
        "found": True,
        "match_type": "single",
        "data": {"source": "SVIT verified profile", **facts},
        "query_used": {"profile": intent_id},
        "note": "college_profile",
    }
