# Phase 3D Analysis Task — Email Thread Reconstruction

**Status:** Approved for Analyze
**Date:** 2026-09-23
**Baseline:** current `codex-work`

## 1. Objective

Analyze Phase 3D: reconstruct email conversations/threads from the persisted email corpus created by Phase 3C.

The analysis must define how messages are grouped into `Conversation` records using technical email evidence while preserving ambiguity.

This phase is about thread reconstruction only.

It must not yet implement:
- semantic email analysis;
- AI;
- exact-question extraction;
- tasks/commitments/next steps;
- CRM matching;
- reply proposals;
- filing proposals;
- drafts or mailbox moves;
- Calendar;
- UI/dashboard;
- scheduler.

## 2. Authoritative requirements

Review at minimum:
- `docs/functional-spec.md` section 5.4 and related ambiguity/traceability rules;
- `docs/data-model.md`;
- `docs/architecture.md`;
- `docs/testing-strategy.md`;
- `docs/plans/implementation-phase-3c-plan.md`;
- accepted Phase 3C implementation;
- `app/persistence/models.py`;
- `app/persistence/repositories.py`;
- `app/services/imap_sync.py`.

## 3. Fixed functional rule

Thread reconstruction evidence priority:

1. Message-ID
2. In-Reply-To
3. References
4. normalized subject only as secondary evidence

Participants, dates, folder, CRM context or semantic similarity may not by themselves justify merging conversations.

If evidence is insufficient or conflicting, messages remain separate.

No silent ambiguity resolution.

## 4. Analysis questions

Close or explicitly elevate:

1. exact thread reconstruction service boundary;
2. whether current `Conversation` and `ConversationMembership` schema is sufficient;
3. canonical normalization for Message-ID, In-Reply-To and References;
4. whether stored `normalized_message_id` is already sufficiently normalized or needs application normalization;
5. parsing rules for multiple IDs in References;
6. how direct parent links are built from In-Reply-To;
7. how ancestor links are inferred from References;
8. how to handle malformed IDs;
9. duplicate Message-ID across multiple EmailMessage rows;
10. missing Message-ID;
11. orphan replies whose parent is outside the sync window;
12. late arrival of a parent/root message;
13. thread merge when previously separate components become connected by later evidence;
14. whether thread splitting is ever allowed after persisted evidence changes;
15. conflicting evidence where In-Reply-To points to one component and References to another;
16. subject normalization and exactly when it may be used;
17. whether subject can create a thread without header evidence;
18. handling `Re:`, `FW:`, `Fwd:`, localized prefixes if relevant;
19. whether cross-folder messages are naturally one thread;
20. deterministic conversation identity/idempotency;
21. how existing Conversation rows are reused;
22. how ConversationMembership evidence_type/evidence_reference should be populated;
23. whether one source/email can belong to more than one conversation;
24. transaction boundaries;
25. rebuild/recompute strategy after new mail arrives;
26. incremental thread reconstruction versus full corpus pass;
27. audit/provenance requirements;
28. safe handling of ambiguous/conflicting data;
29. repository methods required;
30. exact fake-only test matrix;
31. proposed subphases if useful;
32. exact Scope Lock.

## 5. Important edge cases

The analysis must explicitly cover:

- A replies to B using In-Reply-To;
- References chain with missing intermediate messages;
- root appears after replies;
- duplicate Message-ID on unrelated messages;
- malformed Message-ID header;
- empty/missing Message-ID;
- two independent emails with same subject;
- long reply chain where subject changes;
- forwarded email;
- one reply references two previously separate local conversation components;
- message moved between IMAP folders;
- UIDVALIDITY reset causing a new location for the same logical email;
- same EmailMessage represented by multiple locations from 3C;
- replay/idempotency;
- metadata correction on an already persisted email.

## 6. Schema-gap rule

If the existing schema cannot safely represent:
- deterministic conversation membership;
- evidence provenance;
- later merging of previously separate threads;
- ambiguity without forced merge;

then STOPPED FOR DECISION and explain the minimal schema alternatives.

Do not implement or modify schema during analysis.

## 7. Guardrails

READ-ONLY except for the analysis document.

No:
- code implementation;
- model/migration changes;
- dependencies;
- network;
- real mailbox;
- AI;
- CRM/Calendar;
- UI/main/scheduler;
- mailbox mutation.

## 8. Output

Create only:

`docs/plans/implementation-phase-3d-analysis.md`

Status:
- READY FOR APPROVAL
- or STOPPED FOR DECISION

Must include:
- reconstruction algorithm;
- evidence hierarchy;
- normalization rules;
- duplicate/missing-ID policy;
- conflict policy;
- incremental/rebuild strategy;
- conversation identity;
- membership evidence contract;
- transaction/idempotency model;
- schema gap assessment;
- required repositories/services;
- test matrix;
- proposed subphases;
- exact Scope Lock;
- open decisions.

## 9. Completion protocol

Commit:

`Analyze phase 3D email thread reconstruction`

Push only to `origin/codex-work`.

Do not touch `main`.
