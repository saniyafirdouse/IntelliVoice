"""
Standalone test — Sarvam AI translation for natural, code-switched Kannada.

Testing two modes specifically built for our use case:
    - "code-mixed": mirrors natural English+Kannada mixing
    - "modern-colloquial": casual, contemporary spoken language

If either produces genuinely natural output, this REPLACES the entire
Google Translate + Groq casualization pipeline with one clean API call.

Run: python tests/test_sarvam.py
"""

import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

test_sentences = [
    "I understand your worry. The college provides mentoring and academic support to students.",
    "CSE stands for Computer Science and Engineering. The annual fee is 145000 rupees for the 2026-27 academic year.",
    "I understand how worried you feel about your son's future in CSE. It's completely normal to feel anxious when marks aren't where you'd like them to be. Many students find that with the right support, guidance, and a focused study plan, they can improve their performance and succeed in their chosen branch.",
]

for mode in ["code-mixed", "modern-colloquial"]:
    print(f"\n{'='*70}\nMODE: {mode}\n{'='*70}")
    for text in test_sentences:
        try:
            response = client.text.translate(
                input=text,
                source_language_code="en-IN",
                target_language_code="kn-IN",
                model="mayura:v1",
                mode=mode,
            )
            print(f"\nEN: {text}")
            print(f"KN: {response.translated_text}")
        except Exception as e:
            print(f"\n❌ Error on mode={mode}: {e}")