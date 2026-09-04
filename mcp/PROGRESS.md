# PROGRESS — mcp/ (THE PRODUCT)

> Working memory for this folder. Read first, update before ending every session.

## Current state — 2026-09-01

**PHASE 2 IS DONE. The finish line passed on a live Claude Code session, 2026-09-01.**

24 tests pass, ruff clean, real stdio transport verified, and all four beats ran in a
CLEAN Claude Code session in a DIFFERENT folder (`D:\my_projects\project_research`).

```
pytest mcp        22 passed
ruff check mcp    All checks passed
stdio handshake   server: cairn, 9 tools listed, structured results returned
```

## What exists

```
mcp/
  pyproject.toml            distribution `cairn-mcp`, console script `cairn-mcp`
  README.md                 install for Claude Code / Cursor / Codex + the 4-beat demo
  src/cairn_mcp/
    server.py               all 9 tools, thin wrappers over the engine
    __main__.py             `python -m cairn_mcp`
  tests/
    conftest.py             demo site + a server with its own memory db
    helpers.py              call() a tool the way a host AI would
    test_server.py          22 tests
```

Plus `../.mcp.json` at the repo root, so Claude Code opened in this repo offers the server
with a **relative** command — clone, make the venv, approve, done. Verified with
`claude mcp list`: `cairn: .venv/Scripts/python.exe -m cairn_mcp - Pending approval`.

## The 9 tools

| tool | path | note |
|---|---|---|
| `cairn_run` | warm | the product. One call, 0 model calls, 0 pages read. |
| `cairn_repair` | warm | applies the host AI's fix to ONE step |
| `cairn_sites` `cairn_show` `cairn_forget` | warm | inspect and wipe |
| `cairn_open` `cairn_look` `cairn_act` `cairn_save` | cold | only for a site never seen |

Two departures from the table in CLAUDE.md, both deliberate:

- **`cairn_open` added.** The plan routed navigation through `cairn_act(action="goto")`.
  That is awkward to describe and easy for a host AI to get wrong, and tool descriptions
  are the entire UX here. A named tool for "start here" is clearer.
- **`cairn_repair` added.** `cairn_run` can detect a break and describe it, but applying
  the fix needs a second call, because the host AI is the thing that decides what the new
  control is. Without this tool the repair loop cannot close.

## Decisions

- **Official `mcp` SDK, not the `fastmcp` package.** Reasons in `../RESEARCH.md`; the short
  version is that FastMCP ships inside the official SDK, `mcp` was already installed, and
  Sibyl's own MCP server uses exactly this shape.
- **The browser runs on its own thread** (`cairn/worker.py` in the engine). Playwright's
  sync API binds objects to their creating thread and refuses to run inside an asyncio
  loop; an MCP server breaks both rules. Marshalling every call onto one thread is the
  proper fix, not a workaround.
- **Every tool returns a `next` string** when the AI has more to do. The result is the only
  thing it sees, so telling it what to do next is not decoration, it is the control flow.
- **Tool descriptions are tested.** `TestToolDescriptions` asserts `cairn_run` says
  "TRY THIS FIRST" and appears before `cairn_open` in the server instructions. A host AI
  that reaches for the cold tools on a known site would quietly destroy the whole point of
  the project, so the wording that prevents it cannot be allowed to rot silently.

## The finish line — PASSED 2026-09-01, observed live

Clean Claude Code (v2.1.252, Opus 5), folder `D:\my_projects\project_research`, which has
never contained any Cairn code.

| beat | asked | what happened |
|---|---|---|
| recall | "Download this month's invoice from http://127.0.0.1:8787" | **one** cairn call. 4 steps replayed, ~2s, no page reading. Reported the saved path. |
| repair | "same thing but the site is now at ...?variant=b" | 2 cairn calls. 3 steps replayed, step 4 broke, it chose `#get-pdf` ("Get PDF"), repaired, re-ran. Said the fix is saved so the next run needs no repair. |
| gate | "Forget 127.0.0.1:8787" | forgotten, and it explained the consequence unprompted: the next download "will need full exploring again". |

**Discovery worked with no prompting.** It went straight to `cairn_run` without being told
to use Cairn — the description rewrite (below) is what fixed that.

### The two failures that got us here, both real

1. **It used `curl` and ignored Cairn entirely.** Cause: `cairn_run`'s summary line read
   "a website **that Cairn already knows**" — a condition the AI cannot evaluate while
   scanning the tool list, so it skipped the tool. And "TRY THIS FIRST, before any other
   **Cairn** tool" only ranked our own tools against each other; it never mentioned the
   shell, which is what it actually chose. Fixed by opening unconditionally with "USE THIS
   FOR ANY WEBSITE TASK" and naming curl/wget/fetch/shell explicitly. Pinned by tests.

2. **Downloads never reached disk.** Found by the host AI itself, not by our tests.
   `Browser` accepted a `downloads` path that nobody passed, so Playwright deleted the file
   when the context closed. Our test only asserted the download *event* fired — it was
   green while proving the wrong thing. Fixed with a default `~/.cairn/downloads`, deferred
   saving (saving inside Playwright's event callback fails with "Download.save_as:
   canceled"), and `saved_files` reported through run/CLI/MCP. Tests now assert a real
   non-empty file.

**Lesson worth keeping:** a real host AI on a real task found a bug that 94 passing tests
did not. Assert the user-visible outcome, not the internal event.

**Phase 1g is DONE (2026-09-02).** Proven through these tools on 8 real websites, two of
them signed in. Nothing here is demo-site-only any more.

## Session log

- **2026-08-31** — folder created, plan written. No code.
- **2026-09-01** — Phase 2 built in one pass. SDK decision closed by reading Sibyl's own
  installed server rather than docs. Found and fixed the Playwright-threading problem with a
  dedicated browser thread in the engine. `call_tool` turned out to return a
  `(blocks, structured)` tuple, which cost one debugging round. Install docs written and the
  project-scoped `.mcp.json` verified with `claude mcp list`.
- **2026-09-02/03** — surface collapsed to `cairn_act` + `cairn_read`, both descriptions
  GENERATED from the engine registries so a capability cannot exist without being
  discoverable. Three commons tools added (`cairn_share`, `cairn_borrow`, `cairn_commons`)
  and the `cairn_run` miss branch rewritten so `next` is REPLACED, not appended — left as it
  was it said "explore this site" and "do NOT explore this site" in the same message.
  `run_stdio()` now reads `CAIRN_AGENT`, `CAIRN_PROFILE` and `CAIRN_DB`, so a second agent
  can be configured from `.mcp.json` at all — before this there was no way to.
  `cairn_forget` now reports what it withdrew from the commons and what it cannot reach.
  **80 tests, ruff clean.**

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

- **2026-09-04 (items 1 and 2 tested for real — both pass)** — the two things a test suite
  could not prove, driven through the actual `cairn-mcp` processes over stdio rather than
  in-process, with a small MCP client written for the purpose.

  **Two agents at once, two profiles — PASSES.** Two real `cairn-mcp` processes with
  different `CAIRN_AGENT`, `CAIRN_PROFILE` and `CAIRN_DB` both opened a browser and read a
  page while the other still held its own. Chrome allows one process per profile, and this
  is exactly what the x402 demo needs; it had never been tested and could only have failed
  in front of a judge.

  **The whole story through the MCP tools — PASSES, including a real payment.** Alice
  learned the demo site through `cairn_act`/`cairn_read`/`cairn_save` (6 steps), replayed it
  warm (6 steps, 0 model calls), shared it and opened a shop. Bob — his own agent, profile
  and memory — bought it through **`cairn_buy`**, which had never been driven through the
  tool surface before, only the CLI. Real settled payments on Base Sepolia each run:
  `0x322eb239…`, `0x103f939a…`. Then `cairn_forget` and the site went back to unknown with
  `was_forgotten=True`.

  **Two apparent failures turned out to be the product being right.** A bought trail would
  not replay for Bob — because `for_sharing()` strips EVERY typed value, so the trail needed
  BOTH `email` and `password`, and the harness had supplied only the password. `cairn_buy`
  had already said so in `you_must_supply`; the harness ignored it. With both set, Bob
  replays 6 of 6. That is the headline feature working: what is sold is the route, never the
  account.

  **One thing left unexplained.** On the first attempt the shop answered HTTP 500 to the
  paid request. It has not reproduced in four later runs. The only suspect is two processes
  holding one SQLite memory file at once — Alice's MCP server and Alice's shop — after the
  MCP server had just failed a run mid-way. Worth knowing before the demo: share from the
  CLI and start the shop, rather than pointing a busy MCP server and a shop at the same
  database.

- **2026-09-05 (Phase 6b — the map reaches the host AI)** — the engine now records every page
  it looks at (`package/PROGRESS.md` has the why). This folder is how an AI ever hears about
  it, which is the half that decides whether the memory does any work at all.

  **Pushed, not pulled.** `cairn_run` returns `pages_known` on all five branches where the AI
  is about to explore — needs_task, the three unknown shapes, and stale. Never on success,
  repair, blocked or needs_login: there is nothing to explore there.

  **Index then detail.** A forty-page map cannot ride inside every reply and most of it is
  irrelevant to any one task, so `cairn_run` carries the table of contents (capped at 25) and
  `cairn_map(site, path)` opens one page.

  **A real bug fixed.** The `needs_task` branch is exactly where a genuinely new task on a
  known site arrives, and it used to end "Do NOT explore, the trail is already there". Right
  when one of `tasks` fits, wrong when none does. It now says both halves.

  **The map is actionable, which is the point.** Each control comes back with a `use` string —
  `role=button|Sign in` — that `cairn_act` takes directly as `ref`. Without it the AI would
  know the button was there and still have to read the whole page to get a ref. Both tool
  descriptions say so, in the house voice.

  `cairn_run`'s docstring promised "three possible answers" while the body had ten shapes.
  It now names needs_task too, and the map.

  16 tools. 112 MCP tests, ruff clean.
