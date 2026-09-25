# Phase 6B1 Acceptance — Process-Local Commercial Activation Gate

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Accepted implementation:
- `app/security/activation.py`
- `test/test_activation.py`
- `app/integrations/openai_analysis.py`
- `test/test_openai_analysis.py`
- `test/test_email_analysis_service.py`
- `test/test_security.py`

Implementation commit:
- `098fe7503a4a281c601cf754da652cb5f93d3888`

## Accepted behavior

- commercial authorization is process-local and defaults OFF;
- new gate instances do not inherit authorization;
- authorization is explicitly revocable and thread-safe;
- OpenAI adapter fails closed without operational ownership;
- OpenAI adapter fails closed with commercial gate OFF;
- checks occur before credential/provider use;
- ownership and gate are rechecked immediately before provider attempts;
- revocation during retry delay prevents the retry;
- ownership loss during retry delay prevents the retry;
- already-sent calls are not claimed cancellable;
- no test/fake-client production bypass exists;
- integration/security tests use explicit fake ownership + explicit gate ON where provider calls are intentionally expected;
- existing minimization, strict schema, no-tools, timeout/retry, prompt-injection and secret-redaction contracts remain intact;
- no route/UI control exists to enable commercial processing.

## Validation

User-reported validation:

`python -m pytest test/test_activation.py test/test_openai_analysis.py test/test_email_analysis_service.py test/test_security.py`
- 86 passed

`python -m pytest`
- 571 passed
- 2 skipped

Commit diff contains only the six approved Scope Lock files.

## Result

**ACCEPTED.**

Proceed to Phase 6B2 only under a new exact Scope Lock.
