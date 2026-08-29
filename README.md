# Job App Agent

A four-stage LLM pipeline that tailors a job application to a posting:

`Extraction -> Gap Analysis -> Draft <-> Critique (capped)`

The project is a cost-conscious portfolio piece and a practical React learning project. Its goal is a traceable pipeline with explicit contracts and safeguards, not a single prompt wrapped in a UI.

V1 produces one tailored Cover Letter targeting 250–350 words in three or four short plain-text paragraphs. Resume tailoring, selection-criteria responses, and multi-document application bundles are outside the initial scope. Gap Analysis distinguishes direct Matches, Adjacent transferable evidence, and Gaps. The letter may emphasize Adjacent evidence, but never turns it into a Match or confesses a Gap.

## Status

The backend stages and local frontend workflow are implemented through the capped Draft/Critique loop. FastAPI exposes typed `/config`, `/extract`, `/gap-analysis`, `/draft`, and `/critique` routes; the React/TypeScript frontend owns sequencing and displays source-checked provenance. `backend/data/profile.json` contains a realistic fictional candidate named Jordan Ellis.

The contracts and major decisions for all four stages, provenance, Critique gating, and frontend orchestration are documented and implemented in mock mode. Remaining work is browser acceptance, hardening, and one explicitly authorized live calibration run.

Agents and contributors should read [AGENTS.md](AGENTS.md), [CONTEXT.md](CONTEXT.md), and the relevant files in [docs/adr/](docs/adr/) before editing.

## Architecture

The backend exposes one stateless endpoint per stage: `/extract`, `/gap-analysis`, `/draft`, and `/critique`. Each consumes validated prior-stage output and returns an explicit Pydantic response model. The React frontend owns sequencing, progressive display, and the capped Draft/Critique revision loop.

One user action starts the full pipeline. The interface reveals stage progress automatically rather than requiring separate clicks for each endpoint.

Users can inspect extracted Requirements, Requirement Assessments, and expandable Profile Evidence. The final Cover Letter remains clean and copyable, with optional per-paragraph provenance disclosures.

The UI identifies the active candidate as Jordan Ellis, a fictional demo Profile. `/config` supplies the Profile name without exposing the complete Profile.

If a stage fails, the UI preserves completed stage results and offers an explicit retry from the failed stage. Changing a Job Posting clears the current Pipeline Run so a new run starts at Extraction. Cancellation stops future scheduling on a best-effort basis.

Keeping orchestration in the browser avoids a blocking all-in-one endpoint or SSE/WebSocket infrastructure. The trade-off is that sequencing is coupled to the client. That would not suit a multi-user service requiring durable jobs and retries, but moving it server-side later is contained: one orchestration endpoint can reuse the same stage functions and contracts.

Model-provider plumbing stays generic. `llm/client.py` performs structured tool calls and transport-level retry without knowing about stages. Each stage agent owns its prompt, fixture, mock/live selection, source checks, and validated response construction. This keeps mock mode on the same processing path as live output.

Each stage separates its HTTP request, internal provider-output model, and public response. Tool schemas contain only model-owned fields; agents add checked and derived fields before returning typed responses.

## Extraction guarantees

Extraction separates evidence from judgment. A Requirement contains a verbatim span from the Job Posting and a `necessity` classification: `required`, `preferred`, or `unstated`.

After parsing model output, the agent drops any Requirement whose normalized span cannot be found in the exact posting string sent to the model. Optional job-title and company values are checked the same way and become absent when unverifiable. Normalization changes representation only, such as whitespace, quotes, dash style, bullets, and trailing punctuation. It never uses fuzzy matching. See [ADR-0001](docs/adr/0001-verbatim-requirement-spans.md).

Mock mode uses a canonical backend-owned sample posting with fixture spans drawn from it. `GET /config` supplies that posting to the frontend, where it will be prefilled and read-only. The fixture exercises the same fidelity checks as live output instead of bypassing them. See [ADR-0002](docs/adr/0002-sample-posting-served-by-backend.md).

## Cost and security controls

- `MOCK_MODE` defaults to true and makes no external model calls.
- `MODEL_NAME` defaults to `claude-haiku-4-5`.
- Model output uses Anthropic tool use with Pydantic-derived schemas.
- Job Posting input is bounded to 50–8,000 characters before model work.
- Extraction is capped at 2,048 output tokens.
- The generic model client retries malformed output once, then returns a sanitized failure.
- LLM endpoints share a configurable per-IP request budget, defaulting to `40/hour`; `/health` and `/config` remain unlimited.
- Job Posting text is treated as untrusted data, escaped, and placed inside explicit prompt delimiters.
- Every endpoint returns a typed response model rather than raw provider or internal objects.
- Default structured logs contain metadata, counts, and content hashes rather than postings, Profile content, rejected text, or raw provider output. Local content logging requires explicit `LOG_LLM_CONTENT=true`.
- The frontend renders untrusted and model-generated content as text, not raw HTML.
- The Draft/Critique loop allows at most two revisions after the initial Draft.
- Prompt caching may be added for repeated Profile context once live stages make its benefit measurable.

Mock mode is the safe public demo. Live mode is deliberate local configuration, not the deployment default.

## Local setup

From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
cp .env.example backend/.env
```

`ANTHROPIC_API_KEY` may remain empty while `MOCK_MODE=true`. Add a key only before an explicitly authorized live run.

Run the backend:

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Run the frontend in another terminal:

```bash
npm run dev --prefix frontend
```

## Verification

```bash
backend/.venv/bin/python -m pytest
npm run lint --prefix frontend
npm run build --prefix frontend
```

Normal tests must remain deterministic, offline, and usable without an API key. The mock API flow has been verified through the first Critique revision and second-pass result. Browser acceptance, cancellation/retry exercise, and an opt-in low-cost live run remain before the v1 exit condition.

## Scope

The first release uses the committed fictional Profile and runs locally without authentication. Its exit condition is a verified local mock pipeline plus one explicitly authorized live run. Resume-to-Profile upload and actual public hosting remain future work, though the application keeps safe deployment defaults.

Write a public `docs/architecture.md` after the Extraction frontend exists, when it can describe implemented behavior rather than predictions.
