---
title: IntelliVoice
emoji: 🎙️
colorFrom: purple
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# IntelliVoice: Eva, the SVIT admission assistant

Multilingual (English, ಕನ್ನಡ, हिंदी) voice assistant for Sai Vidya Institute of Technology admissions.
ISE Final Year Major Project 2026-27.

- `backend/`: FastAPI (language, intelligence, knowledge, memory, response and voice engines)
- `frontend/`: React + TypeScript website with a small Express server
- `Dockerfile` + `deploy/start.sh`: hosting on Hugging Face Spaces (the block above is Hugging Face's settings)

Keys are never in the code: locally they are in `.env`, on Hugging Face in the Space's secrets.
