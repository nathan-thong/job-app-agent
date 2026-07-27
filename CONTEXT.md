# Context

The domain language this project uses. These are the canonical names. Code, prompts,
and schemas should use them and nothing else.

## Job Posting

The raw text a user pastes in. One employer's advertisement for one role. Untrusted
input, always treated as data and never as instructions.

## Requirement

A single thing a Job Posting asks of a candidate. The Extraction stage produces these
and the Gap Analysis stage consumes them.

A Requirement holds two things, kept in separate fields:

- **Evidence.** The wording copied out of the Job Posting, word for word, not
  rewritten. Copying matters because it can be checked. A paraphrase the model
  invented reads the same as one it extracted. Copying also keeps the employer's own
  vocabulary available to the drafting stage, which is the vocabulary that counts when
  you're tailoring an application.
- **Judgment.** The model's reading of how necessary that evidence is.

## Necessity

How strongly a Job Posting demands a Requirement: `required`, `preferred`, or
`unstated`. This is judgment, not evidence. Postings signal it inconsistently, with
"must have", "a plus", or nothing at all, so it's inferred rather than copied.

`unstated` exists to keep the model's uncertainty visible. A two-value field forces a
guess, and a guess recorded as `required` reads the same as a stated "must have". The
third value also lets Gap Analysis decide how softly to treat an unstated Requirement,
instead of that policy being fixed in Extraction where it can't be changed.

## Profile

The candidate's background. The fixed side of the comparison. Unlike a Job Posting it's
trusted, structured, and not supplied per run.
