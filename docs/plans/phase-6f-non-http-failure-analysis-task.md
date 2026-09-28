# Phase 6F Non-HTTP Failure Decomposition Analysis Task

**Status:** READY FOR ANALYSIS
**Date:** 2026-09-28
**Mode:** READ-ONLY
**Trigger:** third live smoke returned `smoke_failed:provider_non_http_failure`

## Objective

Determine, entirely offline, the smallest safe way to distinguish whether the non-HTTP failure occurs:
1. while building local request/schema arguments;
2. during SDK request validation/construction before HTTP;
3. in another local/non-HTTP SDK phase.

Do not call OpenAI.

## Required local evidence

Inspect the actually installed interpreter/package used operationally:
- Python: `C:\Python313\python.exe`
- project dependency: `openai==3.17.0`

Read only local installed SDK source/signatures/metadata. Do not instantiate a real provider request.

At minimum inspect:
- `openai.__version__`;
- signature/source/type hints for the pinned `Responses.create`;
- generated type definitions for `text`, `text.format`, JSON Schema response format and `input`;
- exact generated handling/validation path relevant to the current kwargs;
- whether `timeout` is accepted per-call in this pinned version;
- whether `text={"format": {"type":"json_schema", "name":..., "strict":..., "schema":...}}` is accepted by the pinned version's generated contract;
- whether the current `input=[{"role":"user","content": request_text}]` shape is accepted by the pinned version;
- whether `response_schema()` itself can raise for the current static schema.

## Questions to resolve

1. Can `response_schema()` be executed offline with the existing synthetic contract, and does it complete deterministically?
2. Can the exact request kwargs be validated/serialized offline using the pinned SDK without sending HTTP?
3. Does the pinned SDK expose a local conversion/validation helper that can be exercised safely with a synthetic API key and a fake/no-send transport?
4. If an SDK client must be constructed for offline validation, can this be done with a synthetic key and a transport guaranteed never to send network traffic?
5. Which exact exceptions arise for the current kwargs under offline no-send validation, if any?
6. Can the production code safely split the current broad try into bounded phases such as:
   - `request_schema_failure`
   - `provider_sdk_local_failure`
   without exposing raw exception text?
   Do not adopt these names without justification.
7. Should `response_schema()` be evaluated before entering the provider call try block, or in its own bounded try?
8. Can we narrow the likely root cause without any fourth live call?
9. Is the current pin `openai==3.17.0` materially different from current upstream docs for these arguments?
10. Confirm no model/endpoint/schema semantic change is justified unless the pinned SDK contract proves an incompatibility.
11. Define exact proposed Scope Lock for any correction.
12. Define offline tests that reproduce the exact current synthetic request path with a no-network transport.

## Security and network restrictions

Do not:
- call OpenAI;
- use real API key/keyring;
- read operational config unless strictly necessary for a non-secret static setting, preferably avoid entirely;
- open operational SQLite;
- print/log raw exception text from a real provider;
- change model, endpoint, payload, schema, timeout or retry policy;
- install/upgrade/downgrade packages;
- access network from test code.

If constructing an SDK client is useful, use only:
- synthetic API key;
- explicit fake/no-send transport that fails the test if network dispatch is attempted.

## Preferred diagnostic direction

Prefer phase separation in code over reflecting exception strings.

Examples of safe distinction:
- local schema/build failure before SDK invocation;
- local SDK/no-HTTP failure after invocation starts;
- HTTP/APIStatusError categories already implemented.

The goal is to identify the failing phase, not the raw provider message.

## Deliverable

Create only:

`docs/plans/phase-6f-non-http-failure-analysis.md`

Include:
- exact pinned SDK findings;
- exact current request-contract compatibility findings;
- whether current kwargs can be validated offline;
- whether `response_schema()` succeeds offline;
- recommended bounded phase decomposition;
- exact proposed Scope Lock;
- offline/no-network test matrix;
- verdict: READY FOR PLAN or STOP.

No code changes.
No live call.
No dependency changes.

Commit:

Analyze phase 6F non-HTTP failure

Push only origin/codex-work.
