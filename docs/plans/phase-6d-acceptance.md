# Phase 6D Acceptance — Synthetic Smoke CLI and Adapter Path

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Accepted implementation:
- `app/integrations/ai_smoke_cli.py`
- `test/test_ai_smoke_cli.py`
- `app/integrations/openai_analysis.py`
- `test/test_openai_analysis.py`
- `pyproject.toml`

Implementation commit:
- `5a0bc282cff814c761c298f72732ccae234a269a`

## Accepted behavior

- commercial `analyze(AnalysisInput)` retains ownership + commercial-gate authorization;
- synthetic `smoke()` is public but accepts no payload/input/content arguments;
- smoke constructs one fixed immutable synthetic input internally;
- fixed synthetic input contains no commercial source data or external identifiers;
- smoke does not inspect, enable or mutate the commercial gate;
- smoke requires technical AI enabled and operational ownership;
- ownership is revalidated before provider attempts and retries;
- smoke and commercial analysis share one private provider execution path;
- strict schema, decoder, endpoint allowlist, configured model, credential reference, request limits, timeout/retry, store=false and no-tools behavior are shared;
- smoke is one-shot per adapter instance;
- CLI accepts no payload and acquires the real configured single-instance lock;
- CLI does not query commercial SQLite/source repositories or IMAP/CRM/Calendar;
- all implementation validation is offline/faked;
- no live OpenAI call was performed or authorized.

## Validation

User-reported validation:

`python -m pytest test/test_ai_smoke_cli.py test/test_openai_analysis.py`
- 50 passed

`python -m pytest`
- 611 passed
- 2 skipped

Commit diff contains only the five approved Scope Lock files.

## Result

**ACCEPTED.**

A live smoke remains separately gated under Phase 6F.
Proceed to Phase 6E1 before exposing any state-changing commercial web action.
