# Phase 5A Implementation Task — Remote AI Projection and Structured Decoder

**Status:** Approved for Implement
**Date:** 2026-09-24
**Plan:** docs/plans/implementation-phase-5-plan.md
**Decisions:** docs/plans/phase-5-ai-provider-decisions.md

## Objective

Implement only the pure local Phase 5A boundary that converts the accepted Phase 4 AnalysisInput into a minimized provider-facing projection and decodes a bounded structured response back into AnalysisCandidates.

No network.
No OpenAI SDK.
No credentials.
No configuration changes.
No service/repository/domain/persistence changes.

## Exact Scope Lock

Create only:

1. app/integrations/ai_schema.py
2. test/test_ai_schema.py

No other tracked file may change.

## Required behavior

### Request projection

Build a pure, immutable local projection from AnalysisInput.

Remote payload may contain only:
- ordered per-request aliases: m0 target, m1..m6 priors;
- role;
- sender when present;
- recipients when present;
- subject when present;
- message_date when present;
- exact already-selected body_excerpt.

Do not expose remotely:
- account_scope;
- source_record_id;
- conversation_id/stable_key;
- AnalysisRun/run IDs;
- input_digest;
- original_body_digest;
- span digests;
- IMAP folder/UID/UIDVALIDITY;
- raw MIME;
- attachment metadata/content;
- CRM/Calendar data;
- audit/log data;
- config;
- credentials.

Alias -> source_record_id mapping must remain local only.

Revalidate inherited limits:
- target + at most 6 priors;
- total disclosed body text <= 30,000 Python characters;
- target first;
- preserve selected order;
- metadata-only prior may have empty body_excerpt.

Also impose a finite local UTF-8 serialized request-byte ceiling using a fixed constant in this module for 5A. The exact future config value is 5B; this phase must make overflow testable and fail closed.

### Sensitive-content preflight

Before a remote payload can be returned, inspect the actual disclosed metadata/body excerpts for recognizable prohibited secret-bearing material.

At minimum detect conservative high-confidence forms such as:
- PEM private-key blocks;
- bearer token syntax;
- obvious API-key/token/password assignment patterns;
- common secret prefixes only when detection can be implemented without provider-specific guessing.

On detection:
- fail closed;
- return/raise only a bounded value-free local code;
- do not mask or rewrite source text;
- do not include the detected secret in repr/exception text.

Avoid broad heuristics that would reject ordinary commercial numbers/text unnecessarily.

### Provider-facing strict schema

Expose a versioned strict response schema suitable for later OpenAI Structured Outputs verification.

Requirements:
- top-level additionalProperties false;
- object levels additionalProperties false;
- fixed candidate collections matching existing Phase 4 DTO graph;
- bounded arrays/strings where expressible;
- explicit nullable/required behavior;
- no action/tool fields;
- evidence uses message_alias + start_offset + end_offset + exact_text;
- SupportRef uses kind + zero-based index;
- use only JSON-schema constructs that can later be checked against verified provider support.

Do not claim provider compatibility in 5A; this is a local schema contract.

### Decoder

Decode an already-parsed JSON-shaped Python object into immutable AnalysisCandidates.

Required validation:
- reject unknown fields;
- reject wrong primitive/container types;
- reject bool where int/index expected;
- reject non-finite numeric values if any numeric field is accepted;
- reject invalid/unknown aliases;
- reject offsets outside disclosed excerpt;
- exact_text must equal disclosed excerpt slice;
- compute evidence SHA-256 locally;
- map alias back to local source_record_id;
- reject invalid SupportRef kind/index;
- reject duplicate supports where Phase 4 forbids them;
- reject unsupported enum values;
- reject excessive items/strings/depth/serialized response bytes;
- reject malformed timestamps;
- reject semantically inconsistent output;
- do not silently repair/drop/coerce provider output.

Question exact text must remain evidence-exact.

Quote state must not be trusted as free provider authority. If quote state is represented remotely, validate/derive it consistently with existing local quote semantics before DTO construction.

Dates must remain null/uncertain when not safely representable. Do not fabricate date resolution.

If an output cannot map cleanly to existing Phase 4 DTOs, reject it. Do not modify domain contracts.

## Exceptions / error surface

Use bounded local exception/error codes only.

No exception/repr may contain:
- email body;
- exact secret value;
- remote payload;
- local IDs/digests unless already non-sensitive fixed test identifiers.

## Tests

Cover at least:

1. target-only projection;
2. target + six priors;
3. alias reset per request;
4. exact remote field allowlist;
5. internal IDs/digests absent remotely;
6. 30k character enforcement;
7. seven-message enforcement;
8. target-first ordering;
9. metadata-only prior;
10. UTF-8 request-byte overflow;
11. PEM private key detection;
12. bearer secret detection;
13. obvious token/password assignment detection;
14. benign commercial lookalikes accepted;
15. error text does not include secret value;
16. strict schema has additionalProperties false recursively where applicable;
17. schema has no action/tool capability fields;
18. valid full AnalysisCandidates graph decodes;
19. alias -> source_record_id mapping local;
20. evidence offsets/text validated;
21. span digest computed locally;
22. wrong alias rejected;
23. wrong span rejected;
24. wrong exact text rejected;
25. invalid support kind/index rejected;
26. duplicate support rejected where prohibited;
27. unsupported enum rejected;
28. overlong/excessive response rejected;
29. malformed timestamp rejected;
30. bool-as-int rejected;
31. unknown keys rejected;
32. question text/evidence mismatch rejected;
33. quoted/current question handling remains consistent with local rules;
34. no network/SDK/keyring/config/service/persistence interaction.

Use only synthetic data.

## Restrictions

- no OpenAI import;
- no network/socket calls;
- no dependency changes;
- no config edits;
- no credential access;
- no app/services/email_analysis.py change;
- no app/domain change;
- no persistence/model/migration change;
- no logs of source content;
- no cache/untracked inspection.

## Validation

Run:

python -m pytest test/test_ai_schema.py

Then:

python -m pytest

Tracked diff must contain exactly:
- app/integrations/ai_schema.py
- test/test_ai_schema.py

## STOP conditions

STOP if:
- existing Phase 4 DTOs cannot express the decoded structure safely;
- quote/date/evidence semantics require domain changes;
- secret detection would require rewriting disclosed source offsets;
- provider-specific assumptions are needed;
- another production file appears necessary.

## Completion

Commit:

Implement phase 5A remote AI projection

Push only origin/codex-work.
