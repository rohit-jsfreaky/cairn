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

### 1h. OPTIONAL standalone brain - only if time is free
- `model.py`: OpenRouter HTTP call behind one small interface, so `cairn explore` can run
  without a host AI. Never imported by the warm path. Skip entirely if Phases 2-4 need the time.

## Phase 2.5 - the browsing layer (Sep 2-3)

Finish line in `../MASTER-PLAN.md`. **Read `BROWSING.md` first** - it audits every Playwright
capability and records why each one is in or out. This section is only the order of work.

Two decisions were locked by Rohit on 2026-09-01 and are not open again:

- **One `cairn_act` tool with an `action` argument**, never sixteen MCP tools. Tool choice is
  the most fragile part of the system - a host AI already ignored Cairn once and used `curl`.
  Sixteen more names to choose between would make that worse, not better.
- **Dialogs record the choice AND the message.** On replay, if the message has changed, stop
  and ask. A step that recorded "click OK" must never blindly accept a box that now reads
  "delete 400 rows?".

### 2.5a. Snapshot on Playwright's engine (Sep 2)
- Delete `_COLLECT_JS`. Use `page.locator("body").aria_snapshot(mode="ai")`, which returns
  role, name, url and a `ref` for everything, pierces shadow DOM and reaches into iframes.
- Parse that into `Element`s. Act during exploring through `aria-ref=` selectors.
- **Stored locators stay durable** - refs live for one snapshot only and must never reach
  memory. This is what keeps the change contained.
- OK when: on the hard page, the dropdown, shadow-DOM button, iframe button and late link
  are all found and clickable.

### 2.5b. Actionability and waiting (Sep 2)
- Wait for `visible` (which also waits for stable), not `attached`. **This is a live bug** -
  today Cairn can click an element that is still animating in.
- `wait_for` verb: url | element | text | idle (`networkidle`). A React dashboard is blank
  until its data lands, and this is the single most likely reason a real site fails.
- Fix the viewport. A narrow window shows a hamburger menu instead of a nav bar, so a trail
  recorded at one size breaks at another.
- One place for default timeouts.
- OK when: a page that renders its content after a delay is handled with no fixed sleep.

### 2.5c. The full action set, behind one verb (Sep 2) - DONE 2026-09-01
- goto, click, double_click, hover, fill, type, clear, press, check, uncheck, select,
  upload, scroll_to, scroll, drag, focus, blur, back, reload, wait.
- `type` is real keystrokes - search and autocomplete boxes ignore `fill`.
- `select` must handle label, index and multi-select, not just value.
- Each action records what replay needs, and gets a sensible default postcondition.
- OK when: every action can be recorded, replayed and verified on the demo site.

### 2.5d. Reading (Sep 3) - DONE 2026-09-01
- `read(kind, target)`: text | all_text | value | checked | visible | enabled | attribute |
  count. Without this Cairn can click but never read, so "check my dashboard numbers" is
  impossible - which is half of why anyone would want this.
- New postcondition kinds: value_is, checked_is, element_gone, count_is, attribute_is.
- OK when: a number on a page can be read back, and a `fill` is verified by reading a value.

### 2.5e. More ways to find things (Sep 3)
- Add locator kinds: label, placeholder, test_id, title, alt, and nth/filtered-by-text.
- `test_id` first when present - test ids almost never change, so it is the most durable
  locator available.
- Frame-aware durable locators: a stored locator inside an iframe must name the frame too.
- OK when: ten locator kinds mean a step has ten chances to survive a redesign, not four.

### 2.5f. Page events (Sep 3)
- **Dialogs** - handle, record the choice and the message, and stop on replay if the message
  changed. Playwright dismisses by default, which would silently cancel a save.
- **Popups / new tabs** - record which tab the trail continues in. Never guess.
- **File chooser** - folded into `upload`.
- **`add_locator_handler`** for overlays. A cookie banner learned once is stored in site
  knowledge and dismissed automatically forever after. This is Playwright's own answer to
  the classic killer of recorded flows.
- OK when: a confirm dialog and a cookie banner are both handled without a human.

### 2.5g. The MCP surface (Sep 3)
- Collapse `cairn_open` / `cairn_look` / `cairn_act` into **one `cairn_act`** with an
  `action` argument, plus `cairn_read`.
- Rewrite descriptions so the action list is discoverable from one tool.
- OK when: three vague prompts route to the right action.

### 2.5h. The hard page, kept forever (Sep 3)
- A permanent test page containing every hard thing: div dropdown, shadow DOM, iframe, late
  content, cookie banner, confirm dialog, popup, file input, infinite scroll.
- OK when: the Phase 2.5 finish line in MASTER-PLAN.md passes.

## Phase 5a - agent-to-agent memory (Sep 8) - NOT blocked

The coordination half of the 40% line. `search_similar` is already built and unused; Sibyl's
`tenant_id` is already noted in RESEARCH.md and never used.

- Two `CairnStore`s with different `tenant_id`s, sharing one database.
- Agent B, which has never seen a site, searches memory by task and domain, finds agent A's
  trail, imports it, and runs it.
- `cairn_borrow(site)` MCP tool: look for a trail somebody else left.
- Journal both sides - who left the trail, who followed it.
- OK when: agent B finishes a task on an unseen site in one call, zero model calls.

## Phase 5b - Base x402 (Sep 8) - CUTTABLE, BLOCKED until Discord answers the testnet question

- Open the `x402` Python SDK docs (2.21.0) first, add findings to ../RESEARCH.md.
- Flow: agent B hits an unknown site → `search_similar` shows agent A knows it → pays via x402
  (Base Sepolia, public facilitator, Circle-faucet USDC) → imports the playbook → runs warm.
- Demo proof: the transaction visible on the Base Sepolia explorer, on camera.
