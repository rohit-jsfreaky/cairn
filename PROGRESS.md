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

- **2026-09-04 (the README memory note)** — added a section named exactly **"How memory made
  this possible"**, which the submission rules ask for by name. The substance was already
  spread across "Where the memory lives" and "Forgetting"; a judge working down a checklist
  should not have to infer it from two other sections.

  It names the three abilities that exist only because of the memory layer, which is also the
  language the scoring band uses: a route that outlives the session (warm `playbook`, unique
  per `(tenant, category, name)`); **dynamic storage** — locator ranking and health written
  back by every run, which is why a changed site costs one repaired step instead of a fresh
  exploration; and **coordination** — sharing, borrowing and buying, which are moves between
  Sibyl tenants and the only channel two Cairn agents have. Then the cold tier as the audit
  trail, and `cairn forget` raising `NoTrailError` as the deletion test in one command.

  Every claim in it was checked against the code before writing: `record_hit`/`record_miss` on
  both step and locator, `save_playbook` called back on the replay path (`executor.py:265`,
  `:637`, `:683`), and `NoTrailError` raised rather than a quiet fall back to exploring.

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

  One thing that cannot be fixed, only worked around: Git Bash rewrites `--path /settings`
  into `C:/Program Files/Git/settings` before Cairn ever sees the argument. Nothing here can
  stop that. The slashless form works, and the help text says so.

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

  **Published 0.2.0 on 2026-09-05**, engine first, then the MCP package. Verified the way a
  stranger meets it: a brand-new venv, `pip install cairn-browser-mcp` from real PyPI. The
  dependency floor did its job — it pulled the engine from 0.1.0 up to 0.2.0 on its own. The
  server starts, lists 16 tools with `cairn_map` among them, and `cairn doctor` is clean.

  **The full suite did NOT run locally before this.** Rohit's laptop was overheating from
  repeated browser runs, so it was left to CI on GitHub's machines. What did run since the
  last source change: `test_site_map.py` (57), `test_locators.py` and `test_snapshot.py`
  (the two files the `link_target` change actually touches), plus the clean-venv install
  check above. The rest is CI's job on the next push, and if it is red the fix ships as
  0.2.1 — a PyPI version can never be replaced.

- **2026-09-05 (the real domain, and the images)** — Rohit bought **cairnmcp.fun**.

  `metadataBase` now DEFAULTS to it rather than falling back to `http://localhost:3000`. That
  fallback was a real trap: a deploy that forgot the environment variable would publish
  `http://localhost:3000/opengraph-image` as its social card — a link broken everywhere except
  the machine that built it. `NEXT_PUBLIC_SITE_URL` still wins, so a preview deployment can
  point at itself. Added a canonical URL, `og:url`, `og:site_name`, `og:locale`, plus
  `robots.ts` and `sitemap.ts` that both read the same constant, so the domain cannot be right
  in one place and stale in another.

  **The page art is WebP now: 2,008 KB became 27 KB.** `hero-sky` 1,155 → 18 KB and
  `band-glow` 853 → 9 KB, at `cwebp -q 82 -m 6`, which measures ~50 dB PSNR — visually
  identical, and the built page was checked side by side to be sure.

  **The social cards were deliberately NOT converted to WebP**, though that is what was asked
  for. Next's own installed docs (`node_modules/next/dist/docs/.../opengraph-image.md`) list
  `.jpg .jpeg .png .gif` for `opengraph-image` and `twitter-image`, and `.ico .jpg .jpeg .png
  .svg` for icons — WebP is in neither, and social platforms handle it badly anyway.
  Converting them would have broken the exact thing the domain change exists to fix. They went
  to progressive JPEG instead: **651 KB → 62 KB each**, checked by eye for artefacts.

  `logo-mark.png` and `logo.svg` are referenced by nothing — the mark is drawn inline in
  `CairnMark`. Left in place as source assets for the posts and the video rather than deleted.

  Both `pyproject.toml` Homepages now point at the site. That only reaches the PyPI page on the
  NEXT release; 0.2.0 went out an hour earlier and cannot be re-uploaded.

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
