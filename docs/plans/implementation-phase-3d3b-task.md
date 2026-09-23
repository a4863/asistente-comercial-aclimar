# Phase 3D3B Implementation Task — Account Thread Snapshot Repository

**Status:** Approved for Implement
**Date:** 2026-09-23
**Parent plan:** docs/plans/implementation-phase-3d3-plan.md
**Accepted prerequisite:** Phase 3D3A

## Objective
Implement only the repository read surface required by Phase 3D3 to load a complete account-scoped threading snapshot.

Do NOT implement:
- app/services/email_thread_reconstruction.py
- BEGIN IMMEDIATE orchestration
- retry/busy behavior
- 3D2 invocation
- evidence/decision persistence orchestration
- partition transitions
- lineage creation
- scheduler/UI/integrations.

## Exact Scope Lock
Modify only:
- app/persistence/repositories.py
- test/test_persistence_repositories.py

No other tracked path may change.

## Required repository API

Add to ThreadPersistenceRepository a read-only, caller-transaction method:

load_account_thread_snapshot(account_scope)

It must not commit or begin/close transactions.

Return an immutable/simple structured result suitable for the later service, containing enough data to determine:
1. all account email SourceRecords;
2. eligibility according to Phase 3D3 rules;
3. stored EmailMessage threading headers/subject for eligible sources;
4. current membership for each eligible source, if any;
5. Conversation state for every touched current membership;
6. the complete current member set of every touched conversation, including excluded/non-eligible sources.

Use deterministic ordering by source/conversation/member IDs.

## Eligibility contract

For SourceRecord with:
- source_type='email_message'
- source_system_scope == account_scope

States:

Eligible:
- retention_state == 'active'
- deleted_or_redacted_at IS NULL
- exactly one EmailMessage row exists.

Excluded valid terminal source:
- retention_state IN ('deleted', 'redacted')
- deleted_or_redacted_at IS NOT NULL.

Invalid source state -> repository must fail closed with ValueError:
- active + non-null deleted_or_redacted_at;
- deleted/redacted + null timestamp;
- any other retention_state;
- email SourceRecord with missing EmailMessage representation.

IMAPMessageLocation must NOT affect eligibility or corpus cardinality.

An account may have zero eligible emails.

## Snapshot fields

For each account email source expose at least:
- source_record_id
- account_scope
- retention_state
- deleted_or_redacted_at
- eligible bool
- normalized_message_id
- in_reply_to
- references_header
- subject
- current_conversation_id | None
- conversation_account_scope | None
- conversation_legacy_status | None
- conversation_superseded_at | None
- full_current_member_ids for the touched conversation, sorted tuple.

Do not expose body, attachments, raw MIME, credentials, folders, UIDs, sender/recipient content unless already required by this exact contract (they are not).

## Integrity behavior

Fail closed if:
- account_scope invalid/blank/>100;
- duplicate logical EmailMessage representation is observed despite physical uniqueness;
- eligible source membership points to missing conversation;
- touched conversation has inconsistent current membership rows;
- repository cannot represent the snapshot deterministically.

Do NOT repair:
- legacy_unresolved;
- superseded conversation;
- foreign-account conversation;
- non-email members.

Those states must be faithfully surfaced in the snapshot so the later service can decide/fail according to the approved 3D3 policy.

## Required tests

Add focused synthetic repository tests for:

1. empty account;
2. one active eligible email;
3. email with only unavailable IMAP locations remains eligible;
4. email with no IMAP locations remains eligible;
5. valid deleted source excluded;
6. valid redacted source excluded;
7. active + deletion timestamp rejected;
8. deleted/redacted without timestamp rejected;
9. unknown retention_state rejected;
10. missing EmailMessage row rejected;
11. eligible source with no current membership;
12. eligible source with resolved active conversation;
13. legacy_unresolved membership surfaced, not repaired;
14. superseded conversation membership surfaced, not repaired;
15. foreign-account conversation state surfaced, not normalized;
16. complete current member set includes excluded members;
17. complete current member set includes non-email members if present;
18. deterministic ordering;
19. no body/attachment/location duplication in returned logical rows;
20. method performs no commit.

## Restrictions

- read-only repository behavior only;
- no service code;
- no migration/model/doc change;
- no new dependency;
- no database mutation beyond test fixtures;
- no raw body/content in snapshot return.

## Validation

Run:

python -m pytest test/test_persistence_repositories.py

Then:

python -m pytest

Inspect tracked diff and confirm only the two authorized paths changed.

## Completion

Commit:
Implement phase 3D3B account thread snapshot

Push only origin/codex-work.

If another file is required, STOP.
