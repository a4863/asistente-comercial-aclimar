# Phase 3D1 plan — threading persistence

**Status:** READY FOR APPROVAL
**Date:** 2026-09-23
**Task:** `docs/plans/implementation-phase-3d1-plan-task.md`
**Baseline:** `codex-work` at `243b76f` after fast-forward from `origin/codex-work`

## 1. Objective and boundary

Prepare the approved 3D threading persistence contract only: logical data-model correction, SQLAlchemy models, revision `0005`, repository primitives, and isolated model/migration/repository tests. This document is a plan, not permission to implement. No real mailbox, database, keyring, network, or external integration is accessed by 3D1.

The functional decisions D1–D6 and physical decisions D7–D13 govern this plan. In particular, each logical email will have one current conversation after reconstruction; an unlinked or ambiguous email gets a singleton. That is a target invariant for later 3D reconstruction, not a claim that revision `0005` can synthesize memberships for legacy emails with no prior assignment.

## 2. Sources and current state

Consulted: `AGENTS.md`; `skills/analyze-task/SKILL.md` for the read-only assessment; the task; `implementation-phase-3d-analysis.md`, `implementation-phase-3d-decisions.md`, `implementation-phase-3d-data-model-design.md`, `implementation-phase-3d-physical-decisions.md`; `docs/functional-spec.md`, `docs/data-model.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`; `app/persistence/models.py`, `app/persistence/repositories.py`, revisions `0002`–`0004`, and the current persistence/migration tests. No required source is missing.

`Conversation` currently has only ID, creation time, provenance, and nullable supersession time. `ConversationMembership` is a current projection with unique `source_record_id` and two bounded evidence-summary strings. It permits legacy orphan, mixed-account, and non-email assignments. `SourceRecord.source_type='email_message'`, an `EmailMessage` row, and `SourceRecord.source_system_scope` together establish a logical email and its account. Revision `0004` is current head. There is no thread history or lineage schema. Existing generic conversation repository methods bypass email/account checks and must be brought under the new contract in 3D1.

`docs/data-model.md` presently permits uncertain email membership to be absent. Approved D7 supersedes that statement; the 3D1 implementation must update that logical document **before or together with** the technical schema, explicitly distinguishing the normal reconstructed singleton state from quarantined legacy rows.

## 3. Exact physical contract

All new tables use `id INTEGER PRIMARY KEY`, `created_at DateTime(timezone=True) NOT NULL` with the existing Python `utcnow` default; migration backfills explicit UTC timestamps. SQLite foreign keys must be enabled in repository and test connections. No cascading delete: every new FK uses `ondelete='RESTRICT'` (SQLite `NO ACTION` is acceptable only for pre-existing FKs left unchanged). New tables and added fields use named constraints/indexes. `String` lengths are also enforced with `CHECK length(...)` because SQLite does not enforce a declared `VARCHAR(n)` limit.

### 3.1 Existing tables

| Table/field | Type and contract |
| --- | --- |
| `conversation.account_scope` | `String(100) NULL`; non-null for `resolved`, null only for quarantined `legacy_unresolved`. No Python/server default. |
| `conversation.stable_key` | `String(36) NOT NULL`; immutable canonical lowercase UUIDv4 text, generated locally once for every existing/new row; never derived from headers, subject, members, or components. No server default. |
| `conversation.legacy_status` | `String(20) NOT NULL`, values `resolved`, `legacy_unresolved`; new rows explicitly `resolved`. No server default after backfill. |
| `conversation.provenance`, `superseded_at` | Retained unchanged. `superseded_at` is the current supersession projection, not a replacement for lineage. |
| `conversation_membership.*` | Retain existing columns, FK and `UNIQUE(source_record_id)`; the row remains the authoritative current projection. Retain `evidence_type String(50) NOT NULL` and `evidence_reference String(255) NOT NULL` as bounded *summaries*, not technical evidence storage. Legacy values remain untouched. New summary values are `singleton` / `thread_decision` / `legacy_assignment` and a bounded local reference such as `source:<id>` or `decision:<id>`; never raw header text. |

Named `conversation` constraints: `ck_conversation_scope_status` checks `(legacy_status='resolved' AND account_scope IS NOT NULL) OR (legacy_status='legacy_unresolved' AND account_scope IS NULL)`; `ck_conversation_stable_key` checks length 36 and canonical lowercase UUIDv4 syntax (repository validates UUID version; SQLite checks length/lowercase and hyphen positions); `uq_conversation_scope_stable_key` on `(account_scope, stable_key)`; `ix_conversation_scope_status_superseded` on `(account_scope, legacy_status, superseded_at)`. Quarantined rows have null scope, so the repository also checks stable-key collision globally before creating/backfilling a key. `ix_conversation_membership_conversation_id` supports reverse lookup; preserve the existing source uniqueness without rebuilding its meaning.

### 3.2 New tables

For all SHA-256/replay fields below, store exactly 64 lowercase hexadecimal characters (`String(64) NOT NULL`, named length/hex `CHECK`); digests are of length-prefixed UTF-8 values with a versioned domain prefix, never a raw email body/header or credential. `replay_key` is globally unique, domain separated per table, and immutable. A different logical event must never be forced to reuse a key. UUID stable keys are not replay identities.

Replay serialization is exact: SHA-256 over UTF-8 domain text followed by each field encoded as its decimal UTF-8 byte length, `:`, then its UTF-8 bytes; null is encoded as `-1:`. Domains are `3d1/evidence/v1`, `3d1/decision/v1`, `3d1/membership/v1`, `3d1/lineage/v1`, and `3d1/legacy-baseline/v1`. Evidence fields are `(account_scope, source_record_id, source_revision, normalization_version, header_kind, ordinal, parse_status, token_digest)`; decision fields `(evidence replay_key, reconstruction_key, outcome, target_source_record_id)`; membership fields `(account_scope, source_record_id, old_conversation stable_key or null, new_conversation stable_key, reason, reconstruction_key)`; lineage fields `(account_scope, reconstruction_key, kind, sorted predecessor stable_keys, sorted successor stable_keys)`; baseline fields `(pre-migration conversation_membership.id)`. Store the lowercase 64-character hex result. The two sorted sets use ascending stable-key bytes and the same length-prefix serialization, so caller enumeration order is irrelevant. A changed outcome within the *same* reconstruction key is an integrity conflict, never an implicit overwrite.

| Table | Exact fields beyond `id`, `created_at` | Constraints and indexes |
| --- | --- | --- |
| `thread_evidence` | `account_scope String(100) NOT NULL`; `source_record_id Integer NOT NULL FK source_record.id RESTRICT`; `header_kind String(20) NOT NULL` (`message_id`, `in_reply_to`, `references`); `ordinal Integer NOT NULL` (zero-based token order, including malformed tokens); `parse_status String(12) NOT NULL` (`valid`, `malformed`); `canonical_token String(998) NULL`; `token_digest String(64) NOT NULL`; `normalization_version Integer NOT NULL`; `source_revision String(64) NOT NULL`; `replay_key String(64) NOT NULL`. | Checks: ordinal >= 0; version > 0; valid iff canonical token non-null/nonempty and <=998; malformed iff token null; bounded scope; digest/revision/replay hex. `UNIQUE(replay_key)` and `UNIQUE(source_record_id, source_revision, normalization_version, header_kind, ordinal)`. Indexes `(account_scope, token_digest, header_kind)`, `(source_record_id, source_revision)`. A missing header produces no row; malformed text yields a digest but not a stored raw token. |
| `thread_evidence_decision` | `evidence_id Integer NOT NULL FK thread_evidence.id RESTRICT`; `target_source_record_id Integer NULL FK source_record.id RESTRICT`; `reconstruction_key String(64) NOT NULL`; `outcome String(32) NOT NULL`; `replay_key String(64) NOT NULL`. | Outcomes: `identity_observed`, `accepted_direct_parent`, `accepted_ancestor`, `unresolved_external`, `duplicate_target`, `malformed`, `multiple_in_reply_to`, `self_link`, `cycle_rejected`, `conflict`, `not_linking`. Target non-null **iff** outcome is one of the two accepted-edge outcomes; all other outcomes have null target. `UNIQUE(evidence_id,reconstruction_key)` and `UNIQUE(replay_key)`; indexes `(target_source_record_id)` and `(reconstruction_key,outcome)`. A later corpus/algorithm pass uses a new reconstruction key and appends a new decision; prior decisions stay immutable. |
| `thread_membership_change` | `source_record_id Integer NOT NULL FK source_record.id RESTRICT`; `account_scope String(100) NULL` only for quarantined baseline; `old_conversation_id Integer NULL FK conversation.id RESTRICT`; `new_conversation_id Integer NOT NULL FK conversation.id RESTRICT`; `reason String(32) NOT NULL`; `evidence_decision_id Integer NULL FK thread_evidence_decision.id RESTRICT`; `reconstruction_key String(64) NULL` only for baseline; `replay_key String(64) NOT NULL`. | Reasons: `legacy_assignment_baseline`, `initial_assignment`, `merge`, `split`, `repartition`, `correction`. Baseline/initial require old null; reassignment reasons require old non-null; old cannot equal new. Baseline requires null reconstruction/decision; all non-baseline changes require non-null account/reconstruction. `UNIQUE(replay_key)`; indexes `(source_record_id,created_at,id)`, `(old_conversation_id)`, `(new_conversation_id)`, `(account_scope,reconstruction_key)`. New is never null, so removal without successor is not represented. |
| `thread_lineage_operation` | `account_scope String(100) NOT NULL`; `kind String(16) NOT NULL` (`merge`, `split`, `repartition`); `reconstruction_key String(64) NOT NULL`; `replay_key String(64) NOT NULL`; `provenance String(50) NOT NULL` (`thread_reconstruction` for new operations). | `UNIQUE(replay_key)`; index `(account_scope,created_at,id)`; bounded account/provenance, hex checks. One operation groups all predecessor→successor edges for one component transition. `repartition` is the N:N case. |
| `thread_lineage_edge` | `operation_id Integer NOT NULL FK thread_lineage_operation.id RESTRICT`; `predecessor_conversation_id Integer NOT NULL FK conversation.id RESTRICT`; `successor_conversation_id Integer NOT NULL FK conversation.id RESTRICT`. | `CHECK(predecessor_conversation_id <> successor_conversation_id)`; `UNIQUE(operation_id,predecessor_conversation_id,successor_conversation_id)`; indexes on each conversation FK. Edges are Cartesian predecessor×successor pairs within the operation; no isolated edge insertion. |

Named constraint/index inventory for new tables (the column sets are those stated above):

| Table | UNIQUE / CHECK names | Index names |
| --- | --- | --- |
| `thread_evidence` | `uq_thread_evidence_replay`, `uq_thread_evidence_source_revision_ordinal`, `ck_thread_evidence_kind`, `ck_thread_evidence_parse_status`, `ck_thread_evidence_token_shape`, `ck_thread_evidence_ordinal_version`, `ck_thread_evidence_digests`, `ck_thread_evidence_scope` | `ix_thread_evidence_scope_token_kind`, `ix_thread_evidence_source_revision` |
| `thread_evidence_decision` | `uq_thread_decision_evidence_reconstruction`, `uq_thread_decision_replay`, `ck_thread_decision_outcome`, `ck_thread_decision_target`, `ck_thread_decision_keys` | `ix_thread_decision_target`, `ix_thread_decision_reconstruction_outcome` |
| `thread_membership_change` | `uq_thread_membership_change_replay`, `ck_thread_membership_change_reason`, `ck_thread_membership_change_old_new`, `ck_thread_membership_change_baseline`, `ck_thread_membership_change_keys` | `ix_thread_membership_change_source_time`, `ix_thread_membership_change_old`, `ix_thread_membership_change_new`, `ix_thread_membership_change_scope_reconstruction` |
| `thread_lineage_operation` | `uq_thread_lineage_operation_replay`, `ck_thread_lineage_operation_kind`, `ck_thread_lineage_operation_keys`, `ck_thread_lineage_operation_scope_provenance` | `ix_thread_lineage_operation_scope_time` |
| `thread_lineage_edge` | `uq_thread_lineage_edge_pair`, `ck_thread_lineage_edge_nonself` | `ix_thread_lineage_edge_predecessor`, `ix_thread_lineage_edge_successor` |

The canonical token is a lowercased, bracket/outer-whitespace-stripped comparison token, never the complete References header. `token_digest` is SHA-256 of the canonical token when valid and of a bounded, domain-separated malformed observation representation when invalid; do not persist malformed raw text. `source_revision` is a SHA-256 fingerprint of the source ID and stored Message-ID/In-Reply-To/References header values at the pass snapshot; it changes when relevant stored headers change. The parser/normalizer itself is **not** implemented in 3D1: repository APIs accept already validated bounded evidence values; parser behavior and exact token-chain limits belong to 3D2. `reconstruction_key` is a versioned SHA-256 fingerprint of account, algorithm version, and the sorted logical email/source IDs plus relevant header revisions in the consistent full-corpus snapshot. This distinguishes a new knowledge state from an exact replay; no message text is embedded in the key.

### 3.3 Transactional invariants beyond row constraints

Physical FKs/checks cannot prove cross-table email type/account equality, append-only history, operation shape, or global acyclicity. The 3D1 repository must enforce these inside one caller-owned SQLite transaction, without committing itself:

1. Every new resolved conversation, evidence row, decision target, current membership, history change, and lineage participant belongs to the same nonempty account. Every source must have `source_type='email_message'` **and** an `EmailMessage` row. Reject quarantined conversations for new normal operations.
2. `ConversationMembership` update/insert and exactly one corresponding `ThreadMembershipChange` insert occur in the same transaction after comparing old state. On unchanged replay, neither row changes. Rollback leaves neither changed. No delete/reset API for history/evidence/decisions/lineage. Legacy generic repository methods must delegate to these guarded primitives or reject use for 3D-resolved email assignments; direct unguarded writes are not an authorized path.
3. Accepted decision target exists, is email, is in the evidence source's account, differs from source, and does not create a directed parent cycle; rejected/ambiguous decisions never carry a target. Evidence rows and decisions are insert-only. Same evidence can have decisions in different reconstruction passes, not two outcomes in the same pass.
4. A lineage operation is inserted only with its complete edge set. `merge` has >=2 distinct predecessors/1 successor; `split` 1 predecessor/>=2 successors; `repartition` >=2 of each. All conversations share the operation account; predecessor and successor sets are disjoint, and predecessors must not already be superseded. Check the existing lineage graph plus proposed edges for a cycle before flush/commit, then set predecessor `superseded_at` in the same transaction. No update/delete API for operation or edges.
5. All replay lookups compare stored payload, not merely key existence. A key collision with different content raises and rolls back. Concurrent competing current assignments or stale source/header snapshots fail transactionally and require a new computation later. This phase provides persistence primitives, not the full-corpus orchestration.

## 4. Revision `0005`: legacy backfill and downgrade

Create `alembic/versions/0005_phase_3d1_threading_persistence.py` with `down_revision='0004'`. Upgrade on isolated SQLite uses batch alteration for `conversation`, creates the five new tables and named indexes, and runs these deterministic classification rules before making `stable_key` non-null:

1. Read each pre-existing conversation and its current membership source IDs. A conversation is `resolved` only if it has at least one member, every member is an `email_message` source with an `EmailMessage` row, all scopes are identical/nonempty, and the old conversation is not already superseded. Derive that one account scope. Never infer scope from configured mailbox, subject, address, or provenance string.
2. Orphan, mixed-account, non-email, missing-email-representation, empty-scope, or already-superseded legacy conversations become `legacy_unresolved` with null account scope. Preserve their existing memberships, evidence summaries, provenance, timestamps, and supersession value exactly. Exclude them from normal 3D reconstruction until a separately approved repair; do not fabricate lineage.
3. Assign a fresh canonical UUIDv4 stable key to every existing conversation, including quarantined ones, checking uniqueness during the batch. This is local identity, not a threading conclusion. Do not rewrite source records or email headers.
4. For **every** pre-existing membership, append one `thread_membership_change` row with reason `legacy_assignment_baseline`, old null, new equal to existing conversation ID, account scope equal to that conversation's resolved scope or null when quarantined, null decision/reconstruction key, and a domain-separated SHA-256 replay key from the existing membership ID. This records the observed baseline only; it does not claim technical evidence or an historical transition.
5. Enforce added constraints and verify row counts, referential integrity, source uniqueness, exact baseline count, and preservation of legacy evidence strings. A partially failing migration rolls back; no auto-repair of real data.

Downgrade is intentionally fail-closed: before dropping any new table/column, reject with a clear Alembic error if **any** conversation or current membership row exists or if **any** row exists in a 3D history/evidence/lineage table. This conservative rule also blocks downgrade of populated legacy databases after baseline creation. Only an empty dataset can return `0005 -> 0004`; no `CASCADE`, silent history loss, or bypass flag. Tests must cover successful empty downgrade/re-upgrade and refusal without data loss for populated legacy and new 3D histories.

## 5. Repository surface authorized in 3D1

Add a narrow thread-persistence repository in `app/persistence/repositories.py` with caller-owned session/transaction and no external clients:

- `create_resolved_conversation(account_scope, provenance)` and account-scoped current conversation/membership reads. The caller checks existing membership (initial singleton) or persisted lineage operation replay identity (merge/split/repartition) **before** requesting a new conversation; the repository creates an opaque UUID once inside the caller transaction. An unchanged replay never creates a new conversation, and transaction rollback removes any provisional row.
- `append_evidence(...)`, `append_decision(...)` with replay lookup/payload equality and scoped email/target validation; immutable history reads by source and reconstruction key.
- `assign_current_membership(...)` accepts old/current expectation, new conversation, bounded evidence summary, reason, optional decision, reconstruction key and replay key; atomically inserts/updates current projection plus one history row; no-op exact replay; reject stale projection.
- `record_lineage_operation(...)` accepts the full predecessor/successor sets and one replay key, validates kind/shape/account/non-self/no-cycle, inserts operation and all edges, supersedes predecessors atomically; lineage traversal reads by predecessor and successor.
- Existing `ProvenanceRepository.create_conversation` and `add_conversation_membership` must no longer create unscoped, unhistoried resolved email state. Update their signatures/call paths and the tests in scope to require account, email, and history or to explicitly reject obsolete usage; do not create new `legacy_unresolved` rows through normal APIs.

The repository performs no header parsing, graph reconstruction, scheduler invocation, network access, AI, audit expansion, or 3C sync changes. Caller transaction management and crash rollback follow the existing SQLAlchemy session pattern. The later 3D service must revalidate the corpus snapshot before using these primitives.

## 6. Order, tests, and acceptance

1. Update `docs/data-model.md` singleton/current projection/history/lineage/quarantine language in the same implementation change set before or with the schema; resolve the two contrary sentences in §5 and §12 explicitly.
2. Add SQLAlchemy columns/tables/constraints/indexes; create `0005` with equivalent schema and safe legacy backfill/downgrade guard.
3. Add only the scoped repository primitives and adapt the legacy conversation repository boundary; add synthetic tests.
4. Run `python -m pytest test/test_persistence_models.py test/test_migrations.py test/test_persistence_repositories.py`, then `python -m pytest`; inspect complete diff, Alembic head, and changed-file list.

Required tests use isolated synthetic SQLite with FK enforcement: exact columns/nullability/checks/unique/indexes; singleton current uniqueness; account/email validation; bounded tokens/digest and decision target semantics; duplicate Message-ID evidence kept as distinct rows; evidence later decision with new reconstruction key; append-only/no-op replay; projection+history rollback; merge/split/N:N shape, self-edge, cross-account, cycle, and duplicate replay; valid and each quarantined legacy classification; baseline provenance/count; populated downgrade refusal and empty downgrade/upgrade; no raw complete References, body, credentials, or external access. Existing migration/model/repository tests must remain green. An isolated database created by tests is allowed only during later implementation, never a real user database.

Acceptance: schema, migration and model agree; every new resolved assignment is account-scoped/email-only and history-backed; all immutable records survive replay/merge/split; quarantine never invents provenance; populated downgrade cannot discard history; `main` and external systems remain untouched.

## 7. Scope Lock for the later 3D1 implementation

**IN SCOPE — only these seven paths:**

- `docs/data-model.md`
- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/versions/0005_phase_3d1_threading_persistence.py`
- `test/test_persistence_models.py`
- `test/test_migrations.py`
- `test/test_persistence_repositories.py`

**OUT OF SCOPE:** parser, graph engine, thread reconstruction service, scheduling, UI, IMAP adapter/sync, AI, CRM, Calendar, real account access, other docs/code/tests/migrations, dependencies, config, and `main`.

**RESTRICTIONS:** no real-data migration run during implementation; no raw full References/header/body in new history or audit; no inferred legacy account; no ambiguous automatic merge; no auto-approval or external mutation; no destructive populated downgrade; no new package; no changes outside seven paths. The present planning task itself creates **only this plan file** and performs its explicitly requested commit/push.

## 8. Risks, dependencies, ambiguity, and result

Main risks: false account/thread linkage, historical evidence loss, a replay that creates duplicate identities, current projection diverging from history, unguarded legacy repository calls, SQLite FK/length assumptions, and real-data downgrade loss. Mitigations are the named constraints, repository transaction checks, quarantine, replay payload comparison, isolated tests, and fail-closed downgrade. Dependencies are existing SQLAlchemy/Alembic/SQLite and the approved D1–D13 policies; no new dependency or external system is required.

**Ambiguities requiring a functional/model decision:** None for the 3D1 persistence layer. The exact parser grammar and token/chain limits belong to a later 3D2 plan and are not silently selected here. The existing 3C high-water sync does not guarantee re-fetch of changed old UIDs; this is an **OUT-OF-SCOPE DISCOVERY** for a future sync task, not a reason to alter 3D1.

**Result: READY FOR APPROVAL.** Approval of this plan and its Scope Lock is required before implementation.
