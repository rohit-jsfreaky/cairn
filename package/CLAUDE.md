# CLAUDE.md — package/ (the Cairn engine)

The brain. A Python package: the agent, the memory logic, the CLI, the tests.
Everything else in this repo is a thin layer over this package.

Read `PLAN.md` for what to build and `PROGRESS.md` for where we are. Update PROGRESS.md
before ending every session. Root rules in `../CLAUDE.md` apply here too.

## Stack (versions verified in ../RESEARCH.md)

Python 3.11+ · playwright 1.62 · sibyl-memory-client 0.7.0 · pydantic v2 · typer (CLI) ·
pytest · ruff (format + lint). Nothing else without a reason written in PROGRESS.md.
No model SDK is a required dependency — OpenRouter (optional) is a plain HTTP call.

## Structure (keep it exactly this flat — judges must read it in minutes)

```
package/
  pyproject.toml
  src/cairn/
    __init__.py
    store.py       # ALL Sibyl Memory calls. The ONLY file that imports sibyl_memory_client.
    models.py      # Playbook, Step, Locator, SiteKnowledge, RunMetrics — pydantic models
    browser.py     # Playwright session helpers (launch, fresh context, teardown)
    operations.py  # the verbs the caller drives: look, act, verify. Returns small clean views.
    distill.py     # raw trace -> Playbook (intents, postconditions, ranked locators)
    executor.py    # warm path: replay playbook, verify postconditions, repair broken steps
    model.py       # OPTIONAL standalone brain. OpenRouter ONLY. Never imported by the warm path.
    events.py      # typed events (StepStarted, MemoryWrite, MemoryRead, DriftDetected...)
    payments.py    # ALL x402 calls. The ONLY file that imports x402 / web3 / eth_account.
    shop.py        # the HTTP shop: catalogue free, trail behind a 402. No x402 imports.
    cli.py         # cairn run / forget / sites / export / share / borrow / sell / buy
  tests/
    test_store.py
    test_models.py
    test_deletion_gate.py   # THE judges' litmus test, automated
    demo_site/              # tiny local site; ?variant=b renames/moves controls (the "break it" switch)
```

## Hard boundaries (these ARE the architecture)

1. **`store.py` is the only file that touches Sibyl.** Judge finds every memory read/write in
   one file. Every public function there gets a one-line docstring saying which tier and why.
2. **NO brain inside the engine on the main path.** The engine exposes operations (look, act,
   verify); the caller does the thinking — normally the user's Claude Code via `mcp/`.
   `model.py` is an OPTIONAL standalone mode, **OpenRouter only** (never Anthropic direct),
   and nothing on the warm path may import it. Cairn must run fully with no API key at all.
3. **The warm path uses ZERO model calls.** Replay + postcondition checks are plain
   deterministic Python. This is the demo metric: run 1 = many tool calls, run 2 = one.
4. **Every step has a postcondition.** No postcondition, no step. A playbook that cannot
   verify itself is a stale cache — the exact thing we are not building.
5. Events out, never prints. Everything the agent does emits a typed event from `events.py`.
   The CLI renders them; the backend streams them. No `print()` in library code.
6. **`payments.py` is the only file that touches x402.** Same reasoning as `store.py`: a
   judge checking the onchain action finds all of it in one file. Nothing else imports
   `x402`, `web3` or `eth_account` — `shop.py` included, which is why `payments.gate()`
   exists. Enforced by a test that walks the source. And nothing on the warm path may
   import `payments` or `shop`: replay stays offline, deterministic and free.

## Clean code rules

- Type hints everywhere. `ruff check` and `ruff format` clean before ending a session.
- Small functions, one job each. If a function needs a comment to explain its middle, split it.
- Pydantic models for every data shape that crosses a file boundary. No loose dicts.
- No bare `except:`. Catch the specific error, handle it or re-raise with context.
- No magic numbers — constants with names at the top of the file.
- No dead code, no commented-out blocks, no TODO left behind at session end: do it or log it
  in PROGRESS.md.
- Tests are not optional here: `store.py`, `distill.py`, and the deletion gate must have tests.
- Secrets only from environment variables (`.env` is git-ignored; `.env.example` is committed).

## Definition of done for any task in this folder

Code written + ruff clean + tests pass + PROGRESS.md updated. All four, or it is not done.
