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
