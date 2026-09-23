# Phase 3D2 Decisions — Canonical Header Parser and Pure Thread Graph Engine

**Status:** APPROVED
**Date:** 2026-09-23

## A — Conservative Message-ID grammar
Approved:
- accept only one visible-ASCII token structurally shaped as local@domain;
- no internal whitespace;
- optional surrounding whitespace;
- optional single outer angle-bracket pair;
- canonical comparison token is the full token lowercased;
- comments, complex quoted local-parts, domain literals, nested/unbalanced brackets, stray prose, or opportunistic extraction from arbitrary text are malformed;
- malformed identifiers never create edges.

## B — Bounds and fail-closed overflow
Approved:
- canonical token maximum: 998 characters;
- processed header value maximum: 32 KiB;
- References maximum: 100 tokens;
- over-limit header creates no graph edge from that header;
- over-limit References does not retain a linking prefix;
- no silent truncation that can alter topology.

## C — Mixed valid/malformed References
Approved:
- any malformed segment invalidates the References chain for automatic linking;
- independently valid tokens may still be emitted as parsed evidence;
- the chain itself is not used for connectivity;
- do not skip across malformed gaps.

## D — References-only linking
Approved:
- only the last valid, uniquely locally resolved token in a completely valid References chain may become the References linking candidate;
- earlier valid References tokens remain ancestor/support evidence only;
- missing external intermediates do not by themselves invalidate an otherwise valid chain;
- two local messages sharing only a missing external ancestor remain separate.

## E — Multiple/invalid In-Reply-To
Approved:
- missing In-Reply-To permits normal References evaluation;
- exactly one valid identifier is the strongest direct-parent candidate;
- more than one valid identifier => multiple_in_reply_to and suppress all automatic outgoing linking from that source;
- malformed In-Reply-To with no valid identifier also suppresses all automatic outgoing linking from that source;
- no References fallback when In-Reply-To is ambiguous or malformed.

## F — Conflict and cycle policy
Approved:
- if unique In-Reply-To and References candidates point incompatibly across components, reject all outgoing edges from that source for that reconstruction;
- do not keep a preferred subset;
- if an outgoing edge set would create a directed cycle, reject all outgoing edges from that source for that reconstruction;
- conflict/cycle evaluation must be corpus-wide and input-order independent;
- incoming accepted edges from other sources may still place that message in a component.

## G — Secondary subject normalization
Approved diagnostic-only normalization:
- trim outer whitespace;
- collapse internal whitespace;
- case-insensitive comparison;
- repeatedly remove recognized leading prefixes:
  - Re:
  - Fw:
  - Fwd:
  - RV:
  - R:
  - Enc:
- allow surrounding whitespace around the colon;
- continue removing repeated recognized prefixes until none remains;
- preserve bracketed tags such as [EXTERNAL] or [PROYECTO X];
- subject never affects connectivity, conflict resolution, or component membership.

## H — Pure snapshot/output and fingerprint
Approved input per logical email:
- account_scope
- source_record_id
- message_id
- in_reply_to
- references
- subject
- source_revision

Approved output:
- parsed evidence;
- evidence decisions;
- accepted directed edges;
- deterministic connected components;
- normalized diagnostic subject;
- reconstruction_key.

Determinism:
- reject mixed-account or duplicate source inputs;
- corpus ordered by source_record_id;
- component members sorted ascending;
- components sorted by minimum source_record_id;
- reconstruction fingerprint is versioned and includes account_scope, algorithm version, and sorted (source_record_id, source_revision) pairs;
- subject is excluded from reconstruction_key because it cannot affect topology;
- body and unrelated metadata are excluded.

## Consequence
Codex must revise docs/plans/implementation-phase-3d2-plan.md into an exact implementation-ready READY FOR APPROVAL plan using these decisions. No code implementation is authorized yet.
