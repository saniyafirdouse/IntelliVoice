#!/usr/bin/env bash
# Starts IntelliVoice inside the Hugging Face Space (2026-11-20).
set -e
cd /home/user/app

# The trained MuRIL weights (913 MB) are not in Git. If MURIL_REPO is set (a private Hugging Face
# model repo holding model_weights.pt), download them; HF_TOKEN (a Space secret) gives access.
# Without them IntelliVoice still works (simpler language detection).
WEIGHTS=backend/models/muril_multitask/model_weights.pt
if [ ! -f "$WEIGHTS" ] && [ -n "$MURIL_REPO" ]; then
  echo "Downloading MuRIL weights from $MURIL_REPO ..."
  python -c "import os; from huggingface_hub import hf_hub_download; hf_hub_download(os.environ['MURIL_REPO'], 'model_weights.pt', local_dir='backend/models/muril_multitask', token=os.getenv('HF_TOKEN'))" \
    || echo "MuRIL weights not downloaded: using the simpler language detection"
fi

# Backend (inside only) in the background, website in front on port 7860
(cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000) &
cd frontend && exec npx tsx server/index.ts
