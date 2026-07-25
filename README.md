# Job App Agent

A 4-stage LLM pipeline — Extraction → Gap Analysis → Draft ⇄ Critique (capped loop) — for tailoring a job application to a posting. FastAPI backend, one endpoint per stage; React + TypeScript frontend owns pipeline orchestration.

## Status

Scaffolding only: FastAPI backend with a `/health` endpoint, Vite React + TypeScript frontend that confirms the round trip, and `backend/data/profile.json` populated with convincing mock data (not a real person). Pipeline stages are not yet implemented.

## Architecture

Orchestration lives in the frontend, not the backend. The backend exposes one stateless endpoint per stage (`/extract`, `/gap-analysis`, `/draft`, `/critique`); each takes the previous stage's Pydantic-validated output and returns its own. A React state machine (`usePipeline.ts`) calls these in sequence, populating the UI as each stage completes, and owns the capped draft/critique revise loop. This avoids needing SSE/WebSocket streaming to show intermediate results, and matches a mock-first, stage-by-stage build order. The trade-off: pipeline sequencing is coupled to the client, which wouldn't scale to a multi-user backend service — out of scope for v1, and a contained change later (one new endpoint reusing the same stage functions).

## Cost controls

- `MOCK_MODE` env var: `llm/client.py` branches at a single call site, returning fixtures with zero network calls when true.
- `MODEL_NAME` env var, default `claude-haiku-4-5`, read once in `config.py`.
- Prompt caching on the profile block for repeat calls within a run (once live).
- Capped revise loop (`MAX_REVISE_ITERATIONS`) in `usePipeline.ts`.

## Running locally

Backend:

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env` in `backend/` and fill in `ANTHROPIC_API_KEY` before setting `MOCK_MODE=false`.

## Tests

```bash
cd backend
pytest
```
