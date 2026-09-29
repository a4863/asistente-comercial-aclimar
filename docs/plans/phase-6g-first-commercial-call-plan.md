# Phase 6G — First commercial call rollout plan

**Date:** 2026-09-29

**Status:** STOP — one-request guarantee and verification are not established

## Authority and scope

This document plans, but does not execute, a first controlled analysis of one operator-selected existing email. The approved Global-processing decision, accepted protected localhost gate UI, accepted manual initial/retry route, and successful fixed-synthetic 6F smoke are prerequisites; none authorizes the real commercial call. No operational config, database rows, keyring material, mailbox, provider response or commercial content was inspected for this plan. No code, test, migration, dependency or credential change is made.

Sources: `docs/plans/phase-6g-first-commercial-call-plan-task.md`, `docs/plans/phase-6g-commercial-processing-decision.md`, `docs/plans/phase-6g-protected-gate-ui-acceptance.md`, `docs/plans/phase-6g-commercial-activation-analysis.md`, `docs/plans/phase-6f-thirteenth-live-smoke-result.md`, approved Phase 5/6 decisions, and the current `app/web/routes.py`, `app/web/templates/status.html`, `app/main.py`, `app/security/activation.py`, `app/integrations/openai_analysis.py`, `app/config.py`, `app/services/email_analysis.py`, `app/persistence/models.py` and related repository contracts.

## Blocking contradiction

The task requires **exactly one live provider disclosure** and post-call verification of **no second provider attempt**. One UI `Analyze` click is not equivalent to one provider attempt:

- `app/config.py` requires `AISettings.max_retries == 1` when loading operational settings; this is not an operator-adjustable zero-retry TOML value.
- `OpenAIAnalysis._execute()` calls `client.responses.create()` within `range(settings.max_retries + 1)`. Timeout, connection, rate-limit and 5xx classes can cause a second automatic attempt if the local deadline permits. The SDK's own retries are disabled, but the adapter's retry remains.
- The adapter rechecks live ownership and gate before retry, but a gate left ON while awaiting the first result permits that retry. Disabling only after the analysis settles is too late to guarantee no retry; disabling during an in-flight call is not a deterministic one-shot control and may convert an otherwise valid transient recovery into failure.
- `AnalysisRun` and the bounded web result contain run status, not provider-attempt count. One `completed` run could have followed one or two `responses.create()` calls. Dashboard usage/spend is not an exact local per-run attempt ledger and may lag. Thus the required post-call proof cannot be obtained from the accepted surfaces.

This is not merely a test gap: the current policy explicitly permits one automatic transient retry, whereas this rollout task prohibits a second provider attempt. No approved no-retry commercial mode or safe attempt-count verification exists. Do not execute the first commercial call under this contradictory contract.

## Conditional operator preflight — only after blocker resolution and new authorization

1. Confirm the deployed branch/build is the accepted 6G UI commit `8099f5c31e1f590df81e391a75c6976b48ed73ec` or a later separately accepted descendant, with a clean tracked working tree. Confirm the Global-processing decision applies to the actual project/credential; no EU/ZDR claim follows. Do not infer commercial authorization from the synthetic smoke.
2. Confirm one controlled operational worker only, `run()` without reload or multiple workers, exclusive lock ownership, successful startup cutover/recovery, and no competing or pending commercial operation. Fail closed if the cutover marker is missing with `reserved` runs or startup is not ready. Do not sweep/repair state by heuristic. The current bounded status does not itself enumerate all `reserved` rows, so an exact all-run verification would need a separately approved read-only operational check if required beyond startup and selected-item status.
3. Inspect only non-secret operational settings/status: `operational=ready`, AI enabled, provider `openai`, endpoint class `global`, approved `gpt-6-sol` model, credential **presence** `present`, and commercial gate `blocked`. Do not display or retrieve the key, prompt, raw provider payload or email body. Confirm signed local session and CSRF control are usable. If any state differs, do not enable the gate.
4. From the bounded read-only selector, choose exactly one existing eligible item with `ready` state after reviewing only sender, subject and date necessary to identify an appropriate first case. Do not type/paste an internal source ID, select a second email, or copy content into this plan. `completed`, `in_progress` and `retry_required` are not a fresh first-call target.

No actual deployment preflight was performed while writing this document.

## Conditional one-shot UI sequence

Only after a revised, approved attempt policy, successful preflight and a **separate explicit one-shot authorization**:

1. Confirm status `commercial=blocked` in the same ready, owned worker.
2. Click **Enable commercial analysis (Global)** once via the protected localhost control and verify the reloaded status is `authorized`. If the control is unavailable or status does not match, STOP before Analyze.
3. Immediately click **Analyze** exactly once for the single selected `ready` email. This uses the existing `POST /analysis/email` with session, CSRF, same-origin Origin and valid Host; no direct API call, retry endpoint, force mode, second tab or second email. Do not click again on delay/uncertainty. The service reserves a normal manual run, calls the adapter outside the DB transaction, then revalidates source/conversation and persists validated evidence locally. The remote projection remains target plus at most six priors, capped body excerpts, ephemeral aliases, no attachments/internal IDs/tools, and `store=false`.
4. Await the bounded result. **Do not click Retry analysis** during this rollout, even if the selector later says `retry_required`; that would need another explicit authorization. Do not invoke the smoke CLI or any background/scheduler path.
5. Immediately click **Disable commercial analysis**, then verify the status is `blocked`. Do this after success or any bounded failure. Disabling prevents new attempts/retries but does not retract already transmitted data. No email move/send/archive, CRM/Calendar/WhatsApp mutation or automatic external action follows.

## Bounded outcomes and success/failure criteria

The only candidate success result is `completed`, paired with exactly one expected local manual `AnalysisRun(status=completed)` for the selected target/current input, locally persisted source evidence/provenance, no unauthorized external action record, and final gate `blocked`. **`completed_replay` is not success** for validating a first commercial transmission: it makes no new provider call. Even `completed` is **not sufficient under the current contract**, because it cannot prove that only one provider attempt occurred.

Treat `blocked`, `unavailable`, `disabled`, `credential_missing`, `credential_unavailable`, `invalid_security`, `invalid_request`, `invalid_target`, `no_analyzable_body`, `in_progress`, `retry_required`, `retry_not_available`, `failed_retryable`, `stale_retryable`, `completed_replay`, any bounded provider diagnostic, ownership/readiness loss, unexpected data category/external mutation, or inability to verify final `blocked` as STOP/not accepted. One result may conceal whether the provider already received data; do not infer zero transmission from failure. Do not retry, select another item or change mode automatically. Record only the bounded code, run state and non-sensitive provenance checks; never print source body, raw JSON, request/response, credential, prompt, secret-bearing logs or provider error text.

The web result intentionally exposes only a fixed status code. Post-call local verification, when separately authorized, must use existing read-only run/evidence/action-record contracts and report counts/states rather than content. No new commercial action is needed to verify state. Absence of local unauthorized action records does not replace checking the relevant external system if a mutation anomaly is suspected; any such investigation needs its own scope.

## Rollback

On a pre-dispatch failure, keep or return the gate to `blocked` and STOP. If a request is already in flight, disabling can prevent later attempts once the adapter reaches its recheck, but cannot cancel or recall a request already dispatched. Allow in-flight work to settle and record only a bounded outcome. If the protected disable control cannot be used, stop the worker only after work settles safely; a fresh worker starts OFF. Do not treat a process kill, browser refresh, timeout or dashboard counter as proof that provider disclosure did not occur. Any unverified gate state, extra attempt, stale reservation, unexpected external mutation or privacy concern requires separate review before another call.

## Decision required to unblock

Choose and separately approve **one** of these mutually different contracts before a revised rollout plan:

| Option | Consequence |
| --- | --- |
| Preserve the current adapter's one automatic transient retry | Authorize one operator `Analyze` action for one email but allow **up to two provider attempts** with the same minimized input. Revise the task's “no second provider attempt” and verification criteria explicitly; one completed run will not prove the exact attempt count without additional instrumentation. |
| Require exactly one provider attempt | Approve a separately scoped, offline-tested zero-retry commercial execution mode or equivalent fail-closed mechanism, plus a bounded way to verify the per-run attempt count if exact post-call proof remains mandatory. This is new implementation/planning work; the current TOML loader cannot select zero retries. |

Do not silently reinterpret “one Analyze” as “one provider request,” change the operational TOML to an unsupported value, infer exact attempts from `AnalysisRun`, or call OpenAI to investigate. Any subsequent code change needs its own analysis/plan/Scope Lock/approval. Once this decision is resolved, revalidate the preflight and obtain a fresh one-shot authorization identifying the single UI-selected eligible email before any commercial transmission.

## Result

**STOP.** The accepted stack cannot guarantee or verify the task's exact one-provider-attempt requirement. The gate remains OFF; no real commercial call is authorized or performed.
