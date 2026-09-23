# Phase 4 — email/thread analysis: Analyze Task

**Status: STOPPED FOR DECISION — BLOCKED**
**Scope:** analysis only; no implementation authorization.

## 1. Objective, context, and interpretation

Assess whether the accepted local IMAP/threading foundation can support traceable commercial analysis of a reconstructed email conversation. Phase 4 is meant to identify summaries, exact questions, commitments, actions, deadlines, next steps, response need, risk, priority, and candidate business context while preserving `source → extraction → inference → proposal`. This report identifies the decisions required before a deterministic implementation plan. It does not select a provider, change a schema, or define an implementation task.

The application is local and single-user. Phase 3D3 supplies account-scoped current conversations and technical threading evidence; it does **not** implement commercial analysis. The CRM remains authoritative for company/contact/work/opportunity/offer master data, and AI has no authority to approve or execute actions.

## 2. Documentation consulted

- `AGENTS.md`; `skills/analyze-task/SKILL.md`; `docs/plans/implementation-phase-4-analysis-task.md`.
- `docs/functional-spec.md` §§3.4, 4, 5.4–5.6, 9, 11–16, 21–29.
- `docs/data-model.md` §§5, 7–12; `docs/architecture.md` §§3–5, 7, 10–11.
- `docs/security.md` §§4–9; `docs/testing-strategy.md` §§2–9; approved `docs/plans/remote-ai-data-policy.md`.
- Approved `docs/plans/implementation-phase-3d3-plan.md`; `app/domain/email_threading.py`; `app/services/email_thread_reconstruction.py`; relevant sections of `app/persistence/models.py` and `app/persistence/repositories.py`; relevant model/repository/threading tests.

No listed authoritative document was missing. No test suite or migration was run.

## 3. Current-state inventory and gap

| Existing capability | Verified state | Phase 4 gap |
| --- | --- | --- |
| Email corpus/threading | `EmailMessage` stores body, headers, subject, timestamps and one `SourceRecord`; current `ConversationMembership` plus append-only threading evidence/lineage exist. 3D3 reconstructs topology. | No commercial analysis unit, revision, run record, or input-selection policy. Thread reconstruction key covers ID headers, not body/content changes. |
| Derived data | `ExtractedFact`, `Inference`, `Proposal`, `FactSourceEvidence`, `InferenceSupport`, `ProposalSupport`; basic repository append methods. | No analysis-run identity or general dedupe/correction contract; only `ExtractedFact` has `superseded_at`. `value_reference` is 255 characters and is not an exact-question field. |
| Operational objects | `Question.question_text` is text; `Task`, `Commitment`, `NextStep`, `Alert` and `OperationalEvidenceLink` exist with lifecycle checks. | Commitment has no responsible-party field or certainty of deadline. Operational evidence can link a source ID but no approved message-local span convention. No current-analysis-versus-history relation. |
| AI boundary | Architecture calls for provider-agnostic `AIService`; tests require a deterministic fake. | No AIService interface, structured DTO, provider adapter, or remote-disclosure gate is implemented. No provider/model selected. |
| CRM identity | `CRMReference`, `CRMContextLink`, confirmed `IdentityLink` with correction history exist. | No Phase 4 policy for using confirmed identity versus candidate text mentions or live CRM API lookup. Similar names cannot become confirmed associations. |

The existing tests exercise basic derivation support, operational lifecycles/evidence, identity corrections, and threading; they do not establish commercial extraction, AI minimization, analysis replay, or changed-content correction behavior. There is **NO IMPLEMENTATION YET** of Phase 4 commercial analysis.

## 4. Proposed boundary and data flow — contingent, not approved

The boundary under analysis is local email-conversation analysis, not an external action workflow. Candidate flow: select account/conversation and relevant retained message content → construct a minimized, source-identified analysis input → enforce disclosure policy before any provider call → obtain structured *candidates* from provider-agnostic AIService/fake → validate evidence and classify fact/inference/proposal → persist with replay/correction provenance inside a local transaction → expose reviewable operational candidates. Exact unit, selection, revision, storage, and lifecycle transitions remain undecided below.

The input must never include an entire mailbox/database, unrelated customer records, credentials/tokens, logs/audit payloads, or attachment bytes. Email body/needed metadata may be disclosed remotely only at the smallest relevant message/excerpt/thread subset. Quoted old text and signatures are potential duplicates but no approved removal algorithm exists; removing them could erase the only evidence of a question. A provider failure must not turn a candidate into a persisted fact or trigger an external write. A persistence failure after a provider response must leave no partial derived state; retry behavior requires the analysis identity decision.

`Question.question_text` can hold exact text, but a source ID alone does not prove a verbatim location or distinguish a newly asked question from a quoted earlier one. `FactSourceEvidence` and `OperationalEvidenceLink` are reusable links, not a complete approved span convention. `Commitment` can begin in `detected`, `Task` in `proposed`, `Question` in `detected`, and `NextStep` in `proposed`; completion/fulfilment/answering cannot be inferred silently from model output. Response-needed, risk, priority, and commercial context are not automatically facts merely because a model returned them.

## 5. Candidate interfaces and model reuse, without selection

An eventual provider-neutral input would need scoped source identities, the deliberately selected text/metadata, a content/reconstruction revision, and disclosure classification. Output would need typed candidates, source-local evidence references, uncertainty, and no approval/execution command. The application service—not AIService—would validate output and map it to domain/persistence objects. A deterministic fake would use synthetic input only. Whether a provider adapter is built in Phase 4 is not implied by this analysis; the security policy permits minimized remote disclosure but does not select a provider.

Existing entities may represent some candidates: explicit source statements as `ExtractedFact`; conclusions such as response need or risk as `Inference`; recommendations as `Proposal`; exact questions as `Question` plus evidence; detected promises as `Commitment`; generated internal work as `Task`; proposed next commercial action as `NextStep`. This is a *possible mapping*, not an approved one. In particular, `Proposal` and `ActionProposal` are different: the latter concerns one concrete external mutation requiring explicit approval. Neither AI output nor an internal proposal may directly mutate IMAP, Calendar, or CRM.

Schema changes may be required for an analysis-run/content-revision identity, source-local evidence spans, commitment responsibility/date certainty, bounded classification values, and append-only corrections of inference/proposal/operational projections. The current physical model does not establish these semantics, so this report does not authorize columns, tables, migration numbers, or repository APIs.

## 6. DECISIONS REQUIRED FROM USER

**STOPPED FOR DECISION.** Each item has at least two reasonable interpretations with materially different replay, privacy, or data-model effects. Approve the desired semantics before planning implementation.

1. **Unit and trigger.** A: analyze the full current conversation on every content revision (simple context, larger disclosure/compute); B: analyze only the new/changed message with a bounded prior-context subset (smaller disclosure, needs aggregation and carry-forward rules); C: analyze an explicitly selected thread subset on demand (human control, less automatic coverage). Specify whether synchronization, thread repartition, and manual request trigger a run.
2. **Replay identity and changed content.** A: key on conversation ID plus ordered source IDs/content revisions (new run after any body/header/member change); B: key on selected excerpt/input digest and policy version (avoids irrelevant reanalysis but requires canonical selection); C: source/message-level keys with aggregation (different dedupe semantics). The 3D2 reconstruction key alone is insufficient because body changes can leave headers/topology unchanged. Define what happens when the same input yields different AI output.
3. **Exact-question evidence.** A: store verbatim question in `Question.question_text` with source ID and bounded message-local span/quote reference; B: retain exact question only as an `ExtractedFact` and link `Question` to it; C: use source ID without span (simpler, weaker verification). Decide how quoted historic questions are distinguished from newly asked questions and what evidence qualifies an `open → answered` transition.
4. **Commitment ownership and dates.** A: add explicit responsible-party classification/reference and date-certainty fields; B: encode them only in description/provenance (no reliable query/validation). Decide whether AI-detected promises stay `detected` until user/authoritative-source confirmation, and whether an explicit source promise can itself justify `confirmed`. Decide how relative/uncertain deadlines are represented.
5. **Candidate-to-record semantics.** A: create `ExtractedFact`/`Inference`/`Proposal` first and link operational objects; B: create operational objects directly with source evidence; C: persist candidates for review before creating operational objects. These differ in duplicate prevention, audit trail, and what AI may create automatically. Resolve response-needed/risk/priority value sets and whether they are inference, alert, proposal, or a combination.
6. **Reanalysis/correction.** A: append versioned analysis runs and explicit supersession links while retaining previous derivations and operational history; B: update current projections with separate audit records; C: retain parallel candidate sets pending manual reconciliation. Current `Inference`/`Proposal` and operational objects lack a general supersession relation. Define treatment of stale open questions/tasks/commitments; they must not silently disappear or become completed.
7. **Disclosure selection.** A: local deterministic extraction of relevant messages/excerpts before remote AI (requires an approved relevance/quote-dedup rule); B: send a bounded current-thread subset with no automated excerpting (more disclosure); C: require manual selection/confirmation for remote transmission (less automation). Set size limits, truncation behavior, and whether sender/recipient identities or any locally confirmed CRM context are included by default. All options must satisfy the approved minimization prohibitions.
8. **CRM boundary.** A: Phase 4 creates text-only candidate mentions and reuses exact locally confirmed identity links, deferring live CRM API reads to a later phase; B: Phase 4 performs minimal read-only CRM API lookup for the analysis (additional integration and disclosure boundary). Neither permits similarity-based confirmation or CRM writes. Decide whether a confirmed contact identity may influence candidate company/work/opportunity context, which can remain ambiguous.
9. **Failure/transaction status.** A: provider failure creates only a bounded local failure/audit marker and no derived records; B: keep a retryable analysis-run status record; C: no persisted status, relying on caller retry/logging. Specify local transaction scope for all candidates/evidence, and whether a changed source snapshot between provider call and commit aborts/retries or persists a versioned stale result for review.

These are functional/data/security decisions, not choices for the implementer to infer. No concrete AI provider/model is required to decide the provider-neutral contract; any later real adapter remains separately scoped.

## 7. Risks and controls

- **High — factual contamination:** inferred customer, promise, answer, risk, or priority becomes a fact or confirmed CRM relationship. Require typed candidates, evidence, explicit confirmation rules.
- **High — privacy/prompt injection:** oversized remote context, sensitive data or embedded instructions. Enforce a pre-provider allowlist/minimizer, no secret/attachment/log fields, output validation, and synthetic adversarial tests.
- **High — stale/duplicate operations:** changed body or thread membership with unchanged 3D2 key, replay producing duplicate tasks, or corrected analysis silently removing open items. Decide analysis revision, dedupe and append-only correction semantics first.
- **Medium — loss of exact evidence:** quote trimming or summary-only storage erases question wording/source location. Verify exact message-local evidence independently of model summaries.
- **Medium — external authority confusion:** AI-generated proposal interpreted as permission to draft, move, write CRM or Calendar. Keep ActionProposal approval/revalidation/execution separate.
- **Medium — provider failure:** output may arrive after source changes or persistence may fail after AI response. Revalidate local snapshot and use an atomic local write once semantics are approved.

## 8. Tests required after decisions

Use synthetic isolated unit, repository, service, security and fake-AI tests. Cover exact question wording and source/span; quotation versus new question; distinct fact/inference/proposal; responsible party and uncertain deadline; response-needed/risk/priority bounded values; initial lifecycle and evidence links; ambiguous identity/business context; no CRM writes; unchanged replay; body edit with unchanged technical thread key; merge/split/repartition effect on analysis identity; differing AI outputs for same input; correction preserving old records and open operational state; provider/validation/persistence failure; changed snapshot before commit; minimization/allowlist and no credentials, attachments, logs, unrelated records; injection text remaining data; no external mutation or automatic approval. Deterministic fake AIService and local SQLite only; no real production integration. No tests were executed during this analysis.

## 9. Conditional subphase split and Scope Lock

No implementation task is created. After decisions, prefer separately approved small tasks (roughly 2–4 tracked files each where practical): (1) analysis revision/evidence data-model decision and targeted migration/model tests, if needed; (2) provider-neutral DTO/validation/minimization with pure tests; (3) repository idempotency/correction primitives with focused tests; (4) local orchestration plus fake-AI acceptance/security tests. A real provider adapter and live CRM lookup require their own later authorization if selected. Exact paths, migration, order, and contracts depend on the decisions above.

**IN SCOPE now:** read the listed docs/code/tests and create only this analysis document.

**OUT OF SCOPE now:** implementation, real AI provider/model selection, CRM API integration, external writes, scheduler/UI, mailbox/Calendar changes, migrations, tests execution, and implementation-task creation.
**RESTRICTIONS:** no changes to production files, schema, dependencies, Git `main`, real accounts/databases, caches, or untracked files; this analysis alone does not approve implementation.

**OUT-OF-SCOPE DISCOVERY:** 3D3 thread reconstruction keys are based on ID headers, not body content (`app/domain/email_threading.py`). This is appropriate for topology but cannot serve as Phase 4 commercial-analysis revision. Do not alter 3D3; define a separate approved analysis identity in later design.

## 10. Result

**BLOCKED — STOPPED FOR DECISION.** The existing specification establishes goals and safety boundaries, but the decisions in §6 are necessary before a deterministic Phase 4 plan, schema change, AIService contract, or implementation can be approved.
