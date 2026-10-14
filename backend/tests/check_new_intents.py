"""
Quick check that new kinds of questions reach the right topic (2026-10-13).

Uses only the local Sentence Transformer matching (no Groq calls, no tokens used).
Run from the backend folder with the venv active:

    python tests/check_new_intents.py

Each line shows the expected topic, the best match and its similarity score.
"OK" = the local matcher alone already gets it right. A "check" line is not
necessarily wrong — in the real pipeline Groq decides the unclear ones — but
tell Claude about any "check" lines.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sentence_transformers import util  # noqa: E402

from engines.intelligence_engine import embedding_model, intent_embeddings, intent_labels  # noqa: E402

CASES = [
    ("Tell me about this college", "ask_about_college"),
    ("What courses do you offer?", "ask_courses_offered"),
    ("Is ISE branch available?", "ask_courses_offered"),
    ("How many seats are there in CSE?", "ask_courses_offered"),
    ("Can diploma students get lateral entry?", "ask_lateral_pg_admission"),
    ("How do I get MBA admission?", "ask_lateral_pg_admission"),
    ("Is the college safe for girls?", "ask_safety"),
    ("Is there ragging?", "ask_safety"),
    ("Can we visit the campus on Saturday?", "ask_campus_visit"),
    ("How do I pay the fees?", "ask_fee_payment"),
    ("Can I get an education loan?", "ask_fee_payment"),
    ("Is there a gym and NCC?", "ask_sports"),
    ("Do you help with GATE coaching?", "ask_higher_studies"),
    ("When does college reopen?", "ask_important_dates"),
    ("What is the hostel fee?", "ask_hostel_facilities"),
    ("What is the bus fee?", "ask_transport_routes"),
    ("College ladkiyon ke liye safe hai kya?", "ask_safety"),
    ("Yava yava courses ide?", "ask_courses_offered"),
    ("Fees hege kattodu?", "ask_fee_payment"),
    ("CSE fee eshtu?", "ask_fees_branch"),
    ("My KCET rank is 25000, which branch can I get?", "ask_rank_prediction"),
    ("With rank 18,000 can I get CSE?", "ask_rank_prediction"),
    ("Nanna rank 30000, yava branch sigutte?", "ask_rank_prediction"),
    ("What was the KCET cutoff for CSE last year?", "ask_cutoff"),
]

ok = 0
import torch  # noqa: E402

stacked = torch.stack(intent_embeddings)
for question, expected in CASES:
    sims = util.cos_sim(embedding_model.encode(question, convert_to_tensor=True), stacked)[0]
    best = int(torch.argmax(sims))
    got, score = intent_labels[best], float(sims[best])
    good = got == expected
    ok += good
    print(f"{'OK   ' if good else 'check'}  {score:.2f}  {question:45s} -> {got}" + ("" if good else f"   (expected {expected})"))
print(f"\n{ok}/{len(CASES)} matched by the local matcher alone.")
