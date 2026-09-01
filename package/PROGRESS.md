# PROGRESS — package/

> Working memory for this folder. Read first, update before ending every session.

## Current state — 2026-09-01

- **Phase 0 PASSED.** Sibyl memory round-trips across a genuinely separate process on
  Windows. See `../RESEARCH.md` for the verified API and the corrected version numbers.
- **Phase 1a DONE.** `models.py`, `store.py` and `tests/test_store.py` exist.
  `pytest` → **12 passed**.
- Next: 1b, the local demo site.

## Environment

- venv at the repo root: `.venv` (gitignored). Run things with `.venv/Scripts/python.exe`.
- `pip install -e "package[dev]"` — editable, so `import cairn` works anywhere.
- Chromium for Playwright is NOT installed yet. Needed before 1c:
  `.venv/Scripts/playwright.exe install chromium`

## Done

- [x] `pyproject.toml` — hatchling, src layout. Note: hatchling refuses `readme`/`license`
      paths outside the package folder, so it uses the SPDX string `license = "MIT"` rather
      than pointing at the root LICENSE.
- [x] `models.py` — `Locator`, `Postcondition`, `Step`, `Playbook`, `SiteKnowledge`,
      `RunMetrics`. Plain dataclasses with explicit `to_dict`/`from_dict`, because these
      bodies are written into Sibyl as JSON and the stored shape should be a decision, not
      a side effect of a library.
- [x] `store.py` — **the only file in the whole project that imports
      `sibyl_memory_client`.** That is the judges' 2-minute rule.
- [x] `tests/test_store.py` — 12 tests, including two that spawn a real second interpreter.

## Decisions made here

- **Locator confidence is a score, not a boolean.** `hits - 2*misses`, normalised. A miss
  counts double, so one failure outweighs one success. Unproven locators start at 0.5, not
  1.0, so a brand new guess never outranks something with a track record.
- **A step's health is its best locator.** If any single way of finding the element still
  works, the step is fine. That is what lets a CSS change survive when the role name holds.
- **`forget_site` archives, never deletes.** Matches Sibyl's forgetting-vs-deleting
  doctrine: replay can no longer follow the trail, but the record it existed survives.
- **Tests never touch the real memory.** Every test gets its own `tmp_path` database.
  The developer's `~/.sibyl-memory/memory.db` is off limits to the suite.

## Next action

**1b — the demo site.** A tiny FastAPI app in `tests/demo_site/`, 3-4 pages
(login → list → detail → action), with `?variant=b` moving the main control. That switch is
used by the repair tests AND by the demo video, so it needs to exist before 1c and 1e.

## Blockers

None.

## Session log

- **2026-08-31** — folder created, plan written. No code.
- **2026-09-01** — venv + Sibyl installed, Phase 0 finish line passed, Phase 1a built and
  green (12 tests). Corrected the Sibyl version numbers in RESEARCH.md; the ones recorded
  from PyPI on 08-31 were already stale.
