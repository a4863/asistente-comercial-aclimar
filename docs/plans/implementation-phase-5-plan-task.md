# Phase 5 Planning Task — Real OpenAI Provider Integration

**Status:** Approved for Plan Task
**Date:** 2026-09-24
**Decisions:** docs/plans/phase-5-ai-provider-decisions.md
**Analysis:** docs/plans/phase-5-ai-provider-analysis.md

## Objective

Create the implementation plan for the approved Phase 5 OpenAI provider integration.

This is a PLAN task only.

Do not implement code.
Do not add dependencies.
Do not configure credentials.
Do not call OpenAI.
Do not run live-network tests.

## Authoritative inputs

Inspect:
- AGENTS.md
- docs/functional-spec.md
- docs/architecture.md
- docs/security.md
- docs/testing-strategy.md
- docs/plans/remote-ai-data-policy.md
- docs/plans/phase-4-acceptance.md
- docs/plans/phase-5-ai-provider-analysis.md
- docs/plans/phase-5-ai-provider-decisions.md
- app/domain/email_analysis.py
- app/services/email_analysis.py
- app/config.py
- app/security/credentials.py
- pyproject.toml
- current config/credential/analysis/security tests

Ignore __pycache__, .pytest_cache and unrelated untracked files.

## Required plan

Create a staged plan with small approved-by-stage increments.

At minimum address:

### 5A — remote projection and structured schema
Define exact provider-neutral/provider-facing request and response projection.
Requirements:
- ephemeral aliases;
- no internal IDs/digests/run IDs/conversation keys remotely;
- exact allowed metadata;
- bounded 30k body disclosure and max six priors remain inherited from Phase 4;
- strict JSON Schema;
- exact mapping to AnalysisCandidates;
- sensitive-content preflight fail-closed gate;
- no network in 5A.

Aim for 2 files if practical.

### 5B — non-secret config and credential reference
Define:
- AI provider/model non-secret settings;
- EU/base endpoint handling;
- timeout=60s;
- retry count=1;
- output/token ceiling;
- enabled flag if needed;
- logical keyring reference;
- secret-key rejection from TOML;
- fake keyring tests;
- no real credential creation.

Aim for 2–4 files.

### 5C — OpenAI adapter
Define:
- official OpenAI Python SDK dependency and version strategy;
- Responses API;
- GPT-6 Luna configured model default or approved explicit config behavior;
- strict Structured Outputs;
- no tools/functions;
- no streaming;
- one in-process concurrent request;
- one transient retry max;
- bounded timeout/deadline;
- bounded provider error classification;
- no raw provider exception text;
- no logs of prompts/responses;
- fake client/transport tests only.

No service/domain/persistence edits unless the plan proves they are required; if required, STOP rather than assuming.

### 5D — integration/security verification
Define:
- composition of concrete adapter behind existing AIService;
- service integration with doubles;
- prompt-injection regression;
- minimization regression;
- replay/force/stale semantics unchanged;
- sensitive-content gate;
- no external action authority;
- no real network in default pytest.

### Optional live smoke
Must be a separate, explicitly invoked, disabled-by-default task using synthetic content and deliberate user action.
It must never run in normal pytest or app startup.

## Exact planning requirements

For each subphase provide:
- goal;
- exact proposed Scope Lock paths;
- prerequisites;
- detailed behavior;
- test cases;
- STOP conditions;
- expected commit message;
- commands for focused and full validation;
- explicit exclusions.

Identify whether any existing file must change to instantiate the adapter in production. Do not silently add UI/routes/scheduler activation.

If the official SDK version/model/API capability must be verified externally before implementation, mark that as a pre-implementation verification gate.

## Output

Create exactly:

docs/plans/implementation-phase-5-plan.md

The plan must end with:
READY FOR APPROVAL
or
BLOCKED

## Scope Lock

This Plan Task may create/modify only:
- docs/plans/implementation-phase-5-plan.md

## Completion

Commit:
Plan phase 5 OpenAI provider integration

Push only origin/codex-work.
