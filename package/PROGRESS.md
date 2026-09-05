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

### The escape hatch is DONE (2026-09-02)

Rohit asked for full Playwright parity — all 177 methods as named actions — because we
cannot predict what a real site will need. He was right about the risk and had already been
proved right twice.

What we built instead, with his agreement: **one `evaluate`, plus the three gaps a hatch
cannot cover.** 21 tests in `tests/test_escape_hatch.py`.

- **`evaluate`** — any JavaScript, on the page or on one element. `recordable=False`, and
  the description says so in capitals, because a step made of code cannot be repaired:
  repair works by finding an element again, and a blob has no element.
- **`read(console_errors)` and `read(failed_requests)`** — collected as they happen, capped
  at 50. A dashboard that stays empty is usually one failed request, not a missing element.
  Ordinary `console.log` chatter is dropped; only errors and warnings are kept.
- **`set_time`** — a trail recorded in September reads the wrong month in October, and
  nothing about that looks like a broken step.
- **`screenshot`** — for showing a human. Never a step.

`actions.perform` now returns a value, so `evaluate` and `screenshot` can answer something.
Everything else still answers None.

**Correcting myself:** my old reason for excluding `evaluate` was that it let an AI run
arbitrary code. That was weak — the host AI already has shell access and could write its
own Playwright script. The real reason is repairability, and not recording it solves that.

**Full parity is deferred, not dropped** — Phase 7 in MASTER-PLAN.md. The rule for
promoting one of the 94 to a real action: a real website needed it. Not a guess.

### Phase 1g started — GitHub, the first real site (2026-09-02)

Driven by a clean Claude Code session in `D:\my_projects\cairn-test`, with no knowledge of
this project. Full write-up in `cairn-test/FINDINGS.md`.

**What held up:** `cairn_run` was called first — no curl, no WebFetch. The snapshot handled
GitHub completely, including a frame nobody expected (every ref on the second repo was
`f1e...`). `cairn_note` immediately caught something no locator could: the issues tab badge
is a cached count and disagrees with the live filter.

**Six bugs, four of which could not have been found on a page we wrote ourselves:**

1. **P0 — the trail could not produce the answer.** `cairn_save` stored one step: the
   `goto`. The number came from a read, and reads were never recorded. So a saved trail
   walked to a page and stopped, and the host AI had to work the answer out again every
   time — which is the entire cost this project exists to remove. Reads can now be
   remembered as steps, and `cairn_run` returns `answers`.
2. **P0 — one trail per domain.** `save_playbook` keyed on the domain alone, so
   `github.com` could hold exactly one task ever. Now keyed `domain::task-slug`.
   `forget_site` clears every trail on the site, or the gate would only half hold.
3. **P1 — a false "the site was rebuilt", which deleted the trail.** One broken step out of
   one is 100%, so any failure on a short trail retired it. There is now a floor: below
   three steps a trail is repaired, never retired. Repair is recoverable; retiring is not.
4. **P1 — link targets came back wrapped in quotes.** Playwright writes
   `- /url: "#start-of-content"`. We kept the quotes, so `href_path` returned `"`. The
   `structural` locator is our second most durable kind and it was silently useless on
   every GitHub link.
5. **Found while fixing 2** — `cairn_sites` called `load_playbook(domain)`, which now
   returns nothing when a site has several trails. Every multi-task site would have
   vanished from the listing.
6. **Found while fixing 1** — a page-level read (`title`, `url`) names no element, so it
   has no locators, and replay could not run it at all.

**A test that asserted the bug.** `test_one_site_cannot_hold_two_conflicting_trails`
checked that saving a second task *overwrites the first*. It passed for two days. It was
written when one-trail-per-domain looked like a design choice, and GitHub proved it was a
defect. Now `test_one_site_can_hold_several_trails`.

**Still to do in 1g:** PostHog (needs Rohit to sign in once, then the Google/SSO and
React-dashboard path is proven), and the three-run measurement — cold, warm, and warm after
`cairn_forget`.

### The warm path is proven on a real website (2026-09-02)

```
cairn_run(site="github.com", task="count open issues on elysiajs/elysia-openapi")
  ok  known  2 steps  1391 ms  model_calls: 0  pages_read: 0
  answers: {"number of open issues shown on the Issues tab": "Issues\n117"}
```

One call, 1.4 seconds, no model, and the answer came back by itself — on a site nobody
here controls. Health read 1.0 for a trail that had run and 0.5 for one saved but not yet
replayed, which is exactly right.

**Two more bugs, both from that run:**

- **A remembered trail was reported as an unknown site**, so the host AI re-explored and
  saved over it. Two faults: a task had to be worded *identically* to match, and "which of
  these trails?" was reported as "never seen this site". Now matched on meaningful words,
  and `NeedsTask` reports `known: true` with the list.
- **Found by a test while fixing that:** with one trail on a site it was returned for *any*
  request. "Cancel my subscription" would have run "count open issues".

**Three tests so far have turned out to be asserting a bug** — one trail per domain, zero
health for a locator-less step, and now the single-trail shortcut. Tests protect against
regressions. Only a real site protects against being wrong about the design.

### PostHog: the sign-in works, and a dashboard number is reachable (2026-09-02)

**Google accepted the window.** Playwright's bundled Chromium sets `navigator.webdriver =
true` and launches with `--enable-automation`, and Google blocks OAuth on anything that
says so. In Cairn's login flow that claim was false — the person signs in themselves, in a
window they can see, and Cairn never touches the password. Now: real Chrome, automation
flags off, `HeadlessChrome` stripped from the user agent. Verified false in both modes.

**Then the real problem.** PostHog keeps its numbers in plain `div`s with no role, so the
snapshot correctly does not offer them as controls — and they have no `ref`. `ref` took
only refs, so the AI fell back to `page_text` and the saved answer became **the whole
page**: five thousand characters with `22` somewhere inside. Every warm run would hand that
back for a model to search. Dashboard numbers are the main use case, so this was fatal to
it.

`ref` now takes a CSS selector too. The AI tried exactly that, twice, unprompted — the
strongest evidence there is that it should have worked.

**The escape hatch paid for itself on its first real dashboard.** The AI used
`action="evaluate"` on its own to inspect the DOM when refs failed, and got the five metric
tiles out. Nobody predicted that page, and nobody had to.

**One flaky test fixed properly rather than retried:** the download flush ran before
`browser.text()`, and the download event could land during that read — queued, never saved,
but reported as done. Moved the flush to just before the trace entry. Five clean runs.

### PostHog: the AI built its own selector (2026-09-03)

After the wording change it stopped reaching for `page_text` and did this instead, which is
the whole design working together:

1. Saw the metric tiles had no `ref`.
2. Used **`evaluate`** — the escape hatch — to walk the DOM and find where the number lived.
3. Used it again to find the container holding only the Visitors tile.
4. Built `div.rounded.border.bg-surface-primary:has-text("Visitors") div.text-4xl`.
5. **Verified it matched exactly one element** before committing.
6. Remembered that read, so the answer is `"22"` — not five thousand characters.
7. Wrote a site note with the selector *and the reason not to use page_text*.

Nobody predicted that page. The escape hatch is what let it through, which was the whole
argument for building it rather than 94 named actions.

**BUG 16, found by checking rather than assuming:** `describe` overwrote the AI's selector
with a path computed from the page — `div > div > div:nth-of-type(2)`. Theirs is anchored
to meaning and survives a tile being added; ours does not. We were silently replacing the
good locator with the fragile one. Both are now kept, theirs ranked first.

**Deletion gate proven on a real logged-in site:** memory gone, full re-exploration forced,
and the login survived — it lives in the browser profile, not the trail.

### Phase 5a is DONE (2026-09-03) — agent-to-agent memory

One agent's trail, followed by another that has never opened the site. 557 tests pass
(479 engine + 78 MCP).

```
alice                                  bob  (has never seen the site)
────────────────────────────────       ──────────────────────────────────────
learns it, 12 calls, slow
cairn share acme.com
                                       cairn run --site acme.com
                                         -> unknown, but alice left a trail
                                       cairn borrow acme.com
                                       cairn run --site acme.com --task "..."
                                         -> one call, the answer, no model
```

**Identity is a Sibyl tenant.** `CAIRN_AGENT` or `--agent`. Unset means Sibyl's own default
tenant, which is where every trail learned before today already lives — so nothing had to
be migrated, and agent A in the demo is simply the agent that already knows things.

**Two clients, neither of which ever moves.** The first design switched one client's tenant
around each shared operation. That is unsafe here: the MCP server calls the store from the
browser thread AND from anyio worker threads, so a switch has a window in which another
thread's `save_playbook` lands in the shared tenant — publishing a private trail, silently,
with no error. There is now a client per tenant, built once, and a test that hammers it from
six threads.

**A trail carries the route, never the person.** Whatever was typed into a field leaves, and
the step is marked as needing a value using the same mechanism passwords already use — so
whoever follows it signs in as themselves. The account hint stays behind. Sharing reports
every note it published and every value it withheld, so nothing goes out unseen.

**The commons remembers what happened to it.** Borrows are counted, outcomes recorded, and
offers ranked by "worked for three agents, failed for none". That is what makes it storage
that changes because agents used it, rather than a file copy.

**A fix travels back.** `contribute_repair` merges a borrower's repaired locators into the
original offer and adds them to the contributors, without taking authorship. Agent A learned
it, agent B fixed it, agent C runs the fixed version, and none of them ever spoke.

### Three bugs this phase found before it could start

1. **`search_similar` had never worked.** It asked the result for `.entities` then
   `.results`; `search_entities` returns a `list` subclass with neither, so it returned `[]`
   for every input from the day it was written. Nothing called it, so nothing noticed — and
   both plan files named it as the centrepiece of this phase.
2. **Every listing silently truncated at 100.** Fine for one agent's own trails; not for a
   commons holding everybody's.
3. **A `value_is` check carries the typed value.** Redacting the step and leaving the check
   behind would have published the email twice over. Caught by a test, not by reading.

### The gate, still honest

- **The warm path never reads the commons.** Written into `executor.py`'s docstring and
  enforced by a test that greps the file, because if replay could fall back to a shared
  trail then `test_deletion_gate.py` would be proving nothing.
- **Forgetting leaves a tombstone.** Without it, a judge forgets a site and the very next
  message says "somebody else has it — borrow it", which reads as evasion. Cairn now refuses
  to volunteer it and says why. Asking again on purpose still works; walking the site again
  lifts it.
- **Forgetting cannot reach another agent's copy**, because Sibyl offers no way to enumerate
  tenants. That is a real isolation guarantee and it is now stated out loud rather than
  discovered.

### Said honestly

Replay is zero model calls. **The handoff is not free**: run (miss) -> borrow -> run is
three tool calls and two model turns, against roughly fifteen calls and a page read per turn
for exploring. A judge who counts will catch an overclaim.

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

### 2.5g is DONE (2026-09-01) — the MCP surface

`cairn_open` and `cairn_look` are gone. Exploring is now two verbs:

- **`cairn_act(intent, action, ref?, value?, to?)`** — all 31 actions, chosen by argument
- **`cairn_read(kind, ref?, attribute?)`** — `kind="page"` lists the controls (the default,
  because "what is on this page" is the first thing anyone wants), and the 12 read kinds
  answer questions about one element

12 tools became 11, but the number that matters is the exploring surface: four tools became
two. This is Rohit's locked decision from 2026-09-01, and the reason holds up — a host AI
already ignored Cairn once and reached for `curl`, and 29 tool names would have made that
worse.

**Both descriptions are generated** from `actions.ACTIONS` and `reads.READS`. A hand-kept
list drifts the first time an action is added, and an action a host AI cannot see may as
well not exist. Two tests walk the registries and fail if any name is missing from the
description.

**One thing the tests caught:** collapsing the tools lost a warning. The old `cairn_open`
description said it was only for sites that are *not known*; my replacement said "use this
for any website task" and nothing about calling `cairn_run` first. A host AI reading that
would explore a site whose task is already learned — which throws away the entire point of
the project. `test_the_cold_tools_say_they_are_only_for_unknown_sites` failed and the
wording is now pinned by two assertions.

56 MCP tests, up from 36.

### 2.5h is DONE (2026-09-01) — the hard page

`tests/demo_site/hard.py`, served at **`/hard`** on the demo site, so it is a real URL and
can be shown on camera. Nine things, each one chosen because it has broken a recorded flow
on a real site:

1. a dropdown built from `div`s, with no `<select>` anywhere
2. a button inside a shadow DOM
3. a button inside an iframe
4. content that only appears once the data arrives
5. a cookie banner covering the page at a moment nobody chose
6. a `confirm()` that stops the browser dead until answered
7. a link that opens a new tab
8. a file input hidden behind a styled button
9. a list that only grows as you scroll

19 tests, including one that walks all nine in a single journey with no fixed sleeps and no
model, and one that checks every step of that journey recorded a durable way to find its
element again — a journey that cannot be replayed is a demo, not a memory.

### Two bugs found by checking the finish line rather than assuming it

Both were features that looked finished and were not:

1. **`recordable=False` was declared and honoured nowhere.** `highlight` was being written
   into the trail. On replay it would draw a box for nobody, and then have its postcondition
   checked anyway — a step that can only fail.
2. **A learned overlay was never written to memory and never read back.** "Learned once,
   dismissed on every later run" was half built: the banner was cleared on the run that met
   it and covered the page again on every run after. Now `dismiss_when_seen` saves to
   `SiteKnowledge`, and the executor re-arms them before the trail starts.

Checking bug 2 turned up a third: **Playwright registers overlay handlers per page, not per
browser**, so a flow that continued in a new tab met the banner all over again having
already "learned" it. Every tab now inherits what the site is known for.

## PHASE 2.5 IS COMPLETE

All eight steps. **385 tests** (329 engine + 56 MCP), ruff clean.

The finish line in MASTER-PLAN.md, checked honestly — two of the five need a caveat:

- Item 2 says every action "records, replays and verifies". Recording and verifying are
  proven for all 31 actions and 12 reads. Warm replay goes through the same registry and is
  proven end to end on the demo site, but not every individual action has been replayed
  warm. Nothing suggests a gap; it is simply not claimed.
- Item 3 says "three vague prompts route to the right action". That needs a model, and this
  project has no API key by design. What is tested instead: every action name appears in the
  one tool description, generated from the registry so it cannot drift.

The other three pass outright.

## Next action

**Phase 1g — one or two real websites.** Everything is still proven against our own pages.
The hard page is deliberately nastier than the demo site, but it is still a page we wrote,
and that is the last remaining gap between "demo" and "product"., then 2.5b (waiting), 2.5d (reading), 2.5e (locators), 2.5f (events),
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
- **2026-09-03** — Phase 5a: agent-to-agent memory. Identity as a tenant, a commons,
  share/borrow/contribute, the tombstone, and the CLI a judge can drive. Found that
  `search_similar` had never worked, that listings truncated at 100, and that a `value_is`
  check republishes the value it was redacting. 479 engine + 78 MCP pass.
- **2026-09-02** — Phase 1g on GitHub, the first real site. Six bugs, two of them P0:
  a trail could not produce an answer, and a site could hold only one task. 368 engine +
  60 MCP pass. One existing test turned out to be asserting the bug.
- **2026-09-02** — The escape hatch: `evaluate` (never recorded), console and
  network diagnostics, `set_time`, `screenshot`. 21 tests; 354 engine + 56 MCP
  pass. Full Playwright parity deferred to Phase 7, not dropped.
- **2026-09-01 (later)** — Phase 2.5h + close-out: the hard page at /hard, nine
  obstacles, 19 tests. Checking finish-line item 5 found three bugs: `recordable`
  was never honoured, overlays were never saved or re-armed, and overlay handlers
  are per-page so new tabs missed them. Phase 2.5 complete, 385 tests.
- **2026-09-01 (later)** — Phase 2.5g: exploring collapsed to cairn_act + cairn_read,
  descriptions generated from the registries. 20 new MCP tests (56 total). The tests
  caught that the collapse had dropped the "call cairn_run first" warning.
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

- **2026-09-03 (the browser would not start — fixed)** — Chrome refused Cairn's saved
  profile outright: it launched, ran a healthy startup, and exited with no error in its own
  log. Real Chrome opened a *fresh* profile fine and the bundled Chromium opened *this*
  profile fine, so the fault was the pairing, not either half. Two things were wrong and
  both are fixed. First, `_open_profile` turned EVERY Playwright error into "the profile is
  already open" — the same catch-all mistake as the earlier silent sign-out, and it sent us
  hunting for a browser window that did not exist. It now reports what actually happened,
  names both possible causes, and quotes the browser. Second, the rule "never open the
  profile with the other browser, because Chromium cannot read a session Chrome wrote"
  turned out to be FALSE: measured on the real profile, Chromium opened it and PostHog was
  still signed in on the real dashboard. So the other browser is now a fallback rather than
  a refusal, and the swap is reported through `profile_note` instead of being silent.
  A dead browser is worth less than a working one plus an honest sentence.
  Two false leads worth remembering: a binary search over the 160 MB profile "found" a
  culprit file that a 5x repeat proved innocent (0/5 both ways), and all 22 zero-byte
  SQLite journals turned out to be normal, not leftovers.

- **2026-09-03 (Phase 5b — Base x402 — BUILT)** — a trail you can sell. The original plan
  assumed payment could be bolted onto the local commons; it could not, because x402 is
  defined by an HTTP 402 exchange and the commons is two Sibyl tenants in one local file with
  no network anywhere. So the phase grew an HTTP boundary: `cairn sell` serves this agent's
  shared trails, `cairn buy` (and the `cairn_buy` MCP tool) pays for one. That also closes a
  real gap — two agents could previously only share memory by sharing a database file.
  Design rules held to: browsing the catalogue is FREE and carries no steps or locators (it
  reuses `describe_offer`, a shape with none in it to leak); the trail is genuinely
  unreachable without a settled payment; **the trail never goes on chain**, only the payment
  does; and the local commons stays free, because charging your own second agent on your own
  laptop is theatre. All x402 lives in ONE file, `payments.py`, mirroring the `store.py` rule
  — `shop.py` goes through `payments.gate()` rather than importing the SDK, and a test walks
  the source to keep it that way.
  Borrowing and buying now share `_import_offer`, so a bought trail gets the same provenance,
  the same protection over a repaired trail and the same note merging. Two import paths would
  have drifted, and the paid one is the one nobody exercises by accident.
  **518 engine + 98 MCP tests, ruff clean.** Four new deletion-gate tests are the ones that
  matter: a bought trail can still be forgotten, the transaction cannot bring it back, the
  seller's shelf empties when the seller forgets, and the buyer keeps what it paid for when
  the seller forgets.
  Facts were read off the INSTALLED SDK, not its docs, which were wrong twice: `ResourceConfig`
  takes `payTo` (camelCase) while `PaymentOption` takes `pay_to`, and the ASGI middleware needs
  the async resource server. Also found: the middleware skips settlement on any 4xx, so a
  buyer who pays for a trail the shop does not have gets a 404 and an untouched wallet.
  No new `events.py` types: share and borrow do not emit any either, the cold journal is the
  record, and three event classes nothing subscribes to would be dead code.
  **Still needed from Rohit: a funded wallet.** Everything up to the signature is verified —
  a live shop answering a real `HTTP/1.1 402 Payment Required`, the challenge naming Base
  Sepolia and the real USDC contract `0x036CbD…F7e`, and a purchase attempt that reached the
  facilitator and failed only on funds.

- **2026-09-03 (Phase 5b FINISH LINE PASSED — a real payment on Base Sepolia)** — the whole
  chain works end to end against the real network. Alice shares a trail and opens a shop;
  Bob, with his own database and no memory at all, browses the catalogue for free, is refused
  with a genuine `402 Payment Required`, pays, and receives the route.
  **Transaction: `0xd7de79f7f9bd41491d1419bd87e64ce10b674570204c3b0f379ced3a23173e14`**
  (sepolia.basescan.org, block 46345013): **0.01 USDC from Bob's wallet to Alice's.** Two
  distinct addresses on purpose — the first attempt used one wallet for both sides and the
  transaction showed money going in a circle, which is a weak thing for a judge to click on.
  Bob's wallet holds **zero ETH**: in x402 the facilitator submits the transaction and pays
  the gas, and the buyer only signs an EIP-3009 authorisation.
  Then the gate, live: `cairn forget` on Bob leaves `cairn sites` empty and the playbook
  `None`, while the receipt with that transaction hash is still sitting in the cold journal.
  A receipt proves a purchase happened; it is not a copy of what was bought.
  One fix on the way: the CLI said "paid a fee" because the facilitator returns the settled
  amount blank more often than not. `payments.browse` now carries the shop's asking price
  down onto each listing, so both the CLI and `cairn_buy` can say **$0.01**.
  Test wallets live in `~/.cairn/wallet.env` and `~/.cairn/alice-shop.env`, outside the repo.
  They hold faucet money only and are worth nothing anywhere.
  **518 engine + 98 MCP tests, ruff clean.**

- **2026-09-04 (Phase 6 — hardening, part one)** — an audit before touching anything, then
  the fixes. Five real bugs, not tidying:
  1. **`steps_repaired` had never once been true.** `executor.py` hardcoded it to 0 and
     nothing incremented it, because a run cannot repair anything — it stops at the broken
     step and the fix arrives as a separate call. The CLI printed "0 repaired" after every
     run regardless, including runs of a trail that HAD been repaired, and `benchmark.py`
     faked its own repair count by hand to make the README table read right. Replaced with
     `trail_repairs`, which is the trail's real repair history, mentioned only when it is
     non-zero. Two tests now hold it in place.
  2. **Three blind `except Exception`** — including `except (PWTimeout, Exception)` in
     `resolve()`, where the second clause swallowed the first along with any real bug in
     `_to_playwright` and reported it as ordinary site drift. All narrowed to
     `PlaywrightError`, so only the browser's own failures count as drift and a fault of
     ours surfaces as itself. **`BLE` added to ruff's `select`** in both packages so this
     cannot come back — it had already caused two incidents here.
  3. **A machine with no browser was told its profile was broken** and invited to delete it.
     `_is_missing_browser` existed but was only consulted on the clean-mode path, and
     profile mode is the default. It now says `playwright install chromium` and explicitly
     that nothing is wrong with the profile.
  4. **The front door was Windows-only.** `.mcp.json` named `.venv/Scripts/cairn-mcp.exe`,
     and Claude Code reads that file the moment anyone opens the repo — so a judge on a Mac
     got a broken server before reading a word. Now it runs `mcp-server.py`, a launcher that
     finds the venv on either layout. The README shows both `claude mcp add` commands, and
     the demo site's busy-port help no longer prints `netstat`/`taskkill` to Linux users.
  5. **`mcp>=1.29.1` let a fresh install pick up mcp 2.x, where `FastMCP` was renamed to
     `MCPServer`.** The server raised ModuleNotFoundError on import and never started. This
     venv held 1.29.1 from an earlier install, so all 616 tests passed while a stranger's
     `pip install` was completely broken. **This is the one that would have hit every
     judge.** Found by building the wheels and installing them into a clean Python 3.11
     virtualenv. Pinned to `<2`; migrating to 2.x is post-deadline work.

  Also: the 47 payment tests are `importorskip`-gated, so the README's Development block now
  installs `[market]` first — otherwise "all tests passed" can be true while none of the
  Base code ran. CI does the same.

  **Packaging.** `cairn` and `cairn-mcp` are both taken on PyPI by unrelated projects, so
  the distributions are now **`cairn-browser`** and **`cairn-browser-mcp`**. Only the
  distribution names changed: the import package is still `cairn` and the commands are still
  `cairn` and `cairn-mcp`. Added readmes, classifiers and project URLs so the PyPI pages are
  not blank. All four artefacts pass `twine check`, and both wheels install and run from a
  clean Python 3.11 venv.

  **CI.** `.github/workflows/test.yml` installs from scratch on Ubuntu against Python 3.11
  and 3.13, runs both suites with `[market]`, and checks ruff. It cannot run until Rohit
  pushes. The lint commands were verified locally from the repo root first.

- **2026-09-04 (CI went red on the first push — found, reproduced and fixed)** — ruff passed,
  install passed, the browser installed; **the engine tests failed on both Python 3.11 and
  3.13.** GitHub would not hand over the logs (log download needs admin rights even on a
  public repo, and the annotations said only "Process completed with exit code 1"), so it was
  reproduced locally instead: **WSL Ubuntu, a fresh clone of the pushed commit, the exact CI
  steps.** It failed there in 55 seconds.

  The failure: `test_a_chrome_profile_stays_on_chrome` asserted `_channel == REAL_CHROME`
  flatly. **The product was right and the test was wrong.** A Linux runner has no real
  Chrome, so Cairn correctly fell back to bundled Chromium and reported the swap through
  `profile_note` — exactly the behaviour built yesterday. The test simply assumed Chrome
  exists everywhere, which is a Windows assumption.

  Rewritten to pin the rule that actually matters and holds on every platform: **a swap is
  never silent.** If Chrome opened the profile, there is nothing to report; if it could not,
  the fallback must say so. That tests more than the old assertion did.

  Both suites now pass on Linux — **521 engine + 98 MCP** — and Linux is markedly faster
  than Windows (4m22s against about 12 minutes), so CI will not be the slow part.

  Also bumped `actions/checkout` v4 -> v7 and `actions/setup-python` v5 -> v7; the old majors
  target Node 20, which GitHub now force-runs on Node 24 and warns about. Versions were read
  off the GitHub API rather than guessed.

  Worth recording plainly: **this is exactly what CI was added for.** 616 tests passed on
  Windows for days while one of them could not pass on Linux at all.

- **2026-09-04 (the second red CI run — a headed browser, and a driver leak behind it)** —
  the logs Rohit pasted named it immediately, which the API never would have:

      ERROR:ui/ozone/platform/x11/ozone_platform_x11.cc] Missing X server or $DISPLAY
      ERROR:ui/aura/env.cc:246] The platform failed to initialize.  Exiting.

  `test_the_login_window_is_not_flagged_either` opens a **headed** browser, because the
  sign-in window is the one a real person uses. A CI runner has no display. WSL never
  caught it because WSLg provides one — which is why two local reproductions passed while
  CI kept failing.

  **The second bug is the one that mattered.** `Browser.start()` called
  `sync_playwright().start()` and only cleaned the driver up for `ProfileUnavailable`. Any
  other failure left it running — and that driver owns an asyncio loop in the thread, so
  every LATER browser anywhere in the process died with "It looks like you are using
  Playwright Sync API inside the asyncio loop". One browser that could not open became
  **five failures and three errors**, none of which named a display. `start()` now opens
  inside a try and stops the driver on any failure, re-raising the real reason untouched.
  Three tests pin it, including the one that actually bit: a browser still starts fine
  after a failed one.

  The headed test now skips when there is no display and says so. xvfb would let it run on
  CI for real and is worth adding later; it was deliberately left out mid-deadline, because
  every extra moving part in that workflow has cost a red build and a push to discover.

  Verified under the exact CI condition — Linux, `DISPLAY` unset: **523 passed, 1 skipped**
  plus 98 MCP. Windows green too.

  The lesson worth keeping: **WSL is not a CI runner.** It has a display, twelve cores and
  a warm HOME. Two clean local runs proved nothing about a bare machine.

- **2026-09-04 (the three edge cases a real user actually hits)** — found by walking through
  a fresh install rather than the test suite. None of them exotic.

  1. **`cairn login` on a machine with no screen** — a server over SSH is the ordinary case,
     and it ended in a raw Playwright X server error. Now a `NoDisplay` error carrying a
     sentence a person can act on: run it on a desktop and copy `~/.cairn/browser-profile`
     across, or forward a display with `ssh -X`. Reported the same way in the CLI and the
     MCP tool, and `_why_refused` says it FIRST — otherwise the profile advice would have
     sent somebody deleting their sign-ins over a missing monitor.
  2. **A captcha was reported as a broken step.** `browser.captcha_on_page()` looks for the
     usual markers (reCAPTCHA, hCaptcha, Turnstile) and replay now returns `blocked=True`
     with an explanation instead of a repair request. Deliberately NOT `needs_repair`:
     there is nothing to repair, no AI can get past a human check, and calling it drift
     marked good locators dead for a page the trail never reached. The MCP tool tells the
     host AI to stop rather than try.
  3. **A slow site was quietly recorded as drift — the dangerous one.** It threw no error.
     Every locator missed because the page had not finished drawing, each miss was written
     down, health fell, and a "repair" would replace working locators with identical ones.
     `_replay_step` now makes ONE pass collecting misses without recording them; if nothing
     resolved at all it waits for the page to go quiet (`networkidle`, bounded at 5s) and
     looks once more. Only the pass that actually decides the step's fate is allowed to
     blame anything. The retry happens only when NOTHING resolved — if something resolved
     and the action or check failed, that is real, and repeating it could click twice.
     `settle()` was never enough here: it waits for `domcontentloaded`, which fires long
     before a JavaScript app has drawn anything.

  Five tests cover these, including one where a button appears after 2.2 seconds and the
  assertion is that its locator records **zero** misses.

  **Also: how the tests get run has changed.** Running the full Windows suite and a WSL suite
  at the same time was cooking Rohit's laptop. From here: one process at a time, targeted
  files locally, and the full 600-test sweep belongs to CI, which runs it on GitHub's
  machines on two Python versions for free.

- **2026-09-04 (item 3 — the real sites, re-walked, plus a genuinely hard new one)** — four
  trails now, all at health 1.0, every one replayed in 2 steps with **zero model calls**.

  **GitHub, both trails still hold.** `microsoft/playwright` came back **153** open issues
  against **117** on Sep 2 — the number moved, which is the proof that replay reads the live
  page rather than handing back a stored answer. `elysiajs/elysia-openapi` replayed in 1.3s.

  **PostHog, relearned.** Its trail had been wiped by an earlier deletion-gate demo. Signed
  in and working through the Chromium-owned profile, so yesterday's browser fallback kept the
  session exactly as it claimed. 2 steps, 2.3s.

  A mistake worth writing down: the first attempt remembered
  `[data-attr='web-analytics-dashboard']`, which is the ENTIRE dashboard — thousands of
  characters, precisely the anti-pattern `cairn_read`'s own description warns about. Caught
  it, used `restart_trail`, and narrowed to `> div:first-child`, which returns just the
  summary strip. The warning in that tool description earns its place.

  **Google Search Console — the hardest site tried so far, and it works.** 2 steps, 926ms,
  0 model calls, on a signed-in Google property.

  Two findings from it:

  - **Google did NOT block the Chromium-owned profile.** The sign-in went through by hand.
    That had been the open worry since the profile stopped being Chrome-owned.
  - **GSC offers nothing durable to hold on to.** No `data-*`, no ids, no aria-labels on the
    numbers — only obfuscated class names like `.qL2dyd` that change on every Google deploy.
    So this trail WILL break, and that is not a flaw to hide: Cairn will detect the drift,
    stop at that one step and ask for a one-step repair. It is the honest answer for a site
    that gives you nothing stable, and worth saying out loud rather than pretending the nine
    locators save you everywhere.

  Still unresolved: real Chrome continues to refuse this profile, so it stays Chromium-owned.
  It has cost nothing so far — PostHog and Google both work — but the cause is still unknown.
- **2026-09-04 (three things asked for, all done: CI on three operating systems, `cairn
  doctor`, README troubleshooting)** — everything a stranger meets before they meet the
  product.

  **CI now runs on macOS and Windows too.** `.github/workflows/test.yml` went from one job to
  four: ubuntu 3.11, ubuntu 3.13, macos 3.13, windows 3.11. Ubuntu carries both ends of the
  supported Python range, the other two take one end each — three operating systems and both
  versions without paying for six runners. Two things Windows needed: `shell: bash` on the
  install and both test steps, because Windows runners default to PowerShell and every script
  in the file is bash; and `playwright install-deps chromium` split off into a Linux-only
  step, since it is apt-based and has nothing to do elsewhere. **Pushed and green on all
  four jobs plus ruff** — so Cairn is now proved on Linux, macOS and Windows, not assumed.

  **`cairn doctor` exists** — `package/src/cairn/doctor.py`, 10 tests. It checks the seven
  things Cairn needs that are not Python code: Python version, the installed version, a
  browser that starts, the profile opening, memory readable, a writable downloads folder, and
  the optional market extra. Each failure prints the exact command that fixes it. Essential
  and optional are separated, so it exits non-zero only when something is genuinely broken —
  usable in someone's setup script. It is built out of the failures this project actually
  hit, not imagined ones.

  Its own output is the standing record of the profile fault: `browser: chrome` (clean mode
  uses real Chrome) next to `profile: opens with bundled Chromium`. Consistent with the
  unexplained refusal, and now visible without reading any code.

  One bug of mine while writing it: `tempfile.mkstemp` hands back an OPEN handle, and Windows
  refuses to delete a file that is still open, so the downloads probe failed on the machine it
  was written on. `os.close(handle)` before the unlink.

  **README has a troubleshooting section.** The five failures we know are real, in the words
  the code actually prints: no browser (`playwright install chromium` — the most common first
  run), no screen, the profile refusing to open (both causes named, plus `CAIRN_PROFILE` for
  two agents at once), a captcha, and a missing password. All of these had good error messages
  already; none could be found without hitting them first. `cairn doctor` leads the section.

  539 engine tests (was 524 in the README) and 98 MCP tests, ruff clean.

- **2026-09-05 (Phase 6b — the map: Cairn remembers the road, not just the destination)** —
  the biggest change since the browsing layer, and it came from a real user rather than from
  a plan.

  Rohit put Cairn on a client marketplace — vendor, customer and admin, many pages each — to
  drive its end-to-end tests, and found the flaw honestly: **on the first run Cairn and
  Playwright cost the same.** Cairn's memory was keyed by (site, task), so every new task was
  a stranger on a site it had already walked twenty times. His words: walking to the requests
  page to submit a request meant SEEING the list, the view button and the other six sidebar
  items, and binning all of it.

  So Cairn now keeps a **map** of every page it has actually looked at, and what was on it.

  **It costs nothing.** Recorded from `Session.look()` alone, because that snapshot was
  already built, already paid for and about to be thrown away. Proved by a test: a full cold
  walk is still 9 tool calls, exactly as before.

  **The cap is load-bearing, not tidiness.** The explore pass turned up that
  `sibyl-memory-client` has NO per-entity limit — it has a 5 MB whole-DATABASE soft cap, and
  the search index roughly doubles every body. So a runaway map would have stopped trails,
  site knowledge and the commons being written too, mid-run. 60 pages, 30 controls each,
  least-recently-seen evicted first, with a test that measures a worst-case map rather than
  asserting it is fine. The old comment at `store.py:83` claiming a 1 MiB entity cap was
  simply wrong and is now correct.

  **The gate holds.** `SITE_MAP` joins the tuple in `forget_site`, with its own case in
  `test_deletion_gate.py`. A judge who deletes the memory and finds Cairn still knows the
  site's shape would have found a gate that does not hold.

  **Two real bugs fixed on the way, both older than this phase.**

  `cairn_run`'s `needs_task` branch — which is exactly where a genuinely NEW task on a known
  site lands — used to end "Do NOT explore, the trail is already there". True when one of
  `tasks` fits; simply wrong when none does, which is the whole case this phase exists for.

  And `cairn sites` **silently hid any site with more than one trail**. It called
  `load_playbook(site)` with no task, which returns None as soon as a site has two, then
  `continue`d past it without a word — so a site with two tasks vanished from the list
  entirely. That is the exact shape of site this phase is about, and it was only found
  because the new benchmark saved a second task. It now prints one row per trail.

  **Beyond the plan, and the thing that makes it work: the map is actionable.** A map you can
  only read is a hint — the AI would know the Sign in button was there and STILL have to read
  the whole page to get a ref before pressing it, which is the cost the map exists to remove.
  So `cairn_act` now accepts `role=button|Sign in` and `href=/settings`, the same vocabulary a
  trail already stores, resolved by the same code replay uses. `cairn_map` hands back a ready
  `use` string per control. `describe()` still runs afterwards, so a step saved this way gets
  all nine durable locators exactly as a snapshot element would.

  **Rohit's call, taken against my recommendation:** the map travels when a trail is shared or
  sold. It merges rather than replaces, so two agents who walked different corners end up
  knowing both. The FREE catalogue advertises a page COUNT only — never the pages — so a
  browsing stranger can see a map is worth paying for without being handed it. `cairn share`
  prints exactly which paths left, and `cairn map` shows their contents beforehand: consent by
  inspection, the same guarantee the notes already had.

  **The demo site grew two real pages.** Its nav already listed Payments and Settings and both
  were decoration pointing back at `/invoices`. A site with one destination cannot show what a
  map is for.

  **The measured numbers** (`python benchmark.py`, same site, a DIFFERENT task, nothing
  replayed — all three exploring from scratch):

  ```
                  time  tool calls  page reads  model calls
  blind           0.6s          10           3            0   the way it worked before the map
  with map        0.3s           8           1            0   pages Cairn had already walked
  once more       0.3s           7           0            0   and now /settings is mapped too
  ```

  Three page reads became one, then none. Both scripts are hand-written, exactly as Monday
  already was, and the benchmark says so — it measures what the map makes available, not an
  AI being clever.

  591 engine tests, 112 MCP tests, ruff clean. New surface: `cairn map <domain> [--path]`,
  `cairn_map(site, path?)`, `pages_known` on five `cairn_run` branches, and `cairn sites` now
  showing a site that was explored but never saved.

  Still to do: the marketplace run for the real headline number, which is Rohit's.

- **2026-09-05 (gap 2: the map on real websites, and the five bugs that found)** — the map
  had only ever run against the demo site in this repo. Driven through a REAL `cairn-mcp`
  process over stdio, against six real sites, it worked — and immediately exposed things the
  demo site is too polite to show.

  | site | offered | pages | controls kept | note |
  |---|---|---|---|---|
  | github.com | 60 | 2 | 100 | followed `https://github.com/pricing` from the map |
  | developer.mozilla.org | 60 | 2 | 100 | followed `/en-US/` from the map |
  | news.ycombinator.com | 60 | 1 | 50 | 7 links correctly kept as EXTERNAL |
  | docs.python.org | 60 | 1 | 50 | `/3/library/pathlib.html` → `/:id/library/pathlib.html` |
  | us.posthog.com (signed in) | 50 | 1 | 37 | `/project/400792/home` → `/project/:id/home` |
  | search.google.com | 31 | 1 | 24 | landed on the signed-OUT page; the session has expired |

  **Bug 1, and the worst of them — older than this phase.** `href_path` throws the host away,
  and `Element.locators()` built its `structural` locator from the result. GitHub writes its
  own navigation absolutely, so the locator read `href=/pricing` while the DOM attribute said
  `https://github.com/pricing` — a locator that could never match the element it was made
  from. Every trail on such a site has been carrying one that silently missed; invisible
  because the other eight locators covered for it. Fixed with `link_target`, which keeps the
  host and still strips the query and fragment. `href_path` is untouched, because
  postconditions genuinely do want the bare path.

  **Bug 2.** The same stripping turned every EXTERNAL link into a fake page of the current
  site. On Hacker News, where every story points somewhere else, the map was recording other
  people's websites as pages of news.ycombinator.com. Same fix.

  **Bug 3.** PyPI answered the automated browser with a bot challenge page — title "Client
  Challenge", zero controls — under the real URL. The map recorded it as the project page.
  Pages with no controls are no longer recorded at all: nothing worth remembering, and
  remembering it would tell a later run this page is empty. (Our captcha markers do not catch
  this style of challenge. Noted, not chased.)

  **Bug 4.** Every real site opens with a screen-reader "Skip to content" link. Its target is
  a fragment, not a place, so the map was offering an AI somewhere to go that is where it
  already is. Fragment-only targets are no longer recorded as destinations — the control is
  still kept, because a site can hang `href="#"` on a button worth pressing.

  **Bug 5, mine.** The size-guard test built its pages as `/section/0/overview` … which all
  normalise to `/section/:id/overview`. It was measuring ONE page and calling it a full map.
  It now asserts the page count first, so it can never go hollow again quietly.

  **The caps were wrong, and now they are measured.** 30 controls per page was set blind;
  GitHub offers over 60 and keeping 30 meant keeping the global header and almost nothing
  belonging to the page. Raised to 50. A genuinely full map then measured 228 KB, which is a
  lot of a 5 MB database to spend on one site, so pages came down 60 → 40. Ids collapse, so
  forty DISTINCT pages is a large application.

  **What did NOT break:** `use` strings resolve on real signed-in apps. On PostHog
  `role=link|Skip to content` found the real anchor; on Search Console `role=link|Start now`
  found the real one. Both then failed to CLICK, because the element sits outside the
  viewport and Playwright will not click what it cannot bring into view. That is the browsing
  layer and it is pre-existing — the map's half worked.

  **Two things for Rohit:** the Search Console session has expired and needs `cairn login`
  again; and `/3/library/...` collapsing to `/:id/library/...` is the id rule being eager on
  a version number. Left alone deliberately — being less eager would break the case the rule
  exists for, where `/requests/1` … `/requests/900` would otherwise fill the map.

  Both packages bumped to **0.2.0**, and `cairn-browser-mcp` now floors its dependency at
  `cairn-browser>=0.2.0`: `cairn_map` calls `store.load_site_map`, which 0.1.0 does not have,
  so an unpinned resolve could pair a new server with an old engine and fail on a user's
  first call.

- **2026-09-05 (macOS CI found a real race, not a test wobble)** — 596 passed, one failed, and
  only on macOS: `test_switch_by_number` asked for tab 1 and was told there was only one tab.

  The test slept a fixed 300 ms after `window.open` and assumed the tab had arrived. That was
  enough on Linux and Windows and not enough on a macOS runner — which means it was never
  long enough anywhere, only lucky.

  **The same race is in the product, which is why this is not just a test fix.** A tab opened
  by the SITE arrives on a Playwright event, not on the call that caused it, so there is a gap
  between `window.open` returning and Cairn knowing the tab exists. A host AI that clicks a
  `target=_blank` link and then calls `switch_tab` can land in exactly that gap and be told the
  tab is not there.

  `switch_tab` now waits for a tab that is still opening, using the same poll-and-return shape
  as the download grace period (`TAB_GRACE_MS`, `TAB_POLL_MS`) — it returns the moment the tab
  appears, so only a run where the tab genuinely never arrives pays the wait. It waits for ONE
  pending tab only: asking for tab 7 with one open is a mistake, not a race, and still fails
  at once.

  The sleeping is done through Playwright rather than `time.sleep`, because the sync API only
  delivers its events while a Playwright call is running — a plain sleep would sit there and
  the tab would never be reported at all.

  The three tab tests now wait for the CONDITION instead of a guessed number of milliseconds,
  and `test_switch_by_number` deliberately does not wait at all any more: `switch_tab` has to
  do the waiting itself, which is the thing being claimed.

  **Released 0.2.1** the same day, both packages. The engine carries the tab fix; the MCP
  package had no code change and went out only so its PyPI page shows cairnmcp.fun, which a
  metadata edit cannot reach without a release.

  The dependency floor stayed at `cairn-browser>=0.2.0` on purpose — nothing in the server
  needs the tab fix, and raising a floor for a bug fix would force an upgrade nobody asked
  for. One consequence worth knowing, seen while verifying: for a minute after upload, PyPI's
  index had the MCP package at 0.2.1 while still offering the engine at 0.2.0, so a fresh
  install in that window paired 0.2.1 with 0.2.0. Correct — the floor allows it — just
  without the tab fix. It settles on its own; `--no-cache-dir` forces the point.

- **2026-09-05 (five bugs from Rohit's marketplace, and two worse ones they led to)** — the
  first real product feedback from outside the demo site, and it was worth more than a week
  of our own testing.

  **The dangerous one, and he was right to rank it first.** `_element_by_selector` never
  checked how many elements a selector matched, and `Browser.locate` took `.first`. On a
  table with a menu button in every row, `button[aria-haspopup="menu"]` matched all of them,
  Cairn clicked row one's, and returned **ok: true**. He spent eight calls hunting a fault in
  his own application that was never there. Worse than a wrong answer: it reports success, so
  nothing downstream doubts it, and `cairn_save` then writes it into a trail to be replayed
  for ever. Cairn now refuses, says how many matched, names the first few by their text, and
  names the ways to mean one of them.

  **The Radix bug was that bug.** He reported that Cairn could not open a shadcn/ui dropdown
  and suspected our click was synthetic — not sending the `pointerdown` Radix opens on. Rather
  than special-case it, the hard page gained a menu that opens ONLY on `pointerdown` and
  ignores `click` entirely. **Cairn opens it.** So the clicks were always real pointer events;
  what actually happened is that his selector matched a menu button in every row, Cairn opened
  the first, and he inspected a different one. Two tests pin the pointer behaviour forever now.

  **`count` could only ever return 1.** Found while fixing the `all_text` crash. `locate()`
  took `.first`, so `count` and `all_text` had always been looking at a single element — while
  `count`'s own description promised "how many elements match — there are 3 unpaid invoices".
  It had been quietly answering 1 for every list on every page, and nothing caught it because
  no test ever counted something there was more than one of. `locate(one=False)` now, driven
  by a `many` flag on the two ReadSpecs that mean it.

  **The crash** — `all_text` on a node with no text at all, which is what an `svg` inside an
  icon button is. Playwright answers None; `.strip()` did the rest.

  **The two papercuts.** A plain control NAME as a `ref` now gets told it can be said as
  `"role=button|Next: Document Submission"` — which really works, since the map made that
  form real. And `select` on a Radix combobox now says it is not a real `<select>` and to
  click the button instead, rather than passing Playwright's message straight through.

  **It immediately caught six of our own selectors.** The 26-site benchmark was reading the
  first of many on six sites — `.titleline a` matched sixty elements on Hacker News. Exactly
  the bug he reported, in our own benchmark, invisible until the check existed. They now say
  `>> nth=0` out loud, and the error message names that form first because it is the shortest
  one that works on any selector.

  13 new tests in `test_ambiguous_selectors.py`, plus 2 on the hard page.

- **2026-09-05 (two more from the marketplace: the SPA link, and the nameless buttons)** —
  both reported as blocking, and the first one was not the bug it looked like.

  **`click` "did not follow" React Router links.** Reported as: every form of `ref` returns
  `ok: true` with `navigated: false`, the URL never changes, and the same selector in plain
  Playwright navigates fine. The obvious reading was that our click was synthetic and never
  reached React — the same theory as the Radix report, and wrong for the same reason.

  A React Router `<Link>` went into the hard page: a real anchor that calls `preventDefault`
  and then `pushState`. Measured:

  ```
  cairn click -> navigated: False, url: .../hard
  url straight after : .../hard
  url 300ms later    : .../hard/orders
  ```

  **The click always worked.** `settle()` waits for `domcontentloaded`, which fires instantly
  on a single-page app because no document ever loads, so Cairn read the address before the
  app had changed it. Not merely a false report either: a saved step would have recorded the
  OLD url as its postcondition and been wrong for ever after.

  `Browser.await_url_change` now gives a client-side navigation a bounded moment to show up —
  on the cold path when an anchor was clicked and has not moved, and on replay when the step
  is recorded as one that changes the address. It returns the instant the URL differs, so the
  only click that pays the wait is one that genuinely goes nowhere.

  **The map dropped every control without an accessible name.** That filter was mine, with a
  reason written next to it: "something with no name cannot be found by name later". True, and
  beside the point. On an admin table the unnamed controls ARE the ones that matter — view,
  approve, reject, suspend, all icon-only `<button>`s with no text and no aria-label. The map
  listed the sidebar and the search box and none of the things anybody wanted to click, on
  precisely the page it was supposed to save the most work on.

  They are kept now, numbered by position among controls of the same role, and they come back
  as a ref that works: `role=button >> nth=3`. Same spelling Playwright uses, so one form
  covers a stored control and a plain CSS selector alike, and `_as_stored_locator` reads the
  suffix into `Locator.nth`, which `_to_playwright` already applied. Rohit's own framing was
  the right one: imperfect, and far better than the control being absent.

  **The hard page gained both shapes**, and neither existed before — which is exactly why
  neither bug was ever caught here. It now also carries a table row of icon-only buttons.

  One more found on the way: `remember_overlay` crashed on a session with no store, though
  `Session(browser)` is a supported shape. The overlay is still cleared; only the writing down
  is skipped.

  17 tests in `test_ambiguous_selectors.py`.

- **2026-09-05 (three more from the marketplace: the label ref, one password per role, and
  a run that finished too early)**

  **A label as a `ref` still said nothing useful.** `"Export Vendors CSV"` is perfectly
  valid CSS — three tag names in a descendant chain — so Playwright does not reject it, it
  simply finds nothing, and the message stopped at "nothing on this page matches". True,
  useless, and silent about the one form that works. It now recognises a label (words with
  spaces and no selector punctuation) and answers with `role=button|Export Vendors CSV`. A
  real selector that finds nothing is deliberately NOT lectured about labels.

  **One password per domain, on a site with three sign-ins.** The marketplace has a
  customer, a vendor and an admin login on one host, each with its own password. Two of
  three saved trails could never have replayed, and the third would have tried the wrong
  password against a real login — which is how an account gets locked out. Secrets are now
  scoped by PROFILE, which already exists per role, with the plain domain entry as the
  fallback so every secrets file anybody already has keeps working:

  ```json
  {"marketplace.example.com": {"admin": {"password": "..."}, "password": "fallback"}}
  ```

  `CAIRN_SECRET_<DOMAIN>_<PROFILE>_<FIELD>` does the same from the environment, and the
  missing-secret message names the profile it wants. One thing worth its own test: a
  profile BLOCK is never mistaken for a value, so `{"admin": {...}}` is another profile and
  not a secret called "admin".

  **A run returned while the site was still moving.** Replaying an admin sign-in worked —
  four steps, `ok: true` — and a caller reading the URL immediately afterwards saw the
  sign-in page and concluded the trail had failed, then went off to re-explore a site Cairn
  already knew. Exactly the cost this project exists to remove.

  The shape is specific and extremely common: the last step is a submit BUTTON. A button
  has no href, so nothing at learn time knew the address was about to change, and the
  step's own check is about the element rather than the URL — it passes on the page it
  started on. A trail ending in an ACTION now lets the site finish landing before the run
  reports done; a trail ending in a READ, which is most of them and all of the benchmark,
  waits for nothing at all.

  The hard page gained that shape too — a submit button that redirects a beat later — so it
  can never regress. It now carries twelve awkward things, five of them added today by real
  reports.

  One of my own on the way: the deletion gate forbids the literal word "shop" anywhere in
  `executor.py`, comments included, and I had written it in a comment about a product
  listing. The guard is right to be that blunt — reworded rather than loosened.

  11 new tests across `test_secrets.py`, `test_ambiguous_selectors.py` and the new
  `test_run_finishes.py`.

- **2026-09-05 (the head-to-head, and the benchmark catching ME at the same trick)**

  Six sites, one task each, driven through three MCP servers as a host AI would drive them.
  Pinned versions so a rerun measures the same thing: `@playwright/mcp@0.0.80`,
  `chrome-devtools-mcp@1.8.0`.

  ```
  tool                    run   calls   bytes to model   seconds   sites ok
  cairn                     1      24          114,493      42.1   6
  cairn                     2       6            3,604       4.0   6
  chrome-devtools-mcp       1      18          851,729      33.7   6
  chrome-devtools-mcp       2      18          851,721      27.9   6
  playwright-mcp            1      18          891,799      35.7   6
  playwright-mcp            2      18          891,845      36.4   6
  ```

  **The first run costs Cairn MORE calls than either of them** — 24 against 18 — because
  Cairn also saves the trail. That is the honest shape of the trade and it belongs in the
  table: you pay a fourth call once, and the second run costs one.

  Neither of the others is trying to remember anything, and the table says so. Their second
  run is their first run, to the byte.

  **The first version of this benchmark was false, and false in OUR favour.** Every Chrome
  DevTools call had failed — `pageId` is required there and I had not passed it — and each
  returned a 488-byte error. Because an error message is text, the run reported six
  successful sites at **2,928 bytes**, which would have made the tool that never ran look
  like the cheapest thing in the table. Publishing it would have been indefensible: the
  first person to rerun it catches us.

  It is the same failure Cairn itself was fixed for twice today — reporting success for a
  result that is not there — and it landed in the measuring instrument. An `isError` reply
  now counts as no answer at all.

  Playwright MCP's numbers were checked individually and are genuine: `pkg.go.dev` really
  does cost it 506,608 bytes for one reading, against Cairn's 615 on a warm run.

- **2026-09-05 (the fixes the benchmark and the marketplace forced — matching, wrong page,
  passwords)**

  Three things were wrong, and two of them were worse than what was reported.

  **1. Naming the task was WORSE than saying nothing.** `load_playbook` had one clause,
  `if len(keys) == 1 and not task`. A site with exactly one trail replayed perfectly when
  the caller named no task and refused when it named one that did not match word for word
  — while the tool description tells the caller to name the task. Cairn steered its own
  callers into the path that fails, which is why the head-to-head benchmark showed it
  costing MORE than tools that remember nothing.

  On top of that, `_overlap` divided by the length of the REQUEST, so every extra word
  lowered the score, the site's own name included:

  ```
  trail saved as "read the first quote"
    "tell me the first quote"                                        0.67  matched
    "what is the quote at the top of the page"                       0.33  missed
    "find the top quote on quotes.toscrape.com and who said it"      0.11  missed
  ```

  Now: scored against the SHORTER of the two, the domain's own words stripped from the
  request first, and a lone trail runs whenever the request shares any meaningful word with
  it (`shares_meaning`). Sharing NO word is still a refusal — "cancel my subscription" must
  never run "count open issues". The legacy bare-domain fallback got the same guard; it
  used to hand back its trail whatever was asked for.

  **2. A wrong-page replay was quietly destroying healthy trails.** Replaying "sign in as
  admin" while already signed in lands on the dashboard, and Cairn offered twenty-three
  dashboard controls to bind the email step to. That was the reported half. The unreported
  half was worse: the decision came AFTER the locators had been tried, so every such replay
  recorded a miss against a perfectly good locator. A few of those drag health under half,
  `is_stale` turns true, and the trail is retired.

  A step now records the page it was performed on (`Step.page`, filled by `distill` from
  `url_before`), and replay compares pages BEFORE it touches a locator, before `_blame` and
  before `_repair_request`. The earlier attempt keyed on the `goto` URL check, which misses
  almost every real trail: `url_contains` is a substring test, so a trail starting at a bare
  host matches every page on that site, and a trail that navigates by CLICKING never went
  through that branch at all. Old trails load with an empty page and opt out.

  **3. `_places_to_look` could type the wrong password into a real login.** The order was
  profile env, PLAIN env, profile file, plain file — so an unprofiled environment variable
  outranked the profile's own entry in `secrets.json`. With `CAIRN_SECRET_SHOP_PASSWORD`
  exported for the customer sign-in and the admin password in the file, running as `admin`
  typed the CUSTOMER's password into the admin login, silently. That is the account lockout
  profiles exist to prevent, and the docstring promised the opposite order. Both of a
  profile's places now come before both domain-wide ones.

  The missing-password message also names the profile — `default` included, which it used
  to hide — and names the sibling profiles that DO have that secret. The password was
  usually in the file all along, under `admin`, and the message sent people to edit a file
  that was already correct.

  Also: `cairn run` prints something for `wrong_place` instead of exiting 1 in silence
  (exit code 5), and the CLI names the profile even when it is `default`.

  647 tests, ruff clean. The deletion gate caught me a second time — the word "requests" in
  two new comments — and the comments were reworded rather than the guard loosened.

- **2026-09-05 (why Cairn was losing its own benchmark: the trail had no answer in it)**

  The head-to-head was re-run after the matching fixes and Cairn still cost more than tools
  that remember nothing. The per-site trace said why, and it was not matching at all:

  ```
  quotes.toscrape.com  run 1  cairn_run, act, act, read, read, save
                       run 2  cairn_run, READ, READ      <- read the page again
  developer.mozilla    run 1  cairn_run, act, act, read  <- never saved at all
  news.ycombinator     run 3  cairn_run                  <- "reported success but
                                                             returned no title data"
  ```

  `Session.read` only wrote a read into the trail when the caller passed `remember=True`.
  The read tool's description says so in capitals — "REMEMBER THE READ THAT IS THE ANSWER"
  — and across twelve real runs the caller passed it **zero times**. So every trail walked
  to the page and stopped. The warm run replayed the navigation, answered nothing, and the
  model read the page itself, which is the entire cost Cairn exists to remove.

  Telling it harder was never going to work. An unmarked read is now kept aside, and `save`
  puts it into the trail ONLY if the trail would otherwise answer nothing at all. A marked
  read is obeyed exactly and never second-guessed; a task that read nothing still saves no
  read; a whole-page dump is never chosen for anybody, because remembering one hands back
  thousands of characters on every future run. The chosen read goes back where it happened,
  not on the end, so a read before a click still replays before that click. `cairn_save`
  says when it chose, because only the caller knows whether it picked the right one.

  **Measured after the fix — ONE sweep, all rows from the same run** (4 public sites, one
  real Claude session per tool, Sonnet 5 / medium, three runs each, 2026-09-05, $3.20):

  ```
  tool                   run  tool calls      tokens   seconds  sites ok
  cairn                    1          28   1,195,197     142.0      4
  cairn                    2          14     645,305      84.5      4
  cairn                    3           8     415,287      75.0      4
  playwright-mcp           1          16     709,717      79.1      4
  playwright-mcp           2          16     712,668      88.6      4
  playwright-mcp           3          16     709,708      92.1      4
  chrome-devtools-mcp      1          16     727,238      93.4      4
  chrome-devtools-mcp      2          16     726,224      90.9      4
  chrome-devtools-mcp      3          16     726,772     106.2      4
  ```

  Cairn pays more on run 1 — it is also learning the site — and less from then on. **A
  learned site costs exactly 2 calls, and one of those two is this harness loading the tool
  schema, not Cairn.** The other tools pay that same call and it is in their numbers too.
  Neither of them is trying to remember anything, and their rows say so: run 3 is run 1.

  Before this fix the same sweep read 29 / 20 / 18 and Cairn was LOSING on every run.

  **The one blemish, recorded because it is real:** on `news.ycombinator.com` the model
  explored, answered, and never called `cairn_save`, so run 1 taught Cairn nothing and run 2
  had to explore again — that is the whole of the 14. It saved on run 2 and run 3 cost 2
  calls. `cairn_read` now says at the moment of the answer that the site costs full price
  again unless it saves, and 3 of 4 sites saved first time. The remaining lever is to have
  the `unknown` reply hand back the exact `cairn_save(task=...)` call, since `cairn_run`
  already knows the task string. Not done, because changing it would make this table
  describe code that no longer exists — it needs its own sweep.

  653 engine tests, ruff clean.

- **2026-09-05 (ten repeats on one real page — the curve, not the snapshot)**

  Rohit's objection to the three-run table was correct and worth writing down: add the three
  runs up and Cairn totals 50 calls against 48 and 48. Three runs is barely past the paying
  part, so the sum hides the entire point of a cache.

  So: `pkg.go.dev/net/http`, one task, **ten runs**, each a fresh `claude -p` session with
  nothing carried over but Cairn's memory. `pkg.go.dev` rather than `quotes.toscrape.com`
  on purpose — a real documentation page, not a scraping practice site. On the toy site
  every tool is cheap and every curve is flat.

  ```
  run   cairn (cum)        playwright-mcp (cum)   chrome-devtools-mcp (cum)
   1     7    7    294k     5    5    208k         6    6    248k
   2     2    9    398k     5   10    415k         5   11    461k
   3     2   11    492k     7   17    697k         5   16    673k
   4     2   13    595k     7   24    978k         5   21    886k
   5     2   15    699k     4   28  1,148k        10   31  1,282k
   6     2   17    803k     5   33  1,356k         9   40  1,655k
   7     2   19    907k     5   38  1,563k         5   45  1,865k
   8     2   21  1,011k     8   46  1,881k         5   50  2,078k
   9     2   23  1,114k     4   50  2,051k         5   55  2,290k
  10     2   25  1,218k     5   55  2,263k         5   60  2,500k
  ```

  **Cairn is ahead from run 2 onward, on both measures.** Over ten runs: 25 calls against
  55 and 60 (**55% and 58% fewer**), 1.22M tokens against 2.26M and 2.50M (**46% and 51%
  fewer**). The payback is one run, not four — on a real page the other tools cost 5 to 8
  calls per run, not 3.

  The second finding is one nobody was looking for. **Cairn's nine warm runs landed between
  93,513 and 103,887 tokens — 10k apart.** Playwright's ten runs ranged over 147k and Chrome
  DevTools' over 187k, with 10-call and 9-call outliers where the model got confused by a
  page it had already read nine times. Replay is deterministic Python, so the same task
  costs the same every time. A tool whose price you can predict is a different product from
  one whose price you cannot.

  Cost: $1.95. Written to `benchmark-repeat10-pkg-go-dev.json`. The benchmark now takes
  `--site`, `--runs` and `--out`, because every sweep used to overwrite the same file — a
  single-site re-measure silently replaced a full head-to-head that cost real money.

- **2026-09-05 (six sites, ten runs each — Cairn won ONE, and that is the useful part)**

  Five more sites were added to the ten-repeat sweep. The list and the tasks were fixed
  BEFORE any of them was measured, and every one is written down here whatever it says.

  ```
  site               cairn          playwright     chrome-devtools   cairn per run
  pkg.go.dev         25  1.22M      55  2.26M      60  2.50M         7 then 2
  docs.python.org    26  1.28M      20  1.02M      30  1.40M         8 then 2
  en.wikipedia.org   29  1.38M      20  1.02M      45  1.96M         6, 7, then 2
  pypi.org           46  2.02M      30  1.47M      30  1.51M         7 then 4
  huggingface.co     43  1.91M      30  1.51M      30  1.55M         6,7,4,5,2,6,4,2,3,4
  github.com         70  2.95M      51  2.16M      60  2.53M         7 every run
  ```

  **Two of those rows are bugs, and the benchmark is what found them.**

  1. **`github.com` never went warm in ten runs.** The caller said
     `github.com/microsoft/playwright` — no scheme — so `urlparse` never stripped the path
     and the whole string became a memory key of its own. Cairn learned the site under
     `github.com`, looked it up under the long string, and found nothing. Every run. It
     never errored; it was only slow, which is how it survived 650 tests, an earlier
     benchmark and eight real sites. `domain_of` now strips a path with or without a
     scheme and lowercases, and all ten call sites in the MCP server go through it instead
     of their own `if "://" in site` test.
  2. **`pypi.org` sat at 4 calls because its trail answers nothing.** The model answered
     from `cairn_read(kind="page")`, which is the control list — exploration, not a value.
     Recording that list as a step would be worse (replay would hand back the whole page),
     so `cairn_save` now says plainly that the trail answers nothing and how to fix it,
     instead of replying "ok". `huggingface.co` looks like the same thing plus a save that
     only sometimes happened.

  **The third finding is not a bug and matters more.** On `docs.python.org` and
  `en.wikipedia.org` Cairn worked perfectly — 2 calls on every warm run — and still lost,
  because Playwright MCP also costs 2 calls there: its `navigate` reply already contains
  the heading. There is nothing for memory to save. Cairn pays 6-8 calls to learn the site
  and never earns it back.

  So, said plainly: **on "open one page, read one visible fact", Cairn is not cheaper.** It
  wins when the page is big — `pkg.go.dev`, 25 calls against 55 — and it should win much
  more on multi-step work, which is what it is for and what none of these six tasks
  measure. That belongs in the README as a limit, not hidden.

  655 engine tests, 38 MCP server tests, ruff clean. The six JSON files are kept per site.
  The numbers above were measured BEFORE both fixes and must be re-measured before they are
  published anywhere.

- **2026-09-05 (measuring the right thing at last — 52% fewer calls)**

  Rohit's objection to the six-site table was right: adding the runs up gave 188 against
  206, and nobody changes tools for 9%. The cause was the benchmark, not the product. Every
  task in it was "open one page, read one line" — the cheapest thing a browser tool does,
  two or three calls for anybody, so memory had almost nothing to save. **The benchmark was
  built so that our ceiling was their floor.**

  Real work has steps. Three multi-step journeys were added to `benchmark_agents.py`
  (`--journeys`), each done TEN times, each run a fresh Claude session:

  ```
  journey (10 runs)      cairn          playwright     chrome-devtools
  github.com             28  1.36M      83  3.38M      33  1.68M
  quotes.toscrape.com    27  1.32M      60  2.57M      60  2.62M
  books.toscrape.com     41  1.93M      56  2.77M      56  2.81M
  ALL THREE              96  4.61M     199  8.73M     149  7.10M
  ```

  **52% fewer tool calls and 47% fewer tokens than Playwright MCP; 36% and 35% fewer than
  Chrome DevTools MCP. 30 of 30 correct for every tool.** Cairn wins every journey — the
  same comparison that was a tie on one-page lookups.

  The shape is the point: `10, 2, 2, 2, 2, 2, 2, 2, 2, 2`. A learned journey costs two
  calls whether it is two steps or twenty, while Playwright's github row reads
  `8, 8, 18, 7, 9, 9, 7, 6, 5, 6` — it never gets cheaper, because it is not trying to.

  **What unlocked it was one last bug, and it was subtle.** On books.toscrape.com the price
  lives in `.price_color`, which matches SEVEN elements, so the read was refused —
  correctly. But the refusal LISTS the matches to be helpful, so the model read the answer
  out of the error message, reported it, and never made a successful read. The trail saved
  with no answer in it, and every run re-read the page. Our own helpful error removed the
  reason to try again, which is why no wording fixed it.

  `cairn_save` now takes `answer` — the value the caller is about to report. Cairn finds
  which element says exactly that and stores every durable way of finding it again. Zero
  extra calls for the caller. The text is deliberately NOT kept as a locator (a test caught
  me storing "the element reading £45.17", which would miss the day the price moves), and a
  value matching no element is never recorded. Where several elements say it — a price in a
  header and again in a tax table — the first is kept and the reply says how many matched;
  an ambiguous CLICK is still always refused, because a wrong click does something.

  Verified with a real model before spending: books.toscrape.com run 2 went from 7 calls to
  2. The sweep cost $9.10, and every session ran at below-normal priority with a cooldown,
  so the machine stayed usable.

