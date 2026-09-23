# Phase 3D3 plan — full-corpus thread reconstruction service

**Status:** READY FOR APPROVAL
**Date:** 2026-09-23
**Task:** `docs/plans/implementation-phase-3d3-final-plan-task.md`
**Baseline:** `a20be7a` on `codex-work`

## 1. Objective, authority, and current state

Implement, only after separate approval, one local account-wide reconstruction service that takes the retained logical-email corpus, invokes the accepted pure 3D2 engine, and atomically persists its 3D1 evidence/decisions, current conversation projection, assignment history, and lineage. It must never infer topology beyond 3D2. Exact replay creates no new `Conversation`, `ThreadEvidence`, `ThreadEvidenceDecision`, `ThreadMembershipChange`, `ThreadLineageOperation`, or `ThreadLineageEdge`.

This final plan applies approved `implementation-phase-3d3-decisions.md` A–G and the final-plan task. Also consulted: `AGENTS.md`; the previous 3D3 STOP plan; 3D decisions D1–D13; the 3D1/3D2 plans and accepted models, repositories, migration and tests; `docs/functional-spec.md` §5.4/24.1; `docs/data-model.md` §§4–5/10/12; `docs/architecture.md` §§3–4/9–11; `docs/security.md`; and `docs/testing-strategy.md`. No required source is missing. No code or test is changed by this planning task.

Current facts: `EmailMessage` has one unique `source_record_id`; IMAP locations may be active or unavailable and are not logical thread nodes. `SourceRecord` owns account scope, source type, retention state and deletion/redaction timestamp. 3D2 returns ordered `ParsedEvidence`, matching `EvidenceDecision`, accepted edges, components and a reconstruction key; evidence indexes are tuple indexes, not persisted IDs. `ThreadPersistenceRepository` has caller-owned-session guarded primitives but no full-account snapshot/orchestration. 3D1 physically allows only `merge|split|repartition` lineage; the approved correction 1→1 requires revision `0006` and a matching model/repository change. `ThreadMembershipChange.reason` already permits `correction`.

## 2. Exact public service contract and transaction

Create `app/services/email_thread_reconstruction.py` with:

```text
@dataclass(frozen=True, slots=True)
ThreadReconstructionResult(
    account_scope: str,
    status: Literal['completed', 'busy_retry_later'],
    reconstruction_key: str | None,
    source_count: int | None,
    component_count: int | None,
    conversations_created: int,
    memberships_changed: int,
    lineage_operations_created: int,
)

reconstruct_account_threads(engine: sqlalchemy.Engine,
                            account_scope: str) -> ThreadReconstructionResult

ThreadReconstructionError(code: Literal[
    'invalid_scope', 'invalid_source_state', 'legacy_unresolved',
    'superseded_membership', 'invalid_partition', 'persistence_conflict'
])
```

Validate an account scope of 1–100 characters with `account_scope.strip()` nonempty before opening a transaction. On `busy_retry_later`, key and counts of sources/components are `None`, all write counts are zero, and no transaction was acquired. On `completed`, key/counts are present; counts report rows created/changed in *this* pass (zero for an exact replay). Preflight/integrity/persistence failures raise `ThreadReconstructionError` with one of the bounded codes above after rollback; `legacy_unresolved`, unexpected superseded membership, invalid source/partition, and replay-payload conflict are failures, not a degraded success. No exception includes raw headers, subject or body.

Use one fresh SQLite connection per attempt. Before the transaction, enable and verify `PRAGMA foreign_keys=ON`, set `PRAGMA busy_timeout=0`, and close any preliminary SQLAlchemy logical transaction. Issue explicit `BEGIN IMMEDIATE` on that connection **before any corpus or membership read**, then bind one SQLAlchemy `Session` to that same connection. Do not commit inside repositories. Perform all reads, 3D2 computation, inserts/updates and validation under this one write reservation; flush, check postconditions, commit the connection once, and close session/connection. On every failure roll back the same connection. The reserved writer slot blocks concurrent 3C writes during the pass; no optimistic read-then-revalidate step and no component-level commits are allowed. Do not perform IMAP/network work while the reservation is held.

Only a SQLite busy/locked error while acquiring `BEGIN IMMEDIATE` is retried: **three attempts total**, using fresh connections, with 100 ms between attempts 1→2 and 2→3. Other errors are not retried automatically. After the third acquisition failure return `busy_retry_later`; no corpus read or write occurred. A busy/error after acquisition rolls back and raises a bounded failure rather than replaying a partly executed pass. The application caller may schedule a later independent attempt; 3D3 itself adds no scheduler.

## 3. Exact corpus read and preflight

`ThreadPersistenceRepository.load_account_thread_snapshot(account_scope)` is a caller-transaction read. Select `SourceRecord` joined one-to-one to `EmailMessage` on `EmailMessage.source_record_id`, constrained to `SourceRecord.source_system_scope=account_scope` and `source_type='email_message'`, ordered by `SourceRecord.id`. Fetch source ID, scope/type, `retention_state`, `deleted_or_redacted_at`, stored `normalized_message_id`, `in_reply_to`, `references_header`, and `subject`; **do not join IMAP locations into corpus cardinality**. Select the account's email `SourceRecord` IDs separately to fail if a purported eligible source lacks its one `EmailMessage` row; uniqueness is already physical. No folders, UIDs, location state, body, attachments, sender, date, participant, CRM context or current Conversation ID enters 3D2.

The eligible predicate is `source_type='email_message' AND source_system_scope=account_scope AND retention_state='active' AND deleted_or_redacted_at IS NULL AND one EmailMessage row exists`. `active` with null deletion/redaction timestamp is the current locally retained/non-redacted state. A recognized terminal state `redacted` or `deleted` **with** non-null deletion/redaction timestamp is excluded. Any other state/timestamp combination fails preflight rather than silently redefining eligibility. All eligible emails participate even if every IMAP location is `unavailable` or there is no current location. There is no email-specific `deleted_at_source` field and none is added. Excluded sources retain historical memberships/evidence, but are not passed to 3D2 or reassigned by this pass. An empty eligible corpus is valid.

In the same transaction, load every current `ConversationMembership` for eligible source IDs with its `Conversation`, plus **all** current members of each touched conversation (including excluded sources) for exact-set comparison. Validate source-email/account consistency, no duplicate/foreign current assignment, and that every touched conversation is `resolved`, same-account and not superseded. If any eligible source is currently assigned to `legacy_unresolved`, fail the entire pass **before 3D2 or topology persistence**; no degraded subset and no repair. An eligible source with no current membership is valid only as an initial candidate. An eligible source pointing to a superseded conversation is an integrity failure, not a silent reassignment. A touched resolved conversation with non-email or foreign-account members is also an integrity failure. Excluded members of an otherwise valid touched conversation remain historical/current as-is; they do not become new 3D2 nodes, and their presence prevents falsely classifying the old *full* member set as unchanged. If such an excluded member is later made eligible again while pointing to a superseded conversation, the pass fails pending a separate repair policy.

Calculate 3D1-compatible `source_revision` from each eligible source ID and its **stored** three ID header strings; construct one `EmailThreadInput` per source with subject diagnostic only. Invoke `reconstruct_threads(account_scope, tuple(inputs))` once. Verify returned source IDs/components partition exactly the selected IDs, decisions have the same count/order as evidence, every accepted edge has exactly one matching accepted decision and a selected same-account target, and every source appears exactly once. The 3D2 reconstruction key is the pass/replay identity; it excludes location and subject by approved contract. The write reservation makes a post-read stale check unnecessary.

## 4. Evidence/decision persistence and source-local attribution

Before any conversation creation, persist all 3D2 observations in returned evidence order via `append_evidence` with exactly its account, source ID, kind, ordinal, status, bounded token/digest, normalization version and source revision. Save `evidence_index → persisted ThreadEvidence.id`. The repository derives/verifies the existing `3d1/evidence/v1` replay key and current header revision. Then persist decisions in returned order via `append_decision`, mapping each `decision.evidence_index` through that table and passing the 3D2 reconstruction key, exact outcome and nullable target. Save `evidence_index → persisted ThreadEvidenceDecision.id`. Each valid/invalid observation receives exactly one decision for this reconstruction; an unchanged replay reuses rows after payload comparison. Never store full raw References, bodies, malformed text, or secrets in new history.

3D2 permits at most one accepted outgoing edge per source. For a membership **change**, use that source's accepted decision ID as `evidence_decision_id` if present; otherwise use `NULL`. Never use a different source's edge to justify the assignment. For the bounded current-projection summary: accepted source-local edge uses `evidence_type='thread_decision'`, `evidence_reference='decision:<id>'`; a no-edge singleton uses `singleton`/`source:<id>`; a no-edge root in a multi-email component uses `thread_decision`/`source:<id>` as a source-local component summary with null decision pointer. This summary is not technical evidence; the component and stored 3D2 decisions remain authoritative. Unchanged memberships keep their existing summary and create no history.

## 5. Deterministic partition comparison and transition matrix

Let `N` be the sorted 3D2 components (each a set of eligible source IDs). Let `O` be touched active resolved conversations, each with its **full** current member set; its overlap with eligible IDs determines whether it participates in this pass. Build a bipartite graph with one vertex per `O` and `N` and one edge `(old conversation, new component)` for each eligible source that currently belongs to that conversation and lies in that component. Source IDs without old membership add no predecessor vertex. Compute connected overlap groups; include each isolated new component as its own group. Sort groups by minimum new source ID and, if needed, old stable key; sort all predecessor IDs by stable key and successor components by minimum source ID. This order is for deterministic operations, not thread topology or stable-key derivation.

| Overlap group | Classification | Identity and lineage | Membership history |
| --- | --- | --- | --- |
| 0 predecessors, 1 new component | `initial` | Create one fresh resolved conversation; no lineage. | Every source `initial_assignment`, old null. |
| 1 predecessor, 1 successor, and the predecessor's **full** current member set equals that new component | `unchanged` | Retain exact old `Conversation.id`/stable key; no lineage or new identity. | No projection/history change, even when a new header revision creates new evidence/decisions. |
| ≥2 predecessors, 1 successor | `merge` | Fresh successor; one grouped merge operation and complete predecessor→successor edges. | Every previously assigned eligible source moving to successor uses `merge`; previously unassigned sources use `initial_assignment`. |
| 1 predecessor, ≥2 successors | `split` | Fresh conversation for every successor; one grouped split operation, complete edges. | Prior members use `split`; unassigned sources use `initial_assignment`. |
| ≥2 predecessors, ≥2 successors | `repartition` | Fresh conversation for every successor; one grouped repartition operation, Cartesian edges. | Prior members use `repartition`; unassigned sources use `initial_assignment`. |
| 1 predecessor, 1 successor, but full old member set differs | `correction` | Fresh successor; one **1→1 correction** lineage operation/edge, superseding the predecessor. | Prior eligible members use `correction`; newly included sources use `initial_assignment`. |

There is no 0-predecessor multi-successor connected group: each isolated new component is processed separately. Newly seen sources never count as predecessors. A previously assigned eligible source that changes component always follows its overlap group's classification; there is no arbitrary old-conversation winner. If an old full member set contains an excluded source, it cannot satisfy `unchanged`; its eligible members transition under the table while the excluded source's stored membership is not rewritten. A touched old conversation is superseded only once, in its one overlap group. All components in a changed group receive new identities, even if one happens to resemble an old subset. Subject, current conversation ID, and stable key do not modify 3D2 components.

For each changed group, create successor conversations in sorted component order **only after** the complete account snapshot, preflight, 3D2 computation, evidence/decision mapping, and deterministic comparison show the group is not `unchanged`. With all new rows flushed but uncommitted, record one lineage operation for merge/split/repartition/correction; it creates all Cartesian edges and supersedes predecessors atomically. Then assign each eligible source that requires a new membership with `assign_current_membership`, passing the observed old ID or null, new ID, exact group reason, bounded summary, reconstruction key, and source-local decision pointer. For unchanged groups call no assignment/lineage mutator. Flush and validate before one account commit. No generic `AuditEvent` write occurs in 3D3; approved typed histories are the audit record for this phase.

## 6. Replay, rollback, and postconditions

Before creating any opaque conversation key, compare the complete current partition under `BEGIN IMMEDIATE` with the computed components and confirm each touched active conversation's **full** member set. If every group is `unchanged`, or the corpus is empty, do not create a conversation, membership change or lineage operation. Evidence/decision APIs still run and return existing rows on exact same-key replay; if a new reconstruction key has unchanged topology they may append new decisions, but no identity/history transition occurs. Never treat merely finding an old membership replay key as proof that the *current* projection still matches it: the existing 3D1 method may return a later current projection for an old key.

3D1 replay keys/payload checks cover evidence, decisions, membership changes and lineage; opaque UUIDv4 stable keys are generated only after comparison proves a new transition. One account-wide transaction means a crash, exception or rollback before commit leaves none of its provisional conversations/evidence/decisions/history/lineage; a crash after commit leaves the entire current partition, so retry observes exact-set `unchanged` groups and reuses existing evidence/decisions. The lock serializes simultaneous 3D3/3C SQLite writers. No partial component pass or separate success marker is needed. A replay-key collision with unequal payload fails closed and rolls back.

Before commit assert: selected IDs equal the disjoint union of 3D2 components; every eligible source has exactly one current membership to an active resolved same-account conversation; every such conversation's eligible members equal exactly one computed component; every real changed assignment has exactly one appended history row; every changed overlap group has the required complete, acyclic same-account lineage; unchanged groups have no new lineage/history; accepted decisions reference only selected same-account targets; excluded sources were not reassigned; and no raw header/body/secret entered threading history. Empty corpus produces a completed, zero-change result. On validation failure rollback the entire pass.

## 7. Exact repository and schema extensions

In `app/persistence/repositories.py`, add `load_account_thread_snapshot(account_scope)` returning ordered email/source data plus relevant current memberships and full touched-conversation member sets under the caller's reserved transaction; add only narrow account/replay/partition reads necessary for the comparison. Keep methods session-injected and non-committing. Extend `record_lineage_operation`'s accepted kind/shape with `correction: exactly one predecessor and one successor`; retain disjoint IDs, non-self edge, same-account checks, cycle detection, immutable replay payload validation, complete edge insertion, and atomic predecessor supersession. Do not weaken merge/split/repartition guards. `ThreadMembershipChange.reason='correction'` and its physical check already exist; no change to that table or accepted outcome enum is needed. The service must not rely on the generic provenance repository's unscoped legacy behavior.

In `app/persistence/models.py`, change only `ck_thread_lineage_operation_kind` to include `'correction'`. Create Alembic revision `0006_phase_3d3_correction_lineage.py`, `down_revision='0005'`. SQLite cannot alter this CHECK in place. Rebuild the operation table while preserving its IDs, timestamps, payloads, unique/check constraints and index: copy `thread_lineage_edge` to a temporary **no-FK** backup table; drop the original edge table first; create/copy the operation replacement with the expanded CHECK; drop the old operation table and install its replacement; recreate the edge table with its original constraints/indexes and copy the backed-up edge IDs/pairs; remove the temporary backup. Preserve all existing merge/split/repartition rows and exact edge contents, keep FK enforcement enabled, and run `PRAGMA foreign_key_check` before completion. The migration must run within a controlled SQLite write transaction, so failure rolls back the table replacement rather than leaving either table missing. Downgrade `0006→0005` first refuses when any correction operation exists, without data loss; otherwise it performs the inverse rebuild and preserves other operations/edges. Test the exact `0005→0006→0005→0006` path on isolated databases, populated legacy lineage preservation, failure rollback and refusal with correction rows. Update `docs/data-model.md` §5 narrowly to state that a changed one-predecessor/one-successor member set also receives a fresh conversation and explicit correction lineage; this approved logical-model extension precedes or accompanies the physical change.

## 8. Implementation order, tests, and acceptance

1. Update the logical model's correction-lineage sentence; add `0006`, model CHECK, repository correction validation and isolated migration/model/repository tests. Do not run migration against the user database.
2. Add the account snapshot/replay read surface and synthetic repository tests, including excluded-retention, quarantine, full old member sets and superseded current membership.
3. Add the application service/result contract and synthetic service tests for lock-before-read, fixed-point 3D2 mapping, partition groups, atomic persistence, replay, and failure behavior.
4. Run `python -m pytest test/test_migrations.py test/test_persistence_models.py test/test_persistence_repositories.py test/test_email_thread_reconstruction.py`, then `python -m pytest`. Inspect full diff, migration head, staged names, and exact Scope Lock before any later commit. Tests use isolated synthetic SQLite only; no production credentials, database or external connection.

Test matrix: zero/one/many eligible emails; one logical email with multiple active/unavailable IMAP locations; only unavailable locations; redacted/deleted/excluded source; malformed/duplicate/ambiguous headers and singleton; direct/References evidence-index→ID and decision target mapping; same-subject non-linkage; legacy quarantine fail-before-topology-write; missing current membership as initial; superseded/mixed-account/non-email current-state rejection; exact old-member-set unchanged; initial multi-email component; merge, split, N:N repartition, and 1→1 correction (including newly unassigned and excluded old members); source-local accepted decision versus null root; deterministic group ordering/permutation; changed headers with same partition; exact replay with zero six-table inserts; rollback injections after evidence, decision, conversation, lineage and membership stages; crash-before/after-commit retry; two concurrent account writers/3C writer; exactly three lock-acquisition attempts and busy result; FK/check/replay/cycle guards; empty and populated `0006` downgrade behavior; no generic AuditEvent, IMAP, network, keyring, CRM, Calendar, AI, raw content or cache-dependent tests.

Acceptance is the postcondition set in §6, zero duplicate rows on exact replay, fail-closed quarantine/invalid state, atomic account-wide rollback, migration/data-model agreement, all specified isolated tests green, and no changed path outside §9. This plan is reviewable but does **not** itself approve implementation.

## 9. Exact Scope Lock

**This planning task — only modified file:** `docs/plans/implementation-phase-3d3-plan.md`. No code, tests, migration, database, caches, dependencies, or `main` change; only the requested commit/push of this plan to `origin/codex-work`.

**Later 3D3 implementation — IN SCOPE, exact paths:**

- `docs/data-model.md`
- `app/persistence/models.py`
- `app/persistence/repositories.py`
- `alembic/versions/0006_phase_3d3_correction_lineage.py`
- `app/services/email_thread_reconstruction.py`
- `test/test_migrations.py`
- `test/test_persistence_models.py`
- `test/test_persistence_repositories.py`
- `test/test_email_thread_reconstruction.py`

**OUT OF SCOPE:** 3D2 parser/graph and its tests; 3C/IMAP adapter, sync and locations; other models/migrations/docs/code/tests; generic AuditEvent writes; scheduler, routes/UI, CRM, Calendar, AI, drafts, moves, sends, external integrations, real mailbox/database, and `main`.

**RESTRICTIONS:** no new dependency or framework; no component-level commit or optimistic post-read revalidation; no partial pass; no automatic quarantine repair; no source exclusion based on unavailable IMAP location; no subject/current-identity-driven topology; no raw full headers/bodies/secrets in thread history/logs; no change to existing lineage kinds beyond adding correction 1→1; no production-data migration run during implementation. A need for a tenth path or semantic deviation requires STOP and a new approval.

## 10. Risks, out-of-scope discoveries, and result

Main risks are writer contention during a full-account pass, false set equality when excluded members remain in an old conversation, current-membership/history divergence, duplicate random identities after retry, FK breakage in SQLite CHECK migration, source-local evidence misattribution, and retention/quarantine leakage. Explicit `BEGIN IMMEDIATE`, complete old-set comparison, atomic assignment/history, replay preflight, fail-closed migration/downgrade, and synthetic concurrency/failure tests address them.

**OUT-OF-SCOPE DISCOVERY:** 3C high-water synchronization may not re-fetch already committed UIDs whose remote headers change in place. 3D3 reconstructs only locally stored snapshots; improving IMAP detection is a separate task. No 3C change is authorized here.

**Open decisions:** None under approved 3D3 decisions A–G and this exact Scope Lock.

**Result: READY FOR APPROVAL.** Separate explicit approval is required before implementing these nine paths.
