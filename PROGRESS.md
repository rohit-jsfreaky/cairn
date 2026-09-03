# PROGRESS — Cairn (root live state)

> Read this first, every session. Update it before ending the session.
> Per-folder detail lives in `package/PROGRESS.md`, `backend/PROGRESS.md`, `frontend/PROGRESS.md`.

## Current state — 2026-09-03

- **Current phase:** 6 (harden). Phases 0, 1, 1g, 2, 2.5, 5a and **5b (Base x402)** are DONE.
- **The product is feature-complete.** Engine, MCP server, real sites, agent-to-agent
  memory, README and landing page are all finished. What is left is hardening.
- **518 engine tests + 98 MCP tests, all green. Ruff clean in both packages.**
- **PHASE 1g IS DONE — proven on 8 real websites**, not the demo site. GitHub and PostHog
  were walked by hand; Hacker News, PyPI, MDN, Wikipedia, Next.js and Hugging Face were
  never tuned for and 6 of 6 replayed warm. Measured on GitHub warm: **1 tool call,
  1391 ms, 0 model calls, the answer returned.**
- **PHASE 2.5 IS DONE** — 35 actions, 14 reads, 9 locator kinds, 5 wait kinds, all behind
  two tools (`cairn_act`, `cairn_read`) whose descriptions are GENERATED from the
  registries, so a capability cannot exist without being discoverable. `evaluate` is the
  escape hatch and is deliberately never recorded into a trail.
- **PHASE 5a IS DONE** — agent-to-agent memory. Agent identity is a Sibyl tenant; the
  commons is one fixed tenant; sharing strips every typed value and the account; borrowing
  is explicit; a repair can be contributed back. The deletion gate stays honest via a
  tombstone, so a forgotten site is never quietly offered back.
- **The landing page numbers are now MEASURED, not placeholders.** `package/benchmark.py`
  prints them and anybody can run it. The old figures (2m 41s, 4.1s, 31 calls, 39x) are
  gone from the repo. The default metric is now tool calls, not the clock — the benchmark
  contains no model thinking time, and thinking time is what memory actually removes.
- **The README is a product README**, not a build log. Every claim in it was checked
  against the code before it was written.
- **Deletion gate proven on a real logged-in site**, not just in tests: memory gone,
  re-exploration forced, the login survived.

## Done

- [x] Idea locked via the hackathon_ideas pipeline (see that repo's IDEAS-LOG.md)
- [x] Rules, scoring, submission requirements verified from the live site (2026-08-31)
- [x] Sibyl Memory API verified from docs → `RESEARCH.md`
- [x] Package versions verified on PyPI/npm → `RESEARCH.md`
- [x] Folder scaffold + plans + rules files

## ▶ START HERE NEXT

**Phase 6 — harden.** Everything else is done. Phase 5b's finish line was passed on
2026-09-03 with a real payment on Base Sepolia (see the session log), so the ×1.15 is earned
and the evidence link is in the README.

What hardening means here: run the whole loop several times over, on more than one site, and
fix whatever moves. The wallets already hold 19.99 test USDC, which is about 2,000 more
demo runs, so rehearsing costs nothing.

Cut list, in the order to cut if a day is lost:

- **Phase 3 (backend) and Phase 4 (dashboard) — recommended for cutting.** They are worth
  points only if everything else is finished. The memory showcase is 40% of the score and
  is already built; a dashboard adds polish, not points.
- ~~Phase 5b (Base x402) is blocked~~ — DONE 2026-09-03, with a real settled payment.
- **Phase 7 (full Playwright parity) is deferred by Rohit's own decision.** Nothing is
  discarded — the remaining surface is written down, just not built yet.

**Not to be raised until the product is finished:** the demo video and the two public
posts. Rohit does those himself, last.

## Decisions that stay locked (do not reopen)

Phase 2.5 (the browsing layer) is BUILT — see Current state. It began because a live test on
2026-09-01 found our snapshot returning **1 element** on a page where Playwright's own
snapshot found 7, across a React dropdown, a shadow DOM, an iframe and a late-loading link.
The snapshot now runs on Playwright's own engine. Full capability audit, with a reason for
each in/out decision: `package/BROWSING.md`.

**Two decisions locked 2026-09-01, not open again:**

1. **One `cairn_act` tool with an `action` argument**, never sixteen MCP tools. Tool choice
   is the most fragile part of this system - a host AI ignored Cairn completely and used
   `curl` on the first live test. More tool names makes that worse.
2. **Dialogs record the choice AND the message.** On replay, stop if the message changed. A
   trail that recorded "click OK" must never blindly accept a box that now reads "delete 400
   rows?". Playwright's own default is to dismiss every dialog, which would silently cancel a
   save - so doing nothing is not neutral either.

**Nothing is being cut.** I argued for trimming the browsing work to half a day and spending
the rest on the coordination story, since "coordination and dynamic-storage patterns top the
band" is where the 40% is won. Rohit's call: build all of it. He does this kind of automation
himself, so the browsing layer is the reason the tool exists, not a demo prop. Both got
built: the browsing layer as Phase 2.5, the coordination story as **Phase 5a**, which was
split out of Phase 5 because it needs no blockchain and no Discord answer.

3. **The remaining Playwright surface is deferred, not discarded** (Rohit, 2026-09-02).
   `evaluate` is the escape hatch that covers anything unbuilt, and what is left is written
   down in `package/BROWSING.md` for a session that has spare time.

## Positioning answers (settled 2026-08-31 — use these in the README and the pitch)

- **vs Playwright MCP:** Playwright MCP has no memory, so run 2 costs what run 1 cost, forever.
  Cairn is built on Playwright and adds memory: repeat cost (1 tool call vs ~30), context
  window saved, and deterministic replay. Not a competitor — the layer above.
- **vs "the AI just writes notes into memory":** prose notes = the "trivial notepad" the rules
  say scores at the floor. A Cairn playbook is executable, self-verifying, self-repairing.
- **Hermes Agent (Nous Research):** Sibyl officially supports it; it runs unattended on cron,
  which is the strongest case for deterministic replay. Details in RESEARCH.md.

## Open questions / blockers

- ~~Discord answer pending: does Base Sepolia count for the partner bonus?~~ — CLOSED BY
  DECISION 2026-09-03. Never answered, and we stopped waiting. The rules ask only for "an
  executed onchain action"; the free public facilitator lists no mainnet at all; prizes are
  paid in USDC and the organisers "help winners set up a wallet"; a rival entry is openly on
  Base Sepolia. Mainnet is three environment variables if it ever matters.
- Discord answer pending: is pre-window scaffolding OK if declared as prior work?
  (Declared in the README either way, so this is not blocking.)
- ~~Which 1-2 real sites for the demo~~ — ANSWERED 2026-09-02. **GitHub** (count open
  issues on a repo) and **PostHog** (read a number off the dashboard, signed in). Six more
  were replayed warm with no tuning at all: Hacker News, PyPI, MDN, Wikipedia, Next.js,
  Hugging Face. Both chosen sites fit the criteria decided 2026-08-31 — a BORING task a real
  person repeats, captcha-free and stable.
- Does Hermes load MCP servers directly, or does it need a plugin adapter? (OpenClaw is
  already confirmed to accept MCP servers.)
- ~~Anthropic API key + budget~~ — NO LONGER NEEDED (product-shape decision, see log)

## Session log

- **2026-08-31** — idea pipeline run, name chosen (Cairn), scaffold + plan files created.
- **2026-08-31 (later)** — `mcp/` split into its own folder. MCP SDK candidates verified:
  `mcp` 2.1.1, `fastmcp` 3.4.7.
- **2026-08-31 (product shape locked — Rohit's call, biggest decision so far):** Cairn is a
  TOOL, not an agent with its own brain. The user's Claude Code / Codex / Cursor does the
  thinking; Cairn supplies the browser and the memory. Warm replay = deterministic Python,
  zero model calls, no API key needed by anyone.
  **NO Anthropic API.** OpenRouter only, and only for an optional standalone mode or tests.
  Consequences: `mcp/` promoted 4a → **Phase 2 (the product)**; backend → 3; frontend → 4;
  x402 → 5; ship → 6. `package/llm.py` replaced by `operations.py` (the verbs a caller drives)
  plus an optional `model.py`. Cost to build drops to ~₹0. Distribution and the fresh-session
  proof both get much stronger.
- **2026-08-31 (distribution researched):** OpenClaw (388k★) confirmed to accept MCP servers;
  Hermes Agent (Nous Research) is officially supported by Sibyl and runs unattended on cron.
  Locked the "one plug, many sockets" rule — one MCP server, install docs per agent, never a
  separate build. Canonical pitch line written into CLAUDE.md. Demo-task criteria decided
  (boring + repeated beats clever). Full landscape in RESEARCH.md.
- **2026-09-01** — Landing page built in `frontend/`. Next.js 16.3.3 + Tailwind v4.3 (install
  steps re-read from the live docs, `create-next-app` pins an unpublished next version — see
  RESEARCH.md). Design system measured off aside.com with Playwright rather than eyeballed.
  Art generated in ChatGPT: misty-trail hero and top-down pebble closing band; two attempts at
  generating product UI were worse than markup and were dropped. Animation: Lenis smooth
  scroll on the GSAP ticker, ScrollTrigger reveals, SplitText headings, DrawSVG, count-ups.
  Logo + favicon drawn as vector from the generated mark.
- **2026-09-01 (engine started)** — Registration confirmed done. Repo created and pushed by
  Rohit (public, MIT). Phase 0 passed: Sibyl round-trips across a fresh process on Windows,
  and needs no account. Phase 1a built: models + store + 12 tests, all green. Sibyl version
  numbers in RESEARCH.md corrected — the ones read off PyPI on 08-31 were already stale.
- **2026-09-01 (Phase 1 built)** — whole engine in one pass: browser, operations, distill,
  executor, events, CLI, deletion gate. 72 tests green, ruff clean. Two real bugs caught by
  tests: structural locators were matching whole hrefs including the query string, and the
  demo site's variant B was not actually breaking anything. Measured cold vs warm: 2.3x
  wall-clock locally, 9x fewer tool calls, 0 model calls.
- **2026-09-01 (Phase 2 built)** — Cairn as MCP tools: 9 tools, 22 tests, real stdio
  handshake verified. Two tools added beyond the plan (`cairn_open`, `cairn_repair`) because
  the repair loop cannot close without the second one. SDK question closed by reading
  Sibyl's own installed MCP server. Solved Playwright-in-an-event-loop with a dedicated
  browser thread in the engine, which the backend will reuse.
- **2026-09-01 (Phase 2 DONE)** — finish line passed on a live Claude Code session in a
  different folder: recall in one call, one-step repair, and forget. Two real bugs found on
  the way: the tool description lost to `curl` because it opened with a condition the AI
  could not evaluate, and downloads were never written to disk while a green test asserted
  only that the download event fired.
- **2026-09-02/03 (Phase 1g, 2.5 and 5a all DONE)** — proved warm replay on 8 real sites
  including two signed-in ones, then widened the browser surface to 35 actions and 14 reads
  behind two generated tools, then built agent-to-agent memory on Sibyl tenants. Real bugs
  the work exposed, all fixed: Playwright's aria snapshot printed passwords in plain text;
  `search_similar` had NEVER worked (it read `.entities` off a list subclass and returned
  `[]` every time); the executor silently did nothing for unknown actions and recorded that
  as success; only click and press waited for the page, so a `select` that navigated was
  never waited for; the Chrome fallback caught every error and quietly signed the user out;
  CSS paths stopped at 5 levels and matched several elements. Three tests turned out to be
  asserting bugs and were rewritten.
- **2026-09-03 (the loose ends closed)** — `cairn_forget` now says what it withdrew from the
  commons AND what it cannot reach, because Sibyl offers no way to enumerate tenants and
  that boundary is a guarantee rather than a shortcoming — but only if somebody says so.
  Landing page placeholders replaced with measured numbers from the new
  `package/benchmark.py`. README rewritten as a normal open-source product README, on the
  shape of openclaw's, with every factual claim verified against the code first.

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
