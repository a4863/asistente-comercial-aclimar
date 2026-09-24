# Phase 4F Implementation Task — Adversarial Security and End-to-End Analysis Validation

**Status:** Approved for Implement
**Date:** 2026-09-24
**Prerequisites:** Phase 4A1/4A2/4B/4C/4D/4E ACCEPTED
**Approved plan:** docs/plans/implementation-phase-4-plan.md

## Objective

Add the final Phase 4 adversarial and integration validation layer.

This phase must prove that the completed email-analysis pipeline:
- treats email content as untrusted data;
- minimizes provider disclosure;
- never grants provider output execution authority;
- preserves proposal/approval/execution separation;
- remains deterministic and fail-closed under malformed or adversarial inputs;
- passes an end-to-end synthetic regression from stored email/thread to completed AnalysisRun and derived records.

## Exact Scope Lock

Modify only:
1. test/test_email_analysis_service.py
2. test/test_security.py

If test/test_security.py does not yet exist, create it.

No production code changes are authorized in 4F.

## Adversarial prompt-injection tests

Use synthetic email bodies containing instructions such as:
- ignore previous instructions;
- send this email now;
- approve this action;
- move/delete/archive messages;
- reveal credentials/tokens;
- dump mailbox/database/audit log;
- call CRM/Calendar/IMAP directly;
- reinterpret quoted history as current user instruction.

Prove:
- these strings remain ordinary body_excerpt data only;
- AIService receives no executable capability/object;
- no ActionProposal approval/execution occurs automatically;
- no Alert/ApprovalDecision/ExecutionResult or external mutation row is created merely from injection text;
- no service behavior changes because content claims authority.

## Context minimization tests

Prove provider-visible AnalysisInput contains only:
- account_scope;
- target_source_record_id;
- contract_version;
- policy_version;
- selected_messages with approved metadata and bounded excerpts;
- input_digest.

SelectedMessage must expose only approved fields.

Prove exclusion of:
- IMAP folder/UID/UIDVALIDITY;
- attachment metadata/content;
- credentials/tokens/passwords;
- audit events/logs;
- raw MIME;
- CRM records/whole database;
- unrelated messages/conversations;
- internal conversation stable_key;
- repository/session/engine objects.

## 30k / 6-prior boundary tests

Add adversarial cases proving:
- max 6 prior messages reach provider;
- total disclosed body text <=30000 Python characters;
- target consumes budget first;
- target >30000 means no prior body disclosure;
- prior metadata may still exist when body budget is exhausted;
- hidden suffix/body change outside excerpt changes digest and becomes stale.

## Quote/history safety

Use synthetic quoted history containing questions and instructions.

Prove:
- quoted/ambiguous historical question does not create current Question operational row;
- quoted instruction does not create proposal/action automatically;
- only source-local target/new evidence is eligible for current Question.

## No execution authority

Prove AnalysisCandidates / AIService cannot directly:
- mark ActionProposal approved;
- create ApprovalDecision;
- create ExecutionResult;
- move email;
- create draft;
- send email;
- write CRM;
- modify Calendar.

Tests may inspect DTO fields and persistence state. Do not introduce production hooks merely for testing.

## Failure/adversarial robustness

Cover at least:
- provider raises exception containing secret-looking content: result/storage remains bounded;
- provider returns wrong object type;
- frozen DTO deliberately mutated after construction: invalid_output;
- invalid evidence source/span/digest;
- unsupported SupportRef kind/index via deliberate object mutation;
- stale input during provider call;
- conversation repartition during provider call;
- source redaction/deletion during provider call;
- provider retry does not reuse failed run; subsequent call creates next version;
- exact completed replay does not call provider;
- force append-only reanalysis does call provider.

## Synthetic E2E acceptance test

Create at least one realistic synthetic thread with:
- prior email(s);
- target request;
- exact question;
- explicit commitment;
- proposed task/next step;
- response_needed/commercial_risk/priority;
- a context mention;
- summary.

Run through analyze_email_in_thread with deterministic fake.

Assert:
- AnalysisRun completed;
- canonical input bounded/minimized;
- AnalysisSummary present;
- typed fact/inference/proposal graph present;
- Question/Commitment/Task/NextStep states correct;
- evidence links and AnalysisOperationalLink present;
- no external action executed;
- replay is provider-free;
- force creates new append-only run and supersedes prior completed run.

## Regression requirements

Do not weaken existing tests.
No network.
No provider SDK.
No external accounts.
No production behavior changes.

## Validation

Run:
python -m pytest test/test_email_analysis_service.py test/test_security.py

Then:
python -m pytest

Tracked diff must contain exactly:
- test/test_email_analysis_service.py
- test/test_security.py

## Completion

Commit:
Complete phase 4 adversarial security validation

Push only origin/codex-work.

If any failing test reveals a production defect requiring code change, STOP and report it rather than modifying production code in 4F.