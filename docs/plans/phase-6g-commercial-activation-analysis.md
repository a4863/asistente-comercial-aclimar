# Phase 6G — Commercial activation analysis

**Date:** 2026-09-29

**Mode:** analysis only; no commercial transmission or operational change
**Verdict:** READY FOR DECISION

## 1. Objective, context and authority

Define the decision boundary for one controlled, real commercial-email analysis. This is not approval to enable the gate, change the operational configuration, select an email, or call OpenAI. The approved Phase 6 plan and decisions D1–D18 require a separate processing-mode decision, an exclusive operational owner, process-local revocable authorization, and a protected manual trigger. Phase 6F's thirteenth fixed-synthetic smoke passed, but its acceptance explicitly excludes commercial use and EU-residency conclusions.

Consulted: `docs/plans/phase-6g-commercial-activation-analysis-task.md`, `docs/plans/implementation-phase-6-plan.md`, `docs/plans/phase-6-activation-decisions.md`, `docs/plans/phase-5-ai-provider-decisions.md`, `docs/plans/remote-ai-data-policy.md`, `docs/security.md`, the accepted 6B1/6B2/6E1/6E2/6E3 and final 6F records, `docs/plans/phase-6f-api-dashboard-evidence.md`, and the current activation, startup, configuration, credential, session, web, analysis-domain/service/repository, projection/adapter code and relevant offline tests. No operational TOML, keyring secret, commercial SQLite rows or live provider response was read.

## 2. Current readiness map

| Boundary | Repository evidence | Readiness |
| --- | --- | --- |
| Provider plumbing | Fixed synthetic 6F smoke passed; strict Responses output and local decoder were exercised. | Technically demonstrated for synthetic input only. |
| Commercial gate | `CommercialActivationGate` is in-memory, thread-safe, initially OFF; each `create_app()` gets a fresh gate. Adapter requires owner and gate before credential use and before each attempt/retry. | Enforcement exists; operator enable/revoke path does not. |
| Protected manual analysis | Bounded read-only email selector; distinct initial/retry POSTs; local Host, Origin, signed session and CSRF checks; live owner/readiness and gate preflight. | Implemented and offline-tested; no commercial call authorized. |
| Ownership/recovery | Operational lifespan acquires exclusive lock, runs cutover/recovery transaction, then marks ready; controlled `run()` uses one worker and no reload. | Implemented; must be verified on the actual deployment before first use. |
| Credential/config/status | Closed operational TOML schema, keyring reference, presence-only status, endpoint-class/model/gate/readiness display. | Mechanism exists; actual deployment values and presence must be checked without revealing secrets. |
| Processing mode | Prior actual-project evidence says **Global / Standard Retention**. No verified EU eligibility for the exact project/key. | **Unresolved external authorization gate.** |

Acceptance files report offline test results, not a current 6G deployment check. The web status currently displays `authorized`/`blocked` but offers no activation control. A search of production code found no call to `commercial_gate.enable()` or `.disable()`; their callers are tests. Therefore merely starting the app, setting `ai.enabled=true`, supplying a key or passing smoke cannot turn commercial analysis on. Direct debugger/import/console mutation is not an approved operator procedure.

## 3. Mutually exclusive processing-mode gate

**Path A — verified EU.** Before planning activation, obtain current control-plane or provider confirmation for the *actual API organization and project*, bind the configured credential to that project, record the precise EU processing/residency setting and applicable retention setting/terms, and verify the required endpoint/base URL is the one configured for that same project. Review the evidence against the already approved EU requirement; do not infer eligibility from an EU-looking URL, user location, model, key presence or synthetic smoke. A project/credential mismatch, absent setting, Global/Standard-only evidence, or unverified retention leaves this path blocked. The existing dashboard record is evidence against assuming the present project is EU-configured, not proof that EU can never be configured later.

**Path B — Global.** Requires a **new, explicit user statement** accepting processing of real commercial email content by the actual OpenAI project in Global mode, with the applicable retention arrangement, before any gate enablement or commercial call. “Proceed with 6G,” approval of this analysis, previous synthetic-smoke approvals and technical configuration are not that statement. Current Global/Standard evidence is not itself consent. Do not silently switch endpoints or projects to satisfy either path; that requires its own reviewed configuration/credential procedure.

No legal/compliance conclusion follows automatically from either technical path. Retain the accepted disclosure policy and any separately required organizational approval.

## 4. Gate lifecycle and activation-mechanism decision

The existing gate and adapter are sufficient for **runtime enforcement**, not for **operator activation**. Gate state is neither persisted nor inherited at restart. Disabling it prevents later attempts/retries, but cannot recall data already sent; an in-flight call may complete. The manual route also checks the gate before reservation, credential-presence lookup and provider construction. There is no scheduler/background commercial trigger. The status route is read-only. The synthetic `smoke()` has a separate fixed input and never enables the commercial gate.

| Candidate | Explicit action, visibility and revocation | Security/implementation consequence | Assessment |
| --- | --- | --- | --- |
| Existing process-local Python API only | `enable()`/`disable()` exist, status is visible, but no supported operator command reaches the live worker. | Ad-hoc debugger/import/test hook is unaudited and may target the wrong process; an external process owns a different gate. | Not an acceptable no-code operational procedure. |
| Protected localhost UI control | Two explicit enable/disable actions in the live worker; existing status can show state. | New protected POST(s) must validate session, CSRF, Origin, Host and live ownership; bounded feedback; no content-bearing parameters; OFF at restart. Must also bind enablement to the separately approved processing mode in the operational procedure. | Viable, smallest reuse of existing web/session boundary. |
| Local CLI command | Explicit operator command and bounded result; status remains in web. | A separate CLI cannot mutate the web worker's in-memory gate. A safe live-worker IPC/control channel would be new attack surface and must authenticate/authorize, prove ownership, and avoid persistence. | Viable only with a larger separately approved IPC design; not a no-code option. |
| Startup flag or environment variable | Easy to set, but no reliable live revocation and can silently re-enable on restart. | Conflicts with OFF-on-every-start, explicit per-process activation and no persistent authorization. | Reject. |

There are two conceivable supported UX designs (protected worker-local UI versus a purpose-built authenticated CLI-to-worker channel), with different security and scope costs. Do **not** choose silently. The operator must decide the mechanism; a UI control is the smaller candidate, not an implicit approval. No activation mechanism may be driven by email text, model output, provider content, or a commercial-analysis POST itself.

**Code needed:** yes, for a supported operator enable/revoke path; no change is needed to the already accepted gate primitive, adapter, manual-analysis service or persistence solely to toggle authorization. A no-code path would require an already supported control of the live worker; none was found. Do not implement a workaround through startup flags, test APIs or separate-process state.

## 5. Data disclosure and first-call protocol (conditional, not authorization)

The existing selector shows at most 20 eligible local email references with bounded sender/subject/date/state, not bodies or digests. For one chosen source, `select_analysis_input()` requires an active, non-redacted email in a resolved, current conversation; it selects the target plus at most six prior messages, with a shared 30,000-character body-excerpt budget. The remote projection contains only ephemeral `m0…m6` aliases, role, body excerpt, and available sender, recipients, subject and date. Those contact fields can identify people/companies; aliases are **not** anonymization. No attachments, full mailbox, CRM/Calendar/WhatsApp data, internal source IDs, conversation keys, run IDs, local digests or source-body hashes are projected. The adapter sends no tools/functions and sets `store=false`; this request flag does not prove residency or zero retention. Sensitive-pattern checks may stop transmission, and embedded source instructions remain untrusted. Decoder/evidence/provenance checks remain local.

After one processing path and activation mechanism have been separately approved and implemented/tested, the controlled first use should be:

1. Confirm the approved build/branch is clean, expected offline security tests pass, and the operator has reviewed the selected processing-mode evidence/acceptance for the exact account/project. Confirm actual non-secret config (model, endpoint class, database identity, account scope), credential **presence only**, and no secret in TOML/logs. Do not infer authorization from a passed synthetic smoke.
2. Stop any old process; start exactly one controlled operational worker with no reload/multiple workers. Confirm exclusive lock and successful cutover/recovery, then status `operational=ready`, expected provider/model/endpoint/credential state and `commercial=blocked`. If cutover marker is absent with reserved runs, startup must fail closed; do not repair heuristically.
3. Operator explicitly enables the gate through the separately approved control. Confirm the same worker reports `commercial=authorized`. Select **one** eligible existing email from the bounded local list after reviewing its safe metadata; do not enter an arbitrary source ID or choose an email in this analysis.
4. Use the existing protected `/analysis/email` POST exactly once for a `ready` item. Use `/analysis/email/retry` only after a separately visible `retry_required` state and a fresh explicit operator click; no force mode. CSRF/session/Origin/Host and live ownership checks must remain effective. `completed_replay` and `in_progress` cause no new provider disclosure. Reservation, source revalidation, candidate/evidence validation and local completion/failure audit use existing service/repository contracts. No mail move/send, CRM or Calendar write follows.
5. Record only the bounded result and normal local `AnalysisRun`/evidence state already authorized. Technical acceptance is one `completed` result with expected local provenance and no external action, or a `completed_replay` result **only if** the objective is explicitly limited to replay behavior; replay cannot validate the first live commercial disclosure. A bounded failure, `stale_retryable`, `in_progress`, ownership loss or security failure is not success. Do not auto-retry or widen the corpus.
6. Immediately disable the gate using the same approved control and verify `commercial=blocked`; if safe revocation cannot be confirmed, stop the worker after any in-flight request has settled and confirm restart OFF. Disabling cannot retract an already-sent request or guarantee cancellation of a call underway.

## 6. Rollback and STOP conditions

Before transmission, stop on missing EU evidence or absent explicit Global acceptance; wrong project/key/endpoint/retention; unreviewed build; absent/failed owner or recovery; wrong or unavailable credential; status mismatch; no eligible target; invalid session/CSRF/Origin; gate that cannot be revoked; or any unexpected data category in the projected request. Leave gate OFF. After dispatch, disable the gate to prevent new attempts/retries, let an already-sent call settle safely, inspect only bounded local status/audit, and require separate review before any retry. No claim that revocation deletes provider-held data. Never switch to Global as a fallback for EU failure. Do not weaken adapter, decoder, minimization, retry or evidence rules to make a first call pass.

## 7. Candidate future Scope Lock, tests and decisions

No implementation Scope Lock is approved by this analysis. If the operator chooses the protected UI, a minimal **candidate** lock is `app/web/routes.py`, `app/web/templates/status.html`, `test/test_status.py`, `test/test_security.py` (and only if demonstrated necessary, a separately approved `test/test_startup.py`). The current gate object in `app/main.py` may already suffice; adding it without need would enlarge scope. The alternate CLI/IPC path needs a fresh design and exact lock rather than borrowing this one. Both options require offline tests for OFF on startup/restart, explicit enable/disable, live-worker ownership, session/CSRF/Origin/Host failures, blocked-before-reservation/credential/provider, disable-before-retry, bounded status, and synthetic/commercial separation. No live call belongs in normal pytest. This analysis ran no tests or migrations because it changes no code.

Required decisions before planning/activation:

1. **Processing mode:** provide verified EU project/credential/endpoint/retention evidence, **or** issue a fresh explicit acceptance of Global processing for real commercial email. The current evidence supports neither EU verification nor Global consent.
2. **Activation UX:** select protected localhost UI control or explicitly request a larger CLI-to-worker control design. Do not use startup/env flags or ad-hoc Python mutation.
3. **Controlled rollout authorization:** after implementation/review and operational preflight, separately authorize the one selected commercial-email action; this analysis does not do so.

Out of scope: code, tests, migrations, dependencies, provider/config/credential changes, real email selection, live OpenAI calls, commercial data transmission, scheduler/background work, and external-system mutations.

## Result

**READY FOR DECISION.** Runtime enforcement and the manual workflow exist, but the external processing-mode gate is unresolved and there is no supported operator enable/revoke entry point. Multiple activation UX choices remain. No commercial activation or transmission is authorized by this document.
