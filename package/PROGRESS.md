# PROGRESS — package/

> Working memory for this folder. Read first, update before ending every session.

## Current state — 2026-09-01

**PHASE 1 IS BUILT. 89 tests pass, ruff clean.**

I marked this phase done once before while three bullets of step 1e and 1f were missing.
That was wrong, and the correction is recorded here rather than quietly patched:

| was missing | plan step | state |
|---|---|---|
| stale rule: >50% broken -> relearn, keep site facts | 1e | **built** |
| archive/drop dead locators on repair | 1e | **built** (dropped, Rohit's call) |
| anything ever WRITING site facts | **no step existed** | **built** — `cairn_note` |
| `cairn run "<task>" --site <url>` took no task | 1f | **built** |
| metrics line missing repairs + tool calls | 1f | **built** |
| a real captcha-free site | 1g | **still open, needs Rohit** |

```
pytest        108 passed
ruff check    All checks passed
```

## The engine

```
src/cairn/
  models.py       Locator, Postcondition, Step, Playbook, SiteKnowledge, RunMetrics
  store.py        THE ONLY FILE THAT IMPORTS sibyl_memory_client
  browser.py      Playwright, always a fresh context; snapshot = short control list
  operations.py   look / act / verify — the cold-path verbs a host AI drives
  distill.py      trace -> playbook (postcondition per step, ranked locators)
  executor.py     warm replay, drift detection, repair requests. ZERO model calls.
  events.py       typed events; library never prints
  cli.py          run / sites / show / forget / export
```

## Finish line, checked honestly

| # | criterion | state |
|---|---|---|
| 1 | cold run completes the task, playbook appears in memory | PASS — 6 steps, 9 tool calls |
| 2 | warm replay in a fresh process, no model involved | PASS on calls, see note on speed |
| 3 | break the site, one step repaired, next run fast again | PASS |
| 4 | `cairn forget` leaves nothing to follow | PASS — `test_deletion_gate.py`, 7 tests |

### The speed number needs re-reading (2026-09-01)

Measured on the local demo site:

```
cold   1852 ms   9 tool calls   6 pages read
warm    803 ms   1 tool call    0 pages read
       2.3x faster,  9x fewer calls,  0 model calls
```

`MASTER-PLAN.md` asks for **>=5x faster**. Wall-clock is **2.3x**, and it is important to
understand why rather than to tune the benchmark until it looks better:

- Both runs perform the same six browser actions and the same page loads. Replay cannot be
  much faster at that part, and never will be.
- The cold run's extra cost is three `look()` calls plus text diffing — milliseconds.
- **The benchmark has no model in it.** Our scripted `cold_run` decides instantly. A real
  host AI reads each snapshot and thinks, which is seconds per step. That thinking time is
  the entire cost Cairn removes, and this measurement contains none of it.

So on a local site with an instant brain, 2.3x is the honest ceiling. The real multiplier
only appears once a real model is in the loop, which happens in Phase 2 through `mcp/`.

**Do not put a wall-clock speed claim anywhere public until it is measured with a real
host AI driving the cold run.** The durable, defensible numbers today are the ones that do
not depend on model speed: **9 tool calls -> 1**, **6 page reads -> 0**, **model calls -> 0**.

Rohit needs to decide whether Phase 1 counts as closed on that basis. Flagged, not assumed.

## Decisions made here

- **Locator confidence is a score.** `hits - 2*misses`, normalised; unproven starts at 0.5
  so a fresh guess never outranks a proven one. A miss costs double a hit.
- **A step's health is its BEST locator**, not the average. One working route is enough.
- **Locators are tried most-durable-first and replay stops at the first hit.** A cosmetic
  redesign therefore costs literally nothing — not even a wasted attempt. Cairn never finds
  out the CSS id died, and should not: probing locators it does not need would spend time
  learning something it has no use for.
- **Passwords are never written to memory.** Found while preparing for a real site: the
  trail was storing `"value": "hunter2"` in plain text, so pointing Cairn at a real login
  would have put a real password into `~/.sibyl-memory/memory.db`. Now a step stores
  `secret: "password"` with no value, and replay resolves it from an environment variable
  or `~/.cairn/secrets.json`, failing loudly if it is missing. `look()` reports a password
  box as `(filled)`, never its contents.
- **`look()` returns field values and a bounded slice of page text.** It used to return
  controls only, which meant Cairn could click but never read — no invoice amount, no
  error message, and no way to see that a login was already filled in. Text is capped at
  1200 characters, which is still a hundredth of a raw page.
- **Site facts are written by the host AI, not guessed by code.** An earlier plan was to
  infer them from the trace (a password field means "needs a login"). That would have
  covered maybe a fifth of what matters and quietly missed the rest: "locks you out after
  five wrong passwords", "the invoice only appears after the 3rd", "use the finance login".
  Those never appear as a step. Rohit rejected the inference version as a partial fix, and
  he was right — `cairn_note` is the real feature.
- **Retiring is not forgetting.** A stale trail is archived while the site facts are kept
  and handed back, which is what makes relearning cheaper than a first visit. `forget`
  still wipes both — that is the gate.
- **Structural locators match the href PATH, not the whole href.** Real sites hang session
  ids and tracking parameters off links. Found by a failing test, not by guessing.
- **`forget_site` archives, never deletes.**
- **Three demo variants, not two.** `b` is a real break (href moves too, every locator
  misses, repair fires). `c` is cosmetic (href survives, no repair, no model). Two different
  events that both get called "the site changed".

## Deviations from package/CLAUDE.md, with reasons

- **dataclasses, not pydantic.** These bodies are written into Sibyl as JSON. Explicit
  `to_dict`/`from_dict` makes the stored shape a decision rather than a side effect of a
  library version. Shapes are still typed, so the "no loose dicts" rule holds.
- **argparse, not typer.** `mcp/` and `backend/` both import this package; the fewer
  dependencies it drags along, the easier `uvx cairn-mcp` is. argparse is stdlib.

## Environment

- venv at repo root: `.venv` (gitignored). Use `.venv/Scripts/python.exe`.
- `pip install -e "package[dev]"`, plus `ruff` and Chromium (`playwright install chromium`).
- Demo site: `python package/tests/demo_site/app.py` -> port 8787, variants a / b / c.

## Next action

**1g — one real, captcha-free website.** Everything is still proven against our own demo
site, which has clean HTML, stable ids, no JavaScript rendering and no cookie banner. That
is the biggest remaining gap between "demo" and "product".

## Known warnings

- `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`.
  Harmless; only act on it if the test client actually breaks.

## Session log

- **2026-08-31** — folder created, plan written. No code.
- **2026-09-01** — Phase 0 passed. Phase 1a (models, store, 12 tests). Phase 1b (demo site).
  Then the whole rest of Phase 1 in one pass: browser, operations, distill, executor, events,
  CLI, and the deletion gate. 72 tests, ruff clean. Two real bugs found by tests: the
  structural locator was matching whole hrefs including query strings, and variant B was not
  actually breaking anything. Measured cold vs warm and found the >=5x wall-clock target is
  not reachable without a model in the loop — flagged above rather than tuned around.
