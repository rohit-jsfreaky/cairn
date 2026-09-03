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
