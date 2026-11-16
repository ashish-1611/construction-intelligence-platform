# 🏗️ Multimodal Construction Intelligence Platform

AI-assisted construction management built with **Google Gemini (Generative AI on Google Cloud)** and **Streamlit**.
Upload site photos and plans, get structured safety and crack reports, estimate materials and cost in **INR**,
schedule tasks with a critical path, check weather risk, and chat with a construction assistant.

## Features (mapped to project milestones)

| Milestone | Module | What it does |
|---|---|---|
| 1. Requirements & environment | `requirements.txt`, `.env.example`, `construction_ai/config.py` | Dependencies, env-based config (API key or Vertex AI) |
| 2. Image-based analysis | `safety.py`, `cracks.py` | Safety/PPE inspection; crack detection (offline heuristic + Gemini vision) |
| 3. Planning & valuation | `materials.py`, `costing.py`, `scheduler.py` | Material quantities, INR cost with GST, dependency-aware schedule + critical path |
| 4. AI implementation | `reasoning.py`, `gemini_client.py`, `schemas.py` | Multimodal reasoning; Pydantic **JSON schema enforcement** with automatic retry |
| 5. Assistant & advisory | `assistant.py`, `weather.py` | Chatbot, daily site briefing, rule-based weather advisory (Open-Meteo, no key) |
| 6. Interface, testing, deployment | `app.py`, `tests/`, `Dockerfile`, CI | Streamlit UI, 28 tests (AI mocked), Docker, GitHub Actions |

## Quick start

```bash
git clone <your-repo-url> && cd construction-intelligence-platform
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # add GOOGLE_API_KEY
streamlit run app.py
```

Without an API key the app still runs: estimation, scheduling, weather and the crack screening heuristic work offline;
AI tabs ask for a key. You can also paste a key in the sidebar (session only).

### Using Vertex AI instead of an API key
```
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_CLOUD_LOCATION=us-central1
```
and authenticate with `gcloud auth application-default login`.

## Tests
```bash
pip install -r requirements-dev.txt
pytest -q
```

## Deploy

**Streamlit Community Cloud (easiest):** push to GitHub → share.streamlit.io → select repo, main file `app.py` →
add `GOOGLE_API_KEY` under *Secrets*.

**Google Cloud Run:**
```bash
gcloud run deploy construction-ai --source . --region asia-south1 --allow-unauthenticated \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=<project>
```
(or store the key in Secret Manager and expose it as `GOOGLE_API_KEY`).

**Docker:** `docker build -t construction-ai . && docker run -p 8080:8080 --env-file .env construction-ai`

## Project layout
```
app.py                     Streamlit UI
construction_ai/           Core library (all logic, unit-tested)
  data/material_norms.json   Editable quantity norms
  data/rates_inr.json        Editable INR rates, overhead, GST
tests/                     pytest suite (Gemini is faked; no network needed)
```

## Important notes
- Estimates use thumb rules (about ±15–20%). Edit the JSON files for your city's rates before relying on them.
- AI output is decision support, not a substitute for a licensed structural or safety engineer.
- Never commit `.env`; it is already in `.gitignore`.

## License
MIT
