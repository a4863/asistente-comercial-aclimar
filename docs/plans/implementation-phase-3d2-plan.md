# Phase 3D2 — canonical threading engine: Analyze/Plan result

**Status:** STOPPED FOR DECISION
**Date:** 2026-09-23
**Task:** `docs/plans/implementation-phase-3d2-plan-task.md`
**Baseline:** `0334ddf` on `codex-work` after fast-forward from `origin/codex-work`

## 1. Objective, context, and interpretation

The requested deliverable is an implementation-ready plan for a *pure*, account-scoped parser and deterministic email-thread graph engine, not an implementation. It must settle the exact accepted Message-ID grammar, bounded parsing, evidence-to-decision mapping, conflict/cycle policy, connected components, immutable input/output contracts, and replay fingerprint. Phase 3D1 already supplies persistent evidence/decision/history/lineage primitives; Phase 3D2 must not call them or mutate any state.

The approved rules determine the safety direction but do not uniquely determine several graph-changing behaviors. The task's explicit STOP rule and `Analyze Task` Ambiguity Rule apply. This document therefore records the confirmed contract, materially different alternatives, and the decisions needed before an exact implementation plan can be approved. It deliberately does **not** select a parser grammar or graph algorithm and is not authorization to implement.

## 2. Documentation and current state

Consulted: `AGENTS.md`; `skills/analyze-task/SKILL.md`; this task; `docs/plans/implementation-phase-3d-analysis.md`, `implementation-phase-3d-decisions.md`, `implementation-phase-3d-physical-decisions.md`, `implementation-phase-3d1-plan.md`; `docs/functional-spec.md` §5.4; `docs/data-model.md` §§5, 12; `docs/architecture.md` §§3–4, 10–11; `docs/testing-strategy.md` §§2–4, 8–9; accepted 3D1 `app/persistence/models.py`, `app/persistence/repositories.py`, migration `0005`, and their model/migration/repository tests. No required document is missing.

The 3D1 schema has `ThreadEvidence` (only `valid`/`malformed` parse status, bounded canonical token, digest, ordinal, normalization version, source revision), `ThreadEvidenceDecision` (one outcome per evidence/reconstruction key), and explicit accepted-edge versus unresolved outcome domains. `ThreadPersistenceRepository.append_evidence` computes the source-header revision with domain `3d1/source-revision/v1` over `(source_record_id, normalized_message_id, in_reply_to, references_header)` using its length-prefixed UTF-8 SHA-256 encoding; it checks the stored headers still match that revision. A valid token digest is SHA-256 of the canonical token bytes. These are real 3D2→3D1 compatibility constraints, not a parser or graph implementation.

There is no `app/domain` package or pure threading module today. Phase 3C's `normalized_message_id` is merely trimmed at ingestion; it is not the Phase 3D canonical ID. One logical email/source is the graph node even if it has multiple IMAP locations. No production data, live mailbox, database, keyring, or network was examined or changed for this analysis.

## 3. Confirmed functional and safety constraints

- Operate over a complete, consistent **single-account** local corpus snapshot; no IMAP, database, SQLAlchemy, repository, scheduler, AI, CRM, Calendar, or UI dependency in the pure engine.
- Compare ID tokens case-insensitively; remove surrounding whitespace and angle brackets for comparison. The eventual canonical token must fit 998 characters. Malformed tokens are invalid evidence, never graph edges. Preserve `References` source order. More than one valid `In-Reply-To` ID cannot create an automatic *direct-parent* edge.
- Index each canonical `Message-ID` to **all** source IDs with that token. A reference to duplicate local targets is ambiguous, never silently resolved by date, subject, participant, folder, or first occurrence. No self-link, directed cycle, or transitive bridge through ambiguous evidence.
- A unique valid local `In-Reply-To` is strongest direct-parent evidence. `References` may corroborate and support ancestors, but incompatible local components must not be merged automatically. Subject is secondary diagnostic evidence only; it never creates an edge or vetoes an otherwise valid technical link merely because the subject changed.
- Each source appears exactly once in the component output; every unlinked, malformed, or unresolved source forms a singleton. Two replies sharing only a missing external ancestor stay separate. A later-arriving root may change the result on a new full-corpus pass. Components must be deterministic and independent of input iteration order.
- Parsed evidence, its decision/outcome, accepted directed edge, and undirected conversation component are distinct output concepts. Raw full `References`, body, credentials, or instruction-like content must not be copied into history/audit. Header and subject text are inert data.

## 4. Material decisions required — STOP

The alternatives below all fit the broad approved rules but produce different accepted edges or evidence. Neither the functional specification nor D1–D13 selects one. An exact plan cannot safely choose on its own.

| Decision | Reasonable alternatives | Material consequence |
| --- | --- | --- |
| **A. Accepted ID grammar and surrounding syntax** | Accept only a conservative single ASCII `local@domain` token with optional outer angle brackets and whitespace; **or** also accept quoted/local-literal or comment/folding forms after structured parsing. Define whether stray prose or nested/unbalanced brackets invalidates the whole header or can be skipped. | The same real header may be a valid edge under one grammar and an invalid singleton under another. Arbitrary scanning can incorrectly extract an ID embedded in unrelated text. D1 says remove surrounding whitespace/brackets and reject malformed IDs, but not which forms count as malformed. |
| **B. Bounds and overflow policy** | Choose exact maximum bytes/characters per header, 998-character canonical-token handling, maximum number of `References` elements, and whether overflow invalidates the complete field or retains a bounded prefix while marking the rest invalid. | Retaining a prefix may create links that whole-field rejection would not; silent truncation loses evidence and order. The 3D1 `parse_status` has no separate `truncated` value, so the representation must also be specified. |
| **C. Mixed valid/malformed `References`** | Preserve independently valid tokens and permit their local ancestor evidence despite malformed segments; **or** quarantine the whole chain from edge creation while retaining per-token observations. Specify whether a gap/stray token resets adjacency. | One policy can merge local components through a partial chain while the other leaves them separate. Both preserve source order and reject malformed-token edges, as D1 requires. |
| **D. `References`-only ancestry** | Accept an edge from a message to each uniquely resolved local ancestor; accept only the nearest unambiguous local predecessor; or require an unbroken validated chain before any ancestor edge. Also decide whether a local ancestor across missing external intermediate IDs may connect components. | These yield different connectivity for missing intermediates and late roots. D2 permits ancestor support but does not define its linking strength or gap rule. Shared *missing* ancestors alone are already prohibited by D3. |
| **E. Multiple/invalid `In-Reply-To` with `References`** | Suppress only the direct-parent edge and still allow independent unambiguous `References` ancestry; **or** isolate the message from all automatic links until the contradictory parent information is resolved. Define whether zero valid IDs with malformed text differs from a missing header. | The first can bridge components despite an ambiguous parent header; the second cannot. D1 prohibits the direct-parent edge for multiple IDs, not every possible References edge. |
| **F. Conflict and cycle resolution unit** | On an incompatible unique `In-Reply-To` and `References` target, reject every candidate edge from that source; **or** retain only the compatible subset (for example the unique direct-parent edge) while rejecting the conflicting ancestors. For a cycle, reject only the completing edge or all edges of the affected source/component. Define an order-independent criterion for “incompatible components.” | The retained subset can still merge a component; whole-source rejection leaves a singleton. Input-order-dependent cycle rejection would violate D6 determinism. D2 prohibits an incompatible merge, but does not select the resolution granularity. |
| **G. Secondary subject normalization** | Fix the exact prefix list (at minimum `Re:`, `Fw:`, `Fwd:`), which localized variants are included, whether matching is case-insensitive, how many repeated prefixes are removed, whitespace folding, and whether bracketed tags remain untouched. | This must not alter connectivity, but it changes diagnostic output and possibly reconstruction fingerprints. The task explicitly requires an exact rule; no approved list exists. |
| **H. Pure snapshot/output and fingerprint contract** | Decide whether the input contains raw stored headers only or pre-parsed tokens; exact immutable record/field types; how missing and malformed observations are represented with 3D1's two statuses; outcome mapping for every rejected/ambiguous case; whether `subject` affects the reconstruction key although it cannot affect edges; and exact algorithm-version/corpus ordering serialization. | Without these choices 3D2 output may be impossible to persist idempotently in 3D1, and equivalent input permutations might produce different keys. The 3D1 source-revision formula is fixed, but the full reconstruction key is only described at a higher level. |

The main approval gate is **A–F** because these change conversation components. **G–H** must also be specified before this task can honestly claim an *exact* implementation-ready plan. The approved D1 rule settles case-insensitive comparison of the **entire** canonical token; whether a particular quoted/commented form is valid remains within A. D3 already settles that subject similarity, a forwarded prefix, or a shared missing external ancestor cannot independently merge messages; no additional decision is needed on those prohibitions.

## 5. Safe output boundary once decisions are approved

The later pure engine may consume immutable per-email records containing account scope, one logical source ID, the three stored header values, optional subject, and source revision; its output must include bounded parsed observations, per-observation outcomes with optional local target only for accepted edges, accepted directed links, sorted components including singletons, and one full-corpus reconstruction fingerprint. It must reject mixed-account or duplicate source inputs rather than guessing. Exact types, signatures, grammar, outcome assignment, ordering, and fingerprint serialization remain **unapproved** until A–H are resolved; the above is a boundary, not an implementation API.

The engine must not return persistent conversation IDs or stable keys: those are assigned by the later transaction/reconstruction service under D5/D10. It must not infer lineage or mutate the 3D1 current projection. A deterministic component is a set of logical source IDs, not an IMAP-folder/UID group.

## 6. Test definition and tentative Scope Lock

After decisions, synthetic pure unit tests must cover: accepted/malformed/empty/folded/commented/quoted/bracketed ID forms; exact 998 and over-limit boundaries; ordered/mixed/truncated References; `In-Reply-To` with 0/1/>1 valid IDs; duplicate Message-ID targets; self-link and directed cycles; conflicting In-Reply-To versus References and two-component bridges; missing intermediates and shared external ancestors; late root in a new full-corpus snapshot; independent same-subject messages; changed subject with intact technical links; forwarded/localized/repeated prefixes and bracketed tags; permutation invariance; singleton coverage; account isolation; stable source/reconstruction fingerprints; exact outcome compatibility with 3D1; and absence of repository/network imports or real credentials. No tests or databases are run during this planning task.

**Tentative IN SCOPE for a later approved implementation:** `app/domain/__init__.py`, `app/domain/email_threading.py`, and `test/test_email_threading.py` only. These are proposed file paths because no domain package exists yet; they do not authorize creation now.

**OUT OF SCOPE:** models, migrations, repositories, persistence writes, full-corpus application service, IMAP adapter/sync, scheduler, UI, CRM, Calendar, AI, drafts, moves, real mailbox/network, and `main`.

**RESTRICTIONS:** pure deterministic in-memory behavior; no SQLAlchemy/IMAP/network/keyring imports; no source mutation or external action; no subject-only edge; no silent first-match or ambiguous bridge; no new dependency. This Scope Lock is **not implementation-approved** while A–H remain open.

For **this** requested Analyze/Plan task, the only authorized file creation is `docs/plans/implementation-phase-3d2-plan.md`, followed by the explicitly requested commit/push. No code, test, data, dependency, database, or other documentation change is authorized.

## 7. Risks, out-of-scope discoveries, and result

Primary risks are a false commercial thread merge from permissive partial parsing, nondeterministic cycle resolution, silently dropped evidence at limits, mismatched 3D1 fingerprints, and untrusted header/subject text being treated as instructions or copied into logs. The eventual tests above must exercise these with synthetic inert data.

**OUT-OF-SCOPE DISCOVERY:** Phase 3C does not necessarily re-fetch a previously committed UID when its stored header changes in place. That synchronization concern remains outside the pure 3D2 engine; a new local snapshot can still be recomputed whenever stored headers do change. No 3C change is authorized here.

**Result: STOPPED FOR DECISION.** Approve exact answers to A–H (especially A–F) before producing an implementation-ready 3D2 plan or invoking `Implement Task`. This document records blockers without selecting among materially different threading semantics.
