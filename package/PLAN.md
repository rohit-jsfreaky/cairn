# PLAN — package/ (Phase 1, then Phase 5)

Finish lines are in `../MASTER-PLAN.md`. Do steps in order — each only depends on the ones
above it.

**Remember the product shape:** no brain in here on the main path. The engine exposes
operations; the caller (normally Claude Code via `mcp/`) does the thinking. Warm replay is
deterministic Python with zero model calls.

## Phase 1 — the engine (Sep 1–4)

### 1a. Memory store + models (Sep 1)
- `models.py`: `Locator` (kind: role|text|css|structural, value, hits, misses, last_ok),
  `Step` (intent, postcondition, locators, health), `Playbook` (domain, task, steps, version,
  health), `SiteKnowledge`, `RunMetrics` (duration, steps_replayed, steps_repaired, tool_calls).
- `store.py`: save/load playbook (WARM `("playbook", domain)`), save/load site knowledge,
  journal runs and repairs (COLD), `forget_site` (archive, never delete), `search_similar`
  (FTS5).
- Tests: round-trip in a FRESH process (subprocess). Doubles as the Phase 0 finish line.
- ✅ `pytest tests/test_store.py` passes, fresh-process test included.

### 1b. Demo site (Sep 1)
- `tests/demo_site/`: tiny FastAPI app, 3-4 pages (login → list → detail → action).
- `?variant=b`: renames and moves the main controls, changes one flow step. The "site changed
  its UI" switch — used by tests AND by the live demo video.
- ✅ both variants run with one command.

### 1c. Browser + operations — the cold path (Sep 2)
- `browser.py`: launch, fresh context (never reuse — fresh session must be provably fresh),
  accessibility-tree snapshot (small and clean, not raw HTML).
- `operations.py`: the verbs a caller drives — `look()` (returns the page as a short element
  list), `act(target, action, value?)`, `verify(expectation)`. Every call records role, text,
  css and structural descriptors of what was touched, plus what changed after.
- ✅ driving these by hand from a Python REPL completes the demo-site task and produces a
  full raw trace. No model involved — you are the brain in this test.

### 1d. Distill — trace → playbook (Sep 2)
- `distill.py`: raw trace → `Step`s. Intent per step, postcondition derived from the observed
  change, 3-4 ranked locators each. Saved via `store.py`.
- ✅ after one cold run the playbook entity exists and reads clearly when printed.

### 1e. Executor — the warm path (Sep 3)
- `executor.py`: load playbook → per step: try locators in confidence order → act → check the
  postcondition → update hits/misses. Deterministic, zero model calls.
- Repair: postcondition fails or every locator misses → mark the step broken, and hand back a
  precise repair request (the caller re-explores that ONE step). Persist the fix, archive the
  dead locator, journal the drift.
- If >50% of steps break → declare the playbook stale, but KEEP site knowledge.
- ✅ demo site: warm run fast; switch to `?variant=b` → exactly one repair → fast again.

### 1f. CLI + metrics (Sep 3)
- `cli.py`: `cairn run "<task>" --site <url>` (warm replay), `cairn sites`, `cairn show
  <domain>`, `cairn forget --site <domain>`, `cairn export <domain>`.
- Metrics line at the end: duration, steps replayed, steps repaired, tool calls. Metrics go
  into the run journal — the frontend reads them later.
- ✅ full warm loop works from the terminal with no API key set anywhere.

### 1g. Real site + the gate test (Sep 4)
- Pick 1-2 real, captcha-free, stable sites (decide with Rohit). Prove the loop.
- `test_deletion_gate.py`: warm replay succeeds → `forget_site` → replay has nothing to follow
  and says so → assert the core function is gone. Runs with **no API key**, so a judge can run
  it in 10 seconds.
- ✅ Phase 1 finish line in MASTER-PLAN.md passes.

### 1h. OPTIONAL standalone brain — only if time is free
- `model.py`: OpenRouter HTTP call behind one small interface, so `cairn explore` can run
  without a host AI. Never imported by the warm path. Skip entirely if Phases 2-4 need the time.

## Phase 5 — Base x402 (Sep 8) — CUTTABLE, BLOCKED until Discord answers the testnet question

- Open the `x402` Python SDK docs (2.21.0) first, add findings to ../RESEARCH.md.
- Flow: agent B hits an unknown site → `search_similar` shows agent A knows it → pays via x402
  (Base Sepolia, public facilitator, Circle-faucet USDC) → imports the playbook → runs warm.
- Demo proof: the transaction visible on the Base Sepolia explorer, on camera.
