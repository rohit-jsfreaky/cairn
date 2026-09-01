# PROGRESS — Cairn (root live state)

> Read this first, every session. Update it before ending the session.
> Per-folder detail lives in `package/PROGRESS.md`, `backend/PROGRESS.md`, `frontend/PROGRESS.md`.

## Current state — 2026-09-01

- **Current phase:** 3 (backend). Phases 0, 1 and 2 are built.
- **Phase 0 finish line passed 2026-09-01:** Sibyl memory round-trips across a genuinely
  separate process on Windows. No account needed — `MemoryClient.local()` works with zero
  credentials, so the "no key, no account" claim is literally true. Details in RESEARCH.md.
- **PHASE 2 (the MCP server) IS DONE — finish line passed live on 2026-09-01.** A clean
  Claude Code session in a different folder did all four beats: recall in one call, repair
  of one step, and forget. It reached for `cairn_run` on its own with no prompting.
  24 tests, ruff clean. Evidence in `mcp/PROGRESS.md`.
- **PHASE 1 (the engine) IS BUILT.** 72 tests pass, ruff clean. Browser, look/act/verify,
  distill, warm executor with drift detection and repair, typed events, CLI, demo site,
  and the automated deletion gate. `store.py` is still the only file that imports
  `sibyl_memory_client`.
- **One finish-line criterion needs your call.** MASTER-PLAN asks for ">=5x faster" on a
  warm run. Measured on the local demo site it is **2.3x** wall-clock, because both runs do
  the same six browser actions and our scripted cold run has **no model thinking time in
  it** — which is the entire cost Cairn actually removes. The numbers that do not depend on
  model speed are solid: **9 tool calls -> 1, 6 page reads -> 0, 0 model calls**. The real
  multiplier can only be measured in Phase 2 with a live Claude Code driving the cold run.
  Detail in `package/PROGRESS.md`. Flagged, not assumed.
- **Registered on hack.sibyllabs.org:** NOT CONFIRMED — Rohit was told twice, closes TONIGHT
  Aug 31 23:59 UTC. Ask him directly if unclear.
- Project named **Cairn** (2026-08-31). Old working name "Muscle Memory" dropped — clashes
  with pig-dot-dev/muscle-mem (766★). "Engram" also dropped — engram.com is a live AI
  product ("AI That Learns From You").
- Scaffold + all planning files created 2026-08-31 (this counts as declared prior work).
- **Sep 1: the landing page is built** in `frontend/` (Next.js + Tailwind v4 + GSAP + Lenis).
  This is out of phase order — Rohit asked for it first. The engine (Phase 1) is still not
  started, and it is the part that must not slip.
- Every number on the landing page is a placeholder. It must be replaced with numbers from a
  real run before the repo is public. See `frontend/PROGRESS.md` Blockers.

## Done

- [x] Idea locked via the hackathon_ideas pipeline (see that repo's IDEAS-LOG.md)
- [x] Rules, scoring, submission requirements verified from the live site (2026-08-31)
- [x] Sibyl Memory API verified from docs → `RESEARCH.md`
- [x] Package versions verified on PyPI/npm → `RESEARCH.md`
- [x] Folder scaffold + plans + rules files

## ▶ START HERE NEXT

**Phases 0, 1 and 2 are done on day 1 of a 10-day window.** The product works end to end.
What is left is what wins points, in this order:

1. **Phase 1g — a real site.** Everything so far is the local demo. One boring, captcha-free
   real site proves this is not a toy. Criteria are already decided further down this file.
2. **Phase 6 pieces that cannot be rushed** — the demo video (the unedited recall beat), and
   replacing the landing page's placeholder numbers with measured ones.
3. **Phase 3 backend + Phase 4 dashboard** — worth doing since we are ahead, but the cut
   order says these go before the memory showcase if time gets tight.

Still outstanding from Phase 1g: pick 1-2 real captcha-free sites and prove the loop there
too. Everything so far is against the local demo site.

Run everything with the repo-root venv: `.venv/Scripts/python.exe`.
Demo site: `python package/tests/demo_site/app.py` (port 8787, variants a / b / c).

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
- Which 1-2 real sites for the demo: not chosen yet. **Criteria (decided 2026-08-31):** a
  BORING task a real person actually repeats — check a dashboard every morning, download a
  monthly invoice/report, refill the same form, pull numbers off an internal tool with no API.
  Boring = repeated = exactly when memory pays. Must be captcha-free and stable. Do not pick
  something clever.
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
