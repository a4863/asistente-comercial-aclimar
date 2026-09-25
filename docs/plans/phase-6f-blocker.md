# Phase 6F Blocker — Runtime AI Configuration Not Reachable by Smoke CLI

**Status:** BLOCKED / NOT EXECUTED
**Date:** 2026-09-25

## Observed result

No live provider call was made.

The operator stopped before execution because the smoke CLI loaded AI configuration with `enabled=False`.

Reported evidence:
- command executed: none;
- provider calls: zero;
- commercial gate: not enabled;
- tracked working tree: clean.

## Root cause confirmed in code

`app/integrations/ai_smoke_cli.py` calls `load_settings()` without a path.

Current `app/config.py` implements:

- `load_settings(path: Path | None = None)`;
- when `path is None`, configuration data is an empty dictionary;
- therefore default `AISettings(enabled=False, base_url=None, ...)` is returned;
- TOML is only parsed when a caller passes an explicit path.

The smoke CLI currently exposes no config-file argument or other approved non-secret runtime configuration source.

As a result, the accepted smoke path cannot become technically enabled through the current CLI contract without a code/composition change.

## Security interpretation

This is fail-closed behavior.

Do not:
- enable the commercial gate;
- inject configuration through environment variables;
- edit provider code ad hoc;
- call OpenAI directly from Python;
- bypass the CLI;
- retry the live smoke.

## Phase 6F status

**NOT ACCEPTED / NOT EXECUTED.**

D18's one-live-call authorization was not consumed because no live invocation occurred.

A corrected runtime configuration-loading contract must be analyzed, planned and implemented offline before a new execution task is issued.
