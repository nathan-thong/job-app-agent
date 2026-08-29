# Job App Agent architecture

Job App Agent is a local, four-stage pipeline for producing one grounded Cover Letter from one Job Posting and the backend-owned Profile:

```text
Job Posting
    │
    ▼
Extraction ──► Gap Analysis ──► Draft ──► Critique
                                         │       │
                                         └─revise┘
                                           (maximum two revisions)
```

The application is deliberately stateless at the HTTP boundary. The React frontend sequences the stages and keeps the current Pipeline Run in memory. The backend owns the Profile, stage validation, source checks, model-provider calls, and derived safety fields.

## Backend boundaries

The FastAPI application exposes six public routes:

| Route | Purpose | Public response |
| --- | --- | --- |
| `GET /health` | Liveness check | `HealthResponse` |
| `GET /config` | Safe demo configuration | `ConfigResponse` |
| `POST /extract` | Copy and classify Job Posting Requirements | `ExtractionResponse` |
| `POST /gap-analysis` | Assess each Requirement against the Profile | `GapAnalysisResponse` |
| `POST /draft` | Produce a structured Cover Letter | `DraftResponse` |
| `POST /critique` | Return Findings and a derived verdict | `CritiqueResponse` |

Each stage has three model layers:

1. A request model for validated input from the previous stage.
2. An internal `*ToolOutput` model containing only provider-owned fields.
3. A public response model containing checked and backend-derived fields.

The generic `StructuredToolClient` knows only how to make an Anthropic structured tool call. It generates the tool schema from the stage's internal Pydantic model, accepts the stage's parser, applies a bounded provider timeout, and retries once for transient transport failures or malformed/parser-rejected tool output. It does not know the meaning of a Requirement, Profile Evidence, or Critique Finding.

Stage agents own prompts, fixtures, mock/live selection, parsing, source checks, normalization, and construction of public responses. Mock mode swaps the provider call for a committed fixture while preserving the same agent guardrails. The default configuration is mock mode and requires no API key.

## Trust and provenance

Extraction treats the Job Posting as untrusted data. The agent escapes a literal closing delimiter, places the posting inside `<job_posting>` tags, and uses representation-only normalization to check returned Requirement, title, and company text. Case, whitespace, quote, dash, bullet, and trailing-punctuation differences may normalize; paraphrases and fuzzy matches do not. Unverifiable Requirements are dropped and the required `dropped_count` proves that the check ran.

Gap Analysis embeds the complete Requirement in every Requirement Assessment and restores the original Extraction order. It keeps the first valid assessment, drops unknown and duplicate assessments, and synthesizes a Gap when an assessment is missing. Match and Adjacent outcomes require checked Profile Evidence; evidence is copied from a named Profile section and is verified with the same representation-only comparison discipline. Unsupported evidence causes a downgrade to Gap when no checked evidence remains.

Draft carries provenance beside each Cover Letter Paragraph. The agent drops Requirements that are unknown or Gaps and drops evidence that is not approved by a surviving Match or Adjacent assessment. It derives the salutation, sign-off, and candidate name from backend-controlled values. The rendered letter contains prose only; provenance is an optional disclosure and is not included when copying.

Critique receives the structured letter and its sanitized provenance. The provider returns semantic Findings only. The backend derives Finding severity and the `pass`/`revise` verdict, adds deterministic word-count and forbidden-structure Findings, normalizes paragraph references, and deduplicates Findings. Any blocking Finding requires revision. Advisory Findings may remain on a passing letter. Deterministic Findings never allow the semantic Critique call to be skipped.

## Frontend Pipeline Run

`usePipeline` owns the state machine:

```text
idle → extracting → analyzing → drafting → critiquing
                                      ↑          │
                                      └ revising ◄┘

critiquing ──pass──► passed
critiquing ──cap───► capped
any active stage ──cancel──► cancelled
any stage failure ─────────► error
```

One Generate action runs the complete sequence. A failed run preserves completed stage outputs and offers explicit retry from the failed stage. Changing the Job Posting clears the current run, while retry does not automatically spend another request. Cancellation aborts the active browser request on a best-effort basis and prevents future stages from being scheduled; a provider call already in progress may still incur cost.

The revision loop permits two revised Draft calls after the initial Draft. Every revision is a complete replacement Cover Letter and is Critiqued again. A run with remaining blocking Findings after the last allowed iteration becomes `capped`, not `passed`.

Generated Cover Letters are immutable. Editing is a separate terminal presentation state available only after `passed` or `capped`; the UI warns that the prior verdict and provenance do not apply to edited text, supports reset, and copies the currently visible version.

## Operational safeguards

- The Profile is loaded and validated once at startup. Mock startup also validates the canonical sample posting and Extraction/Gap Analysis fixtures.
- `/extract`, `/gap-analysis`, `/draft`, and `/critique` share a configurable per-IP request budget, defaulting to `40/hour`. `/health` and `/config` are not rate-limited.
- Live provider calls use `LLM_TIMEOUT_SECONDS`, defaulting to 30 seconds and bounded to 120 seconds.
- Provider errors are converted to stage errors and sanitized HTTP responses. Raw model output is never returned to the browser.
- Default logs record stage metadata, reasons, counts, request IDs, model names where applicable, and content hashes. Rejected content requires explicit local `LOG_LLM_CONTENT=true`.
- CORS is limited to the local frontend origin (`http://localhost:5173`) until deployment needs are known.
- The committed Profile and fixtures contain fictional Jordan Ellis data only. Keys, environments, node modules, and live model output are not committed.

## Verification and scope

The normal test suite is deterministic and offline. Backend tests cover model contracts, source fidelity, provider parsing/retry, provenance normalization, Critique gating, rate limiting, and the complete mock HTTP flow. Frontend verification uses Oxlint and a production TypeScript/Vite build.

The v1 boundary is local mock operation plus one explicitly authorized live calibration run. Public hosting, authentication, persistence, user-supplied Profiles, and resume upload are outside this architecture.
