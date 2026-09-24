# Phase 5 AI Provider Decisions

**Status:** APPROVED
**Date:** 2026-09-24
**Analysis:** docs/plans/phase-5-ai-provider-analysis.md

## D1 — Provider and model

Approved:
- Provider: OpenAI API.
- Initial model: GPT-6 Luna.
- Model must remain non-secret configuration so a later approved change to GPT-6 Sol or another compatible model does not require an architectural rewrite.

Rationale:
- Phase 5 begins with structured email/thread analysis.
- Cost control is important for iterative testing.
- Quality must be evaluated through project-specific evals rather than assumed.

## D2 — API and transport

Approved:
- OpenAI Responses API.
- Official OpenAI Python SDK.
- New dependency is explicitly approved subject to normal dependency review and pinning.
- No web search, browser, computer-use, code execution, function tools, CRM tools, Calendar tools, IMAP tools, or other model-exposed execution capability in this phase.

## D3 — Structured response

Approved:
- Structured Outputs using strict JSON Schema.
- No free-form JSON as the primary contract.
- No tool/function calling for analysis output.
- Provider schema is a provider-facing projection and must map into existing immutable AnalysisCandidates.
- Existing Phase 4 domain/persistence contracts remain frozen.
- Malformed, refused, truncated, incompatible, or semantically invalid provider output must fail closed and map to the existing bounded failure semantics.

## D4 — Remote identifiers

Approved:
- Use per-request ephemeral aliases for selected messages.
- Do not transmit internal database IDs, AnalysisRun IDs, conversation stable keys, local hashes/digests, or other internal identifiers unless a later explicit change justifies them.
- Alias-to-source_record_id mapping remains local.

## D5 — Provider data controls and region

Approved:
- Prefer European processing / EU endpoint where supported by the active OpenAI API project/account and compatible with the selected model.
- Architecture must support provider-side data-control configuration without assuming the user's account has a particular entitlement such as Zero Data Retention.
- No claim that ZDR or a specific residency mode is active until verified on the actual account/project.
- Remote AI data remains governed by docs/security.md and docs/plans/remote-ai-data-policy.md.

## D6 — Sensitive content handling

Approved:
- Initial policy: fail closed on detected credential/token/secret-bearing excerpts.
- Do not implement masking/redaction that changes source text or offsets in Phase 5.
- If sensitive material that is prohibited from remote disclosure is detected in the selected remote payload, do not call the provider.
- Preserve local provenance and report a bounded local failure/degraded outcome without leaking the sensitive value.

## D7 — Operational bounds and credential handling

Approved:
- No streaming.
- Initial request timeout: 60 seconds.
- Maximum automatic retry count: 1, only for explicitly transient provider/network/rate-limit/server failure classes.
- No retry for authentication failure, quota/billing exhaustion, provider refusal, malformed output, policy failure, or local validation failure.
- Single concurrent remote analysis request per process for the initial implementation.
- Output must be bounded by strict schema plus a configurable provider output/token ceiling.
- API credential stored only in Windows Credential Manager through the existing keyring abstraction.
- No API key in TOML, Git, SQLite, logs, audit, exceptions, reprs, or browser output.
- Keep Phase 4 AnalysisRun provider_failure semantics for now.
- Dedicated AI reconnect/status UI is deferred; it must not be silently introduced in this phase.

## Frozen boundaries

Phase 5 must not weaken:
- Phase 4 evidence/provenance validation;
- prompt-injection boundary;
- proposal -> explicit approval -> revalidation -> execution -> audit;
- 30,000-character disclosed body limit;
- maximum six priors;
- no automatic attachment transmission;
- no external action authority for AI output.

## Planning direction

Plan Phase 5 in small increments, expected roughly as:
- 5A provider-neutral remote projection/schema;
- 5B non-secret config + credential reference;
- 5C OpenAI adapter with fake transport/SDK tests;
- 5D service/security integration regression;
- optional live synthetic smoke only under a separate explicit task.

No implementation subphase is automatically approved by this decision record.
