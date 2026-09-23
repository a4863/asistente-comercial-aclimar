# Phase 3D data-model design — thread evidence and history

**Status:** STOPPED FOR DECISION
**Date:** 2026-09-23
**Baseline:** `4471c52` (`codex-work`)
**Task:** `docs/plans/implementation-phase-3d-data-model-task.md`

## 1. Objective, context, and interpretation

Assess the minimum physical extension needed for the approved Phase 3D full-corpus email-thread reconstruction. The design must support one account-scoped, stable current conversation per logical email; new conversations on merge/split; queryable many-to-many lineage; immutable technical-evidence decisions and membership history; deterministic replay; and conservative ambiguity. This document changes no model, migration, repository, service, database, or dependency.

The six decisions in `implementation-phase-3d-decisions.md` settle the functional threading policy at a high level. They do **not** pick the physical shape of lineage, evidence history, current membership, or legacy-data backfill. The task's Schema-gap/STOP rule therefore applies. Sections below state the common requirements, competing viable schemas, and the decisions needed to make a final exact-column design; they are not an approved migration blueprint.

## 2. Sources consulted and current project state

- `AGENTS.md`, `skills/analyze-task/SKILL.md`, the task file, `implementation-phase-3d-analysis.md`, and approved `implementation-phase-3d-decisions.md`.
- `docs/functional-spec.md` §5.4 and audit/ambiguity rules; `docs/data-model.md` §§3–5, 10, 12; `docs/architecture.md` §§3–4, 9–11; `docs/security.md` §§4, 6–8; `docs/testing-strategy.md` §§2–5, 8–9.
- `app/persistence/models.py`, `app/persistence/repositories.py`, Alembic revisions `0002`–`0004`, and current model/migration/repository tests. No required document is missing.

`Conversation` presently has `id`, `created_at`, `provenance`, `superseded_at`. `ConversationMembership` has `id`, `created_at`, `conversation_id` FK, unique `source_record_id` FK, `evidence_type`, and `evidence_reference` (255 characters). There is no account scope, stable conversation key, successor relation, evidence-decision table, membership-history table, or thread reconstruction implementation. `ProvenanceRepository` only creates a conversation and inserts a membership; it does not merge/split or preserve assignment changes. The current unique membership enforces at most one *stored current* assignment per source, but does not enforce email source type or same-account assignment.

The existing schema admits legacy `Conversation` rows with no memberships, memberships pointing to non-email sources, or memberships from different account scopes in one conversation. No real database was inspected; those states are permitted by the physical constraints and must be addressed in a migration policy.

## 3. Confirmed contract and a documentation contradiction

Confirmed: D1 requires Phase-3D-local, versioned, case-insensitive canonical header tokens, ordered References, bounded tokens/chains, and invalid/multiple-In-Reply-To evidence without an automatic edge. D2 rejects duplicate targets, self-links, cycles, incompatible In-Reply-To/References bridges, and transitive merges through ambiguity. D4 requires append-only evidence/decision and membership history. D5 requires a **new** conversation for merge or split, with all predecessors/successors traceable; an old conversation cannot arbitrarily survive as the winner. D6 makes the initial reconstruction a separate local, full account-scoped corpus pass.

**Contradiction requiring approval:** `docs/data-model.md` §12 says uncertain thread membership remains absent, while approved D3 says every logical `EmailMessage` starts with or belongs to a singleton `Conversation` even without an accepted edge. For an ambiguous, malformed, or ID-less message, these prescribe different current-state rows. The task cannot silently treat a lower-priority decision file as an amendment to the higher-priority data model. Either update/approve the logical data model to require singleton membership or revise D3 to preserve unassigned messages. This is a prerequisite for exact `NOT NULL`, uniqueness, backfill, and test expectations.

## 4. Required physical invariants, independent of schema choice

1. Each `Conversation` has a locally stable identity and an account scope. New merge/split output rows receive fresh identities; prior rows remain queryable as superseded history. A key must not be computed from the current set of Message-IDs.
2. One logical `EmailMessage`/`SourceRecord`, regardless of its number of IMAP locations, has at most one current conversation. No new thread table should depend on folder, UID, or UIDVALIDITY. Account scope comes from `SourceRecord.source_system_scope` through `EmailMessage`.
3. Lineage supports one-to-many, many-to-one, and many-to-many predecessor/successor relationships. It must disallow self-edges physically and prevent cycles at least through a transactional graph check; a simple row-level `CHECK` cannot prove global acyclicity.
4. Every accepted/rejected/ambiguous header-edge decision has a bounded reference to the source email, header kind, ordinal, canonical-token fingerprint or bounded token, normalization version, candidate target when unique, decision/outcome, and a replay-safe identity. Malformed and missing-external-ancestor observations must be representable without fabricating a target `EmailMessage`.
5. Membership assignment history is insert-only. It must retain old and new conversation IDs, source, evidence/decision reference, timestamp, and reconstruction identity for each real assignment change. An unchanged full-corpus replay adds no row. Current membership is separately queryable or deterministically derived from immutable history, according to an approved choice.
6. Evidence/history and generic `AuditEvent` serve different purposes. History is the typed source of truth for why a message was grouped; audit records only a safe, bounded summary of a material transition. Neither table stores body text, complete References headers, credentials, or instruction-like content as executable directives.
7. All FK targets and uniqueness rules must be enforced in SQLite as well as SQLAlchemy. Cross-row account equality, email source type, lineage acyclicity, and insert-only behavior require either explicit service/repository checks plus tests or approved physical mechanisms; ordinary single-row `CHECK` constraints alone cannot enforce them.

## 5. Materially different minimal schema alternatives — STOP

The alternatives below both satisfy D4/D5 in principle but differ materially in tables, replay identities, constraints, query shape, and migration behavior. The task explicitly prohibits selecting one silently.

### Alternative A — current projection plus append-only event history

- Extend `conversation` with `account_scope` and a unique stable local key; retain `superseded_at` as the current projection of supersession.
- Retain `conversation_membership` as the one-row-per-source current projection, with bounded evidence reference to a typed decision record. Add an immutable `thread_membership_change` row for each assignment/reassignment, including nullable old/new conversation FKs, source FK, decision/reconstruction key, timestamp, and reason (`initial`, `merge`, `split`, `correction`).
- Add an immutable `thread_evidence_decision` row per parsed header token and decision/version; nullable target source FK for unresolved/malformed/missing targets; field kind, token position, bounded token digest, normalization version, decision domain, and replay key. A later result appends a new row rather than editing an old decision.
- Add `thread_lineage_change` (operation group, account, kind `merge`/`split`, timestamp, replay key) plus `thread_lineage_edge` (group FK, predecessor FK, successor FK, unique pair). This explicitly groups one operation's many predecessors and successors.

The current projection makes queries and the existing unique-source constraint simple, but the service must atomically update it and append history. A physical write outside that service could desynchronize them; tests must detect it. There are **four** new tables in this shape, plus changes to existing tables.

### Alternative B — append-only versions as the current-state authority

- Extend `conversation` with the same account/key fields, but derive current versus superseded status from immutable lineage events rather than trusting a mutable `superseded_at` projection.
- Replace or stop using current `conversation_membership` as authority. Append ordered assignment-version rows per source/reconstruction; the highest committed version defines its one current conversation. A query/view materializes current assignments. A unique `(source_record_id, version)` prevents duplicate versions, while a transaction/service check must prevent two competing latest assignments.
- Separate immutable parsed-header evidence rows from immutable decision rows so a later resolution can cite one parsed token without duplicating it. Store grouped lineage as operation events and participant-role rows, rather than predecessor→successor pairs; a merge/split operation is reconstructed from the grouped participants.

This avoids mutable current projections and avoids repeating parsed evidence, but changes the meaning of the existing membership table, complicates current-state uniqueness, and needs a more substantial migration/query contract. Both alternatives support multiple predecessors/successors and append-only history. Neither is authorized merely by D4's phrase “Alternative A,” which referred to **explicit evidence and history versus the old schema**, not to one of these two physical layouts.

### Additional open choice within either alternative

A stable key could be a generated local opaque identifier assigned once and guarded by a unique `(account_scope, key)`, or a deterministic source/reconstruction-derived key that permits create-on-replay. D5 excludes deriving identity from the current Message-ID set but does not choose between these approaches. The idempotency strategy, legacy backfill, and merge/split re-creation behavior differ. The exact type/length, key generator, and uniqueness contract cannot be finalized yet.

## 6. Lineage, memberships, and evidence semantics needing a choice

For a merge A+B→C, both A and B must be retained and linked to C; for a split A→B+C, A must link to both B and C. A grouped operation identity is needed to distinguish one multi-party change from unrelated pairwise transitions. Every lineage edge requires FKs to the old/new conversation, same-account validation, `old_id != new_id`, and a duplicate-edge constraint. Global cycle checks need the complete graph before commit. Decide whether lineage is a pairwise edge table with a bounded group key, or operation+edge/participant tables with an FK to an operation row.

For current membership, the existing `UNIQUE(source_record_id)` is a useful guard under Alternative A. The current `evidence_type`/`evidence_reference` can only hold a summary; it cannot replace the typed append-only evidence decisions. Changing the current row on merge/split must be accompanied by immutable old→new history in the same transaction. Under Alternative B, a new versioned source of truth replaces this physical guard, so the one-current invariant must be specified differently. Do not delete old history or rewrite evidence decisions.

For evidence, the approved outcomes need at least domains for accepted direct parent, accepted ancestor/support, ambiguous duplicate target, malformed token, multiple In-Reply-To, self-link, cycle rejection, conflict across components, and missing external ancestor. An absent ID is distinct from a malformed token. The row must record header origin (`message_id`, `in_reply_to`, `references`), ordered position (nullable only where not applicable), source/header revision fingerprint, normalization version, target (nullable), decision, and bounded token fingerprint. Whether the canonical token itself is stored up to the approved limit or only a digest plus a source/offset reference is unresolved; raw unbounded References must never be duplicated. Source headers can later change in Phase 3C, so a digest-only old decision has weaker human-readable provenance than an immutable bounded canonical token.

## 7. Constraints and indexes: common requirements, not final DDL

The final design must state exact column nullability, lengths, defaults, FK actions, check domains, and index names. The following are mandatory regardless of alternative:

- Unique account-scoped conversation key; indexes on `(account_scope, superseded/current state)` and lineage predecessors/successors for graph traversal.
- Current-source uniqueness physically in Alternative A; explicit version/order uniqueness and one-latest-assignment enforcement in Alternative B. A FK to `SourceRecord` alone does not prove that a source is an email or shares the conversation account; decide whether repository validation suffices or whether a scoped composite FK/trigger (which could require changing Phase 3C tables) is required.
- Unique replay key for each evidence decision, membership change, and lineage operation; unique lineage edge/participant within its operation; `CHECK` domains for evidence kind, decision, operation kind, assignment reason, positive ordinal/version, and non-self lineage.
- Indexes for account-wide corpus reading, source→current conversation, conversation→members, source/header-revision→evidence, normalized-token digest→candidate decision, and event/lineage lookup. An index on `EmailMessage.normalized_message_id` is not a substitute for Phase-3D canonical normalization; changing Phase 3C tables needs separate justification.
- FK enforcement enabled in the SQLite session/migration tests. Do not claim a row-level `CHECK` enforces acyclic lineage, append-only history, or cross-table account consistency; test the chosen enforcement mechanism.

Exact DDL cannot be safely committed while the alternatives and singleton contradiction remain unresolved.

## 8. Migration strategy and legacy-data blockers

The migration would follow revision `0004` and must be additive unless a separately approved data migration proves a rebuild necessary. An empty database can add tables and constrained account/key fields. For existing rows, safe backfill is not universal:

- A conversation with email memberships all in one source scope could derive that account scope. It still needs an approved stable-key generation and evidence/history baseline policy. The pre-3D `evidence_reference` is not necessarily parsed technical evidence and must not be labeled as such retrospectively.
- An orphan `Conversation` has no source-derived account. A conversation containing mixed account scopes or a non-email `SourceRecord` is physically possible. Assigning the configured mailbox account would invent provenance. Options: fail migration with a diagnostic and require a separate approved repair; or retain nullable/`legacy_unresolved` rows excluded from 3D until explicitly resolved. These yield materially different nullability, constraints, and tests.
- Existing `ConversationMembership` rows are current assignments only. A synthetic baseline history row can state “legacy assignment observed during migration” without claiming technical evidence, but requires an approved provenance marker. Alternatively leave legacy history absent and start history at the first 3D reconstruction; this leaves past assignment provenance incomplete.
- Down-migration cannot be called lossless after new merge/split/evidence history exists; the exact downgrade policy must either refuse with data present or explicitly document data loss. Never silently drop history in a populated user database.

No real database is inspected or changed in this task. No migration is created or run.

## 9. Repository and transaction implications

Later repositories would need account-scoped conversation/current-membership reads; stable-key/idempotent create; append-only evidence decisions; append-only membership changes; merge/split lineage creation and traversal; account/source validation; exact replay lookup; and an atomic component-change operation that checks current source/header versions and lineage acyclicity before commit. Repositories remain session-injected and non-committing; the application service owns transaction boundaries.

A single reconstructed component change must atomically create fresh conversation(s), supersede prior conversation(s), record grouped lineage, change current assignments (or append authoritative versions), append evidence/history, and add a bounded audit summary. On FK, uniqueness, stale-input, or audit failure, roll back the whole unit and recompute on a later run. The full-corpus computation remains local; the approved design does not embed threading in 3C or start a scheduler. Whether multiple independent component changes share a transaction is a later service-plan decision, not a schema default.

## 10. Test matrix for a later approved migration/model task

- Upgrade empty isolated SQLite `0004→new head`, inspect every table/column/FK/index/check/unique constraint, then downgrade/re-upgrade under the approved loss policy.
- Upgrade a synthetic legacy database with one valid email conversation, singleton/current membership, orphan conversation, mixed-account conversation, and non-email membership; verify the selected backfill/fail/quarantine rule without invented account/evidence.
- Merge two predecessors into one new conversation; split one predecessor into two new conversations; many-to-many lineage; no old-conversation survivor; duplicate lineage edge and self-edge rejection; service-level or physical cycle rejection.
- One current conversation per email source, cross-account and non-email rejection, duplicate current membership/version failure, correct FK behavior, and no rows orphaned by a failed transaction.
- All approved evidence states, ordered References, invalid/ambiguous tokens, nullable target for missing ancestor, normalization version, bounded storage, token/chain limits, and replay-key uniqueness.
- Append-only evidence/history: corrected header or changed graph appends new decisions/assignment changes; unchanged full rebuild appends none; failed audit/commit rolls back projection and history together.
- Retention/redaction: preserve minimum lineage/audit identities without raw body, unbounded headers, secret-like data, or external calls. Tests use only synthetic fixtures; no real mailbox, network, keyring, AI, CRM, or Calendar.

No tests were run in this read-only analysis/design phase; pytest and migrations would create files/databases.

## 11. Risks, Scope Lock, and out-of-scope discoveries

High risks are false cross-account membership, fabricated legacy provenance, untraceable merge/split, two conflicting current assignments, cycles, replay duplicates, and confidential header content copied into history/audit. The data model must preserve evidence as inert data; email text cannot grant operational authority.

**IN SCOPE now:** read the approved decisions and current model/migrations/tests; create only this design-analysis document; commit/push it as explicitly requested.

**OUT OF SCOPE now:** any model, migration, repository, service, adapter, configuration, dependency, test, UI, scheduler, IMAP, AI, CRM, Calendar, or `main` change; real data inspection/mutation.

**RESTRICTIONS for a later model/migration task:** name exact files in a separately approved plan; no Phase 3C table changes unless an approved physical invariant strictly requires them; no raw body/full References duplication; no forced ambiguous membership; no silent legacy backfill or destructive downgrade; test against isolated synthetic SQLite only.

**OUT-OF-SCOPE DISCOVERY:** the existing generic conversation repository permits non-email memberships and does not validate account scope. This is a legacy-data/migration risk, not authorization to change that repository now. The earlier analysis also identified that 3C high-water sync does not automatically re-fetch changed old UIDs; that separate synchronization concern is unchanged here.

## 12. Decisions required and result

1. Reconcile `docs/data-model.md`'s absent ambiguous membership with D3's mandatory singleton, by an explicit approved logical-model update or revised D3.
2. Choose a physical authority: current membership projection plus append-only change history (Alternative A), or append-only assignment versions from which current state is derived (Alternative B).
3. Choose grouped lineage shape and stable conversation-key/idempotency scheme; specify physical versus transactional enforcement of same-account, email-only, acyclic, and append-only invariants.
4. Choose combined versus separate parsed-evidence/decision rows, and bounded canonical-token storage versus digest/source-offset references.
5. Approve legacy orphan/mixed/non-email handling, baseline-history provenance, and safe downgrade behavior.

**STOPPED FOR DECISION.** These choices change exact tables, columns, FKs, constraints, indexes, and migration tests. The present task's STOP rule and `Analyze Task` ambiguity rule prohibit selecting among them. This document is not READY FOR APPROVAL as a physical design and authorizes no implementation.
