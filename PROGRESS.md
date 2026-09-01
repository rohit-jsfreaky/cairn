# PROGRESS — Cairn (root live state)

> Read this first, every session. Update it before ending the session.
> Per-folder detail lives in `package/PROGRESS.md`, `backend/PROGRESS.md`, `frontend/PROGRESS.md`.

## Current state — 2026-09-01

- **Current phase:** 0 (Setup) — plus the landing page, built out of order on Rohit's call.
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

## ▶ START HERE TOMORROW (Sep 1, day 1)

Read `../CLAUDE.md`, then `MASTER-PLAN.md`, then `package/PLAN.md`. Then, in order:

1. **Check with Rohit:** is registration done? Any Discord answers yet?
2. **Phase 0 finish line** (30 min): `pip install 'sibyl-memory-cli[mcp]'` → `sibyl init` →
   `playwright install chromium` → write a throwaway script that saves an entity and reads it
   back **from a second fresh process**. Confirm Windows paths work for `MemoryClient.local()`.
3. **Then Phase 1a** — `package/PLAN.md`: models + store + fresh-process test.

Do not skip step 2. If Sibyl does not round-trip on Windows, everything else is built on sand.

No API key is needed for any of this. That is by design — see the product shape.

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
