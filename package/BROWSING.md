# BROWSING.md — what Cairn must be able to do on a real website

Written 2026-09-01, after a test proved the browsing layer was far weaker than assumed.

## Why this document exists

Cairn was tested against a page containing a React-style dropdown, a shadow DOM, an iframe,
and a link that loaded late. Our page snapshot found **1 element**. Playwright's own
snapshot found **7**, with working handles for every one — including the button inside the
iframe.

The cause was not a missing feature. It was that the snapshot had been hand-written instead
of calling Playwright, which already does it better. The risk is that the same mistake is
sitting in the rest of the browsing layer, unseen, waiting for a real site.

So this document does not list the things we happened to think of. It lists **everything
Playwright can do**, taken from the installed library, and decides for each one whether
Cairn needs it. If something is missing from Cairn later, it should be because this document
said "no" on purpose.

## The rule that decides everything

> **A capability belongs in Cairn if it can be recorded once, replayed later with no model
> involved, and checked afterwards by a postcondition.**

Three consequences fall out of this, and they are the reason the list below is not simply
"all of Playwright":

- **No arbitrary JavaScript.** `evaluate` would let a step do anything, cannot be verified,
  and turns the trail into code we cannot reason about. It is also an escape hatch that
  would quietly become the answer to every hard problem.
- **No network manipulation.** Route interception and HAR replay change what the site *is*.
  Cairn's claim is that it repeats what a person did, on the real site.
- **No test-framework machinery.** Tracing, video, `pause`, `pick_locator` belong to a test
  runner, not to a memory.

## Where Cairn stands today

Measured 2026-09-01, before Phase 2.5 began, and updated as each step lands.

| | Playwright offers | Cairn had | Cairn has now |
|---|---|---|---|
| ways to act on an element | 21 | 4 | **21, plus 6 page-level** ✅ 2.5c |
| ways to read from a page | 18 | 1 (page text) | 1 — still to do (2.5d) |
| page-level events (dialogs, popups, uploads) | yes | none | none — still to do (2.5f) |
| frames / shadow DOM | yes | none | none — still to do (2.5a) |

It started at roughly a quarter, and the missing parts were ordinary things: a hover menu,
a checkbox filter, a confirm dialog, a login that opens a new tab, a cookie banner.

---

# The complete inventory

Every public capability of `Locator`, `Page`, `BrowserContext`, `Keyboard`, `Mouse`,
`FrameLocator`, `Dialog`, `FileChooser` and `Download`, taken from playwright 1.62.0.

## 1. Acting on an element — `Locator` (21 methods) — ✅ ALL BUILT (2.5c, 2026-09-01)

All 21 are implemented in `src/cairn/actions.py` and each one has a test in
`tests/test_actions.py`. `test_every_action_is_exercised` fails if an action is ever added
without a test, so this table cannot drift away from the code again.

**This table originally marked the last five "no".** Rohit overruled that on 2026-09-01:
build everything, lose no edge case. The original reasoning is kept in the last column,
because two of those five turned out to earn their place and the other three did not — and
that is worth being honest about rather than quietly rewriting.

| Playwright | Cairn verb | in? | why |
|---|---|---|---|
| `click` | `click` | **yes** | already have |
| `dblclick` | `double_click` | **yes** | grids and file lists need it |
| `hover` | `hover` | **yes** | menus that only open on hover are everywhere |
| `fill` | `fill` | **yes** | already have |
| `type` / `press_sequentially` | `type` | **yes** | search and autocomplete boxes ignore `fill`, because they listen for keystrokes |
| `clear` | `clear` | **yes** | a field must be emptied before retyping, or values concatenate |
| `press` | `press` | **yes** | already have — Enter, Escape, Tab, combinations |
| `check` | `check` | **yes** | filters and consent boxes |
| `uncheck` | `uncheck` | **yes** | as above |
| `set_checked` | `set_checked` | **yes** | kept as its own verb, not folded (Rohit, 2026-09-01). `check` means "make sure it is ticked" and is safe to repeat; `set_checked` means "make it match this value". Only the second lands on a state we know for certain, and warm replay wants certainty |
| `select_option` | `select` | **yes** | now takes value, `label:`, `index:` and multi-select. Label matters most: sites change an option's hidden value far more often than the words a person reads |
| `set_input_files` | `upload` | **yes** | attaching a receipt or a CSV is a real repeated task |
| `scroll_into_view_if_needed` | `scroll_to` | **yes** | long lists and lazy loading |
| `drag_to` / `drop` | `drag` | **yes** | rarer, but kanban boards and reordering are real |
| `focus` | `focus` | **yes** | some forms only validate on focus/blur |
| `blur` | `blur` | **yes** | as above |
| `tap` | `tap` | **yes** | *was "no — mobile touch".* Built, but needs `Browser(touch=True)`. Touch is **off by default on purpose**: some sites serve a different mobile layout the moment they detect it, which would change what every other trail sees |
| `select_text` | `select_text` | **yes** | *was "no — a step toward copying".* That reason was wrong. `select_text` then `type` is how you replace the contents of a field that fights `fill` |
| `dispatch_event` | `dispatch_event` | **yes** | *was "no — bypasses the checks".* Still true, and its description says so in capitals. But it is the escape hatch when a site's button ignores a real click, and without it such a site is simply unusable |
| `highlight` / `hide_highlight` | `highlight` / `hide_highlight` | **yes** | *was "no — debugging aid".* Built, but marked `recordable=False`: they change nothing on the page, so they are never written into a trail |

### Also built, beyond this table: 6 page-level actions

`Locator` is only half the story — a trail has to move between pages too. These take no
element, and live in the same registry so that one `cairn_act` covers a whole flow:

| Cairn verb | why |
|---|---|
| `goto` | open an address |
| `back` / `forward` | history, for flows that branch and come back |
| `reload` | some dashboards only refresh their numbers this way |
| `scroll` | the page itself, for feeds that load more as you go |
| `wait` | a fixed pause. Kept, but its own description tells the AI to prefer `wait_for` |

### Five real bugs this step found

Worth recording, because each would have hit a real site and none was visible from reading
the code:

1. **Warm replay silently did nothing for any unknown action** — `executor._do` had no
   `else`. If the page already satisfied the postcondition, that no-op was recorded as a
   **successful replay**. A false pass is worse than a failure.
2. **Only `click` and `press` waited for the page.** A `select` that navigated was never
   waited for. Now one `Browser.settle()` runs after every action.
3. **`select_option` was being given the JavaScript argument shape.** Python takes
   `value=` / `label=` / `index=` separately, so choosing by visible label failed.
4. **`mouse.wheel` returns before the scroll is applied**, so reading the position straight
   after gives the position from *before*. On an infinite feed: scroll, read the same rows,
   forever.
5. **The wheel only moves what is under the pointer**, which starts in the corner.

## 2. Reading from a page — `Locator` (18 methods)

Cairn can currently read page text and nothing else. This is why "check my dashboard
numbers" is impossible today, and it is also what postconditions are built from.

| Playwright | Cairn | in? | why |
|---|---|---|---|
| `inner_text` / `text_content` | `read(text)` | **yes** | the number, the status, the error message |
| `input_value` | `read(value)` | **yes** | also lets us verify a `fill` actually landed |
| `is_checked` | `read(checked)` | **yes** | verifying a `check` |
| `is_visible` / `is_hidden` | `read(visible)` | **yes** | "the dialog closed" |
| `is_enabled` / `is_disabled` / `is_editable` | `read(enabled)` | **yes** | "the submit button became clickable" |
| `get_attribute` | `read(attribute)` | **yes** | href, aria-expanded, data attributes |
| `count` | `read(count)` | **yes** | "there are 3 unpaid invoices" |
| `all_text_contents` / `all_inner_texts` | `read(all_text)` | **yes** | reading a table or a list in one go |
| `aria_snapshot` | the snapshot itself | **yes** | replaces our hand-written collector |
| `bounding_box` | — | **no** | pixel geometry is not something to remember |
| `screenshot` | out of band | **later** | useful for the dashboard, never part of a trail |
| `inner_html` | — | **no** | raw markup is the cost we exist to remove |
| `evaluate` / `evaluate_all` / `element_handle` | — | **no** | see the rule |

## 3. Finding an element — `Locator` (finding methods)

We already store four kinds of locator: role, text, css, structural(href). Playwright can
find in more ways, and each is a candidate for a stored locator kind.

| Playwright | in? | why |
|---|---|---|
| `get_by_role(name=)` | **have it** | the most durable thing on a page |
| `get_by_text` | **have it** | |
| `locator(css)` | **have it** | |
| `get_by_label` | **add** | the right way to find a form field; survives redesigns better than css |
| `get_by_placeholder` | **add** | ditto |
| `get_by_test_id` | **add** | when a site has test ids they almost never change — the single most durable locator available |
| `get_by_title` / `get_by_alt_text` | **add** | cheap, and images/icons often have nothing else |
| `filter(has_text=)`, `nth`, `first`, `last` | **add** | "the third row", "the row containing September" — needed for lists |
| `and_` / `or_` | **no** | combining predicates is more expressive than a stored trail needs |
| `frame_locator` / `content_frame` | **handled** | Playwright's ai-mode refs already reach inside frames (proven: `ref=f1e2`) |

**Six more locator kinds means a broken step has six chances to survive instead of four.**
This is the cheapest reliability we can buy.

## 4. The page — `Page` (118 methods)

### Navigation
| Playwright | Cairn | in? |
|---|---|---|
| `goto` | `goto` | **yes**, have it |
| `go_back` | `back` | **yes** — many flows depend on it |
| `go_forward` | — | **no**, never needed in a recorded task |
| `reload` | `reload` | **yes** — the standard fix for a stuck dashboard |
| `url`, `title`, `content` | internal | **yes** |
| `set_content` | — | **no** — that is fabricating a page |

### Waiting — the thing modern sites need most
| Playwright | Cairn | in? | why |
|---|---|---|---|
| `wait_for_load_state("networkidle")` | `wait_for(idle)` | **yes** | a React dashboard is blank until its data arrives. Without this, `look()` sees an empty page — the single most likely cause of failure on PostHog |
| `wait_for_url` | `wait_for(url)` | **yes** | SPA routing changes the URL without a page load |
| `wait_for_selector` | `wait_for(element)` | **yes** | wait for the thing, not for a guessed number of seconds |
| `locator.wait_for(state=visible)` | used internally | **yes** | **we currently wait for `attached`, which is wrong** — it can act on an element that is still animating in |
| `wait_for_timeout` | `wait(seconds)` | **keep, discourage** | a fixed sleep is a last resort; the description should say so |
| `wait_for_function` | — | **no** | arbitrary JavaScript |

### Events that hang a run if ignored
These are not element actions. If they are not handled, the browser simply stops.

| Playwright | Cairn | in? | why |
|---|---|---|---|
| `on("dialog")` | auto-handle + `dialog` verb | **yes** | an unhandled `confirm()` blocks everything after it. Playwright dismisses by default, which silently cancels deletes and saves — we must decide per step and record the choice |
| `expect_popup` / `on("popup")` | `popup` handling | **yes** | "open in new tab", and most OAuth flows |
| `expect_file_chooser` | part of `upload` | **yes** | some sites open a chooser rather than exposing a file input |
| `expect_download` | have it | **yes** | already working |
| `expect_navigation` | internal | **yes** | |
| **`add_locator_handler`** | `dismiss_when_seen` | **yes — high value** | Playwright's own answer to overlays that appear at unpredictable times: cookie banners, "rate us", survey pop-ups. Register once and Playwright clears it automatically whenever it blocks an action. This is exactly the thing that breaks recorded flows on real sites, and it is already built |
| `expect_console_message`, `page_errors` | diagnostics only | **later** | useful for explaining a failure, not for replay |
| `expect_request` / `expect_response` | — | **no** | this is a test framework's job |

### Input devices
| Playwright | Cairn | in? | why |
|---|---|---|---|
| `keyboard.press` | via `press` | **yes** | including combinations like `Control+A` |
| `keyboard.insert_text` | via `type` | **yes** | |
| `mouse.wheel` | `scroll(amount)` | **yes** | infinite-scroll lists that ignore `scroll_into_view` |
| `mouse.move/down/up` | — | **no** | raw coordinates are the least durable thing possible |
| `touchscreen` | — | **no** | no mobile emulation |

### Frames
| Playwright | Cairn | in? |
|---|---|---|
| `frames`, `frame_locator`, `main_frame` | handled by ai-mode refs | **yes** |

Proven: a button inside an iframe was returned as `ref=f1e2` and was clickable with no
frame-specific code. Durable locators inside frames still need thought — see Open questions.

### Emulation, storage, network, scripts, diagnostics
| Playwright | in? | why |
|---|---|---|
| `set_viewport_size` | **yes** | a narrow window shows a hamburger menu instead of a nav bar, so a trail recorded at one size can break at another. Fix the size |
| `local_storage` / `session_storage` | **no** | the browser profile already carries these |
| `emulate_media`, `clock` | **no** for now | `clock` is worth remembering for date-dependent dashboards. Noted, not built |
| `screencast`, `video`, `pdf` | **no** | not part of a trail |
| `route`, `route_from_har`, `unroute` | **no** | changes what the site is |
| `add_init_script`, `add_script_tag`, `expose_function` | **no** | injecting code into someone's site |
| `pause`, `pick_locator` | **no** | interactive debugging |
| `screenshot` | **later** | for the dashboard and for explaining a repair, never a step |

## 5. The context — `BrowserContext` (40 methods)

| Playwright | in? | why |
|---|---|---|
| `storage_state` / `set_storage_state` | **already solved** | we keep a whole browser profile, which is stronger |
| `cookies` / `add_cookies` / `clear_cookies` | **no** | the profile handles it |
| `grant_permissions` | **yes, narrow** | a site asking for notifications mid-run blocks it. Deny by default |
| `set_geolocation` | **maybe** | some dashboards are region-dependent. Low priority |
| `set_offline` | **no** | |
| `new_page` / `pages` / `expect_page` | **yes** | needed for popup handling |
| `set_default_timeout` | **yes** | one place to control patience |
| `tracing` | **no** | test framework |
| `route*`, `service_workers`, `new_cdp_session` | **no** | |

## 6. Dialog, FileChooser, Download

| Object | Cairn |
|---|---|
| `Dialog.accept / dismiss / message` | recorded as a step: which choice was made, and what the message said |
| `FileChooser.set_files` | folded into `upload` |
| `Download.save_as / suggested_filename` | **already working** |

---

# What Cairn ends up with

**Actions (16)** — goto, click, double_click, hover, fill, type, clear, press, check,
uncheck, select, upload, scroll_to, scroll, drag, focus/blur

**Navigation and waiting (5)** — back, reload, wait_for(url | element | text | idle), wait

**Reading (1 verb, 8 kinds)** — text, all_text, value, checked, visible, enabled,
attribute, count

**Page events (4)** — dialogs, popups and new tabs, file chooser, `dismiss_when_seen` for
overlays

**Locator kinds (10, from 4)** — role, text, css, href, label, placeholder, test_id, title,
alt, nth/filtered

**Postcondition kinds (10, from 5)** — url_contains, text_present, text_gone,
element_present, element_gone, download, value_is, checked_is, count_is, attribute_is

Every one of these is a thin pass-through to Playwright. The cost is breadth, not depth.

---

# Changes to what already exists

1. **Delete `_COLLECT_JS`.** Replace with `page.locator("body").aria_snapshot(mode="ai")`,
   which returns roles, names, urls and refs, pierces shadow DOM and reaches into iframes.
   About 60 lines of my JavaScript deleted.
2. **Act through `aria-ref=` while exploring.** Verified working, including in frames.
3. **Stored locators stay durable.** Refs are only valid inside one snapshot, so they can
   never be written to memory. The trail keeps role/text/css/href plus the six new kinds.
   **This is why this is a contained change: the memory format, the repair logic and the
   deletion gate are untouched.**
4. **Wait for `visible`, not `attached`**, so animations settle before clicking.
5. **Register `add_locator_handler` for cookie banners** as part of site knowledge, so an
   overlay learned once is dismissed forever after.

---

# Open questions — decide before building

1. **Durable locators inside iframes.** A ref like `f1e2` is not stable. A stored locator
   needs to name the frame as well as the element. Probably `frame:<url-or-name> >> role=…`.
2. **Dialogs during replay - DECIDED 2026-09-01.** A step records the choice **and** the
   message. On replay, if the message has changed, stop and hand it back rather than
   accepting. A trail that recorded "click OK" must never blindly accept a box that now says
   "delete 400 rows?". Note that Playwright's default is to *dismiss* every dialog, which
   would silently cancel a save - so doing nothing is not neutral either.
3. **Popups.** When a click opens a new tab, does the trail continue in the new tab or the
   old one? Must be recorded explicitly, not guessed.
4. **`type` versus `fill`.** Cairn should probably choose automatically — try `fill`, and if
   the value does not stick, fall back to real keystrokes. That is a postcondition doing
   useful work rather than a flag the AI has to reason about.
5. **How many verbs before an AI gets confused? - DECIDED 2026-09-01.** **One `cairn_act`
   tool with an `action` argument.** Never sixteen tools. Tool choice is the most fragile
   part of the whole system - a host AI ignored Cairn entirely and reached for `curl` on the
   first live test. Sixteen more names to choose between makes that worse. The action list
   lives in one description where it can be read at a glance.

---

# Prior work to declare

- **Playwright** (Apache-2.0) — Cairn calls it; nothing is copied. The mistake being
  corrected here was writing our own version of something it already provided.
- **`@playwright/mcp`** — their tool design is the reference for which verbs an AI actually
  needs and how to describe them. Design influence, no code. Must go in the README's Prior
  Work section.

---

# Cost and the decision

Roughly **1½ to 2 days** with tests, done properly.

Phases 0–2 are complete and the deadline is Sep 10, so this fits — but it means dropping
the backend and the dashboard. `MASTER-PLAN.md` already lists those as the first two things
to cut, and says never to cut the memory showcase.

I argued for cutting this to half a day and spending the rest on the memory story, since
"coordination and dynamic-storage patterns top the band" is where the 40% is won.

**Rohit's call, 2026-09-01: build all of it, cut nothing.** He does this kind of work
himself, so the browsing layer is not a demo prop - it is the reason the tool exists. Nine
days is enough for both, and the coordination half is now Phase 5a, which needs no
blockchain and is not blocked.

Scheduled as **Phase 2.5, Sep 2-3**. `MASTER-PLAN.md` carries the day-by-day schedule.

## Progress

- **2.5c — the action set: DONE 2026-09-01.** All 21 `Locator` actions plus 6 page-level
  ones, in one registry, wired into both the cold and the warm path. 46 tests. Five real
  bugs found on the way, listed in section 1.
- Still to do: 2.5a snapshot, 2.5b waiting, 2.5d reading, 2.5e locators, 2.5f page events,
  2.5g the MCP surface, 2.5h the hard page.
