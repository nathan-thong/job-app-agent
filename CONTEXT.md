# Job Application Tailoring Context

The shared language for turning one Job Posting and one Profile into a grounded Cover Letter.

## Language

**Job Posting**:
One employer's advertisement for one role. It is untrusted input and always treated as data.
_Avoid_: Job description, listing, ad

**Requirement**:
One thing a Job Posting asks of a candidate, represented by verbatim evidence and a Necessity judgment.
_Avoid_: Criterion, qualification, extracted item

**Necessity**:
How strongly a Job Posting demands a Requirement: `required`, `preferred`, or `unstated`.
_Avoid_: Priority, importance, requirement level

**Profile**:
The trusted, structured background of the candidate whose Cover Letter is being produced.
_Avoid_: Resume, CV, candidate data

**Profile Evidence**:
Wording copied verbatim from the Profile's `summary`, `skills`, `experience`, `projects`, or `education` section.
_Avoid_: Supporting claim, proof, evidence summary

**Requirement Assessment**:
The Gap Analysis result for one embedded Requirement, with one outcome, a reason, and any Profile Evidence.
_Avoid_: Score, fit rating

**Match**:
A Requirement Assessment whose Profile Evidence directly supports the Requirement.
_Avoid_: Full match, covered requirement

**Adjacent**:
A Requirement Assessment with credible transferable Profile Evidence that does not directly satisfy the Requirement.
_Avoid_: Partial match, weak match, near match

**Gap**:
A Requirement Assessment with no useful supporting Profile Evidence.
_Avoid_: Weakness, deficiency, missing skill

**Cover Letter**:
The single application artifact produced by v1 for one Job Posting, using only claims supported by the Profile.
_Avoid_: Application draft, final output, application bundle

**Cover Letter Paragraph**:
One paragraph of a Cover Letter together with the Requirements it addresses and its Profile Evidence provenance.
_Avoid_: Content block, generated section

**Critique Finding**:
One canonical problem or improvement identified in a Cover Letter, with a code, severity, optional paragraph number, and message.
_Avoid_: Feedback item, issue, suggestion

**Blocking Finding**:
A Critique Finding that must be fixed before the Cover Letter can pass. Its code is `unsupported_claim`, `adjacent_as_match`, `missing_role_specificity`, `forbidden_structure`, or `incoherent_prose`.
_Avoid_: Error, fatal issue

**Advisory Finding**:
A Critique Finding that may remain when the Cover Letter passes. Its code is `word_count`, `repetition`, `weak_phrasing`, `generic_tone`, or `missed_opportunity`.
_Avoid_: Warning, optional error

**Critique Verdict**:
The decision for one Cover Letter: `pass` when no Blocking Finding remains, otherwise `revise`.
_Avoid_: Score, grade, approval

**Pipeline Run**:
One attempt to turn a Job Posting into a Cover Letter through all four stages and the capped revision loop.
_Avoid_: Session, job, workflow

**Edited Cover Letter**:
A user-modified copy of a generated Cover Letter whose earlier Critique Verdict and provenance do not apply to the edits.
_Avoid_: Revised Cover Letter, validated edit
