# PROGRESS — package/

> Working memory for this folder. Read first, update before ending every session.

## Current state — 2026-08-31

- Phase 1 not started (build window opens Sep 1).
- Plan and structure locked in `PLAN.md` / `CLAUDE.md`.
- Nothing installed, no `pyproject.toml` yet.

## Done

(nothing yet)

## Next action

1a from PLAN.md — models + store + fresh-process round-trip test.

## Decisions made

- Recall path is deterministic replay; LLM only for explore + repair (demo metric depends on
  this — do not "simplify" it away).
- `forget` archives, never deletes (matches Sibyl doctrine, recoverable for the demo).
- Demo site lives in `tests/demo_site/` with the `?variant=b` break switch.

## Blockers

- Anthropic API key + budget not confirmed (needed from 1c onward).
- 2 real demo sites not chosen (needed by 1g).

## Session log

- **2026-08-31** — folder created, plan written. No code yet.
