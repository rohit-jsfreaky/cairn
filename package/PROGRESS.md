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

**Phase 2.5 - the browsing layer.** Read `BROWSING.md` first, then `PLAN.md` section 2.5.

The short version of why: our page snapshot is hand-written JavaScript that finds a fixed
list of tags. On a page with a React-style dropdown, a shadow DOM, an iframe and a
late-loading link it found 1 element. `page.locator("body").aria_snapshot(mode="ai")` found
7, with a working handle for every one - including inside the iframe. About 60 lines of my
JavaScript get deleted.

Three things in that audit I did not know about and should have:

- **`add_locator_handler`** - Playwright's built-in answer to overlays that appear at random
  moments (cookie banners, "rate us" pop-ups). Register once and it clears them automatically
  whenever one blocks an action. This is the classic killer of recorded flows.
- **We wait for the wrong thing.** `attached` means the element exists. `visible` also waits
  for it to stop moving. On any animated site we can click something mid-flight. Live bug.
- **Six more locator kinds**, especially `test_id`, which almost never changes. Ten ways to
  find an element instead of four is the cheapest reliability available.

### 2.5c is DONE (2026-09-01) — the action set

`actions.py` is a registry of **27 actions**, not a chain of `if` statements. Each entry
carries what it needs, what its value means, how it is verified, and whether it is worth
recording at all. `catalogue()` generates the tool description from that registry, so the
list an AI reads can never drift from the list that exists.

Wired into both paths: `operations.py` (cold) and `executor.py` (warm) now dispatch through
the same registry. 46 new tests, one per action, plus `test_every_action_is_exercised`
which fails if an action is added without a test.

**Five real bugs this turned up, all of which would have hit a real site:**

1. **`executor._do` had no `else`.** Warm replay silently did *nothing* for any action
   outside the four it knew. If the page already satisfied the postcondition, that silent
   no-op was recorded as a successful replay — a false pass, the worst kind.
2. **Only `click` and `press` waited for the page.** A `select` that triggered a navigation
   was never waited for, so the next snapshot could be read off the page being replaced.
   Now one `Browser.settle()` runs after every action.
3. **`select_option` was being given the JavaScript argument shape.** The list-of-dicts form
   is JS-only; Python takes `value=` / `label=` / `index=` as separate keyword arguments. So
   choosing an option by its visible label failed — and label is the durable way to record a
   dropdown choice, because sites change the hidden value far more often than the words.
4. **`mouse.wheel` returns before the scroll is applied.** Reading the position straight
   after a scroll gives the position from *before* it. On an infinite feed that means
   scrolling and then reading the same rows again, forever. Fixed by waiting two animation
   frames — which, unlike waiting for the position to change, is still correct at the bottom
   of a page where scrolling moves nothing.
5. **The wheel only moves what is under the pointer**, and the pointer starts in the corner.
   Now centred first.

Also done early, from 2.5b: **the viewport is fixed** at 1280x800. Layout depends on width —
below a breakpoint the nav collapses into a hamburger button — so a trail recorded at one
size was unreplayable at another.

**Deliberately not done:** `tap` needs a touch-enabled context, and touch is **off by
default**. Some sites serve a different mobile layout the moment they detect touch, which
would change what every other trail sees. It is an explicit `Browser(touch=True)` switch,
and `tap` without it gives a clear message instead of Playwright's raw `hasTouch` error.

### 2.5d is DONE (2026-09-01) — reading

`reads.py`, same registry shape as `actions.py`. **12 read kinds**: text, all_text, value,
checked, visible, enabled, editable, attribute, count, plus url, title and page_text.
40 tests in `tests/test_reads.py`.

Cairn could previously read page text and nothing else, so "check my dashboard numbers"
was impossible — half the reason anyone would want this tool.

**5 new postcondition kinds**: `value_is`, `checked_is`, `count_is`, `attribute_is`,
`element_gone`. `check_postcondition` now calls `reads.read` rather than talking to
Playwright itself, so a check and the read behind it share one code path and cannot
disagree. `Postcondition` gained an optional `target`; old playbooks still load, pinned by
a test.

Two judgement calls worth recording:

- **`editable` is its own read, not folded into `enabled`** as BROWSING.md first said. A
  read-only field is enabled but cannot be typed into. Reporting it as enabled would send a
  caller into a retry loop that can never succeed.
- **A read of something missing answers rather than crashing** where an honest empty answer
  exists: not visible, not ticked, count zero. A postcondition on a missing element fails,
  which is drift the caller repairs — not an error.

**One regression, caught by an existing test:** I added `settle()` to the warm path and
forgot the cold path, so downloads were flushed before the download event arrived and the
file was never written to disk. Fixed by settling after every action on both paths.

### 2.5e is DONE (2026-09-01) — finding things

Four locator kinds became **nine**: `test_id`, `structural`, `label`, `role`,
`placeholder`, `alt`, `title`, `text`, `css`. 34 tests in `tests/test_locators.py`.

Two design calls worth recording:

- **`nth` and `has_text` are refinements, not kinds.** "The third row" and "the row
  containing September" narrow *any* locator, so they are two optional fields on `Locator`
  that compose with all nine kinds — rather than two more kinds that would each only work
  one way. `first` is `nth=0`, `last` is `nth=-1`. They are only attached when an element
  actually has look-alikes, because an index is one more thing that can go stale.
- **Test ids do not go through `get_by_test_id`.** That method reads one globally
  configured attribute name, and real sites use five different ones. Cairn stores the
  attribute *name* with the value, so it matches whichever the site uses with no global
  setting. Still ranked first — a test id is written for machines and rarely touched.

**Two bugs, both caught by one test** — `test_every_locator_a_real_element_offers_actually_resolves`,
which walks every locator an element offers and demands it find that element:

1. **A form field was being given a `text` locator.** The field's name comes from the
   `<label>` beside it, so the text search found **the label, not the field**. Filling a
   label does nothing. That would have failed on the first login form we ever replayed.
2. **`alt` could resolve but was never captured** — the collector never looked at `<img>`.
   The kind existed and no real page could produce one. Images with non-empty alt are now
   collected; empty alt means decorative and is skipped.

A locator that is stored but never resolves is worse than none: it costs a failed attempt
on every replay, forever.

### 2.5b and 2.5f are DONE (2026-09-01) — waiting, and page events

`waits.py`: five real waits — `element`, `gone`, `text`, `url`, `idle` — reached through
one `wait_for` action written as `kind:subject`. None of them is a sleep. The one real
sleep, `wait`, now says in its own description that it is a last resort.

**The `attached` bug was real and is fixed.** `resolve` waited for `attached`, which is
true the moment an element exists — including while it is still animating in and cannot be
clicked. Now `visible`, which also waits for it to stop moving.

Page events, all four plus overlays:

- **Dialogs.** Answered, never ignored — an unanswered `confirm()` stops the browser dead.
  Accept is the default because Playwright's default, dismiss, silently cancels saves. Both
  the wording and the choice are recorded, and replay **stops** if a step that answered
  "Save changes?" meets "Delete 400 rows?".
- **Tabs.** A new tab is noticed and listed, never switched to automatically. `switch_tab`
  is marked `session_handled` in the registry, because it needs Cairn's own tab list and
  `actions.perform` deliberately only knows Playwright.
- **File choosers.** Folded into `upload`. If the target is a real file input it is
  attached to directly; otherwise clicking it opens the chooser, which is caught. Many
  sites hide the input behind a styled button, so one verb has to cover both.
- **Overlays.** `dismiss_when_seen` uses Playwright's `add_locator_handler`, and
  `SiteKnowledge.overlays` remembers them. Registered against the **site**, not the step: a
  cookie banner appears whenever the site feels like it, so pinning it to a step would be
  recording an accident. This is the classic killer of recorded flows.

**One bug I introduced, caught by an existing test:** the download listener was being
attached twice when a tab was seen again, so the same file was queued twice and saving an
already-saved download fails — the file silently never reached disk. Listeners are now
attached once per page.

### Section 5 is DONE (2026-09-01) — the browser context

Four things, 16 tests in `tests/test_context.py`:

- **Permissions are denied by default.** A site asking for notifications puts a prompt over
  the page, and that prompt blocks everything behind it. There is nobody there to answer
  it. `Browser(permissions=[...])` grants one when a site genuinely needs it.
- **Geolocation.** `Browser(geolocation=(lat, lon))`. Passing one grants the geolocation
  permission automatically, because granting it *without* a position makes a site wait
  forever for a fix that never comes. Chrome only hands out a position on a secure origin —
  `about:blank` is not one, which is why the test asks from the demo server.
- **`new_tab`.** A tab we asked for, unlike one the site opened, so switching to it is not a
  guess. It gets the same dialog and download listeners as any other tab.
- **One timeout.** `Browser(timeout_ms=...)` and `set_timeout()`, applied to the context so
  every Playwright call inherits it. Default 15s rather than Playwright's 30s, so a broken
  site surfaces sooner instead of hanging an agent for half a minute per step.

Cookies and storage stay out: keeping a whole browser profile already covers them, and does
it better than replaying a saved blob.

### 2.5a is DONE (2026-09-01) — the snapshot

`_COLLECT_JS` is deleted. `snapshot.py` parses Playwright's own
`aria_snapshot(mode="ai")`. 36 tests in `tests/test_snapshot.py`.

**Measured on the hard page: the old collector found 1 element, this finds 8** — shadow
DOM, iframe contents, a `div` acting as a button, a `div` with a widget role, and content
that loaded late. All eight are clickable.

The `[cursor=pointer]` flag is the quiet win. A `div` with a click handler has no
interactive role at all, and that is the shape most component libraries produce.

**Frames are now named in the locator**, which closes the open question from 2.5e. A ref
reaches into a frame by itself, but a *stored* locator cannot — `page.locator` does not
look inside iframes. `Locator.frame` holds the iframe's own selector and resolution goes
through `page.frame_locator`. A test strips the frame off a working locator and proves it
then finds nothing, so the field cannot rot into decoration.

**Descriptors are read on demand**, not for every element on every look. That would be a
round trip per element and most are never touched.

### The security problem this uncovered

**Playwright's AI snapshot prints every field's contents in plain text, passwords
included:** `textbox "Password" [ref=e3]: hunter2`. Looking at a page would have carried
the password out of the browser and into the trace.

Cairn now keeps only the fact that a field is filled and throws the contents away — one
rule for every field, so there is no exception to remember. `read(value)` gets the real
text when a caller actually wants it, and `describe` reads values in the page where it can
see `type=password` and redact.

The existing test `test_look_never_reports_what_is_in_a_password_box` caught this. It was
written for the old collector and it held the line through a full rewrite of the layer
underneath it — the best argument yet for testing behaviour rather than implementation.

## Next action

**2.5g — the MCP surface**, then 2.5h the hard page kept forever., then 2.5b (waiting), 2.5d (reading), 2.5e (locators), 2.5f (events),
2.5g (the MCP surface), 2.5h (the hard page).

Note the order: the action layer landed first because it is the part that does not depend on
how elements are found. `actions.py` never resolves an element — it is handed a locator. A
test (`test_actions_never_search_for_elements`) pins that, so swapping the snapshot
underneath it cannot quietly turn into a rewrite of the actions.

## Known warnings

**1g — one real, captcha-free website.** Everything is still proven against our own demo
site, which has clean HTML, stable ids, no JavaScript rendering and no cookie banner. That
is the biggest remaining gap between "demo" and "product".

- `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated`.
  Harmless; only act on it if the test client actually breaks.

## Session log

- **2026-08-31** — folder created, plan written. No code.
- **2026-09-01 (later)** — Phase 2.5a: the snapshot moved onto Playwright's engine, the
  hand-written collector deleted, frames named in locators. 1 element -> 8 on the hard
  page. Found that Playwright's snapshot leaks password values, and stopped it.
  36 tests. 314 engine + 36 MCP pass.
- **2026-09-01 (later)** — BROWSING.md section 5: permissions, geolocation, new_tab,
  one timeout. 16 tests. 278 engine + 36 MCP pass.
- **2026-09-01 (later)** — Phases 2.5b + 2.5f: five real waits, the attached→visible
  fix, dialogs, tabs, overlays, file choosers. 34 tests. 262 engine + 36 MCP pass.
- **2026-09-01 (later)** — Phase 2.5e: nine locator kinds plus nth/has_text
  refinements, 34 tests. 228 engine + 36 MCP pass. Two bugs found by the test that
  demands every stored locator actually resolve to its own element.
- **2026-09-01 (later)** — Phase 2.5d: 12 read kinds and 5 postcondition kinds,
  40 tests. 194 engine + 36 MCP pass. Found that adding `settle()` to only one of
  the two paths broke downloads on the other.
- **2026-09-01 (later)** — Phase 2.5c: the 27-action registry, wired into both the cold
  and warm paths. 46 new tests; 154 engine + 36 MCP pass. Five real bugs found, listed
  above — the worst being that warm replay silently no-opped unknown actions and could
  report that as success.
- **2026-09-01** — Phase 0 passed. Phase 1a (models, store, 12 tests). Phase 1b (demo site).
  Then the whole rest of Phase 1 in one pass: browser, operations, distill, executor, events,
  CLI, and the deletion gate. 72 tests, ruff clean. Two real bugs found by tests: the
  structural locator was matching whole hrefs including query strings, and variant B was not
  actually breaking anything. Measured cold vs warm and found the >=5x wall-clock target is
  not reachable without a model in the loop — flagged above rather than tuned around.
