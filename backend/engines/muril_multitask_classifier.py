"""
Inference wrapper for the fine-tuned multi-task MuRIL model
(language + emotion detection, custom two-head architecture).

Same return-shape pattern as classify_intent_groq(), so this can be
swapped into evaluate_engine2.py / evaluate_generalization.py for a
direct, fair comparison against py3langid (language) and the
keyword-based detector (emotion) — same test data, same scoring.
"""

import json
import os
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel

MODEL_DIR = os.path.join(
    os.path.dirname(__file__), "..", "models", "muril_multitask"
)

_tokenizer = None
_model = None
_id2language = None
_id2emotion = None


class MuRILMultiTask(nn.Module):
    """Must match the training architecture exactly — same backbone,
    same two classification heads — or the saved weights won't load
    correctly onto this structure."""
    def __init__(self, model_name, num_languages, num_emotions, dropout=0.3):
        super().__init__()
        self.backbone = AutoModel.from_pretrained(model_name)
        hidden_size = self.backbone.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.language_head = nn.Linear(hidden_size, num_languages)
        self.emotion_head = nn.Linear(hidden_size, num_emotions)

    def forward(self, input_ids, attention_mask):
        outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        pooled = outputs.last_hidden_state[:, 0, :]
        pooled = self.dropout(pooled)
        return self.language_head(pooled), self.emotion_head(pooled)


def _load_model():
    global _tokenizer, _model, _id2language, _id2emotion
    if _model is not None:
        return

    if not os.path.exists(MODEL_DIR):
        raise FileNotFoundError(
            f"Fine-tuned MuRIL model not found at {MODEL_DIR}. "
            "Train it on Colab first, then download and place it here."
        )

    print("Loading fine-tuned multi-task MuRIL model...")

    with open(os.path.join(MODEL_DIR, "config.json"), encoding="utf-8") as f:
        config = json.load(f)
    with open(os.path.join(MODEL_DIR, "language_map.json"), encoding="utf-8") as f:
        language_map = json.load(f)
    with open(os.path.join(MODEL_DIR, "emotion_map.json"), encoding="utf-8") as f:
        emotion_map = json.load(f)

    _id2language = {v: k for k, v in language_map.items()}
    _id2emotion = {v: k for k, v in emotion_map.items()}

    _tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

    _model = MuRILMultiTask(
        config["model_name"], config["num_languages"], config["num_emotions"]
    )
    state_dict = torch.load(
        os.path.join(MODEL_DIR, "model_weights.pt"), map_location="cpu"
    )
    _model.load_state_dict(state_dict)
    _model.eval()

    print(f"✅ Fine-tuned MuRIL loaded — {len(_id2language)} languages, {len(_id2emotion)} emotions")


async def classify_language_emotion_muril(text: str) -> dict:
    """
    Returns language + emotion predictions with confidence scores.
    Same call pattern as the other classifiers in this project.
    """
    try:
        _load_model()

        inputs = _tokenizer(
            text, truncation=True, padding=True, max_length=64, return_tensors="pt"
        )
        with torch.no_grad():
            lang_logits, emo_logits = _model(
                inputs["input_ids"], inputs["attention_mask"]
            )
            lang_probs = torch.softmax(lang_logits, dim=1)
            emo_probs = torch.softmax(emo_logits, dim=1)

            lang_confidence, lang_pred = torch.max(lang_probs, dim=1)
            emo_confidence, emo_pred = torch.max(emo_probs, dim=1)

        return {
            "language": _id2language[lang_pred.item()],
            "language_confidence": round(lang_confidence.item(), 3),
            "emotion": _id2emotion[emo_pred.item()],
            "emotion_confidence": round(emo_confidence.item(), 3),
            "success": True,
        }

    except Exception as e:
        print(f"❌ MuRIL multi-task inference error: {e}")
        return {
            "language": "en", "language_confidence": 0.0,
            "emotion": "neutral", "emotion_confidence": 0.0,
            "success": False, "error": str(e),
        }