# Phase 6F — pre-request-hook Unicode failure analysis

**Mode:** read-only diagnosis, offline and no-network. **Trigger:** ninth live smoke returned `smoke_failed:provider_unicode_before_request_hook`. This document is the sole authorized output; no live credential, keyring, operational configuration/database, or provider was accessed.

## 1. Objective and context

Identify operations inside the installed synchronous `Responses.create()` path that can raise a residual `UnicodeError` before the public `httpx2` request hook. The bounded code proves only that the hook had not run in that adapter attempt. It does not prove the credential is malformed, that a request was dispatched, or that the provider rejected anything.

## 2. Interpretation and documentation consulted

The task is diagnosis of the existing fixed synthetic smoke request, not authorization to change the adapter or perform a tenth live call. Consulted `AGENTS.md`, `docs/functional-spec.md` (remote-AI and credential boundaries), `docs/architecture.md`, `docs/security.md`, `docs/testing-strategy.md`, this task, prior Phase 6F Unicode/hook analyses and approved hook plan, `app/integrations/openai_analysis.py`, `app/integrations/ai_schema.py`, and the relevant installed source of `openai==3.17.0` and `httpx2==2.13.1` on Python 3.13.7. No required document was missing.

## 3. Current implementation and exact pre-hook lifecycle

1. The adapter constructs its fixed smoke input and the minimized request text before acquiring the request lock. Its JSON/UTF-8 input encoding failure maps to `invalid_input`, not this code. It builds `request_kwargs`, including fixed model, instructions, schema, output limit, and `store=False`, before the SDK-call classifier; a failure there maps to `request_schema_failure`.
2. The adapter retrieves a credential string, creates a public `openai.DefaultHttpxClient` with request/response hooks, and creates `openai.OpenAI` with SDK retries disabled. Constructor failures map to `provider_unavailable`. The SDK constructor can also take optional organization, project, and custom-header values from its process environment (`openai/_client.py`, constructor). The adapter does not supply these explicitly.
3. Installed `Responses.create()` applies `maybe_transform` to the request fields, makes request options with bearer authentication, and invokes `_post("/responses", ...)` (`openai/resources/responses/responses.py`, synchronous `create`). The SDK copies/prepares options, creates an ASCII UUID-based idempotency key for this POST, and enters `_build_request` (`openai/_base_client.py`, `request`).
4. `_build_request` calls `_build_headers` **before** building an `httpx2.Request`. OpenAI constructs `Authorization` from `Bearer ` plus the supplied credential; merges fixed SDK headers, optional organization/project and custom environmental headers; and instantiates `httpx2.Headers` (`openai/_client.py`, `_bearer_auth`/`default_headers`; `openai/_base_client.py`, `_build_headers`). Installed `httpx2/_models.py` encodes string header keys and values with ASCII by default. A non-ASCII header value therefore raises `UnicodeEncodeError` here, before any request hook. The SDK also prepares the fixed ASCII URL, JSON body bytes through `openapi_dumps` (`ensure_ascii=False`, then UTF-8 encoding), timeout and `Client.build_request` header/URL/cookie/query merges.
5. The SDK calls `_prepare_request` and then `httpx2.Client.send`. `send` sets timeout, prepares auth, and enters auth/redirect handling. Only inside `_send_handling_redirects` does the public request hook run, before `_send_single_request` (`httpx2/_client.py`). Thus `before_request_hook` covers all prior transform/header/URL/JSON/request/auth work, not just the credential.

The fixed ASCII model, approved base URL, route, instructions, schema keys, and synthetic body all traversed this path in the offline ASCII control. The allowed endpoint and route do not exercise non-ASCII IDNA normalization. The idempotency UUID, retry-count and timeout headers are ASCII. Normal platform headers from this installed runtime also succeeded in the control. A changed SDK/runtime/environment could invalidate that observation; no claim is made about unobserved live environment values.

## 4. Synthetic no-network reproductions

The unchanged application `smoke()` request was run with synthetic credentials, installed SDK, `httpx2.MockTransport`, `trust_env=False`, and a process-local empty environment replacement. Public hook callbacks only incremented counters; the mock returned a synthetic 200 response with deliberately invalid model content. No credential, header, URL, payload, response body, raw exception, or exception identity was printed or retained in the report. `invalid_output` below means the request reached the mock and the synthetic response was deliberately unsuitable; it is the expected control result, not a smoke success.

| Synthetic credential case | Bounded adapter result | Request / response hook | Mock transport entry |
| --- | --- | --- | --- |
| ASCII control | `invalid_output` | 1 / 1 | 1 |
| Character outside ASCII header range | `provider_unicode_before_request_hook` | 0 / 0 | 0 |
| Accented character | `provider_unicode_before_request_hook` | 0 / 0 | 0 |
| Emoji | `provider_unicode_before_request_hook` | 0 / 0 | 0 |
| Leading ASCII space | `invalid_output` | 1 / 1 | 1 |
| Trailing ASCII space | `invalid_output` | 1 / 1 | 1 |
| Embedded newline | `invalid_output` | 1 / 1 | 1 |
| Embedded ASCII control | `invalid_output` | 1 / 1 | 1 |

The whitespace/control cases show only that this no-send transport did not fail *before the hook*. They do **not** establish that those credentials are valid or safe for a real HTTP connection; a later transport/server stage may reject them. No real connection was attempted.

A second no-network run held the credential at synthetic ASCII and varied only one SDK process-environment input at a time. Empty environment reached the mock once; synthetic non-ASCII `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`, or `OPENAI_CUSTOM_HEADERS` each produced `provider_unicode_before_request_hook` with zero mock transport entries. These are independently reproducible **non-credential** sources of the same bounded code. No actual process-environment value was inspected.

## 5. Findings, ambiguities, dependencies, and risks

The strongest demonstrated mechanism is **ASCII encoding of a dynamic HTTP header before the request hook**. A non-ASCII credential is one such mechanism, but optional SDK organization/project/custom headers can produce the same code. The live code does not disclose which one it was. The installed source also leaves lower-probability pre-hook Unicode possibilities in transform/serialization or other environment-derived SDK headers, though the exact fixed request and clean-environment ASCII control produced none. There is no evidence that the server, model, schema, TLS, DNS, or response decoding caused the ninth code.

The real credential cannot be narrowed to an encoding class without reading or inspecting it, including a supposedly harmless character-class check. This task forbids that inspection. A presence-only check of *non-secret* SDK environment-variable names could narrow the environmental alternatives in a separately authorized operator diagnostic, but would not prove the key's contents. Do not infer from the dashboard's older “Last used: Never” status that this specific attempt had zero transport activity; the local hook result is the relevant stage evidence and remains pre-hook only.

Risks: blaming a valid key while an ambient header is malformed; replacing a key without resolving environmental contamination; leaking a secret through logs, exception text, shell arguments or a new validator; treating the no-send newline/control results as approval for live use; and spending another live call before the local input boundary is addressed. No architecture, dependency, model, endpoint, schema, payload, timeout, retry, gate, or ownership change is justified by the evidence.

## 6. Affected elements, Scope Lock, and tests for any future work

**IN SCOPE now:** only this analysis file. **OUT OF SCOPE:** production code, tests, other docs, packages, actual keyring/credential, operational TOML/SQLite, real environment inspection, provider/network calls, and live smoke. **RESTRICTIONS:** no credential value or class inspection, hashes, raw exceptions, headers, URLs, payloads, or secret-bearing logs; no new classification or retry behavior.

Dependencies are the existing adapter/CLI, `openai==3.17.0`, `httpx2==2.13.1`, secure credential CLI, and the approved local ownership boundary. If a later plan is requested, its offline acceptance should include the fixed-request ASCII control, non-ASCII credential and synthetic ambient-header cases, hook counters, no-send enforcement, and no-leak assertions. That is a test recommendation only, not authorization to implement.

**OUT-OF-SCOPE DISCOVERY:** the SDK reads `OPENAI_CUSTOM_HEADERS`, organization and project values from its ambient process environment even when the adapter supplies an explicit API key and base URL. This may matter for hardening future operational configuration, but changing SDK environmental behavior is not within this task.

## 7. Decision and operator recommendation

There are at least two demonstrated sources with indistinguishable bounded outcomes: credential header versus other dynamic SDK headers. Do not guess which caused the ninth live event. The smallest safe next step is operator-side: check whether optional SDK organization/project/custom-header environment settings are intentionally present, without displaying their values; if not required, remove them from the launcher environment. Then use the existing secure credential CLI to delete/reset the stored AI credential and enter a freshly copied key interactively, without echo, shell argument, TOML, or Git. Check only `present/missing/unavailable` afterward. The operator must explicitly authorize any subsequent live smoke; none is authorized by this analysis. A single future smoke could be justified only after that remediation and separate approval, retaining the current one-shot/off-gate controls.

**Code changes justified now:** none. **Functional/design ambiguity:** no new design choice is necessary for this diagnosis; causal attribution remains intentionally unresolved without touching forbidden live inputs. **Decision pending:** operator approval/choice for local environment cleanup and credential re-entry, followed by separate approval if another live smoke is desired.

OPERATOR ACTION
