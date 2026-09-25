# Phase 6E1 Acceptance — Local Session, CSRF and Origin/Host Protection

**Status:** ACCEPTED
**Date:** 2026-09-25

## Scope

Accepted implementation:
- `app/security/session.py`
- `app/main.py`
- `app/web/routes.py`
- `test/test_security.py`
- `test/test_startup.py`
- `test/test_status.py`

Implementation commit:
- `4e860670eea05b7f9b8fd0fb24743fb9ff9e9245`

## Accepted behavior

- runtime session secret is cryptographically random and process-local;
- separately composed app instances receive distinct session secrets;
- session cookie is signed, HttpOnly, SameSite=Strict and bounded by local lifetime;
- CSRF tokens are session-bound and compared with hmac.compare_digest;
- missing/invalid CSRF fails closed;
- request Host is restricted to approved local loopback/test authorities;
- malformed, misleading and foreign Host values are rejected;
- same-origin local Origin validation is reusable for protected actions;
- null/foreign/malformed/mismatched origins fail closed;
- GET /health and GET / remain non-mutating;
- no commercial POST route exists;
- status does not expose session secret/CSRF material;
- startup recovery/single-instance ownership behavior remains intact;
- no OpenAI, credential or commercial-gate mutation was introduced.

## Validation

User-reported validation:

`python -m pytest test/test_security.py test/test_startup.py test/test_status.py`
- 72 passed

`python -m pytest`
- 634 passed
- 2 skipped
- 8 warnings

`git diff --check` passed.

Commit diff contains exactly the six approved Scope Lock files.

## Result

**ACCEPTED.**

Proceed to Phase 6E2 only after fixing the manual-trigger request/UI contract.
