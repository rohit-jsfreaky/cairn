# PROGRESS — Cairn (root live state)

> Read this first, every session. Update it before ending the session.
> Per-folder detail lives in `package/PROGRESS.md`, `backend/PROGRESS.md`, `frontend/PROGRESS.md`.

## Current state — 2026-09-03

- **Current phase:** 6 (harden). Phases 0, 1, 1g, 2, 2.5 and 5a are DONE.
- **The product is feature-complete.** Engine, MCP server, real sites, agent-to-agent
  memory, README and landing page are all finished. What is left is hardening.
- **479 engine tests + 80 MCP tests, all green. Ruff clean in both packages.**
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

**Phase 6 — harden.** The only thing left before submission is proving it does not wobble:
run the whole loop several times over, on more than one site, and fix whatever moves.

Cut list, in the order to cut if a day is lost:

- **Phase 3 (backend) and Phase 4 (dashboard) — recommended for cutting.** They are worth
  points only if everything else is finished. The memory showcase is 40% of the score and
  is already built; a dashboard adds polish, not points.
- **Phase 5b (Base x402) is blocked** on Discord and is not worth waiting for.
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

- Discord answer pending: does Base Sepolia (testnet) count for the partner bonus?
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
