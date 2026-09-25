# Runtime configuration loading — implementation plan

**Status:** READY FOR IMPLEMENT (requires explicit implementation approval)

**Date:** 2026-09-25

## 1. Objective and authority

Make the controlled launcher and both operational CLIs load one user-local, non-secret TOML file without changing inert app construction, commercial authorization or provider behavior. Authority: `docs/plans/runtime-config-loading-plan-task.md`, the accepted `docs/plans/runtime-config-loading-analysis.md`, the user's approval of the path below, `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, and existing contracts in `app/config.py`, `app/main.py`, the two CLIs and the OpenAI adapter. This plan does not authorize a live smoke call.

## 2. Canonical path and exact API

The **only operational** path is Windows current-user LocalAppData known folder + `ACLIMAR` + `Asistente Comercial` + `config.toml`, displayed as `%LOCALAPPDATA%\ACLIMAR\Asistente Comercial\config.toml`. CWD, repository/executable location, argv, application-specific environment variables and search paths have no role.

In `app/config.py` add:

- `_windows_local_appdata() -> Path`: on `sys.platform == "win32"`, call `shell32.SHGetKnownFolderPath` via stdlib `ctypes` for `FOLDERID_LocalAppData` (`{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}`), flags `0`, current-user token `NULL`. Declare the GUID structure and API argument/result types explicitly; receive a raw pointer, copy with `ctypes.wstring_at`, and always free it with `ole32.CoTaskMemFree`. Require successful HRESULT, nonempty absolute result. Do **not** read `%LOCALAPPDATA%` from `os.environ`, shell expansion or registry fallback. On non-Windows or any API/path failure, raise the bounded error below. Tests monkeypatch this one private function to return a temporary known-folder stand-in; they never invoke the real API or inspect real LocalAppData.
- `operational_config_path() -> Path`: append exactly the three fixed components to `_windows_local_appdata()`. No argument or fallback. Validate the final target before reading: each fixed child component must not be a Windows reparse point (via `lstat`/file attributes; missing final file is handled below), and the final target must be a regular file, not a directory/device/link. Do not create directories/files. Treat any inspection error as failure.
- `class RuntimeConfigError(ValueError)`: exception text is exactly `configuration_unavailable` for every discovery/read/parse/schema failure; chain suppressed at CLI/launcher boundary. It never contains a path, key name, TOML value, OS error, parser location or secret.
- `load_operational_settings() -> Settings`: resolve the fixed path once, require/read the regular file once, parse with the existing `load_settings(path)` semantics plus the strict schema below, and return one immutable `Settings` snapshot. Wrap known-folder, missing, non-regular, unreadable, encoding, TOML and validation failures as `RuntimeConfigError("configuration_unavailable") from None`. Do not cache globally, hot-reload or write the file. The caller invokes it once per process/command.

Preserve `load_settings(path: Path | None = None)` as an explicit parser/defaults API: `None` still returns fail-closed defaults and never discovers LocalAppData. An explicit test path still parses that path. Strict schema validation applies to supplied TOML too; existing callers of `load_settings()` without a path retain default behavior.

## 3. Exact TOML schema

Only these top-level tables are accepted; no top-level scalar, extra table, dotted unknown table or unknown key inside any table is accepted. Tables must be TOML tables. Empty approved tables, and an empty but present TOML file, are valid and use existing defaults; this never makes AI enabled. Do not echo rejected names or values in operational errors.

| Table | Allowed keys | Validation/defaults |
| --- | --- | --- |
| `[server]` | `host`, `port` | `host` exactly `127.0.0.1` (default same); `port` integer, not bool, 1–65535 (default 8000). |
| `[database]` | `url` | Nonempty string (default `sqlite:///assistant.db`); existing SQLite/lock layer remains authoritative on supported identity. No DB is opened merely by parsing. |
| `[imap]` | `host`, `port`, `account`, `account_scope`, `folder_allowlist`, `initial_window_days`, `max_body_bytes`, `credential_service`, `credential_account` | Preserve existing validated defaults and nonempty/positive rules; `port`/integer fields reject bool; `folder_allowlist` must be a nonempty array of distinct nonempty strings. Credential fields are references, not secrets. |
| `[ai]` | `enabled`, `provider`, `model`, `base_url`, `timeout_seconds`, `max_retries`, `max_output_tokens`, `max_request_bytes`, `credential_service`, `credential_account` | `enabled` exact bool, default false. `provider` exactly `openai`, default same. `model` nonempty trimmed string, default `gpt-6-sol`; it remains configurable under existing approved model policy. `base_url` absent when disabled is allowed; if supplied, retain existing strict HTTPS/no-credentials/query/fragment/port/path checks and require exactly `https://api.openai.com/v1` or `https://eu.api.openai.com/v1` whenever enabled. `enabled=true` must appear explicitly in TOML and requires `base_url` explicitly present and allowlisted. Adapter checks its own allowlist again before credential retrieval and remains authoritative. `timeout_seconds=60`, `max_retries=1`; `max_output_tokens` positive int; `max_request_bytes` positive int not above existing Phase 5A ceiling. All numeric fields reject bool. Existing defaults apply when omitted. `credential_service/account` are nonempty trimmed logical references, never secret values. |

The preflight allowlist in configuration may duplicate the adapter's two existing literal endpoint values only to reject an unsupported operational setting **before** smoke obtains the lock or keyring; it cannot expand the adapter's authority. A change to the adapter's allowlist requires its own approval, not a silent change here. `enabled=false` never means commercial-gate ON, even with an endpoint or credential present. No implicit enablement from file existence, provider, keyring or smoke success.

Reject secret-bearing fields/tables by closed schema (for example `api_key`, `password`, `token`, `[credentials]`) without echoing contents. Do not store or accept API keys, IMAP passwords or OAuth tokens in TOML. Windows Credential Manager/keyring remains the sole secret store; TOML holds only credential references. This task does not create the actual config file or change a real credential.

## 4. Entry-point and bounded-error behavior

| Entry point | Valid operational config | Missing/invalid config |
| --- | --- | --- |
| `app.main.run(settings=None)` / installed `asistente-aclimar` | Call `load_operational_settings()` exactly once before `create_app(..., _operational=True)` and `uvicorn.run`. Retain one snapshot for DB/lock/AI/port. | Abort before app creation, DB/lock, keyring, Uvicorn or readiness. Raise `SystemExit("configuration_unavailable")`; console exit 1 and only that bounded stderr line, no raw traceback/value/path. |
| `run(settings=<Settings>)` | Use the supplied object directly; no discovery. Existing controlled startup contract unchanged. | Not applicable to file discovery. |
| `create_app()` and module-level `app = create_app()` | Keep using `load_settings()` defaults when no Settings is injected. No runtime discovery, keyring lookup, DB, network, lock or provider call on import/construction. | Not applicable; the module-level ASGI object stays non-operational. |
| `asistente-aclimar-credential {set,status,delete}` | Load once before constructing keyring or prompting. Use the configured AI `credential_service/account`; status remains `present/missing/unavailable`, set remains non-echoing, delete bounded. No provider call. | stdout exactly `unavailable\n`, empty stderr, exit 1. No keyring operation, prompt or default-reference fallback. Invalid arguments/help keep existing early handling without discovery. |
| `asistente-aclimar-ai-smoke` | Load once. If AI disabled, retain `disabled\n`/exit 1 before lock, credential or provider. If enabled with allowlisted endpoint, follow the existing one-shot fixed synthetic/lock/credential/adapter path. No gate access. | stdout exactly `unavailable\n`, empty stderr, exit 1; no lock, keyring or provider. Invalid arguments/help keep existing early handling. Unsupported enabled endpoint counts as invalid config and produces the same bounded failure before lock/keyring/provider. |

No config-path flag, env override, alternate direct Python provider call, automatic config creation, logging of raw parsing errors or commercial-gate activation is allowed. No operational command reloads settings mid-run. A config edit requires a fresh invocation; it does not mutate a running gate.

## 5. Scope Lock and implementation order

**IN SCOPE — modify exactly these eight files, no others:**

1. `app/config.py` — ctypes known-folder resolver, fixed-path operational loader, bounded error, closed TOML schema and enabled-endpoint preflight; preserve defaults API.
2. `test/test_config.py` — temporary known-folder injection and strict schema/path/error cases.
3. `app/main.py` — only `run()` discovery and bounded failure; leave `create_app()` and module-level app inert.
4. `test/test_startup.py` — injected Settings bypass, one load, no startup on failure, import/create_app inertness.
5. `app/security/credential_cli.py` — common loader before keyring/prompt, bounded failure.
6. `test/test_credential_cli.py` — configured reference, shared file and failure isolation with fake keyring.
7. `app/integrations/ai_smoke_cli.py` — common loader before lock/keyring/adapter, bounded failure.
8. `test/test_ai_smoke_cli.py` — shared config, disabled/invalid/unsupported endpoint behavior with fakes.

**OUT OF SCOPE:** `app/integrations/openai_analysis.py`, gate, routes/templates, `app/security/credentials.py`, persistence/models/migrations, domain/services, `pyproject.toml`, real config file, real keyring, OpenAI, and all other files.

**RESTRICTIONS:** no dependency, migration, schema change, new CLI argument, environment config override, live call, real LocalAppData inspection or commercial activation. If implementation needs another file, new behavior outside the closed schema or a new functional decision, STOP. Do not change an approved existing TOML key silently; report the incompatibility for a separate decision.

## 6. Offline verification matrix

1. `test/test_config.py`: monkeypatch `_windows_local_appdata` to a temporary directory; verify exact fixed child path independent of CWD, no OS/env fallback, one read, no writes; failures for non-Windows/known-folder API failure, missing file, directory, symlink/junction/reparse child, unreadable file, bad UTF-8 and malformed TOML all raise the same value-free error. Assert no secret/path in exception/repr/log output. Unknown top-level/table key, secret-bearing key and invalid scalar/type fail. Empty file/approved tables remain disabled defaults. Valid approved schema preserves all parsed values. Enabled AI requires explicit true and one of two allowlisted URLs; unsupported endpoint fails before any secret/provider action.
2. `test/test_startup.py`: mocked loader called once for `run()` without Settings, never for supplied Settings, import or `create_app()`; invalid/missing config exits 1 with bounded text before `uvicorn.run`, lifespan, lock, DB, keyring or readiness. No production SQLite access.
3. `test/test_credential_cli.py`: use temporary TOML through mocked known-folder resolver and fake keyring; all three commands use its configured reference, no fallback to defaults on missing/invalid config, no prompt or keyring call after failure; invalid arguments/help avoid discovery; no raw TOML/secret in stdout/stderr/logs.
4. `test/test_ai_smoke_cli.py`: same temporary file and fake lock/keyring/adapter; enabled allowed endpoint reaches the existing synthetic fake once; disabled fails before lock; unsupported/malformed/missing config fails before lock/keyring/provider; no commercial gate or real network access. The known folder stand-in and app launcher use identical settings/DB identity.
5. Run `python -m pytest test/test_config.py test/test_startup.py test/test_credential_cli.py test/test_ai_smoke_cli.py`, then `python -m pytest` with existing offline fixtures. Run `git diff --name-only`, `git diff --check` and inspect full diff; stage only eight allowed files. Do not run Phase 6F live smoke as verification.

Acceptance requires deterministic Windows path selection, one immutable runtime snapshot per invocation, no ambient config read on import/create_app, closed non-secret TOML schema, bounded fail-closed errors, no secret/keyring/network/DB access on invalid config, unchanged independent commercial gate and all offline tests green.

## 7. Rollback, risks and STOP findings

Because this is code-only and does not create/migrate a real config file or DB, rollback is reverting the future implementation commit after stopping the operational process. **Do not** fall back to defaults or another config path if the new file is absent/invalid. Existing credential entries are neither moved nor deleted. Phase 6F remains unexecuted until a separately approved live task rechecks file, endpoint, credential presence, lock ownership and gate state.

Risk: fixed Windows folder could be unavailable, path could be a reparse point, or existing approved TOML might contain extra keys. Each fails closed; do not auto-migrate or loosen the schema. Another risk is divergent preflight/adapter endpoint lists; the adapter remains final authority and tests cover the two currently approved values. No need for dependency, migration or database change was found. No unresolved decision or out-of-scope file is currently required.

**Verdict: READY FOR IMPLEMENT**, subject to explicit approval of this plan and exact eight-file Scope Lock.
