# Phase 3D2 Implementation Task — Canonical Header Parser and Pure Thread Graph

**Status:** Approved for Implement
**Date:** 2026-09-23
**Baseline:** current `codex-work`
**Plan:** `docs/plans/implementation-phase-3d2-plan.md`

## 1. Objective

Implement exactly the approved Phase 3D2 pure deterministic email-threading engine:

- strict canonical parsing of Message-ID, In-Reply-To and References;
- bounded malformed/overflow evidence;
- diagnostic-only subject normalization;
- duplicate Message-ID index preserving ambiguity;
- deterministic parent/ancestor candidate selection;
- corpus-wide conflict rejection;
- corpus-wide cycle rejection;
- accepted directed edges;
- deterministic connected components including singletons;
- 3D1-compatible source revisions;
- deterministic reconstruction key.

No persistence or external integration is part of this task.

## 2. Scope Lock — authorized files only

Create/modify only:

- `app/domain/__init__.py`
- `app/domain/email_threading.py`
- `test/test_email_threading.py`

No fourth file may change. If another file is required, STOP.

## 3. Implementation authority

Follow `docs/plans/implementation-phase-3d2-plan.md` exactly.

Do not reinterpret:
- grammar;
- limits;
- References behavior;
- In-Reply-To blocking behavior;
- conflict/cycle semantics;
- decision mapping;
- ordering;
- source_revision;
- reconstruction_key.

If implementation requires a semantic deviation, STOP.

## 4. Critical parser invariants

1. Message-ID grammar:
   - complete token only;
   - ASCII visible local@domain;
   - one matching optional outer angle pair;
   - outer SP/HTAB only;
   - no opportunistic substring extraction;
   - canonical whole identifier lowercase;
   - max canonical token 998 characters.

2. Header bounds:
   - raw ID-header max 32,768 UTF-8 bytes;
   - References max 100 spans;
   - overflow fail-closed for topology;
   - no topology from truncated prefix.

3. References:
   - preserve ordinal order including malformed observations;
   - any malformed span makes entire References chain non-linking;
   - only last uniquely locally resolved token in a wholly valid chain is a linking candidate;
   - earlier tokens are support only.

4. In-Reply-To:
   - missing permits References fallback;
   - exactly one valid token may provide direct-parent candidate;
   - malformed, over-limit or multiple valid IDs blocks all outgoing linking from that source.

5. Message-ID duplicates:
   - index token -> all matching source IDs;
   - never first-match;
   - duplicate target = ambiguity.

## 5. Critical graph invariants

- at most one provisional outgoing link per source;
- direct parent preferred over References fallback;
- incompatible local IRT/References candidates => reject all outgoing links from that source;
- cycle membership => reject all outgoing links from every source in the cycle;
- conflict/cycle detection must be simultaneous/fixed-point and input-order independent;
- incoming safe edges to blocked sources may remain;
- components use accepted edges as undirected connectivity;
- every source appears exactly once;
- unlinked sources are singletons;
- subject never changes graph topology.

## 6. Pure public contract

Implement exactly the constants, frozen+slots dataclasses, signatures, ordering, evidence-index semantics and output contract defined in the approved plan.

Only Python standard library imports are permitted in the domain module.

No:
- SQLAlchemy;
- repositories;
- FastAPI;
- adapters;
- keyring;
- network;
- filesystem persistence;
- database;
- logging of raw headers.

## 7. Fingerprint compatibility

### source_revision
Must byte-match 3D1:

domain:
`3d1/source-revision/v1`

fields in order:
- source_record_id
- message_id
- in_reply_to
- references

Use the approved length-prefixed UTF-8 serialization and `-1:` for None.

### reconstruction_key
Domain:
`3d2/reconstruction/v1`

Include:
- account_scope
- ALGORITHM_VERSION
- source_count
- sorted pairs of source_record_id + source_revision

Exclude:
- subject;
- body;
- folder/UID;
- Conversation IDs;
- unrelated metadata.

## 8. Required tests

Implement the complete approved test matrix, at minimum:

### Parser
- valid/invalid local/domain grammar;
- whole-token lowercase normalization;
- outer whitespace/brackets;
- comments/quotes/domain literals/folding/prose rejection;
- 998 vs 999 token;
- 32,768 vs 32,769 UTF-8 bytes;
- 100 vs 101 References spans;
- malformed mixed References;
- missing vs empty;
- IRT 0/1/multiple;
- valid+malformed IRT;
- malformed digest contains no raw output.

### Graph
- direct reply;
- References-only fallback;
- missing external intermediates;
- duplicate Message-ID target;
- self-link;
- incompatible IRT/References;
- two-component bridge rejection;
- directed cycles;
- simultaneous cycles/conflicts;
- permutation invariance;
- incoming edge to blocked node;
- singleton coverage;
- late-root recomputation;
- independent same-subject messages;
- changed subject with same topology.

### Subject
- Re/Fw/Fwd/RV/R/Enc;
- repeated prefixes;
- spacing around colon;
- bracketed tags preserved;
- subject excluded from reconstruction key.

### Fingerprints/contracts
- byte-for-byte 3D1 source revision compatibility;
- invalid supplied source revision rejection;
- deterministic reconstruction key;
- empty corpus;
- mixed account rejection;
- duplicate/nonpositive source ID rejection;
- output ordering;
- accepted edge ↔ accepted decision correspondence;
- no persistence/framework/external imports.

## 9. Validation

Run:

`python -m pytest test/test_email_threading.py`

Then:

`python -m pytest`

Both must pass.

Inspect exact diff against this task baseline and confirm only three authorized paths changed.

## 10. Completion protocol

Commit:

`Implement phase 3D2 canonical threading engine`

Push only to `origin/codex-work`.

Do not touch `main`.
