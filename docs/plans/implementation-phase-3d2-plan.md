# Phase 3D2 plan — canonical headers and pure threading graph

**Status:** READY FOR APPROVAL
**Date:** 2026-09-23
**Task:** `docs/plans/implementation-phase-3d2-final-plan-task.md`
**Baseline:** `b3b9c52` on `codex-work`

## 1. Objective, authority, and current state

Implement, only after separate approval, a pure deterministic parser and graph engine for a complete local, account-scoped snapshot of logical emails. It yields bounded parsed observations, one decision per observation, accepted directed links, connected components including singletons, diagnostic normalized subjects, and a versioned reconstruction key. It never assigns database `Conversation` IDs, changes current memberships, accesses IMAP/SQLite, or calls any external system.

The formerly blocking alternatives A–H are closed by approved `docs/plans/implementation-phase-3d2-decisions.md`. This plan refines those approved choices into a testable technical contract; it does not add a business rule. Inputs consulted: `AGENTS.md`; this final-plan task; the prior 3D2 plan and decisions; approved 3D decisions D1–D13; the 3D1 plan and accepted models/repository/migration/tests; `docs/functional-spec.md` §5.4, `docs/data-model.md` §§5/12, `docs/architecture.md` §§3–4/10–11, and `docs/testing-strategy.md` §§2–4/8–9. No required source is missing.

3D1 persists `ThreadEvidence` with `valid|malformed` status, ordered `header_kind/ordinal`, canonical token or null, SHA-256 digest, normalization version, and source revision. `ThreadEvidenceDecision` stores one outcome per evidence/reconstruction key, with target ID only for `accepted_direct_parent` or `accepted_ancestor`. Phase 3C's `normalized_message_id` is merely stored/trimmed text, not a canonical comparison ID. The engine must use one node per `EmailMessage`/`SourceRecord`, independent of its IMAP locations. No pure threading module exists yet.

## 2. Exact implementation files and public pure contracts

Create exactly `app/domain/__init__.py` (empty package marker), `app/domain/email_threading.py`, and `test/test_email_threading.py` in the later implementation. The domain module may import Python standard-library `dataclasses`, `hashlib`, `re`, and typing only. It must not import SQLAlchemy, repositories, application services, adapters, network/keyring, or framework objects. All dataclasses below are `frozen=True, slots=True`; all returned collections are tuples, never mutable sets/lists. Public names and signatures:

```text
NORMALIZATION_VERSION: int = 1
ALGORITHM_VERSION: int = 1

EmailThreadInput(account_scope: str, source_record_id: int,
    message_id: str | None, in_reply_to: str | None,
    references: str | None, subject: str | None,
    source_revision: str)
TokenObservation(ordinal: int, parse_status: Literal['valid','malformed'],
    canonical_token: str | None, token_digest: str)
HeaderParse(field_state: Literal['missing','valid','malformed','over_limit','multiple'],
    observations: tuple[TokenObservation, ...])
ParsedEvidence(account_scope: str, source_record_id: int, header_kind: str,
    ordinal: int, parse_status: str, canonical_token: str | None,
    token_digest: str, normalization_version: int, source_revision: str)
EvidenceDecision(evidence_index: int, outcome: str,
    target_source_record_id: int | None)
AcceptedEdge(source_record_id: int, target_source_record_id: int,
    kind: Literal['direct_parent','ancestor'], evidence_index: int)
SubjectDiagnostic(source_record_id: int, normalized_subject: str | None)
ThreadingResult(account_scope: str, reconstruction_key: str,
    evidence: tuple[ParsedEvidence, ...],
    decisions: tuple[EvidenceDecision, ...],
    edges: tuple[AcceptedEdge, ...],
    components: tuple[tuple[int, ...], ...],
    subjects: tuple[SubjectDiagnostic, ...])

parse_message_id(value: str | None) -> HeaderParse
parse_in_reply_to(value: str | None) -> HeaderParse
parse_references(value: str | None) -> HeaderParse
normalize_subject(value: str | None) -> str | None
calculate_source_revision(message: EmailThreadInput) -> str
calculate_reconstruction_key(account_scope: str,
    messages: tuple[EmailThreadInput, ...]) -> str
reconstruct_threads(account_scope: str,
    messages: tuple[EmailThreadInput, ...]) -> ThreadingResult
```

`EvidenceDecision.evidence_index` and `AcceptedEdge.evidence_index` are zero-based indexes into the returned `evidence` tuple, not persistent evidence IDs. A future 3D service may persist the observations first and then map those indexes to 3D1 IDs. Parsers return no database objects. Reject non-string header/subject values (other than `None`), mixed account scopes, duplicate/nonpositive source IDs, invalid account scope (empty or >100 characters), malformed source-revision hex, or a source revision that does not match the three supplied stored header values with `ValueError`; never guess/correct input. An empty corpus is valid when `account_scope` is valid.

## 3. Exact ASCII ID grammar and bounded parser

`Message-ID` accepts **exactly one complete token**, not a substring. Around each token permit ASCII SP/HTAB only; permit either no brackets or one *matching outer* `<...>` pair. After removal, the token must be visible ASCII with exactly one `@`, no internal whitespace/control/non-ASCII, and this application grammar:

```text
atom        = one or more of A-Z a-z 0-9 ! # $ % & ' * + / = ? ^ _ ` { | } ~ -
local       = atom ('.' atom)*
label       = ASCII alphanumeric OR ASCII alphanumeric
              followed by 0..61 ASCII alphanumeric-or-hyphen
              followed by ASCII alphanumeric
domain      = label ('.' label)*
identifier  = local '@' domain
```

`label` length is 1–63; no requirement for more than one domain label and no separate DNS-total-length test. No empty dot segment, trailing/leading dot, quoted local part, domain literal, comment, nested/unbalanced bracket, stray punctuation/prose, backslash escape, or internal/folded CR/LF is accepted. Canonical token is the entire identifier ASCII-lowercased (both local and domain), with no brackets/outer SP/HTAB; never lower only the domain. Maximum canonical length is **998 ASCII characters inclusive**. Thus malformed or 999-character tokens cannot identify a node or create an edge.

For `In-Reply-To` and `References`, scan the *entire* header left-to-right as a sequence of token spans separated by one or more ASCII SP/HTAB; each span is an unbracketed identifier or one bracketed identifier. Adjacent bracket pairs without separator, prose, comments, commas, internal/folded whitespace, or stray bracket characters are malformed spans; do not opportunistically extract embedded IDs. Preserve zero-based span ordinals, including malformed spans. A present empty/whitespace-only value is malformed (one ordinal-0 malformed observation), distinct from `None` (missing, zero observations). Missing Message-ID similarly produces no evidence. Mixed valid/malformed `References` keeps valid parsed observations in order but invalidates the **whole chain for connectivity**. A malformed `In-Reply-To` span suppresses outgoing links from that source even if another span was valid; if all spans are valid but more than one identifier appears, state `multiple` and suppress all outgoing links. A single valid span is `valid`. A missing `In-Reply-To` permits References evaluation.

Bounds apply to each of the three raw stored ID-header values **before parsing**: UTF-8 length at most **32,768 bytes**, token at most 998 characters, and References at most **100 spans**. `None` is missing. A value above 32 KiB yields `over_limit`, one ordinal-0 malformed observation, and **no edge from that header**. A References value with >100 spans yields `over_limit`: emit observations for the first 100 spans plus one malformed overflow sentinel at ordinal 100, but **no References edge**, even from an otherwise valid prefix. A >998-character token within the 32 KiB header becomes one malformed observation; it invalidates a References chain or In-Reply-To field. There is no silent truncation used for topology. Message-ID and In-Reply-To have no 100-span allowance; a multi-span Message-ID is malformed and multi-span In-Reply-To follows the rule above.

Valid `token_digest` is `sha256(canonical_token.encode('utf-8')).hexdigest()`, exactly as 3D1 checks. Malformed observation digest is SHA-256 of domain `3d2/malformed/v1` followed by length-prefixed UTF-8 `header_kind`, decimal `ordinal`, decimal **full raw span byte length**, and at most the first 998 raw span bytes; for whole-header overflow use the full header byte length and first 998 header bytes. The raw span/header is not included in `TokenObservation`, `ParsedEvidence`, decisions, logs, or result. Every malformed/overflow observation has `canonical_token=None`, `parse_status='malformed'` for 3D1, and an ordinal unique within its header/revision. `HeaderParse.field_state` keeps `missing`, `multiple`, and `over_limit` distinctions in pure memory without requiring a new 3D1 enum. A valid observation retains `parse_status='valid'` even if the *chain* is unusable for linking.

## 4. Subject diagnostic only

`normalize_subject(None)` returns `None`; a present whitespace-only subject returns `''`. A subject over 32,768 UTF-8 bytes returns `None` diagnostically and never blocks technical linking. Otherwise trim outer whitespace, collapse every run of Unicode whitespace to one ASCII space, then repeatedly remove a **leading** case-insensitive prefix from exactly `Re`, `Fw`, `Fwd`, `RV`, `R`, `Enc`, followed by optional whitespace, `:`, and optional whitespace. Stop at the first non-prefix; do not remove bracketed tags such as `[EXTERNAL]` or `[PROYECTO X]` or a prefix hidden behind a tag. Collapse/trim again and Unicode-`casefold()` the remainder. `Re: Fwd : Subject` becomes `subject`; `Re: [EXTERNAL] Fwd: Subject` becomes `[external] fwd: subject` (tag retained, casefolded). The result is a diagnostic comparison string only: it cannot create/veto an edge, affect conflict/cycle decisions or components, or enter the reconstruction key. A changed subject with intact technical links leaves topology unchanged. A forward prefix alone never links emails.

## 5. Deterministic candidate, decision, and graph algorithm

1. Sort input by `source_record_id`; validate one account and unique logical source IDs. Parse each header under §3. Return every valid/malformed observation with `NORMALIZATION_VERSION=1`. Build `canonical Message-ID -> tuple[all source_record_ids]` (ascending); duplicate own Message-IDs remain **separate nodes**, not one selected target. A malformed/missing Message-ID cannot be a local target, but its source can still link outward through sound In-Reply-To/References evidence.
2. For a valid single In-Reply-To token, resolve against that index: 0 local matches means external/unresolved, 1 means a direct-parent candidate, >1 means duplicate-target ambiguity and **no outgoing link from that source**. A candidate pointing back to the same source is `self_link` and also blocks its outgoing link. Missing IRT permits References; malformed/multiple/over-limit IRT blocks **all** outgoing links from that source, including References fallback. Do not choose among duplicate targets by subject, date, folder, participant, or source ID.
3. Only a wholly valid, within-limit References chain can supply a linking candidate. Scan its valid tokens from right to left and choose the **last** token whose Message-ID index has exactly one local source. Earlier valid tokens remain ordered support observations, not additional linking edges. A token with no local match is external/unresolved; a duplicate local match is ambiguous and cannot be selected, but scanning may continue to an earlier unique token. Missing external intermediates do not invalidate a syntactically valid chain. A candidate pointing to the source itself is `self_link` and blocks that source's outgoing link; never skip a self-link to choose an earlier candidate. If the chain has any malformed span, exceeds a bound, or has no unique local token, it supplies no linking candidate. Two replies sharing only an external token never link to each other.
4. For each unblocked source choose at most **one** provisional outgoing link: use the unique local In-Reply-To candidate (`direct_parent`) if present; otherwise, if IRT is missing or valid but external, use the References candidate (`ancestor`) if present. A compatible References candidate when a local direct parent exists corroborates/diagnoses only; it is not a second graph link. Earlier References observations never create independent edges.
5. Resolve conflicts and cycles **simultaneously per iteration, never by input order**. Starting with all provisional links and an empty rejected-source set, compute a graph from currently unrejected sources. For each source with both local IRT and References candidates, remove that source's own link temporarily when testing compatibility. The candidates are compatible iff equal, or the References target is reachable by following directed provisional links from the IRT target (so it is an ancestor); otherwise mark that source `conflict`. Mark all such conflicting sources together, remove their outgoing links, then compute strongly connected components of the remaining directed graph. Mark **every source in every directed cycle** (SCC size >1; self-link was rejected earlier) `cycle_rejected` together and remove their outgoing links. Repeat the conflict/SCC scan until no new source is rejected. Rejected sources never become active again; removal can only destroy paths/cycles, so this finite fixed point is independent of input ordering. Incoming accepted links to a rejected source remain possible, as D3/F allow.
6. Accepted links are the remaining provisional links, sorted by `(source_record_id, target_source_record_id, kind)`. Treat them as undirected only for component construction: initialize every source as a singleton, union endpoints of accepted links, sort members ascending, then sort components by minimum member ID. Do **not** use subject, participant, date, folder, CRM context, duplicate Message-ID equality, or a shared missing external ancestor in union. A late root is a new input snapshot/reconstruction key and may then supply a unique local target; a changed header is likewise recomputed from the full corpus. No persistent conversation identity or merge/split lineage is chosen in 3D2.

There is exactly **one `EvidenceDecision` per `ParsedEvidence`**, in evidence order. The allowed 3D1 outcomes and target semantics are:

| Observation | Outcome / target |
| --- | --- |
| Valid own Message-ID | `identity_observed`, target null, even if another source has the same token. |
| Any malformed or overflow sentinel | `malformed`, target null. Missing header emits no evidence/decision. |
| Valid IRT in a multi-valid IRT field | `multiple_in_reply_to`, target null. A valid token in a field also containing a malformed span is `not_linking`, target null; the malformed span itself is `malformed`. |
| Valid reference/IRT token with no local target | `unresolved_external`, target null. |
| Valid token resolving to >1 local source | `duplicate_target`, target null. |
| Selected linking candidate pointing to self | `self_link`, target null; all outgoing links from that source are suppressed. |
| Candidate suppressed by incompatible IRT/References | `conflict`, target null, on both local candidates; other valid References support tokens remain `not_linking` or their own unresolved/duplicate outcome. |
| Candidate suppressed by cycle | `cycle_rejected`, target null, on the selected candidate. |
| Accepted unique local IRT edge | `accepted_direct_parent`, target is the unique parent source ID. |
| Accepted References-only fallback edge | `accepted_ancestor`, target is the unique local ancestor source ID. |
| Valid but nonselected/compatible References support token | `not_linking`, target null. |

For a blocked source, no token receives an accepted outcome. If a token has a more specific intrinsic failure (`malformed`, `duplicate_target`, `unresolved_external`, `self_link`, `multiple_in_reply_to`), retain that failure instead of replacing it with `not_linking`; only a would-be local linking candidate receives `conflict` or `cycle_rejected`. `EvidenceDecision.target_source_record_id` is non-null **only** for the two accepted outcomes, matching 3D1 checks. `AcceptedEdge` references exactly that accepted observation; no parsed token is automatically an edge. A compatible but nonselected References token is diagnostic support, not an `accepted_ancestor` edge in 3D1.

## 6. Fingerprints, ordering, and replay contract

The 3D1 `_digest` serialization is normative for source revision: start with UTF-8 bytes `3d1/source-revision/v1`; for each of `(source_record_id, message_id, in_reply_to, references)`, append decimal UTF-8 byte length, `:`, then UTF-8 bytes of `str(value)`; encode `None` as `-1:`. SHA-256 lowercase 64-hex is `source_revision`. The pure `calculate_source_revision` must match the existing repository byte-for-byte and reject a supplied mismatch. Its fields are the **stored** strings, not parsed/canonical tokens; subject and body are excluded. A header change therefore changes the revision even if canonical tokens happen to match. The future service is responsible for consistent snapshot/revalidation; 3D2 performs no persistence.

`calculate_reconstruction_key` uses the same length-prefixed encoding, SHA-256 lowercase hex, with UTF-8 domain `3d2/reconstruction/v1` and ordered fields: `(account_scope, ALGORITHM_VERSION as decimal string, source_count as decimal string, source_record_id, source_revision, ... for each source sorted by source_record_id)`. Include **no** subject, body, IMAP location, current Conversation ID, or other metadata. `ALGORITHM_VERSION=1` and `NORMALIZATION_VERSION=1` for this plan; a future semantic parser/graph change must increment the algorithm version, and a canonical-token change must increment normalization version before replay. Input permutation yields the same key, observations, decisions, edges, and components. Two snapshots with changed subject only have the same key/components but may have different `SubjectDiagnostic` values, by design. An empty account corpus hashes its account, version, and count zero.

Order all returned evidence by `(source_record_id, header_rank, ordinal)` with ranks `message_id=0`, `in_reply_to=1`, `references=2`; decisions follow matching evidence order. Subjects sort by source ID. Edges and components follow §5. All `TokenObservation` ordinals are zero-based within the *raw header span order*, including malformed/overflow sentinels. No output contains full raw headers or bodies; tokens are bounded ASCII identifiers and malformed text is represented by digest only. The same canonical input and version yields byte-identical output except that diagnostic subject is intentionally outside topology/replay identity.

## 7. Implementation sequence, tests, and acceptance

1. Create the empty domain package and immutable public contracts in `email_threading.py`; implement validators, length-prefixed SHA-256 and source/reconstruction key functions with only standard-library imports.
2. Implement the strict bounded header scanner, token grammar, malformed/overflow observations, and diagnostic subject normalizer.
3. Implement full-corpus Message-ID index, deterministic candidates, fixed-point conflict/SCC rejection, accepted links, decision mapping, and components.
4. Add synthetic pure tests in `test/test_email_threading.py`; run `python -m pytest test/test_email_threading.py` then `python -m pytest`; inspect the complete diff and exact file list. No real mailbox/database/network/keyring use.

Test matrix: exact local/domain grammar positive/negative, case-fold both sides, outer whitespace/brackets, comments/quotes/domain literals/folding/prose rejection; 998/999 token boundary; 32,768/32,769 UTF-8-byte header boundary; 100/101 References spans with no prefix linking; malformed mixed References preserving valid observations but no chain edge; missing versus present-empty headers; IRT with zero/one/multiple valid IDs and valid+malformed; References-only last uniquely local token across missing external intermediates; duplicate local targets without first-match; two replies with shared external ancestor; self-link; direct-parent and ancestor evidence/outcome/target mapping; competing IRT/References components with **all** outgoing rejected; simultaneous corpus-wide cycles and permutation invariance; incoming link to blocked source; same-subject independent messages; changed subject with intact technical link; all six prefix forms/repetition/whitespace/bracketed tags; late root in a second snapshot; duplicate/mixed-account/invalid-revision input rejection; source revision byte-for-byte compatibility with 3D1 and full reconstruction key deterministic/domain/version/count behavior; empty corpus; no persistence/framework/external imports. Use only synthetic text; never real credentials or commercial data.

Acceptance: every source appears in exactly one sorted component; every accepted edge has one accepted decision and a unique local target; ambiguous/malformed/conflicting/cyclic outgoing links never connect components; only a wholly valid References chain links; subject never affects edges or reconstruction key; outputs and fingerprints do not depend on input ordering; `source_revision` matches 3D1; tests pass without network or database. The plan is reviewed/approved before implementation.

## 8. Exact Scope Lock, dependencies, risks, and result

**IN SCOPE for later 3D2 implementation — exactly three paths:**

- `app/domain/__init__.py`
- `app/domain/email_threading.py`
- `test/test_email_threading.py`

**OUT OF SCOPE:** all models, migrations, repositories, persistence/application services, IMAP adapter/sync, scheduler, UI, AI, CRM, Calendar, drafts/moves, real account/network, other files, dependencies, and `main`.

**RESTRICTIONS:** pure immutable in-memory contracts; no SQLAlchemy or external-system imports; no persistent writes; no raw full References/body/secret in outputs; no guess based on subject/participants/folder; no automatic first-match or transitive ambiguous merge; no new dependency. If a fourth file or a change to 3D1/3C proves necessary, stop and request a separate decision/Scope Lock rather than broadening this plan.

Risks: false component merges from permissive token extraction or partial References, missed links from strict grammar, accidental topology change at bounds, nondeterministic cycle handling, fingerprint mismatch with 3D1, and oversized/untrusted data. The fail-closed scanner, corpus-wide simultaneous rejection, bounded outputs, exact key serialization, and synthetic permutation/boundary tests mitigate these. `source_revision` and the outcome enum are internal compatibility dependencies; no new package or external service is required.

**OUT-OF-SCOPE DISCOVERY:** Phase 3C high-water synchronization does not necessarily re-fetch a previously committed UID whose headers change in place. This does not alter the pure 3D2 contract; a later sync task may address it. No 3C change is authorized here.

**Open decisions:** None for the 3D2 pure engine under approved A–H.

**Result: READY FOR APPROVAL.** This plan and Scope Lock may be reviewed for a subsequent explicit `Implement Task` authorization. This planning task itself modifies only this document, commits it, and pushes it to `origin/codex-work`; it implements no code.
