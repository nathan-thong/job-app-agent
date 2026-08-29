# Provider output is not an API response

Each stage has a Pydantic provider-output model containing only fields the model owns, separate from its request and public response models. Anthropic tool schemas and mock fixtures use the provider-output shape; the agent parses that output, runs source checks and normalization, adds counters and other derived fields, and only then constructs the response. Reusing the public response model as the tool schema would ask the model to invent backend-owned facts such as drop counts, verdicts, salutation, or candidate identity.

## Consequences

The generic LLM client accepts a stage-supplied parser so it can retry one malformed live payload without knowing stage semantics, and agents use the same parser for fixtures. Provider-output models remain internal and never cross the HTTP boundary.
