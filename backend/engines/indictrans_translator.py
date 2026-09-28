"""
IndicTrans2 English -> Kannada translation wrapper.

Uses a manually-replicated pipeline instead of the official
IndicTransToolkit package, since that package requires compilation
that fails on Windows (Application Control policy blocks the build).

Verified on Colab: this manual approach produces output IDENTICAL to
IndicTransToolkit's official pipeline, character-for-character, on
real test sentences — confirmed side-by-side before adopting this.

Pipeline:
    English text -> tag with language pair -> IndicTrans2 model
    -> Devanagari-script intermediate output -> aksharamukha
    (Devanagari -> Kannada script conversion) -> final Kannada text

Requires (all pure-Python or already-installed, no compilation needed):
    pip install transformers torch sentencepiece aksharamukha
"""

import ast
if not hasattr(ast, "Str"):
    ast.Str = ast.Constant  # compatibility shim for aksharamukha on Python 3.12+

import unicodedata
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from aksharamukha import transliterate

MODEL_NAME = "ai4bharat/indictrans2-en-indic-dist-200M"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_tokenizer = None
_model = None


def _load_model():
    global _tokenizer, _model
    if _model is not None:
        return

    print(f"Loading IndicTrans2 (English -> Kannada translation) on {DEVICE}...")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, trust_remote_code=True).to(DEVICE)
    print("✅ IndicTrans2 loaded")


def translate_to_kannada(text: str) -> str:
    """
    Translates English text to grammatically correct Kannada.
    This is intentionally the ONLY job this function does — no attempt
    at casual/conversational tone here, that's a separate step (Groq).
    Returns None on failure — caller must handle that explicitly.
    """
    try:
        _load_model()

        # Manual preprocessing — replicates IndicTransToolkit's tagging step
        normalized = unicodedata.normalize("NFKC", text.strip())
        tagged_input = f"eng_Latn kan_Knda {normalized}"

        inputs = _tokenizer([tagged_input], truncation=True, padding="longest", return_tensors="pt").to(DEVICE)

        with torch.no_grad():
            generated_tokens = _model.generate(
                **inputs, use_cache=True, min_length=0, max_length=256, num_beams=5
            )

        devanagari_output = _tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]

        # Script conversion — replicates IndicTransToolkit's postprocessing step.
        # Verified identical output to the official toolkit on real test sentences.
        kannada_output = transliterate.process("Devanagari", "Kannada", devanagari_output)

        return kannada_output

    except Exception as e:
        print(f"❌ IndicTrans2 translation error: {e}")
        return None