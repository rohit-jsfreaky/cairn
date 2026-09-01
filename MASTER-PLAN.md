# MASTER-PLAN — Cairn

One page. Phases, order, finish lines. Details live in each folder's own PLAN.md — do not
duplicate them here.

**Rule:** a phase only depends on earlier phases. A phase is DONE only when its finish line
passes. If the finish line does not pass, the phase is not done, no matter how much code exists.

## ⭐ The shape of the product (decided 2026-08-31, Rohit's call — read this first)

**Cairn is a TOOL, not an agent with its own brain.** The user's existing AI — Claude Code,
Codex, Cursor — does the thinking. Cairn gives it a browser plus memory.

Why: no API cost for us, anyone installs it in one command (real users → PMF evidence), a
judge tries it inside their own Claude Code with no key to set up, and "fresh session" becomes
the most legible thing in the world (close Claude Code, open it again).

- **Cold run:** the host AI explores the site through Cairn's tools. Many tool calls. Slow.
  Cairn writes the playbook to Sibyl.
- **Warm run:** one `cairn_run` call. Cairn replays the playbook itself — deterministic Python,
  **zero LLM**. Fast.
- The contrast is visible right in the Claude Code transcript. That is the demo.

**No Anthropic API.** If a model is ever needed (optional standalone mode, tests), it goes
through **OpenRouter** only, behind one interface, never required for the main path.

Build order follows dependencies: package → mcp → backend → frontend.

---

## Phase 0 — Setup · Aug 31 / Sep 1  — PASSED 2026-09-01

- Register on hack.sibyllabs.org (closes Aug 31, 23:59 UTC)
- Ask in Discord: testnet OK for Base bonus? scaffolding before Sep 1 OK if declared?
- Install: `pip install 'sibyl-memory-cli[mcp]'`, run `sibyl init`, install Playwright browsers
- Rohit creates the empty GitHub repo (public, MIT)

**FINISH LINE:** a 5-line Python script writes an entity with `sibyl-memory-client`, then a
SECOND fresh process reads it back. Memory round-trip proven on this Windows machine.

## Phase 1 — The engine · Sep 1–4 · `package/` → `package/PLAN.md`  — BUILT 2026-09-01

Browser control, playbook memory, deterministic replay, verification, self-repair. No LLM
inside — the engine exposes operations; whoever calls them does the thinking.

**FINISH LINE (all four, driven from the CLI, on the local demo site + 1 real site):**
1. Cold: guided by tool calls, the task completes and a playbook appears in memory.
2. Warm: `cairn run` replays it in a fresh process, ≥5× faster, **with no model involved**.
3. Break the site (`?variant=b`) → the broken step is detected, repaired alone, persisted;
   next run fast again.
4. `cairn forget --site X` → replay has nothing to follow and reports it. Automated in
   `tests/test_deletion_gate.py` — the judges' litmus test, one command.

## Phase 2 — MCP server · Sep 4–5 · `mcp/` → `mcp/PLAN.md`  — BUILT 2026-09-01

**This is the product.** Cairn as MCP tools, so Claude Code / Codex / Cursor becomes the brain.

**FINISH LINE:** from a CLEAN Claude Code session on another folder — ask it to do the demo
task, it explores through Cairn's tools and learns. Quit Claude Code. Open a fresh session.
Ask again → one `cairn_run` call, done in seconds. Then `cairn_forget` → slow again.

## Phase 2.5 — The browsing layer · Sep 2–3 · `package/` → `package/PLAN.md` §2.5

**Why this phase exists.** Cairn was tested on a page with a React-style dropdown, a shadow
DOM, an iframe and a late-loading link. Our snapshot found 1 element; Playwright's found 7.
The browsing layer is a quarter of what a real website needs, and a memory layer on top of a
browser that cannot reach the second page of a real site is worth nothing.

The full audit of every Playwright capability, and the reason for every in/out decision, is
in `package/BROWSING.md`. Read it before starting.

**Not a rewrite.** Stored locators stay durable, so the memory format, the repair logic and
the deletion gate are untouched. Only "what is on this page" and "what can I do to it"
change.

**STATUS: COMPLETE 2026-09-01.** All eight steps done, 385 tests. Two items below
carry a caveat — see the honest read-out in `package/PROGRESS.md`.

**FINISH LINE (all five):**
1. On the hard page (dropdown built from divs, shadow DOM, iframe, late content, cookie
   banner) every control is found and can be acted on.
2. All sixteen actions and all eight reads record, replay and verify on the demo site.
3. The cold path is ONE `cairn_act` tool with an `action` argument, not sixteen tools, and
   three vague prompts route to the right action.
4. A confirm dialog is recorded with its message; replay stops if the message changed.
5. A cookie banner learned once is dismissed automatically on every later run.

## Phase 3 — Backend · Sep 6 · `backend/` → `backend/PLAN.md`

Thin FastAPI server over the package: run lifecycle, live event stream (SSE), memory
snapshots. No business logic.

**FINISH LINE:** with only `curl` — start a run, watch live events including every memory
read/write, fetch the playbook JSON, trigger forget.

## Phase 4 — Frontend · Sep 6–7 · `frontend/` → `frontend/PLAN.md`

The screen that makes memory visible next to the Claude Code terminal in the video.

**FINISH LINE:** record 60 seconds of cold → warm on the dashboard, show it to someone with
zero context. They must say "it remembered, that is why it got fast" with no help.

## Phase 5a — Agent-to-agent memory · Sep 8 · `package/` + `mcp/` — NOT blocked

Split out of Phase 5 because it needs no blockchain and no Discord answer, and because the
rules say **"coordination and dynamic-storage patterns top the band"** for the 40% that
matters most. We have dynamic storage already; this is the coordination half, and without it
we are only answering half of the biggest scoring line.

One agent walks a site and leaves a trail. A SECOND agent — separate session, separate
Sibyl `tenant_id` — is asked for the same task on a site it has never seen, searches memory,
finds the trail the first agent left, and runs it in one call.

Uses `store.search_similar` (built, currently unused) and Sibyl's multi-tenancy (noted in
RESEARCH.md, never used). This is also the prerequisite for 5b.

**FINISH LINE:** two agents with different tenant ids. Agent B has never seen the site,
finds A's trail through memory, and completes the task in one call with zero model calls.

## Phase 5b — Base x402 · Sep 8 · `package/` → `package/PLAN.md` §Phase-5 — CUTTABLE

**BLOCKED** until Discord answers the testnet question. Adds payment to 5a: agent B pays for
agent A's playbook via x402 on Base Sepolia before importing it.

**FINISH LINE:** one x402 payment visible on the Base Sepolia explorer, made during a run,
playbook transferred and used.

## Phase 6 — Harden + ship · Sep 8–10 · root

- Run EVERYTHING 5×. Kill every flake. A stranger following the README succeeds first try.
- Record the demo video: cold → fresh session warm → live break + repair → forget → slow.
- README (memory map, prior work, how-memory-made-this-possible), two public posts tagging
  @sibylcap.
- Fill the build page by ~21:00 UTC Sep 10, mark ready well before 23:59 UTC.

**FINISH LINE:** submission marked ready, all links checked in a private browser window.

---

## The nine days (set 2026-09-01, after Phases 0-2 landed on day one)

| day | what |
|---|---|
| Sep 1 | ~~Phase 0, 1, 2~~ **done** |
| Sep 2-3 | **Phase 2.5** — the browsing layer |
| Sep 4 | **Phase 1g** — 1-2 real websites, the loop proven off our own demo site |
| Sep 5 | **Phase 3** — backend |
| Sep 6-7 | **Phase 4** — dashboard |
| Sep 8 | **Phase 5a** — agent-to-agent memory. 5b if Discord unblocks it |
| Sep 9 | **Phase 6** — harden, run everything 5×, record the video |
| Sep 10 | README, posts, submit by ~21:00 UTC |

## Cut order when time runs short

Rohit's call 2026-09-01: **nothing is being cut up front.** He uses this kind of automation
himself, so the browsing layer is not a demo prop. This order only applies if a day is lost.

1. Phase 5b (x402) → lose the ×1.15, keep everything else
2. Frontend polish extras (never the three demo panels)
3. Backend + frontend entirely — the MCP demo alone still proves everything
4. NEVER: the engine, the MCP server, the browsing layer, agent-to-agent memory, the recall
   beat, the repair beat, `cairn forget`, or the video quality
