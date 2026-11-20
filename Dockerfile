# IntelliVoice on Hugging Face Spaces (Docker, free CPU) — 2026-11-20
# One container: FastAPI backend on 127.0.0.1:8000 (inside only) + Express/React site on 7860 (public).
# No keys in this image: they come from the Space's Settings -> Variables and secrets.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# Hugging Face runs the app as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# 1. Python packages (CPU-only torch first: the normal one is several GB of GPU files)
COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --user torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir --user -r backend/requirements.txt

# 2. Download the public models once while building (faster start-ups)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')" \
 && python -c "from transformers import AutoModel, AutoTokenizer; AutoModel.from_pretrained('google/muril-base-cased'); AutoTokenizer.from_pretrained('google/muril-base-cased')" \
 && python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

# 3. Website: install and build the React app
COPY --chown=user frontend/package.json frontend/package-lock.json frontend/
COPY --chown=user frontend/scripts frontend/scripts
RUN cd frontend && npm ci
COPY --chown=user frontend frontend
RUN cd frontend && npm run build

# 4. Backend code + start script
COPY --chown=user backend backend
COPY --chown=user deploy/start.sh deploy/start.sh

ENV PORT=7860 BACKEND_URL=http://127.0.0.1:8000 PUBLIC_SITE=true
EXPOSE 7860
CMD ["bash", "deploy/start.sh"]
