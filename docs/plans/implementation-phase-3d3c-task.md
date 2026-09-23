# Phase 3D3C Implementation Task — Reconstruction Core in Caller Transaction

**Status:** Approved for Implement
**Date:** 2026-09-23
**Parent plan:** docs/plans/implementation-phase-3d3-plan.md
**Accepted prerequisites:** Phase 3D3A, Phase 3D3B

## Objective
Implement only the deterministic reconstruction core that runs inside an already-open caller-owned SQLAlchemy Session/transaction.

This task must connect:
- the accepted 3D3B account snapshot,
- the accepted pure 3D2 threading engine,
- the accepted 3D1 persistence primitives.

Do NOT implement transaction acquisition, BEGIN IMMEDIATE, lock retry, Engine-level orchestration, scheduler, routes, UI, IMAP, CRM, Calendar, AI, or external integrations.

## Exact Scope Lock
Create/modify only:
- app/services/email_thread_reconstruction.py
- test/test_email_thread_reconstruction.py

No other tracked path may change.

## Service core contract

Create app/services/email_thread_reconstruction.py with:

- frozen+slots ThreadReconstructionCoreResult
- ThreadReconstructionError with bounded error codes
- internal/public-for-tests function:

reconstruct_account_threads_in_session(session: sqlalchemy.orm.Session,
                                       account_scope: str) -> ThreadReconstructionCoreResult

This function MUST:
- assume the caller already owns the transaction;
- never call commit(), rollback(), begin(), BEGIN IMMEDIATE, or close();
- never retry;
- never access Engine directly.

Phase 3D3D will later add the final Engine-level wrapper and busy/retry behavior.

## Error codes for this phase

Use only bounded codes:
- invalid_scope
- invalid_source_state
- legacy_unresolved
- superseded_membership
- invalid_partition
- persistence_conflict

Never include raw subject/body/header content in exception messages.

## Required algorithm

### 1. Load snapshot
Use ThreadPersistenceRepository(session).load_account_thread_snapshot(account_scope).

Map repository ValueError from invalid scope/retention/snapshot integrity into the bounded service error codes above.

### 2. Preflight
Before any topology persistence:
- select eligible sources only as 3D2 nodes;
- if eligible source current conversation is legacy_unresolved -> fail entire pass with legacy_unresolved;
- if eligible source current conversation is superseded -> fail with superseded_membership;
- if eligible source current conversation account_scope differs from requested account -> fail invalid_partition;
- for every touched current conversation, inspect full_current_members:
  - any member whose source_type != 'email_message' -> fail invalid_partition;
  - any member whose account_scope != requested account -> fail invalid_partition;
- do not repair anything.

Excluded sources do not become 3D2 nodes and are not reassigned.

### 3. Build 3D2 input
For each eligible source, ordered by source_record_id:
- account_scope
- source_record_id
- normalized_message_id
- in_reply_to
- references_header
- subject
- source_revision from accepted calculate_source_revision contract.

Invoke reconstruct_threads exactly once.

Validate:
- components partition exactly all eligible source IDs;
- no duplicate/missing source IDs;
- decisions/evidence mapping is internally consistent;
- accepted targets belong to the selected same-account corpus.

If invalid -> invalid_partition.

### 4. Persist evidence and decisions
Persist all 3D2 evidence in returned order via ThreadPersistenceRepository.append_evidence.
Map evidence_index -> ThreadEvidence.id.

Persist all decisions in returned order via append_decision.
Map evidence_index -> ThreadEvidenceDecision.id.

Exact replay must reuse existing rows.

### 5. Compute old partition
For each eligible source:
- old current conversation may be None;
- old conversation full member set is the complete set from snapshot, including excluded members.

Build deterministic old/new overlap groups exactly as approved:
- old predecessor vertex for each distinct current conversation touched by eligible members;
- new successor vertex for each 3D2 component;
- overlap edge when an eligible member belongs to both;
- isolated new component forms its own group;
- deterministic group ordering by min new source id, then predecessor stable ordering if required only for deterministic processing.

Do not use subject/current conversation identity to alter 3D2 topology.

### 6. Classification
Exactly:

0 old -> 1 new = initial

1 old -> 1 new and full old member set == new component = unchanged

>=2 old -> 1 new = merge

1 old -> >=2 new = split

>=2 old -> >=2 new = repartition

1 old -> 1 new but full old member set != new component = correction

No other classification is valid.

### 7. Conversation identity rules
- unchanged: retain current Conversation exactly; no new Conversation, no membership history, no lineage.
- every changed group: create fresh successor Conversation(s), one per new component.
- no arbitrary survivor.
- initial group has no lineage.
- merge/split/repartition/correction create exactly one grouped ThreadLineageOperation using existing repository primitive.
- correction is exactly 1->1.

### 8. Membership change rules
For each source assigned to a fresh successor:
- no prior membership -> reason initial_assignment;
- prior member in merge group -> merge;
- split -> split;
- repartition -> repartition;
- correction -> correction.

evidence_decision_id:
- accepted decision belonging to that same source if one exists;
- otherwise None;
- never use another source's decision.

evidence summary:
- accepted local decision -> evidence_type='thread_decision', evidence_reference='decision:<id>'
- singleton no accepted edge -> evidence_type='singleton', evidence_reference='source:<id>'
- root/no accepted edge in multi-source component -> evidence_type='thread_decision', evidence_reference='source:<id>'

### 9. Postconditions
Before returning:
- eligible IDs equal disjoint union of components;
- every eligible source has exactly one current membership;
- each current conversation for eligible sources is resolved, same-account, active;
- eligible members of each current conversation equal exactly one computed component;
- changed assignments have history;
- changed groups have complete lineage;
- unchanged groups have no new topology/history rows;
- excluded sources were not reassigned.

If a postcondition fails, raise bounded service error. Caller will roll back.

## Core result

Return at least:
- account_scope
- reconstruction_key
- source_count
- component_count
- conversations_created
- memberships_changed
- lineage_operations_created

Exact unchanged replay should return zero topology-change counts.

## Required tests

Synthetic isolated tests in test/test_email_thread_reconstruction.py:

1. empty corpus;
2. initial singleton;
3. initial multi-email component;
4. unchanged exact-set rerun;
5. merge;
6. split;
7. repartition;
8. correction 1->1;
9. newly unassigned source entering changed group;
10. excluded old member forces correction/change rather than unchanged;
11. source-local accepted evidence pointer;
12. root/no-edge null evidence_decision_id;
13. legacy_unresolved fails before topology mutation;
14. superseded membership fails;
15. foreign-account touched conversation fails;
16. non-email full member fails;
17. malformed/ambiguous singleton behavior delegated to 3D2;
18. same-subject non-linkage remains;
19. evidence_index -> persisted decision mapping;
20. exact replay duplicates no Conversation/ThreadMembershipChange/ThreadLineageOperation/ThreadLineageEdge;
21. new reconstruction key with unchanged topology creates no topology/history transition;
22. function never commits/rolls back/begins/closes caller transaction;
23. no AuditEvent rows created.

Tests may use synthetic SQLite/session fixtures only.

## Restrictions
- no repository/model/migration/doc changes;
- no Engine parameter yet;
- no BEGIN IMMEDIATE;
- no retry/sleep;
- no network/external integrations;
- no generic AuditEvent;
- no raw body/header storage beyond existing accepted evidence behavior;
- no new dependency.

## Validation

Run:
python -m pytest test/test_email_thread_reconstruction.py

Then:
python -m pytest

Confirm tracked diff contains only the two authorized paths.

## Completion

Commit:
Implement phase 3D3C reconstruction core

Push only origin/codex-work.

If another tracked file is required, STOP.
