# Phase 3D Decisions — Email Thread Reconstruction

**Status:** APPROVED
**Date:** 2026-09-23
**Baseline:** current `codex-work`

## D1 — Canonical header normalization

Approved:
- normalization happens inside Phase 3D; do not alter Phase 3C ingestion or the IMAP adapter;
- Message-ID, In-Reply-To, and each References element are parsed into canonical comparison tokens;
- surrounding whitespace and angle brackets are removed for comparison;
- comparison is case-insensitive;
- malformed identifiers are retained only as invalid evidence and cannot create a thread edge;
- multiple identifiers in In-Reply-To are ambiguous and cannot create an automatic direct-parent edge;
- References preserves source order;
- explicit bounded token and chain limits are required.

## D2 — Conservative conflict policy

Approved:
- one valid unique In-Reply-To target is the strongest direct-parent evidence;
- References may corroborate and provide ancestor evidence;
- if In-Reply-To and References incompatibly connect distinct local components, do not merge automatically;
- duplicate Message-ID targets make that reference ambiguous;
- self-links and cycles are invalid;
- never perform transitive merge through ambiguous evidence;
- unresolved conflicts remain unresolved rather than guessed.

## D3 — Orphans and subject

Approved:
- every logical EmailMessage starts with or belongs to a singleton Conversation when no accepted technical edge links it;
- two local replies sharing only the same missing external ancestor are not merged solely for that reason;
- late arrival of the missing parent/root triggers recomputation and may then merge components;
- subject is secondary evidence only;
- subject alone never creates a merge;
- Re:/FW:/Fwd: and localized equivalents may be normalized only for secondary comparison/diagnostics.

## D4 — Full append-only history model

Approved:
- use the analysis Alternative A;
- extend the data model to preserve append-only thread evidence/decisions and membership assignment history;
- current membership remains queryable;
- merges, splits, ambiguities, conflicts, and supersession remain traceable;
- history is never silently rewritten.

## D5 — Conversation identity on merge/split

Approved:
- do not derive a conversation identity directly from the current set of Message-IDs;
- retain local stable conversation identity;
- when previously distinct conversations merge, create a new Conversation and supersede the prior conversations into it;
- when a conversation splits, create new Conversation records and supersede the prior conversation;
- do not arbitrarily pick an old conversation as the winner;
- explicit supersession lineage must remain queryable.

## D6 — Full-corpus deterministic baseline

Approved:
- MVP reconstruction uses a full account-scoped local corpus pass;
- no threading logic is embedded inside Phase 3C;
- threading runs as a separate local service after synchronization;
- incremental reconstruction is deferred until it can be proven equivalent to the deterministic full-corpus result;
- full reconstruction remains local and does not access IMAP/network/keyring/AI/CRM/Calendar.

## Consequence

Phase 3D requires an approved data-model/migration design before implementation.

No schema or implementation change is authorized by this decision record alone.
