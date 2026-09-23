# Phase 3D Physical Design Decisions

**Status:** APPROVED
**Date:** 2026-09-23

## D7 — Singleton current membership
Approved:
- every logical EmailMessage must have one current Conversation after 3D reconstruction;
- standalone, ambiguous, malformed, and otherwise unlinked emails use singleton conversations;
- update docs/data-model.md accordingly; absence of membership is no longer the 3D target state.

## D8 — Current projection + append-only history
Approved Alternative A:
- ConversationMembership remains the authoritative current projection;
- UNIQUE(source_record_id) remains the one-current-conversation guard;
- every real assignment/reassignment is also written to append-only history;
- projection update and history append must be atomic.

## D9 — Grouped lineage operation + edges
Approved:
- ThreadLineageOperation groups one merge/split/reconstruction lineage event;
- ThreadLineageEdge records predecessor -> successor pairs within that operation;
- support N:N lineage;
- self-edge prohibited physically;
- cycles prohibited transactionally before commit;
- same-account enforced transactionally and by available constraints.

## D10 — Opaque stable local conversation key
Approved:
- Conversation receives an immutable opaque local stable key;
- key is unique within account_scope;
- key is not derived from Message-ID, subject, members, or current component;
- replay idempotency uses dedicated replay identities/keys, not conversation-key regeneration.

## D11 — Parsed evidence separate from decision
Approved:
- ThreadEvidence stores bounded parsed technical evidence;
- ThreadEvidenceDecision stores the interpretation/outcome of that evidence;
- one evidence row may receive later decisions as local corpus knowledge changes;
- evidence stores bounded canonical token plus SHA-256 digest, normalization version, header kind, ordinal, source/header revision fingerprint;
- never store the complete raw References header in new threading history/audit rows.

## D12 — Legacy quarantine and baseline history
Approved:
- valid legacy conversations whose email memberships resolve to one account may be migrated;
- orphan, mixed-account, or non-email legacy conversation state must not be assigned invented provenance;
- such rows remain explicitly legacy_unresolved/quarantined and excluded from normal 3D reconstruction until resolved;
- legacy current memberships receive an append-only baseline history reason legacy_assignment_baseline;
- baseline history must not claim technical threading evidence.

## D13 — Destructive downgrade forbidden
Approved:
- a downgrade that would destroy populated 3D evidence, lineage, or membership history must fail closed;
- no silent loss of threading history;
- downgrade behavior must be tested.

## Consequence
Proceed to exact 3D1 model+migration plan. No parser/service implementation is authorized yet.
