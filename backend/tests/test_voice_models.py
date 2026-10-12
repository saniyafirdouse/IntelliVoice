"""
Voice model test — current voices (bulbul:v3) vs Sarvam's newer
bulbul:v4-flash, same sentence, same speed setting.

Prints how long each takes (3 tries each) and saves one file per voice
in tests/output_audio/ so you can LISTEN and compare. Nothing in the app
changes — this only measures. From backend/, venv active:
    python tests/test_voice_models.py
"""

import base64
import os
import statistics
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from engines.tts_engine import (  # noqa: E402
    LANGUAGE_CODES, PACE, _get_client, apply_spoken_forms,
    ensure_final_punctuation, speak_numbers,
)

SENTENCES = {
    "kn": "CSE branch fee KCET ಮೂಲಕ ₹120,000, Management quota ಗೆ ₹325,000. ಇನ್ನೇನಾದ್ರೂ ಕೇಳಬೇಕಿದ್ರೆ ಕೇಳಿ.",
    "en": "The CSE fee through KCET is ₹120,000 per year, and under the Management quota it is ₹325,000.",
    "hi": "CSE ka KCET se fee ₹120,000 hai, aur Management quota mein ₹325,000 hai.",
}
# (model, speaker): current voice first, then the v4-flash candidate(s).
VOICES = {
    "kn": [("bulbul:v3", "roopa"), ("bulbul:v4-flash", "chaitra_kn_conversation")],
    "en": [("bulbul:v3", "ritu"), ("bulbul:v4-flash", "simran_en_customer")],
    "hi": [("bulbul:v3", "simran"), ("bulbul:v4-flash", "simran_hi_conversation")],
}
TRIES = 3
OUT_DIR = os.path.join(os.path.dirname(__file__), "output_audio")


def speak_once(text, language, model, speaker):
    client = _get_client()
    start = time.perf_counter()
    args = dict(text=text, model=model, speaker=speaker, pace=PACE.get(language, 1.0))
    try:
        response = client.text_to_speech.convert(target_language_code=LANGUAGE_CODES[language], **args)
    except TypeError:
        # Older sarvamai versions call this parameter language_code (same as tts_engine.py).
        response = client.text_to_speech.convert(language_code=LANGUAGE_CODES[language], **args)
    return int((time.perf_counter() - start) * 1000), base64.b64decode(response.audios[0])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for language, voices in VOICES.items():
        text = ensure_final_punctuation(apply_spoken_forms(speak_numbers(SENTENCES[language], language), language))
        print("=" * 72)
        print(f"{language}: {text}")
        for model, speaker in voices:
            times, audio = [], None
            for _ in range(TRIES):
                try:
                    ms, data = speak_once(text, language, model, speaker)
                    times.append(ms)
                    audio = audio or data
                except Exception as e:
                    print(f"  {model:<16} {speaker:<26} ERROR: {type(e).__name__}: {str(e)[:150]}")
                    break
                time.sleep(1)
            if times:
                name = f"voice_{language}_{model.split(':')[1]}_{speaker}.wav"
                with open(os.path.join(OUT_DIR, name), "wb") as f:
                    f.write(audio)
                print(f"  {model:<16} {speaker:<26} median {statistics.median(times):>5} ms  "
                      f"(tries: {times})  -> {name}")
    print("\nListen to the files in tests/output_audio/ and compare.")


if __name__ == "__main__":
    main()
