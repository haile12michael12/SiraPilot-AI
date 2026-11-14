# Prompt management and AI evaluation

See the [AI architecture](../ARCHITECTURE.md#ai-architecture) for provider, validation, orchestration, privacy, and approval boundaries. This document defines how prompts and their evaluations should be managed as concrete AI use cases are added.

## Prompt definitions

Keep prompts in source-controlled, feature-owned templates rather than embedding long prompt text in routers, repositories, or provider adapters. Give each prompt a stable identifier and immutable version. A prompt definition records its intended use, required input fields, output schema, and model capabilities it relies on.

Render templates from explicitly validated, named inputs. Treat user text, imported documents, job listings, and tool results as untrusted data, not instructions. Pass only the context required for the use case, keep data boundaries clear, and do not include credentials or hidden system configuration in rendered prompts.

Every AI call and evaluation result identifies the prompt version used. Updating a prompt creates a new version so changes can be reviewed and evaluated; do not silently rewrite prompts at runtime or let model output modify trusted instructions.

## Evaluation

Keep a small, versioned set of synthetic or appropriately de-identified cases for each implemented prompt. Cover valid structured responses, missing or contradictory input, untrusted instructions embedded in source content, and outputs that violate the response schema or safety policy. Assert both schema validity and feature-level quality criteria.

Run evaluations with deterministic fake providers in the default test suite. Live-provider evaluations are opt-in, use explicit credentials and synthetic inputs, and report provider/model and prompt versions. Do not make network calls or require provider secrets in ordinary CI.

Evaluation results are regression evidence, not permission to bypass runtime validation or user approval. A prompt passing its evaluation never makes model output trusted or authorizes a consequential action.
