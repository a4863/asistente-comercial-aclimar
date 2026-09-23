# Phase 3D3 Decisions — Full-Corpus Reconstruction Service

**Status:** APPROVED
**Date:** 2026-09-23

## A — Corpus eligibility
Approved A1:
- every locally retained logical email for the account participates in reconstruction even if all IMAP locations are unavailable;
- IMAP location availability is not a threading eligibility criterion;
- explicitly locally deleted/redacted sources are excluded according to SourceRecord retention/redaction state;
- do not invent a new email-specific deleted_at_source field in 3D3.

## B — Legacy quarantine
Approved B1:
- if any otherwise eligible email in the account currently belongs to a legacy_unresolved conversation, fail the entire account reconstruction pass;
- do not run a degraded subset;
- do not silently move a quarantined source;
- quarantine repair is a separate explicitly approved task.

## C — Transaction boundary
Approved C1:
- one account-wide SQLite write transaction for a reconstruction pass;
- acquire the write reservation before reading the corpus;
- read, compute 3D2, persist evidence/decisions/conversations/memberships/lineage, and commit as one atomic unit;
- no component-level partial commits.

## D — 1→1 lineage correction
Approved D2:
- extend ThreadLineageOperation.kind with correction;
- correction means exactly one predecessor -> exactly one successor;
- use correction when the prior conversation member set changes but there is only one predecessor conversation and one successor component;
- no identity change may be left without explicit lineage;
- sources with no previous membership do not count as predecessors.

## E — Membership reason and evidence pointer
Approved:
- no previous membership => initial_assignment;
- reassigned predecessor member in merge => merge;
- split => split;
- repartition => repartition;
- 1→1 changed-set transition => correction;
- evidence_decision_id uses an accepted decision belonging to that same source when one exists;
- root/singleton/source with no accepted outgoing edge => NULL;
- never attach another source's decision.

## F — Stale snapshot / retry
Approved:
- because the write reservation is acquired before corpus read, no optimistic read-then-revalidate protocol is needed for the pass;
- if the write transaction cannot be acquired because of contention, retry at most 3 attempts;
- after 3 failed attempts, abort cleanly with a busy/retry_later result;
- never perform a partial pass.

## G — Audit boundary
Approved G2:
- 3D3 relies on typed threading history:
  - ThreadEvidence
  - ThreadEvidenceDecision
  - ThreadMembershipChange
  - ThreadLineageOperation
  - ThreadLineageEdge
- generic AuditEvent integration is deferred to a later explicitly approved phase;
- do not duplicate threading history into generic audit now.

## Consequence
Codex must revise docs/plans/implementation-phase-3d3-plan.md into an exact READY FOR APPROVAL implementation plan, including the controlled 3D1 lineage extension for correction 1→1. No implementation is authorized yet.
