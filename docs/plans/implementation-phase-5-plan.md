# Phase 5 — OpenAI provider integration implementation plan

**Status:** proposed staged plan; no subphase is authorized by this document alone.
**Authority:** `docs/plans/phase-5-ai-provider-decisions.md`, the accepted Phase 4 contract and the approved remote-AI policy.
**Scope of this Plan Task:** this file only. No implementation, dependency, credential, provider request or live test.

## Objective and frozen boundary

Connect one OpenAI Responses API adapter to the existing synchronous `AIService.analyze(AnalysisInput) -> AnalysisCandidates` seam without changing Phase 4 domain, persistence, run lifecycle or approval authority. The local app remains single-user and localhost-only. Remote analysis can propose candidates; it cannot approve or execute email, CRM, Calendar or other actions. The accepted reserve → provider outside write transaction → reselect → atomic complete flow, completed replay, force versioning and stale handling remain unchanged. A provider failure continues to become bounded `failed_retryable/provider_failure`; invalid candidate output is rejected by the existing validation path. Do not add a route, scheduler, UI, migration or background activation under this plan.

### Preconditions before any 5C implementation or live enablement

1. Verify against **current official OpenAI documentation and the actual project/account** that the selected GPT-6 Luna identifier supports the Responses API, the intended strict Structured Outputs JSON Schema subset, the chosen output-token parameter, refusal/incomplete indications and compatible EU endpoint. Verify the official Python SDK version and its dependency tree; pin a reviewed compatible version or bounded range with a reproducible lock according to the repository's packaging practice. If any capability is unavailable, STOP; do not silently substitute another model, API, region or free-form JSON mode.
2. Verify the actual account/project's processing region, retention/training controls, billing and credential scope before enabling real use. Preference for EU is not a claim of EU residency or Zero Data Retention. If an acceptable EU route is unavailable or its behavior cannot be verified, leave AI disabled and request an explicit data-governance decision; do not fall back to a non-EU route automatically.
3. Use synthetic data and SDK/client doubles in all automated tests. No implementation subphase automatically authorizes a real credential, provider call or transmission of commercial content. Optional live smoke needs its own approved task.

## Shared contract for the increments

`AnalysisInput` contains the target plus at most six priors and at most 30,000 Python characters of selected body excerpts. It is **not** serialized to the provider. A new projection constructs ordered records with per-request aliases `m0` (target), `m1`…`m6` (priors), role, sender, recipients, subject, UTC message date when present, and the already-selected exact `body_excerpt`. Omit absent optional metadata. This is the complete remote data allowlist. Do not send account scope, source/DB IDs, run/conversation IDs or stable keys, input/original/span digests, IMAP location, raw MIME, attachment data, CRM/Calendar data, audit/logs, configuration or credentials. Alias→source ID and original-body digests stay in local memory only. The selected subset must be relevant to the one analysis; no additional records are fetched in the adapter. Enforce both inherited character limits and a configurable UTF-8 serialized request-byte ceiling before the SDK sees the payload.

The provider-facing response is a versioned strict object with `additionalProperties: false` at every object level and required fields, using empty arrays or explicit null for absent values. Its top-level keys mirror the existing candidate collections: `summary`, `facts`, `inferences`, `proposals`, `questions`, `commitments`, `tasks`, `next_steps`, `response_needed`, `commercial_risk`, `priority`, `context_mentions`. Every array has an explicit bounded item count; every string has a bound no greater than the corresponding Phase 4 domain/database bound. Objects map field-for-field to the Phase 4 DTOs, except evidence uses `{message_alias,start_offset,end_offset,exact_text}` rather than local ID or digest, and nullable evidence fields use null. `SupportRef` is `{kind,index}` with existing zero-based typed collection indexes and preserved order. The schema uses only constructs verified supported by the selected strict Structured Outputs mode; where provider-side `maxLength`/`maxItems` is unsupported, enforce those limits in the local decoder before DTO construction. Do not weaken a domain bound to satisfy the provider.

For each evidence object, resolve only an alias from this request; require integer Python-character offsets with `0 <= start < end <= len(disclosed excerpt)` and exact equality of `exact_text` to the excerpt slice. Then compute the span SHA-256 locally, construct `EvidenceCandidate` with the locally mapped `source_record_id`, and let Phase 4 repository validation recheck against the full stored body. Reject aliases outside the request, unknown fields, duplicate support refs, invalid reference kinds/indexes, unsupported enum values, cycles through support references, overlong values, impossible evidence and malformed dates; never repair or silently drop fields. `QuestionCandidate.question_text` must equal its exact evidence text; quoted/current state must be derived locally from the existing quote classifier and finally revalidated against the original body, not trusted as a provider claim. `resolved_due_at`, task `due_at` and next-step `target_at` may be populated only when valid unambiguous timezone-aware ISO timestamps are returned with supporting source evidence and accepted by existing validation; ambiguous/relative dates remain uncertain/null rather than fabricated. An inability to map the chosen strict schema into every required DTO safely is a STOP condition, not permission to change Phase 4 contracts.

Before projection leaves the process, a conservative local preflight checks the **actual disclosed excerpt and metadata** for recognizable password/API-key/bearer/OAuth/private-key material and secret assignment patterns. On detection, fail closed with a bounded, value-free error; do not mask or alter text/offsets, and do not call the SDK. This is defense in depth, not a guarantee to detect every possible secret. Tests must cover positive and benign lookalike cases. If security review cannot agree an implementable detector with acceptable false-positive behavior, STOP before remote enablement and seek a separate decision. Email text remains untrusted data in a separately delimited user/data payload; trusted instructions are static application text. Never interpolate email into the instruction channel or expose tools/functions.

## 5A — local projection, strict response schema and decoder

**Goal:** make disclosure and candidate conversion testable without network or credentials.
**Proposed Scope Lock:** `app/integrations/ai_schema.py`, `test/test_ai_schema.py` (create only).
**Prerequisites:** this plan and Phase 5 decisions separately approved for 5A; accepted Phase 4 DTO contract. No SDK capability assumption is used in the pure logic.

**Behavior:** expose pure functions to validate/build the allowlisted request and local alias map, return a versioned provider schema, and decode a bounded JSON-shaped response into immutable `AnalysisCandidates`. Prefer a private immutable projection result with only payload plus local map; no persisted identifiers in its remote payload. Recheck the inherited seven-message/30k limits and reject excessive serialized bytes. Use strict parsing: reject unknown keys, non-finite numbers, booleans as indexes, excessive depth/bytes/items, invalid aliases/offsets/text, malformed timestamps/support graph, refusal-like or incomplete response envelopes, and any output not expressible as Phase 4 DTOs. Do not log, serialize or put source text in exceptions/reprs. The sensitive-content gate runs before a remote payload is returned. Define fixed local bound constants and make the request-byte and response-byte ceilings nonzero, finite and covered by tests; provider output-token ceiling is configured in 5B. Keep schema-generation details compatible with the pre-implementation SDK verification gate.

**Tests:** target/prior ordering and alias reset each request; exact field allowlist and absence of internal IDs/digests; 30k/seven-message and UTF-8 byte overflow; metadata-only prior; offset/exact-text/span-digest mapping; all DTO collections and typed support refs; quote-state derivation; malformed, unknown, oversize, truncated, refused and inconsistent output rejection; known secret/token/private-key patterns prevent projection, benign lookalikes do not disclose secrets. No sockets or SDK import.
**Focused validation:** `python -m pytest test/test_ai_schema.py`
**Full validation:** `python -m pytest`
**STOP:** a required output cannot be represented under strict schema or existing DTO/evidence rules; a sensitive preflight cannot be made acceptably fail-closed without changing source offsets; extra source classes are needed.
**Expected commit:** `Implement phase 5A remote AI projection`
**Exclusions:** no SDK, network, keyring access, config, service/domain/persistence edit, migration or real data.

## 5B — non-secret settings and logical credential reference

**Goal:** validate a disabled-by-default OpenAI configuration and isolated keyring lookup without creating a credential.
**Proposed Scope Lock:** `app/config.py`, `test/test_config.py`, `test/test_credentials.py` (modify only; existing `app/security/credentials.py` stays unchanged because its `CredentialStore.get_secret(service, account)` already suffices).
**Prerequisites:** 5A accepted; official endpoint/capability review for any selectable base URL.

**Behavior:** add an `[ai]` non-secret table and frozen settings with `enabled=false` by default, provider fixed to `openai`, model defaulting to the **verified** GPT-6 Luna identifier, timeout exactly 60 seconds for this increment, maximum one automatic retry, a required positive configurable output-token ceiling when enabled, a finite positive request-byte ceiling, an approved EU endpoint/base URL setting, and logical credential service/account names independent of IMAP. Reject secret-bearing and unknown `[ai]` keys, malformed types (including bool-as-int), invalid/empty refs, non-HTTPS/unapproved hosts, URL credentials/query/fragment, and inconsistent enabled settings with value-free errors. If no verified EU-compatible endpoint is configured, keep AI disabled; never silently route elsewhere. Credential lookup occurs only when an enabled adapter operation starts through the existing keyring protocol; missing/revoked secret is a bounded AI-only failure. Do not materialize or print the secret in settings, repr, logs or result objects. Exact model/endpoint choices are gated by the current official/account verification above, not guessed from historical docs.

**Tests:** disabled defaults perform zero keyring/network calls; valid non-secret settings; unknown/secret TOML key rejection; URL/host/region validation; missing or revoked fake-keyring secret; AI/IMAP credential independence; no secret in repr/errors/log capture; output/request bounds.
**Focused validation:** `python -m pytest test/test_config.py test/test_credentials.py`
**Full validation:** `python -m pytest`
**STOP:** verified SDK/region options cannot be expressed safely with the proposed settings, or a secret would need to enter TOML/DB.
**Expected commit:** `Implement phase 5B OpenAI configuration boundary`
**Exclusions:** no real credential creation, provider SDK/dependency, network, UI/reconnect screen or service/domain/persistence changes.

## 5C — concrete OpenAI adapter

**Goal:** implement the one remote `AIService` behind the existing protocol.
**Proposed Scope Lock:** `app/integrations/openai_analysis.py` (create), `test/test_openai_analysis.py` (create), `pyproject.toml` (modify).
**Prerequisites:** accepted 5A/5B; all official SDK/model/schema/endpoint, account data-control, version/pinning and billing gates above passed; separate approval of this exact Scope Lock.

**Behavior:** use the reviewed official OpenAI Python SDK and Responses API with the approved configured model, strict Structured Outputs schema, static trusted instructions and 5A's minimized untrusted payload. Supply **no** tools/functions, no streaming and no SDK implicit retries (adapter owns at most one retry). Retrieve the API credential through the injected `CredentialStore` only immediately before a call. Enforce one in-process concurrent remote request (other requests fail bounded or wait only within the overall deadline), 60-second overall deadline including any retry, explicit per-attempt timeout, bounded output tokens, request/response bytes and maximum two attempts total. Retry once only for verified transient connection/timeout/rate-limit/server classes with a bounded delay inside the deadline; do not retry auth, quota/billing, refusal, policy, malformed/incomplete/oversize output or local validation. Treat a timed-out first attempt as potentially billed. Classify errors using SDK-supported typed status/error information, not raw text; raise only fixed value-free local codes. Do not log prompts, responses, headers, provider exception strings or keys. Decode through 5A, returning only `AnalysisCandidates`; do not persist or execute actions. Keep default OpenAI SDK tracing/telemetry and any automatic transport behavior subject to dependency review; STOP if the SDK cannot satisfy these bounds.

**Tests:** fake SDK/client injection proves exact endpoint/model/schema/timeout/token settings, no tools/stream, no implicit retries, keyring lookup only on enabled use, one active call, deadline and cancellation, transient second attempt only, auth/quota/refusal/incomplete/malformed no retry, secret-free exceptions/logs, valid DTO output, and zero real HTTP requests.
**Focused validation:** `python -m pytest test/test_openai_analysis.py test/test_ai_schema.py test/test_config.py test/test_credentials.py`
**Full validation:** `python -m pytest`
**STOP:** current official API lacks compatible strict schema/model/region; the SDK lacks enforceable retry/timeout/tool controls; safe DTO mapping requires a Phase 4 change; a real endpoint or secret is needed for automated tests.
**Expected commit:** `Implement phase 5C OpenAI analysis adapter`
**Exclusions:** no `app/services/email_analysis.py`, domain, repository, model, migration, route, scheduler, UI or live provider test.

## 5D — composition and security regression

**Goal:** prove the concrete adapter can be injected through the existing `AIService` seam without changing run or action semantics.
**Proposed Scope Lock:** `test/test_email_analysis_service.py`, `test/test_security.py` (modify only).
**Prerequisites:** 5A–5C accepted. Existing composition is explicit caller injection into `analyze_email_in_thread`; no production file must change merely to instantiate the adapter in a test or a separately authorized caller. There is presently no production analysis route/scheduler/factory, so **production activation is deferred** to its own approved Scope Lock rather than silently adding one here.

**Behavior/tests:** use fake client/keyring and isolated synthetic SQLite to exercise valid completion, provider failure, malformed output, stale source, rollback, provider-free completed replay and force versioning. Verify disclosure allowlist (no unrelated messages, attachments, MIME, CRM, Calendar, DB IDs, digests, logs, audit or secrets), sensitive-content fail-closed with zero calls, prompt-injection text treated only as data, no tool/action capability, and zero `ActionProposal`/`ApprovalDecision`/`ExecutionResult` or external writes. Default `pytest` must remain offline; importing the module or starting the app must not call OpenAI.
**Focused validation:** `python -m pytest test/test_email_analysis_service.py test/test_security.py test/test_openai_analysis.py`
**Full validation:** `python -m pytest`
**STOP:** any regression requires production service/domain/persistence changes, or a real endpoint is necessary to prove the test contract. Report and seek a separate task; do not expand this Scope Lock.
**Expected commit:** `Validate phase 5 OpenAI analysis security boundary`
**Exclusions:** no production code edits, UI/routes/scheduler, real network, mail/CRM/Calendar mutation or dedicated AI reconnect/status UI.

## Optional later live smoke — not part of Phase 5 automated increments

**Goal:** deliberate, separately approved synthetic-only connectivity check after account/region/data-control/billing review.
**Proposed Scope Lock:** none authorized now; the separate task must name exact script/test paths before work.
**Prerequisites:** explicit user opt-in, non-production key, verified account controls and endpoint, known spend ceiling; never default startup or test collection.
**Behavior/tests:** one synthetic thread, explicit command and visible confirmation; no commercial content or production credential. Record only bounded outcome metadata.
**Focused validation:** command to be specified in that later task; **not** `pytest`.
**Full validation:** normal `python -m pytest` stays entirely offline.
**STOP:** any uncertainty about account controls, endpoint, cost or credential scope.
**Expected commit:** to be specified by the separate approved task.
**Exclusions:** no automatic smoke, production data, real mailbox/CRM/Calendar actions or default-network tests.

## Plan acceptance and risks

Approve each subphase and its exact Scope Lock separately. Each implementation must inspect its own diff, run the listed focused and full suites, and stop on out-of-scope findings. Main risks are secret-bearing source excerpts, prompt injection, fabricated evidence/date semantics, provider schema incompatibility, data residency/retention assumptions, hidden SDK retry or telemetry behavior and retry cost. The gates and fail-closed mappings above prevent these risks from being silently accepted. The architectural documentation's historical statement that no provider was selected is superseded for this future Phase 5 increment by the approved, later Phase 5 decision record; the existing provider-neutral service boundary remains intact.

READY FOR APPROVAL
