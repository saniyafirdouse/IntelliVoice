"""
Rank-based branch predictor (2026-10-13).

"My KCET rank is 25,000 — which branches can I get?"
The comparison is done HERE in code (not by the language model, which is
unreliable with numbers). The model only puts the result into words.

Data: the "cutoffs" collection — one record per branch and exam with
opening_rank / closing_rank (KCET = Government quota, COMEDK = Management quota).
These are general cutoffs; category-wise cutoffs are not in the data.

Bands (lower rank number = better):
  good_chance  rank <= 85% of the closing rank
  borderline   rank <= 110% of the closing rank
  unlikely     anything above that
"""

GOOD_FACTOR = 0.85
BORDERLINE_FACTOR = 1.10

QUOTA_TO_EXAM = {"Government": "KCET", "Management": "COMEDK"}
BRANCH_NAMES = {
    "CSE": "CSE", "CSE-AIML": "CSE (AI & ML)", "CSE-DS": "CSE (Data Science)",
    "CSE-CyberSecurity": "CSE (Cyber Security)", "CS-BusinessSystems": "CS (Business Systems)",
    "ECE": "ECE", "Civil": "Civil", "Mechanical": "Mechanical", "ISE": "ISE", "MBA": "MBA",
}

NOTE = ("This is based on last year's closing ranks at SVIT. Cutoffs change every year, "
        "so this is a guide, not a guarantee.")


def _band(rank: int, closing: int) -> str:
    if rank <= closing * GOOD_FACTOR:
        return "good_chance"
    if rank <= closing * BORDERLINE_FACTOR:
        return "borderline"
    return "unlikely"


def predict(rank: int, cutoffs: list, exam: str | None = None, branch: str | None = None,
            category: str | None = None) -> dict:
    """Engine-3-style result ({"found": ..., "data": ...}) for Engine 5 to put into words."""
    docs = [d for d in cutoffs if isinstance(d.get("closing_rank"), (int, float))]
    exams = sorted({d.get("exam") for d in docs if d.get("exam")})
    if exam:
        docs = [d for d in docs if d.get("exam") == exam]
    if branch:
        docs = [d for d in docs if d.get("branch") == branch]
    if not docs:
        return {"found": False, "reason": "no_cutoff_for_this_exam_or_branch",
                "query_used": {"rank": rank, "exam": exam, "branch": branch}}

    result = {"student_rank": rank, "based_on": "last year's closing ranks", "note": NOTE}
    if category and category != "General":
        result["category_note"] = (f"These are general cutoffs; category-wise ({category}) cutoffs are "
                                   "not available here, so please confirm with the admission office.")

    by_exam = {}
    for d in sorted(docs, key=lambda d: d["closing_rank"]):
        ex = d.get("exam") or "exam"
        name = BRANCH_NAMES.get(d.get("branch"), d.get("branch"))
        entry = f"{name} (closing rank {int(d['closing_rank']):,})"
        bands = by_exam.setdefault(ex, {"quota": d.get("quota"), "good_chance": [], "borderline": [], "unlikely": []})
        bands[_band(rank, d["closing_rank"])].append(entry)

    if branch and len(by_exam) == 1:
        (ex, bands), = by_exam.items()
        verdict = next(k for k in ("good_chance", "borderline", "unlikely") if bands[k])
        result.update({"exam": ex, "branch": BRANCH_NAMES.get(branch, branch), "verdict": verdict,
                       "detail": bands[verdict][0]})
    else:
        result["results_by_exam"] = by_exam
        if not exam and len(exams) > 1:
            result["exam_note"] = ("The exam was not mentioned, so results for both KCET and COMEDK are given; "
                                   "KCET and COMEDK ranks are different, so use the one for your exam.")
    return {"found": True, "match_type": "single", "data": result,
            "query_used": {"rank": rank, "exam": exam, "branch": branch}, "note": "rank_prediction"}


def wanted_exam(entities: dict) -> str | None:
    return entities.get("exam") or QUOTA_TO_EXAM.get(entities.get("quota"))
