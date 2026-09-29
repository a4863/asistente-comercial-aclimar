# Phase 6G — First commercial call rollout plan v2

**Date:** 2026-09-29

**Status:** READY FOR ONE-SHOT AUTHORIZATION — planning only; no live call authorized

## Authority and corrected boundary

The approved Global-processing decision permits planning for real commercial content. The protected localhost gate UI and manual analysis route are accepted, and the fixed-synthetic Phase 6F plumbing passed. The [approved retry-policy decision](phase-6g-first-commercial-retry-policy-decision.md) resolves the prior plan's STOP: **one operator-selected target email, one initial Analyze click, and up to two automatic provider attempts** for the same minimized input when the existing adapter classifies the first failure as transient. There is no manual retry, second target, force reanalysis or attempt-count proof. Neither that decision nor this plan authorizes the live call.

Sources reviewed: `docs/plans/phase-6g-first-commercial-call-plan-v2-task.md`, the approved Global/retry decisions and accepted 6G UI/6F records, the previous STOP plan, and the current status/manual routes, gate/ownership lifecycle, adapter retry loop, configuration, analysis service, selection/projection and persistence contracts. No operational configuration, keyring secret, live mailbox/database content or provider response was accessed.

## Exact preflight — all conditions must pass before gate enable

1. Confirm the deployed code is the accepted 6G UI commit `8099f5c31e1f590df81e391a75c6976b48ed73ec` or a later **accepted** descendant, with a clean tracked working tree. Confirm the separate one-shot authorization for this rollout has been granted. Do not treat Global consent or the successful synthetic smoke as that authorization.
2. Confirm exactly one controlled operational worker, no reload/multiple workers, and no competing assistant process. The worker must own the exclusive lock and complete startup cutover/recovery before readiness. A startup failure, marker/reservation conflict, unexpected pending commercial work or ownership uncertainty is STOP, not a reason to bypass recovery. Do not run a new smoke or other provider task concurrently.
3. On the existing localhost status page, verify `operational=ready`, AI `enabled`, provider `openai`, endpoint class `global`, approved model `gpt-6-sol`, credential presence `present`, and commercial authorization `blocked`. Verify the actual non-secret operational config/project identity corresponds to the approved Global path; inspect presence only, never the credential value. Endpoint class alone is not proof of account/project terms.
4. Confirm the page issues a signed-session-bound CSRF token, the protected controls are available from the same local browser origin, and no unexpected `in_progress`, `completed` or `retry_required` state applies to the proposed target. If the selector is empty/unavailable, or the target is not `ready`, STOP. Do not choose a different email to salvage a failed preflight without revisiting the one-shot selection.
5. Select exactly one existing eligible `ready` item from the bounded read-only selector using only the sender, subject and date needed to confirm it is an appropriate first case. Do not type/paste an internal ID, copy body text into a document, or select a second target. “One email” means one **target**; the existing disclosure policy may include up to six eligible prior messages from its reconstructed conversation within the shared 30,000-character excerpt budget. The operator should account for that context before authorizing the click.

This document does **not** assert that any of these deployment-specific checks has been performed. Any mismatch leaves the gate blocked and requires review.

## Exact one-shot operator sequence

1. Observe `commercial=blocked` in the ready, owned worker.
2. Click **Enable commercial analysis (Global)** once. Wait for the page to reload; confirm `commercial=authorized` and the disable control is visible. If enable fails or the displayed state is uncertain, STOP before Analyze and revoke if possible.
3. With the previously chosen single `ready` target, click **Analyze** exactly once. This invokes only the existing protected initial `POST /analysis/email`. Do not click Analyze again because of delay, a browser refresh, a lost response, or a bounded failure. Do not call `/analysis/email/retry`, use the visible Retry analysis button, use force mode, or choose another email.
4. Let the existing adapter settle. SDK-internal retries remain disabled; the adapter permits **at most one automatic retry** only for its approved transient classes while deadline, ownership and gate checks still pass. Thus one click may issue one or two provider attempts carrying the same minimized target/prior projection. Do not toggle the gate during ordinary in-flight work merely to suppress this approved retry.
5. Record only the bounded UI status. As soon as the result settles, click **Disable commercial analysis** and verify the reloaded status reports `commercial=blocked`. Perform this even after a failure or `completed_replay`. Do not start any further analysis while the gate is authorized.

The protected route and adapter retain session/CSRF/Host/Origin, live ownership, gate, credential and source-revalidation checks. The local service reserves a manual run, makes its provider call outside the DB transaction, then revalidates current source/conversation before persisting validated output. The remote projection remains minimized with ephemeral aliases and no attachments, internal IDs/digests or tools; `store=false` and local decoder/evidence validation remain unchanged. No email send/move/archive, CRM, Calendar or WhatsApp action follows automatically.

## Bounded outcomes and acceptance

**Primary success:** one operator Analyze action on the sole selected target returns `completed`; the expected local manual `AnalysisRun` reaches `completed` with evidence/provenance linked to the current source; no unauthorized external action is recorded or observed; and the final gate is confirmed `blocked`. Do **not** require proof of whether the adapter made one or two provider attempts. A `completed_replay` is **not** first-live-commercial success because it may involve zero new provider disclosure.

**STOP / not accepted:** `blocked`, `unavailable`, `disabled`, `credential_missing`, `credential_unavailable`, `invalid_security`, `invalid_request`, `invalid_target`, `no_analyzable_body`, `in_progress`, `retry_required`, `retry_not_available`, `failed_retryable`, `stale_retryable`, `completed_replay`, any bounded provider diagnostic surfaced locally, owner/readiness loss, unexpected data category/external mutation, or inability to disable and confirm `blocked`. Some provider failures are intentionally collapsed to `failed_retryable` by the service; a failure code does not prove no data was sent. On any such outcome: do not click Analyze or Retry again; disable the gate when safe, record the bounded state only, and STOP for separate review/new authorization.

## Post-call verification without commercial content

- Confirm the status page shows `commercial=blocked` and no further action was taken. The UI result must be `completed` or one of the bounded STOP outcomes; no raw exception/provider result is needed.
- With a separately authorized **read-only local** check of existing analysis/run/evidence records, verify exactly the expected single new manual run for this target/initial action, its final state, and evidence/provenance presence **only if completed**. Inspect counts, types, status and linkage—not source text, quotes, prompt, raw JSON, credential, internal digests or exception details. `completed_replay` should not create a new provider-backed run and remains not accepted for this first-call objective.
- Confirm no unexpected action-proposal execution/audit record and no other target run arose during the window. No scheduler/background execution is part of this phase. Any suspected mail/CRM/Calendar/WhatsApp mutation is a STOP for separately scoped verification; never perform an external mutation to test absence.
- Do not use dashboard usage/spend or local `AnalysisRun` to infer an exact provider-attempt count. Under approved Option A, that count is intentionally **not** an acceptance criterion.

## Rollback and interruption

Before Analyze, leave or return the gate to `blocked` on any failed preflight or status mismatch. After dispatch, an already-sent request cannot be recalled. If a serious concern arises while it is in flight, disabling the gate prevents a later automatic attempt once the adapter rechecks it, but may leave the operation in a bounded failure state; do not kill the worker merely to stop a dispatched request. Let already-sent work settle safely. After settlement, use the protected disable control and verify `blocked`. If that UI control is unavailable, stop the worker **after** in-flight work settles; a fresh process starts with the gate OFF. Record only bounded outcomes and require a new decision before any further click.

## Code-change decision and authorization boundary

**No code change is required** for this rollout contract. The accepted gate UI, protected manual initial POST, current `max_retries == 1` adapter policy, source revalidation and local persistence already implement its mechanics. No retry setting, provider instrumentation, scheduler, new route, migration or dependency is planned. This planning task ran no tests or live calls; implementation tests and Phase 6F synthetic success are prior accepted evidence, not a substitute for the deployment-specific preflight.

The next step is **one separate, explicit authorization** to perform this controlled rollout after the actual preflight and selection conditions are met. That authorization covers one UI-selected eligible target and one initial Analyze click, with zero or one automatic transient retry allowed by the existing adapter. It does not cover a manual retry, second target, second click, new smoke or any external action. Until then, keep the commercial gate OFF.

## Result

**READY FOR ONE-SHOT AUTHORIZATION.** The prior exact-one-provider-attempt contradiction is resolved by the approved Option A. The plan remains documentation only; no commercial call or gate activation was performed.
