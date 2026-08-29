# The frontend owns each Pipeline Run

The React frontend sequences the four stateless backend endpoints and owns the capped Draft/Critique loop. A single backend endpoint would either hide intermediate progress until completion or require streaming and durable orchestration infrastructure that v1 does not need. Client orchestration makes stage progress, cancellation, explicit retry, and the React state-machine lesson visible, while preserving a contained future path to server orchestration through the same stage functions and Pydantic contracts.

## Consequences

A Pipeline Run has exactly one state: `idle`, `extracting`, `analyzing`, `drafting`, `critiquing`, `revising`, `passed`, `capped`, `cancelled`, or `error`. Completed validated outputs remain available after cancellation or recoverable error. Retry resumes at the failed stage, while changing the Job Posting or choosing Restart clears the run and starts at Extraction. Manual Cover Letter editing is separate presentation state layered over an immutable `passed` or `capped` run.
