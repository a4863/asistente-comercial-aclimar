# Phase 3D Analysis — Email Thread Reconstruction

**Status:** STOPPED FOR DECISION (BLOCKED under Analyze Task)
**Date:** 2026-09-23
**Baseline:** `ba5f90d` on `codex-work`
**Task:** `docs/plans/implementation-phase-3d-analysis-task.md`

## 1. Objective, context, and interpretation

Determine whether the persisted, account-scoped email corpus can be grouped into auditable `Conversation` records using technical header evidence, including late arrivals and corrections. This is an analysis of rules, data sufficiency, and a possible implementation boundary; it is not authorization to implement. Phase 3C already persists one `EmailMessage` per `SourceRecord`, potentially multiple IMAP locations for that email, and normalized text/header fields. Phase 3D must operate on those logical email/source rows, **not** on locations as if each location were a different message.

The fixed hierarchy is Message-ID, In-Reply-To, References, then normalized subject only as secondary evidence. Insufficient or conflicting evidence must not silently merge conversations. Participants, dates, folder, CRM context, and semantic similarity cannot independently establish membership.

## 2. Documentation and implementation consulted

- `AGENTS.md`; `skills/analyze-task/SKILL.md`; this phase's analysis task.
- `docs/functional-spec.md` §§5.1–5.4, 21–24; `docs/data-model.md` §§3–5, 10, 12; `docs/architecture.md` §§3–4, 6, 9–11; `docs/security.md` §§4, 6–8; `docs/testing-strategy.md` §§2–5, 7–9.
- `docs/plans/implementation-phase-3c-plan.md` and approved 3C decisions; accepted 3C service, repository, adapter, model, migration, and synthetic tests.

No required document is missing. No tests were run: the Analyze Task read-only restriction excludes test commands that create databases or runtime files.

## 3. Current state and authoritative boundaries

- `EmailMessage` stores `normalized_message_id`, `in_reply_to`, `references_header`, `subject`, `source_record_id`; `SourceRecord.source_system_scope` identifies the account. The adapter's `_optional_text` **only strips surrounding whitespace**. Thus the `normalized_message_id` name does not establish canonical Message-ID validation, case handling, or parsing. References remains one text field, not a parsed ID list.
- `Conversation` has an auto-increment ID, `provenance`, and nullable `superseded_at`; it has no account scope, stable thread key, successor link, or revision. `ConversationMembership` has one unique `source_record_id`, one `conversation_id`, one `evidence_type`, and one `evidence_reference` limited to 255 characters. The physical migration implements those constraints. No thread reconstruction service, thread-specific repository, or thread tests exist.
- The general `AuditEvent` can retain bounded event metadata but has no typed old/new conversation relation or immutable membership snapshot. `SourceObservation` records synchronization observations, not historical thread-edge decisions. `IdempotencyIdentity` is generic and has no approved conversation-key contract.
- Phase 3C deliberately represents genuine duplicate Message-IDs as separate email/source records when identity evidence is insufficient. A move or UIDVALIDITY reset may give one email multiple locations; thread reconstruction must deduplicate by `EmailMessage.id`/`source_record_id` and ignore location state as thread identity.
- Threading is an assistant-owned, local derived state. It must neither access IMAP again nor execute mailbox/CRM/Calendar/AI actions. Header text remains untrusted data, never instructions.

## 4. Reconstruction algorithm candidate — NOT APPROVED

This describes a technically coherent candidate, not a selected policy. Decisions in §8 are prerequisites.

1. Read a consistent snapshot of all `EmailMessage`/`SourceRecord` rows in the configured account scope, including messages whose prior IMAP location is unavailable. Use exactly one logical email node per source. Do not use folder, UID, or UIDVALIDITY to define thread identity.
2. Parse Message-ID, In-Reply-To, and ordered References into validated, bounded canonical tokens under one versioned normalization rule. Retain parse failures and all candidate evidence as data; never interpret a header as an instruction. Index token → **all** local email nodes, not one node. A token resolving to zero nodes is external/missing; more than one is ambiguous. Self-links and cycles are rejected or isolated under an approved rule.
3. Build candidate directed parent/ancestor edges. A unique In-Reply-To target is potential direct-parent evidence. Each References token is potential ordered ancestor evidence; the final resolvable token is not automatically a direct parent when intermediates are missing. A Message-ID identifies a message node and does not, alone, join two messages. Subject can corroborate or flag a candidate but cannot independently create an edge under the approved hierarchy.
4. Compare all evidence for a message before accepting an edge. If In-Reply-To, References, duplicate IDs, or cycles produce incompatible components, leave the conflicting edge unresolved and do not bridge components until the conflict policy is approved. Avoid transitive merging through an ambiguous node. A malformed or missing Message-ID never becomes a guessed identity; a reply may still have a unique external parent token, but whether two such orphans may group by that missing token is undecided.
5. Construct connected components only from accepted, unambiguous technical edges. Recompute affected components when mail or stored headers change; late root arrival may connect prior orphans. Diff the computed assignment against persisted current membership and apply the approved create/reuse/merge/split policy in a transaction that also records evidence, provenance, and audit. A retry with unchanged inputs must not create new conversations, memberships, or audit entries.

The candidate is deliberately conservative. It cannot be turned into an implementation plan until normalization, conflict handling, component lifecycle, and schema decisions are approved.

## 5. Evidence and edge-case findings

| Case | Confirmed safe boundary / unresolved choice |
| --- | --- |
| A replies to B via In-Reply-To | Unique, valid local B is direct-parent evidence; whether contradictory References vetoes it remains a decision. |
| References chain with missing intermediates | Preserve ordered tokens; do not invent absent messages. Whether shared missing ancestors connect local orphans is undecided. |
| Root arrives after replies | Re-evaluate candidate edges and components. The policy for merging existing conversations and preserving prior identities/history is undecided. |
| Duplicate Message-ID on unrelated emails | Index must retain both candidates. A reference to that token is ambiguous unless a separately approved disambiguation rule exists; 3C's occurrence policy does not make Message-ID unique for threads. |
| Missing/empty/malformed Message-ID | No own canonical token; never guess one from subject, sender, date, or folder. Rules for otherwise valid outgoing references and orphan grouping remain open. |
| Same subject, independent emails | No subject-only merge. A forwarded message or `Re:`/`FW:`/`Fwd:`/localized prefix is not itself technical linkage. The exact secondary subject-normalization rule remains open. |
| Long chain with changed subject | Technical links can still support one component; subject mismatch cannot silently override them without an approved conflict rule. |
| One reply points to two existing components | In-Reply-To versus References precedence is insufficiently specified; neither automatic bridge nor automatic preference is authorized. |
| Cross-folder move / UIDVALIDITY reset | Multiple locations of one `EmailMessage` contribute one node; changes of location do not create or split a thread. A separate ambiguous 3C occurrence remains a separate node. |
| Replay / corrected stored headers | Must recompute deterministically and preserve prior derivation/evidence. Whether corrections may split a prior component and how the history is represented is undecided. |

## 6. Membership, identity, provenance, and transaction findings

The logical model forbids a message in multiple conversations and permits no membership when evidence is insufficient. It does **not** say whether a technically unlinked root gets a singleton `Conversation` or no membership. This affects late-root merges and stable identity.

For current membership, a bounded `evidence_reference` could point to a source ID or an evidence digest rather than storing a long References header. Its exact type/value contract is not approved. A single `evidence_type`/`evidence_reference` cannot faithfully express multiple supporting and conflicting header edges or an assignment's revision history. Raw headers or body must not be copied into audit, logs, idempotency keys, or result fields.

An auto-increment `Conversation.id` is a database identity, not a deterministic component identity. A full-corpus pass could reuse an existing row by current membership; when two components merge or one splits, however, choosing a survivor/new ID and updating memberships changes externally observable IDs. `superseded_at` alone does not identify the successor or preserve the old assignment. The current unique `source_record_id` constraint prevents keeping both old and new membership rows for one source. Merely updating/deleting rows loses the old membership/evidence unless an approved append-only history contract exists. Generic bounded `AuditEvent.outcome_reference` is not a typed replacement for that history without an explicit policy.

A safe candidate transaction boundary is: compute from a stable local snapshot; validate that relevant source/header versions have not changed; then atomically persist one approved component change with membership/evidence/history/audit and any conversation supersession. On conflict or commit failure, roll back and recompute on a later run. A full account-scoped rebuild is a simple deterministic baseline; incremental recomputation may be an optimization only if it is proven equivalent for late roots, merges, splits, and corrections. Neither trigger nor transaction granularity has yet been approved. No external transaction or mailbox operation belongs here.

## 7. Schema-gap assessment

**The current physical schema is not sufficient for the complete 3D contract as written.** It can represent a current one-conversation-per-source assignment and a coarse single evidence reference, and it can leave uncertain sources unassigned. It cannot safely retain the full evidence decision and prior membership when late arrivals or corrected headers merge/split components while preserving traceable history and stable conversation identity. The limitation is structural, not a missing repository method.

Minimal alternatives requiring approval:

- **A — explicit thread evidence and history:** add an append-only evidence/decision record for parsed header edges and conflicts; append-only membership/assignment history with old/new conversation references and reason; and an account-scoped stable conversation key plus an explicit supersession/successor relationship. Keep the existing unique current membership. This supports replay, conflict review, late-root merge, and correction/split without overwriting history, but requires a separately approved data-model update and migration.
- **B — constrained current-schema behavior:** forbid automatic merge/split or accept only current membership plus bounded generic audit metadata. This avoids a migration but cannot fulfill the requested late-root/component-merge and lossless provenance behavior without weakening approved auditability. It is not implementable under the present task's requirements without changing those requirements explicitly.

No schema, migration, or documentation contract is changed by this analysis.

## 8. Decisions pending before a 3D implementation plan

1. **Canonical header identity.** Define valid Message-ID token syntax, whitespace/comment/bracket handling, case policy, malformed/multiple In-Reply-To handling, ordered References parsing, maximum token/chain limits, and whether normalization is applied at ingest or only during thread derivation. The current adapter merely trims text.
2. **Edge/conflict policy.** Decide whether a valid In-Reply-To edge survives contradictory References, whether References may link local nodes across missing intermediates, how duplicate Message-ID targets are treated, and how cycles/self-links are rejected. In particular, decide whether one reply may ever merge two previously separate components.
3. **Orphans and subject.** Decide whether replies sharing a missing external ancestor may form a provisional component; whether an unlinked root/standalone message receives a singleton conversation or no membership; and what exact secondary subject normalization/use is permitted. Subject alone must not authorize a merge.
4. **Conversation lifecycle.** Define deterministic account-scoped conversation key/ID reuse, merge survivor or successor policy, whether changed evidence may split a component, and how late arrival/correction updates current membership without losing history.
5. **Data-model authorization.** Approve a schema/history design adequate for multiple evidence edges, ambiguity, membership revisions, and supersession, or explicitly narrow the functional and audit requirements. This decision must precede model/migration and repository planning.
6. **Recomputation boundary.** Approve a full-corpus baseline versus incremental strategy, trigger on 3C inserts/updates versus separate invocation, and transaction/revalidation unit. Incremental output must be equivalent to the approved full computation.

These are genuine alternatives with different outcomes; the Ambiguity Rule prohibits silently selecting one. No implementation code is proposed.

## 9. Dependencies, risks, and tests for a later approved plan

Internal dependencies: current email/source persistence, account scope, conversation/membership repository, audit/provenance boundary, and a future approved model/migration if alternative A is chosen. There is no need for IMAP, network, keyring, AI, CRM, Calendar, or a new package in the thread reconstruction service.

High risks: false transitive merge through duplicate IDs or a conflicting References chain; permanent mis-grouping after late root/correction; lost membership history on reassignment; nondeterministic IDs across rebuilds; accidental multiple memberships; and raw/untrusted header content in audit or error text. Treat headers as inert, bounded data and leave uncertain edges unresolved.

Fake-only test matrix after decisions: direct reply; ordered References with missing intermediate; late root; duplicate/empty/malformed IDs; conflicting In-Reply-To/References; cycles and self-link; independent same-subject and changed-subject chain; forwarded/localized prefixes; two-component bridge; cross-folder and UIDVALIDITY multiple locations; ambiguity remaining unassigned; account isolation; merge/split and old→new history; exact replay; metadata correction; deterministic full versus incremental result; concurrent-version/commit failure rollback; no raw content in audit/results; no real external access. Repository tests must prove physical one-current-membership constraint and any approved new history/key constraints.

## 10. Proposed subphases and exact Scope Lock

After decisions: (1) approve data-model/evidence/lifecycle contract and, only if selected, a migration and repository plan; (2) implement a pure header parser and graph decision engine with synthetic tests; (3) implement transactional persistence/rebuild and idempotency with fake-only integration tests. Each subphase requires its own approved plan and file list.

**IN SCOPE for this Analyze Task:** inspect the named documentation, accepted 3C code, model/migration/repository/tests; create only this analysis document.

**OUT OF SCOPE:** implementation, schema/migration changes, adapter/3C changes, semantic extraction, AI, CRM matching, Calendar, reply/filing proposals, drafts, moves, UI, scheduler, real mailbox/network/credentials.

**RESTRICTIONS:** no code or test edits, dependencies, database writes, migrations, external actions, or `main` changes. No plan or implementation is approved by this document. Only the explicitly requested analysis file, commit, and push are permitted writes.

## 11. Out-of-scope discoveries

- Phase 3C's `normalized_message_id` is trim-only. Correcting adapter or persisted historical headers is outside this analysis; the 3D parser contract must not presume stronger normalization.
- Phase 3C's incremental high-water processing does not by itself re-fetch a previously committed UID when its header changes in place. Automatic detection of such external metadata corrections is a separate 3C synchronization question; 3D must still define recomputation when a persisted email row does change.

## 12. Result

**STOPPED FOR DECISION.** The evidence hierarchy is established, but the conflict/orphan/lifecycle rules and the physical evidence/history representation are not. Resolve §8, then approve a separate 3D plan and Scope Lock before implementation.
