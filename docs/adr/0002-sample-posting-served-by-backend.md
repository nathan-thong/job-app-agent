# Mock mode runs on a sample posting the backend serves

## Context

The check in [ADR-0001](0001-verbatim-requirement-spans.md) made the Extraction fixture
depend on its input. Fixture spans have to be substrings of whatever posting was pasted,
or every one of them gets dropped. An arbitrary blob of plausible requirements no longer
works in `MOCK_MODE`.

This matters more than a developer convenience. If the app is ever deployed publicly,
`MOCK_MODE` defaults to `true` so a stranger can't spend the API budget. Mock mode is
what visitors would see. It's the demo, not a stub.

## Decision

Ship a fictional `backend/data/sample_posting.txt` and draw the Extraction fixture's
spans out of it. The check then runs unmodified in mock mode.

In mock mode the frontend fills the Job Posting textarea with the sample, makes it
read-only, and puts a notice above it. The honest pitch is that this is the pipeline
running on a sample posting, and you can clone it and add a key to run your own. That's
exactly what's happening.

Both the sample text and the mock-mode flag reach the frontend through one endpoint,
`GET /config`, returning `{mock_mode, sample_posting}`, fetched once on mount. Without it
the sample would have to be duplicated into a frontend constant, where it would drift
from the file the fixture was drawn from. `sample_posting` comes back `None` when mock
mode is off, so a live deployment never ships the text.

## Rejected

**Skipping the check in mock mode.** This doesn't only disable the check in the
fixture-driven tests that make up most of the suite. It goes around the `dropped_count`
guard from ADR-0001. The field has no default so the agent can't forget it, but a skipped
check fills it with `0` every time, and the schema then certifies that a check happened
when it didn't.

**Deriving spans from the real input at mock time.** A hand-rolled span picker is a worse
LLM. Its output would be visibly mediocre, it would be the first thing a visitor saw, and
they'd have no way to tell "this is a stub" from "this app is bad".

**An editable box whose contents get ignored.** The UI would be doing something other
than what it appears to do, which is a worse lie than a disabled textarea.

## Consequences

The sample posting is deliberately messy, to exercise the normalising rather than flatter
it. It needs a hyphen inside a word, like "e-commerce" or "front-end", to prove dashes get
mapped and not stripped. It needs a requirement hard-wrapped across two lines, curly
quotes and apostrophes, a requirement ending in a full stop, and mixed bullet characters.

It also has to ask for things the Jordan Ellis profile doesn't have. Two or three required
items, say Kubernetes, GraphQL, or a specific industry, and at least one preferred item.
Write a posting Jordan fully matches and Gap Analysis returns an empty list, which leaves
step 4 unable to tell "no gaps found" from "the stage is broken".

The bracketed-list case, "experience with AWS (Lambda, RDS, S3)", stays in the sample, but
the fixture quotes the whole bracketed string so it matches. Baking a legitimate drop into
the canonical pair would pin it at `dropped_count == 2` forever, where an expected two
looks identical to a new third. The recombination limit gets its own small test with a
hand-written fixture instead.

The test that runs the sample through with the canonical fixture isn't a happy-path smoke
test. It's what pins the fixture to the sample. Edit `sample_posting.txt` without updating
the fixture and it fails straight away, and that's the only thing keeping the demo from
degrading quietly over time.
