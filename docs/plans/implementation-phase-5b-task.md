# Phase 5B Implementation Task — OpenAI Configuration and Credential Boundary

**Status:** Approved for Implement
**Date:** 2026-09-24
**Plan:** docs/plans/implementation-phase-5-plan.md
**Decisions:** docs/plans/phase-5-ai-provider-decisions.md
**Prerequisite:** Phase 5A ACCEPTED

## Objective

Implement only the non-secret AI configuration boundary and credential-reference behavior needed for later OpenAI adapter work.

No OpenAI SDK.
No network.
No real credential creation.
No provider call.
No UI/reconnect screen.

## Exact Scope Lock

Modify only:

1. app/config.py
2. test/test_config.py
3. test/test_credentials.py

Do not modify app/security/credentials.py unless a genuine incompatibility is discovered; if that happens, STOP and report it instead of expanding scope.

## Required configuration

Add an immutable AI settings structure under Settings.

Approved non-secret settings:

- enabled: bool, default false
- provider: exactly "openai"
- model: default "gpt-6-sol"
- base_url or equivalent endpoint setting
- timeout_seconds: exactly 60 for this phase
- max_retries: exactly 1
- max_output_tokens: positive integer, configurable
- max_request_bytes: positive integer, configurable and compatible with Phase 5A request ceiling
- credential_service
- credential_account

The exact default endpoint must be conservative and must not silently claim EU processing unless explicitly configured/verified.

AI must remain disabled by default.

## TOML rules

Support an [ai] table.

Reject:
- secret-bearing keys such as api_key, key, secret, token, access_token, refresh_token, password, bearer, authorization;
- unknown keys;
- wrong primitive types;
- bool-as-int for integer settings;
- empty provider/model/credential refs;
- provider values other than "openai";
- timeout not equal to 60;
- max_retries not equal to 1;
- non-positive bounds;
- malformed URLs;
- non-HTTPS URLs;
- embedded URL credentials;
- query strings;
- fragments;
- unapproved/unknown hosts if a host allowlist is used.

Do not silently normalize dangerous input into accepted config.

## Endpoint behavior

The configuration must distinguish between:
- generic OpenAI endpoint configuration;
- explicitly configured EU endpoint/region preference where supported later.

Do not claim or infer data residency from a hostname alone.

If the plan cannot express this cleanly without provider verification, keep only a conservative HTTPS base URL field and mark actual EU activation as a 5C precondition rather than inventing semantics.

## Credential boundary

Use the existing CredentialStore / KeyringCredentialStore contract as-is.

Tests must prove:
- AI and IMAP credential references are independent;
- missing AI credential returns None from a fake keyring;
- credential retrieval itself does not expose the secret in repr/error/logging;
- config stores only logical service/account names;
- no secret value enters Settings.

Do not add setters.
Do not create or persist a real API key.

## Tests

Cover at least:

1. AI disabled defaults.
2. provider default openai.
3. model default gpt-6-sol.
4. timeout default/exactly 60.
5. max_retries default/exactly 1.
6. positive output-token ceiling.
7. positive request-byte ceiling.
8. valid [ai] TOML loads.
9. unknown [ai] key rejected.
10. secret-bearing [ai] keys rejected.
11. provider other than openai rejected.
12. empty model rejected.
13. empty credential service/account rejected.
14. bool-as-int rejected for numeric fields.
15. zero/negative numeric bounds rejected.
16. non-HTTPS endpoint rejected.
17. endpoint with username/password rejected.
18. endpoint with query/fragment rejected.
19. AI credential reference independent from IMAP.
20. fake keyring returns AI secret only for exact service/account.
21. missing/revoked fake AI credential returns None.
22. no secret appears in Settings repr.
23. no secret appears in caught config/credential errors.

Use synthetic values only.

## Restrictions

- no OpenAI import;
- no dependency changes;
- no network;
- no API key creation;
- no Windows Credential Manager mutation;
- no service/domain/persistence/migration changes;
- no UI/routes/scheduler;
- no real account assumptions;
- no cache/untracked inspection.

## Validation

Run:

python -m pytest test/test_config.py test/test_credentials.py

Then:

python -m pytest

Tracked diff must contain exactly:
- app/config.py
- test/test_config.py
- test/test_credentials.py

## STOP conditions

STOP if:
- existing CredentialStore abstraction is insufficient;
- a fourth production file is required;
- endpoint/region semantics require unverified assumptions;
- config needs persistence or migration;
- a real credential or network call appears necessary.

## Completion

Commit:

Implement phase 5B OpenAI configuration boundary

Push only origin/codex-work.
