# Phase 6F — Unicode ValueError family plan

**Status: READY FOR IMPLEMENT — planning only.** This plan authorizes no provider call, live smoke, code change, credential access, or commercial activation by itself.

## Objective, authority, and evidence limit

Add exactly one fixed diagnostic category, `provider_unicode_error_family`, for a residual `UnicodeError` escaping `client.responses.create(**request_kwargs)`. Authority: `docs/plans/phase-6f-unicode-value-family-plan-task.md` and the approved `docs/plans/phase-6f-value-subclass-analysis.md`; checked against the current adapter, CLI, and offline tests. The seventh live smoke returned `provider_value_subclass_family`, proving only a non-exact `ValueError` descendant at that catch boundary. A no-network 200 response with invalid UTF-8 JSON bytes reproduced that broad code with the fixed synthetic request, but **does not identify the seventh live exception, response source, or dispatch stage**.

## Exact mapping and precedence

Inside the existing `except Exception as error` around **only** `client.responses.create(**request_kwargs)`, preserve all current branches and their order through:

1. timeout/connection and verified HTTP/auth/quota/rate handling, including anomalous `APIStatusError -> provider_failure`;
2. exact `APIResponseValidationError`, exact `json.JSONDecodeError`, exact `TypeError`, exact `ValueError`, exact `RuntimeError`;
3. residual `openai.OpenAIError`, `httpx2.RequestError`, and `OSError` families.

Insert **one** branch immediately after the current residual `OSError` branch and immediately before the current residual `ValueError` branch:

```python
elif isinstance(error, UnicodeError):
    category, transient = "provider_unicode_error_family", False
```

Leave `elif isinstance(error, ValueError): category, transient = "provider_value_subclass_family", False` and all following branches unchanged. This ordering is essential: exact `json.JSONDecodeError` stays `provider_response_json_failure`; exact `ValueError` stays `provider_sdk_value_failure`; a residual `UnicodeError`, `UnicodeDecodeError`, `UnicodeEncodeError`, or `idna.IDNAError` reaches the new code by inheritance; an unwrapped `pydantic.ValidationError`, `pydantic_core.PydanticSerializationError`, or other custom non-Unicode `ValueError` subclass remains `provider_value_subclass_family`. A custom `JSONDecodeError` subclass also remains in that residual value bucket unless it independently inherits UnicodeError. Existing OpenAI/HTTP/OS checks retain priority. The new category is **non-transient**: one adapter SDK attempt, no sleep or retry. Keep current request lock release and `_raise(category)` behavior.

The code names a known built-in family; it must not derive a concrete class identity. Do not add Pydantic- or IDNA-specific production imports or categories, `provider_value_other_family`, or any generic catch-all. The Unicode code means only an encoding/decoding-family exception; it does **not** mean invalid UTF-8 occurred in the live smoke or that the provider supplied malformed bytes.

## CLI output and security invariants

Add exactly the literal `provider_unicode_error_family` to the existing `_DIAGNOSTIC_CODES` allowlist. It must produce one stdout line `smoke_failed:provider_unicode_error_family\n`, empty stderr, exit code 1, and release the lock. Preserve all previous allowed codes and the generic `smoke_failed\n` fallback for unknown, internal, non-string, and unhashable codes. Preserve `passed`, `disabled`, `lock_unavailable`, `unavailable`, help, and invalid-command behavior.

Neither adapter nor CLI may emit or derive a concrete exception class name/module, MRO, `str`/`repr`/`args`, cause/context, malformed response bytes, provider message/body, request payload, URL/headers, or secrets. No transport instrumentation or assertion about provider/intermediary origin or pre-/post-dispatch timing. The existing synthetic-only smoke and ownership/commercial-gate boundaries remain unchanged.

## Exact Scope Lock and per-file steps

**IN SCOPE — exactly four tracked files:**

1. `app/integrations/openai_analysis.py`: insert only the `UnicodeError` branch above, directly between residual `OSError` and `ValueError`; do not alter imports, call arguments, branch order elsewhere, or retry logic.
2. `test/test_openai_analysis.py`: add fake-client UnicodeError/UnicodeDecodeError/UnicodeEncodeError and synthetic IDNAError classification tests with one call/no sleep/lock release/no leak; add pinned SDK + explicit `httpx2.MockTransport`, `trust_env=False`, synthetic key, and invalid UTF-8 `application/json` response test using the unchanged fixed smoke request. Retain/regress exact JSON/ValueError, residual Pydantic validation/serialization, safe custom ValueError subclass, and existing transport/HTTP/auth/quota/timeout/connection behavior and request kwargs.
3. `app/integrations/ai_smoke_cli.py`: add only the one literal to `_DIAGNOSTIC_CODES`; no flow change.
4. `test/test_ai_smoke_cli.py`: add the one literal to the allowed-code matrix; verify exact bounded output, empty stderr, exit 1, lock release, and unchanged generic fallback for unknown/non-string/unhashable values.

**OUT OF SCOPE:** any fifth tracked file; model, endpoint, Responses API, schema, payload, output tokens, timeout/deadline, retries/delay, dependencies/package versions, keyring, credentials, gate, ownership, routes/UI, config, SQLite, persistence, telemetry, or network access. **RESTRICTIONS:** no new production import, Pydantic-specific code, raw response/exception content, concrete-class reflection/fingerprint, provider call, live smoke, or operational secret/config/database access. If any is needed, STOP rather than expanding the task.

## Offline/no-network acceptance matrix

- Fake-client injected `UnicodeError`, `UnicodeDecodeError`, `UnicodeEncodeError`, and `idna.IDNAError`: new fixed code, exactly one SDK call, zero sleeps, released request lock, and no injected secret-like text in adapter error, captured stdout/stderr, or logs. IDNA injection tests inheritance only; it does not imply the fixed ASCII URL takes an IDNA failure path.
- Pinned `openai==3.17.0` SDK with synthetic key, explicit MockTransport/no-send and `trust_env=False`: a local 200 `application/json` response containing invalid UTF-8 bytes maps to `provider_unicode_error_family` with one mock dispatch. Never print the bytes or infer the live failure from this reproduction.
- Precedence regressions: exact `json.JSONDecodeError -> provider_response_json_failure`; exact `ValueError -> provider_sdk_value_failure`; Pydantic validation/serialization injected outside ordinary SDK wrapping and a custom ValueError subclass stay `provider_value_subclass_family`; normal strict-response Pydantic validation remains wrapped as the existing `provider_response_validation_failure`. Preserve existing OpenAI/HTTP/OS family results and malformed/unrelated fallback.
- Unchanged contract tests: HTTP/auth/quota/connection/timeout retry counts and ordering; `request_schema_failure`; client factory and request kwargs; synthetic smoke one-shot/ownership; CLI allowlist exactness, previous diagnostics, and unknown/non-string/unhashable fallback. No real keyring, LocalAppData, SQLite, DNS, TLS, socket, or provider traffic.

Run `python -m pytest test/test_openai_analysis.py test/test_ai_smoke_cli.py`, then `python -m pytest`, then `git diff --name-only` and `git diff --check`. The tracked diff must contain exactly the four files above, with no fifth file. Tests must remain offline and green. A later live synthetic smoke requires **separate explicit authorization** and is not an implementation acceptance test.

## Rollback, risks, and verdict

If a future implementation fails offline validation, revert the one adapter branch, one CLI literal, and their tests as a single four-file diagnostic change; do not compensate by changing model, endpoint, schema, payload, dependencies, timeout, retries, or gate. The primary risk is overinterpreting the new family as proof of malformed provider JSON. It provides only a bounded family distinction. If a separately authorized future live result remains `provider_value_subclass_family`, STOP for a new decision rather than adding speculative categories or exposing dynamic identity.

No unresolved design choice blocks implementing **this one approved-category plan** within the stated Scope Lock. Approval of the implementation task is still required.

**READY FOR IMPLEMENT.**
