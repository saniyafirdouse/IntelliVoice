"""
Standalone test — Sarvam AI Bulbul v3 text-to-speech.
Tests real project text across all three languages, saves audio files
so you can actually listen and judge naturalness/accent quality.

Run: python tests/test_sarvam_tts.py
"""

import os
from dotenv import load_dotenv
from sarvamai import SarvamAI
from sarvamai.play import save

load_dotenv()

client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

# Real text from our own project's earlier outputs, one per language
test_cases = [
    {
        "language_code": "kn-IN",
        "speaker": "kavya",
        "text": "Nimma chinte artha aagutte. CSE alli students-ge proper guidance mattu support sigutte.",
        "filename": "test_kannada.wav",
    },
    {
        "language_code": "hi-IN",
        "speaker": "roopa",
        "text": "CSE ka yearly fee 145000 rupees hai. Agar saal ka fee same rahe to poora four saal ka total roughly 580000 rupees ho sakta hai.",
        "filename": "test_hindi.wav",
    },
    {
        "language_code": "en-IN",
        "speaker": "ritu",
        "text": "The Computer Science and Engineering branch, or CSE, covers programming, algorithms, databases, and the fundamentals of artificial intelligence.",
        "filename": "test_english.wav",
    },
]

for case in test_cases:
    print(f"\nGenerating {case['language_code']} audio...")
    try:
        audio = client.text_to_speech.convert(
            text=case["text"],
            language_code=case["language_code"],
            model="bulbul:v3",
            speaker=case["speaker"],
        )
        save(audio, case["filename"])
        print(f"✅ Saved: {case['filename']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   If this mentions 'target_language_code' or 'unexpected keyword',")
        print("   your installed sarvamai version may be older — try replacing")
        print("   'language_code' with 'target_language_code' in this script.")

print("\nDone. Open each .wav file and listen — check for natural accent,")
print("correct pronunciation of English terms inside Kannada/Hindi, and")
print("no awkward pauses at the language-switch points.")