# Job App Agent frontend

This React and TypeScript frontend presents the local Job App Agent Pipeline Run:

`Extraction -> Gap Analysis -> Draft <-> Critique (capped)`

The frontend owns stage sequencing, progress states, cancellation, failed-stage retry, and the two-revision cap. It receives the fictional Jordan Ellis Profile name and the canonical sample Job Posting from the backend's `GET /config` endpoint. In mock mode the sample is prefilled and read-only, and the pipeline makes no external model calls.

## Local development

Install dependencies from the repository root:

```bash
npm ci --prefix frontend
```

Start the backend first, then run the frontend:

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

In another terminal from the repository root:

```bash
npm run dev --prefix frontend
```

The frontend defaults to `http://localhost:8000` for the backend. Set `VITE_API_BASE_URL` before starting Vite when using another local API origin.

## Verification

```bash
npm run lint --prefix frontend
npm run build --prefix frontend
```

The production build uses TypeScript project checking followed by Vite. The interface renders Job Posting text and model output as text, keeps Profile Evidence collapsed until requested, and supports editing only after a generated Cover Letter reaches `passed` or `capped`.

Manual browser acceptance remains a separate release check for the complete mock flow, cancellation, retry, cap, editing, reset, and copy behavior.
