# Phase 6G — Commercial Processing and Activation UX Decision

**Status:** APPROVED DECISION
**Date:** 2026-09-29

## Processing mode

The user explicitly selected **Global processing** for real commercial data and stated:

> Acepto el procesamiento Global de datos comerciales reales mediante OpenAI para este asistente.

This satisfies the explicit processing-mode decision required by the approved Phase 6G boundary.

This decision:
- authorizes planning and implementation of the commercial activation path for Global processing;
- does NOT itself enable the runtime commercial gate;
- does NOT authorize an immediate commercial provider call;
- does NOT authorize background/scheduled commercial analysis;
- does NOT change minimization, evidence, provenance, security or approval rules.

## Activation UX

The user selected:

**Protected localhost UI control**

Rejected for this phase:
- CLI-to-worker IPC;
- startup/environment authorization;
- debugger/import/manual Python mutation.

## Runtime invariants

The commercial gate must remain:
- process-local;
- OFF on every process start/restart;
- explicitly enabled by the local operator;
- explicitly revocable;
- visible through bounded local status;
- protected by existing session, CSRF, Origin and Host controls;
- available only while the operational worker owns the exclusive lock and is ready;
- incapable of being enabled by email content, model output, provider content or an analysis request.

No persistent authorization state is permitted.

## Commercial call boundary

A first real commercial analysis still requires a separate one-shot rollout authorization after:
- the UI control is implemented;
- offline tests pass;
- the implementation is reviewed and accepted;
- operational preflight confirms correct build, lock, readiness, credential presence and Global endpoint/config state.

Commercial gate remains OFF now.
