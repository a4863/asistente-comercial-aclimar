# Phase 6F — Pre-Request Unicode Operator Remediation

**Status:** OPERATOR ACTION
**Date:** 2026-09-28
**Source:** docs/plans/phase-6f-pre-request-unicode-analysis.md

## Goal

Remove plausible pre-request Unicode contamination without inspecting or exposing secret values.

## Step 1 — check only presence of relevant OpenAI environment variables

Check whether these variable names are present in the current process/user/machine environment:

- OPENAI_ORG_ID
- OPENAI_PROJECT_ID
- OPENAI_CUSTOM_HEADERS

Do not print their values.

If any are present and are not intentionally required for this assistant, remove them from the environment source that launches the assistant.

Do not alter unrelated proxy variables or other environment settings.

## Step 2 — reset the stored API credential

Use only the existing secure credential CLI:

1. delete the stored credential;
2. set a freshly copied API key interactively;
3. verify only bounded status = present.

Do not:
- paste the key into chat;
- pass it on the command line;
- store it in TOML, Git, PowerShell history, or logs;
- inspect/hash/classify the key characters.

## Step 3 — stop before live execution

After environment cleanup and credential reset:

- do not run the smoke yet;
- verify tracked Git state is clean;
- request fresh explicit authorization for the next live smoke.

## Interpretation

This remediation does not prove the ninth failure was caused by the credential or ambient SDK headers. It only removes the two strongest locally reproduced pre-hook Unicode sources before the next bounded diagnostic attempt.

No code change is authorized or required.
