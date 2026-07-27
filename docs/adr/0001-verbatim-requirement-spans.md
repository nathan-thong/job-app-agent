# Requirement spans are copied word for word, and the agent checks them

## Decision

The Extraction stage copies each Requirement's `text` out of the Job Posting word for
word instead of paraphrasing it. A plain function in the agent layer, not a Pydantic
validator, drops any span that doesn't appear in the posting once both sides are
normalised.

## Why copy rather than paraphrase

A paraphrase the model invented reads the same as one it extracted. There's no way to
tell them apart, so paraphrased output can't be checked at all. A copied span can be
tested against its source, which turns "did the model make this up?" into a substring
comparison.

Copying also keeps the employer's own words available to the Draft stage, and those are
the words that matter when you're tailoring an application to a posting.

The model's judgment still has a home. It goes in `necessity`. Evidence gets copied,
judgment gets classified, and the two never share a field.

## Why not a Pydantic validator

Checking a span against its source needs the posting, and the posting isn't a field on
the response. A validator would have to read it from `ValidationInfo.context`, which is
optional. That leaves two choices, both bad.

Skip the check when context is missing, and the validator quietly does nothing in the
fixture-driven tests that make up most of the suite. Those are exactly the places you'd
assume it was protecting you. Or raise when context is missing, and `ExtractionResponse`
can't be built at all without dragging the posting along with it.

The first is the dangerous one. It looks like an unconditional guarantee and isn't.

There's a cleaner way to say where the split falls. A response model answers whether the
data is well-formed, and that question needs nothing but the data. Fidelity asks whether
the data matches a source, which needs both. Different questions, different homes.

The model still does one useful thing here. `dropped_count` has no default, so the
response can't be constructed if the agent skipped the check. The schema enforces that
the check ran. It never claims the check passed.

## Normalising: representation, not content

Both sides are normalised before comparison, for case, whitespace, quote style, dash
style, leading bullet markers, and trailing punctuation. None of these change a word, so
none of them can turn a paraphrase into a match.

Fuzzy matching is ruled out. Edit distance, token overlap, and embedding similarity all
make different word sequences equal, which is the exact failure this check exists to
catch.

Dashes get mapped to a single character rather than stripped. Stripping them turns
"e-commerce" into "ecommerce" and "co-op" into "coop", which makes genuinely different
strings equal. Mapping fixes the "3–5 years" against "3-5 years" mismatch without
touching hyphens inside words.

## Consequences

Not every dropped span is a hallucination. A posting reading "experience with AWS
(Lambda, RDS)" might produce "experience with AWS Lambda", which is a sensible way to
split it up and still fails the substring test. A bare count can't tell that apart from
a fabrication, so dropped spans get logged on the server rather than only counted.

`dropped_count` isn't shown in the UI to start with. Telling a user that four
requirements were discarded gives them nothing to act on and costs confidence for
possibly no reason.

The check is a second layer of defence against prompt injection, but only against
fabrication. Text an attacker planted in the posting is a substring of the posting, so
anything the model repeats back passes cleanly. That's not a reason to soften the prompt
delimiters.

The prompt still tells the model to copy exactly. The check backs that instruction up
and doesn't replace it. A prompt that doesn't ask for copied spans will fail this check
constantly, and you'll lose an afternoon debugging normalisation that was never the
problem.
