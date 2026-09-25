# Runtime configuration loading — analysis

**Status:** READY FOR PLAN (proposed contract; no implementation authorized)

**Date:** 2026-09-25
**Decision confirmed by user:** fixed local TOML path `%LOCALAPPDATA%\ACLIMAR\Asistente Comercial\config.toml`.

## 1. Objective and context

Make the controlled application launcher, credential CLI and one-shot synthetic smoke CLI consume the same approved, non-secret local TOML settings. Phase 6F stopped before a live call because the smoke CLI calls `load_settings()` without a path; that currently returns defaults with `ai.enabled=False`. This analysis makes no code, test, configuration, database, credential or provider change.

## 2. Interpretation and documentation consulted

This is a runtime-discovery correction, not a new configuration format, provider, activation mechanism or live-smoke authorization. Consulted `AGENTS.md`, `docs/plans/runtime-config-loading-analysis-task.md`, `docs/plans/phase-6f-blocker.md`, `docs/plans/phase-6f-live-smoke-task.md`, `docs/plans/implementation-phase-6-plan.md`, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, `app/config.py`, `app/main.py`, both CLI modules, the adapter and their offline tests. No canonical config filename was found elsewhere in the inspected project documentation/code. The functional specification and data model do not define this technical path.

## 3. Current state

- `load_settings(path=None)` parses an explicitly supplied TOML path, but `None` means an empty dictionary and safe defaults. `AISettings.enabled=False`, `base_url=None`. It does not discover a local file.
- `run(settings=None)`, `credential_cli.main()` and `ai_smoke_cli.main()` all call `load_settings()` with no path. `create_app(settings=None)` and the module-level `app = create_app()` do likewise. The operational launcher and CLIs therefore do not share an operator-editable runtime file.
- `load_settings(path)` already rejects malformed TOML, non-loopback server host, invalid AI settings and unknown AI keys. It does **not** reject every unknown top-level table or every unknown key in non-AI tables; a secret-bearing unused table could currently be silently accepted. That is a security gap in the *future runtime TOML contract*, not a reason to read or edit any real file now.
- The adapter's authoritative endpoint allowlist is `https://api.openai.com/v1` and `https://eu.api.openai.com/v1`; the configuration parser requires HTTPS and a limited URL shape, but the adapter performs the final allowlist check before credential retrieval. Technical `ai.enabled` does not enable the independent commercial gate.
- Three installed console scripts exist: `asistente-aclimar`, `asistente-aclimar-credential`, `asistente-aclimar-ai-smoke`. No other installed operational script was found in `pyproject.toml`. The module-level ASGI app is non-operational and must remain free of runtime-file discovery.

## 4. Candidate approaches and rejected approaches

| Approach | Assessment |
| --- | --- |
| One fixed file under the user-local Windows application-data directory, centrally resolved | Recommended. User approved its exact logical path. Keeps CWD, checkout and executable location irrelevant. |
| Repository/CWD-relative TOML | Rejected: different launch directories could select different settings and SQLite/lock identities; risks accidental Git inclusion. |
| Search upward, scan multiple locations, or accept an arbitrary config path/CLI flag | Rejected: ambiguous precedence and an untrusted path-selection surface for operational commands. |
| Config-path or secret override through application-specific environment variables | Rejected: another unreviewed runtime route; secrets remain in keyring. The OS-known `%LOCALAPPDATA%` folder is a location, not an AI-setting override. |
| Change bare `load_settings()` globally to auto-discover | Rejected: would make `create_app()`, `app = create_app()` and existing isolated tests read ambient state. |

## 5. Recommended exact contract for the plan

1. The sole operational file is the Windows current-user LocalAppData known-folder child `ACLIMAR\Asistente Comercial\config.toml`, conventionally displayed as `%LOCALAPPDATA%\ACLIMAR\Asistente Comercial\config.toml`. Resolve the Windows known folder centrally, then append these fixed components; do not accept CWD, argv, an application-specific environment override, fallback directories, a path inside the repository or user-provided file names. If the known folder cannot be resolved safely, fail closed. The loader reads only; it never creates the directory/file or rewrites TOML.
2. Preserve `load_settings(path: Path | None = None)` as an explicit parser/defaults API for tests and inert `create_app()`. Add one dedicated operational loader/discovery entry point in `app/config.py`. It resolves the canonical path, requires a regular readable file and delegates to `load_settings(path)`. A missing, unreadable, malformed or invalid file causes a bounded configuration failure, not default operational settings or a search elsewhere. Do not echo TOML contents, path-derived sensitive details or raw parser exceptions at a CLI boundary.
3. Only `run(settings=None)` uses that operational loader. An explicitly supplied `Settings` object remains a test/composition injection and avoids ambient file reads. `create_app()` and module import remain inert with respect to the runtime TOML, keyring, network, database and provider. Direct `uvicorn app.main:app` remains non-operational and does not become a configuration-discovery back door.
4. Credential CLI `set/status/delete` and smoke CLI use the same operational loader before keyring access, lock acquisition or provider construction. Their existing no-path command syntax remains unchanged. Missing/invalid config returns only a fixed bounded `unavailable` outcome and nonzero exit; credential status does not fall back to a default keyring reference. The controlled launcher aborts before operational readiness with a bounded configuration error; it does not serve with default settings.
5. For **operational AI use**, TOML must explicitly contain `[ai] enabled = true`, `provider = "openai"`, a nonempty model and `base_url` equal to one of the adapter's existing allowlisted endpoints. Omitted/false `enabled` is OFF, never inferred from credential presence, endpoint or smoke success. Other numeric settings retain current validated defaults unless the approved plan requires stricter explicitness. The adapter's allowlist remains authoritative; no arbitrary endpoint, localhost URL or new provider is introduced. The fixed path may contain AI disabled for non-AI operation, but then smoke returns `disabled` without a provider call.
6. Keep API keys/tokens out of TOML, Git, command-line arguments, environment-variable overrides, logs, browser output and plaintext SQLite. Credential service/account in TOML are **non-secret references** only; Windows Credential Manager/keyring remains the secret store. Runtime parsing must reject unknown top-level tables and unknown keys in every supported table (including secret-looking keys), with bounded errors that never repeat values. Do not silently accept a `[credentials]` table. No real credential is accessed by analysis or offline tests.
7. Runtime settings are loaded once per process/command, not hot-reloaded during a provider attempt. This prevents the app and its lock from drifting to different database identities. Changing the file requires a new controlled invocation; it never toggles the process-local commercial gate.

The bounded-error choice for missing/invalid operational TOML is a **recommendation for plan approval**, not a change already made. It follows the task's fail-closed and explicit-error preferences. No live smoke is authorized by this document.

## 6. Dependencies and exact proposed Scope Lock

**IN SCOPE — future implementation, modify only:**

- `app/config.py` — canonical operational path resolver/loader and strict non-secret TOML validation;
- `app/main.py` — controlled `run()` load while preserving inert `create_app()`/module import;
- `app/security/credential_cli.py` — shared operational loader, bounded failure;
- `app/integrations/ai_smoke_cli.py` — shared operational loader, bounded failure;
- `test/test_config.py` — discovery/parser/fail-closed cases;
- `test/test_startup.py` — launcher injection, missing/invalid config and inert import/construction;
- `test/test_credential_cli.py` — same configured reference and bounded missing/invalid cases with fake keyring;
- `test/test_ai_smoke_cli.py` — same settings, disabled/missing/invalid/allowlist cases with fake lock/provider.

**OUT OF SCOPE:** adapter, domain, services, persistence, migrations, routes/templates, credential storage implementation, other integrations, documentation beyond the approved analysis/plan workflow, real local configuration and real secrets.

**RESTRICTIONS:** no new dependency; no database or schema change; no CLI config-path flag; no environment override; no automatic directory/file creation; no live OpenAI call; no commercial-gate activation; no change to adapter endpoint allowlist or smoke payload; no production SQLite or keyring in tests. If strict parsing exposes an incompatible existing *approved* TOML key, STOP rather than silently expanding the schema. Any implementation Scope Lock change needs approval.

Internal dependencies are `tomllib`, `pathlib`, Windows known-folder lookup using the standard library, the existing keyring abstraction, and the existing adapter allowlist. No dependency installation or migration is indicated. Platform-specific resolution must be injectable in tests so they never read the operator's actual LocalAppData.

## 7. Offline test matrix and acceptance

- Canonical known-folder path, independent of CWD; no arbitrary path/argv/env override; missing known folder, missing file, directory in place of file, unreadable file, malformed TOML and invalid fields fail closed with bounded errors.
- Reject secret/unknown keys in every table and unknown top-level tables without echoing values. Accept only valid non-secret TOML. Verify explicit `ai.enabled=true` plus allowlisted endpoint for smoke; missing/false enabled remains disabled; unsupported endpoint never reaches credential or provider.
- `run()` with explicit `Settings` performs no discovery; `run()` without settings loads once. Import and `create_app()` do not read the canonical file, keyring, database or network and do not acquire a lock. Operational startup with bad config never declares readiness.
- Credential `set/status/delete` use the same configured service/account with fake keyring; missing/invalid config performs no keyring operation or prompt and emits only a bounded result.
- Smoke uses the same configured database/lock identity and AI settings with fake lock/credentials/provider. Missing/invalid config never acquires the lock or calls provider; disabled/unsupported endpoint cannot cause a provider call. Existing no-payload, one-shot synthetic and commercial-gate-OFF tests continue to pass.
- Run focal tests for the four named test files, then the full offline `python -m pytest`; inspect exact diff and Scope Lock. Tests must not touch real LocalAppData, keyring or OpenAI.

## 8. Risks and out-of-scope discoveries

Principal risks: differing config selection between launcher/CLI; accidental default keyring reference; lock/database mismatch; secret text accepted under ignored TOML keys; leaking parser/OS errors; ambient file reads at import; treating technical enablement as commercial authorization. The contract addresses these with one fixed resolver, strict parsing, bounded failures, explicit injection and unchanged independent gate.

**OUT-OF-SCOPE DISCOVERY:** the existing parser silently ignores unknown top-level/non-AI keys. Its correction is included only insofar as necessary to guarantee that the newly discovered operational TOML cannot carry secrets; unrelated parser redesign is excluded.

## 9. Ambiguities and decision status

The earlier path ambiguity is resolved by the user's approval of `%LOCALAPPDATA%\ACLIMAR\Asistente Comercial\config.toml`. No additional product, data-model or security choice is required to draft the plan. The proposed missing/invalid-file and CLI contracts require normal plan review/approval before implementation; they are not silently enacted here.

## 10. Verdict

**READY FOR PLAN.** The eight-file proposed implementation Scope Lock is exact, offline-testable, dependency-free and migration-free. Phase 6F remains blocked until an approved plan and implementation make the runtime TOML reachable, offline tests pass, and a separate live execution task revalidates its preconditions.
