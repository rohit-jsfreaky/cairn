# CLAUDE.md — Cairn (read this first, every session)

**Cairn = a browser agent that learns a website once, and re-learns only what moved.**

A cairn is a small pile of stones hikers leave on a trail, so the next traveller knows the way.
This agent walks a website once, leaves markers (a playbook in Sibyl Memory), and every later
run follows the markers instead of re-exploring. When the site changes, it repairs only the
broken step and saves the fix.

Built for the **Sibyl Labs Hackathon** (build window Sep 1–10, 2026).
**Submission deadline: Sep 10, 23:59 UTC.** Judging Sep 11–12.

## The one rule that decides everything (the gate)

Judges delete the Sibyl Memory layer. If the project still does what it claims, it is
disqualified. Memory must be load-bearing.

What this means for us, concretely:

1. All Sibyl Memory calls live in ONE file: `package/src/cairn/store.py`. The rules say a
   judge must find the read/write calls in under 2 minutes. One file makes it 10 seconds.
2. `cairn forget --site <domain>` must exist. It wipes that site's memory. A judge runs it and
   watches the agent become slow again. That is the deletion test as a one-line command.
3. The demo video needs one continuous UNEDITED segment: fresh session + on-screen timestamp,
   agent recalls and executes fast. Plan every feature so this beat is easy to record.
4. Scoring: memory load-bearing 40% ("coordination and dynamic-storage patterns top the band"),
   innovation 25%, technical execution 20% ("survives a second run and a curious judge"),
   pitch 15%, +10 PMF bonus (verifiable evidence only), ×1.15 with one verified partner stack
   (Base), ×1.25 with two.

## Folder map

| folder | what | phase | plan |
|---|---|---|---|
| `package/` | the engine — browser + memory + replay + repair + CLI + tests | 1 (and 5) | `package/PLAN.md` |
| `mcp/` | **the product** — Cairn as MCP tools for Claude Code / Codex / Cursor | 2 | `mcp/PLAN.md` |
| `backend/` | thin FastAPI server — runs the engine, streams live events | 3 | `backend/PLAN.md` |
| `frontend/` | Next.js dashboard — makes memory visible in the demo video | 4 | `frontend/PLAN.md` |

**Product shape (locked 2026-08-31):** Cairn is a TOOL, not an agent with its own brain. The
user's Claude Code / Codex / Cursor / OpenClaw / Hermes does the thinking; Cairn gives it a
browser plus memory. Warm replay is deterministic Python with ZERO model calls. **No Anthropic
API.** If a model is ever needed (optional standalone mode, tests) it goes through
**OpenRouter** only, behind one interface, never on the main path. Reasoning in `MASTER-PLAN.md`.

**The canonical one-line pitch** (use this in the README, the video, the posts, everywhere):

> Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.

**Distribution rule — one plug, many sockets.** MCP is a shared socket. We build ONE MCP
server; Claude Code, Cursor, Codex, OpenClaw (388k★) and Hermes all accept MCP servers. Adding
another agent costs **install docs, never a separate build**. If a session ever proposes a
per-agent version, stop — that is how 10 days disappear. Make Claude Code perfect first
(Rohit uses it daily), then add install snippets. Landscape detail in `RESEARCH.md`.

Root files: `MASTER-PLAN.md` (phases + finish lines), `PROGRESS.md` (live state — read it
first, update it last, every session), `RESEARCH.md` (verified facts + open questions).

## Working rules (non-negotiable)

1. **Read `PROGRESS.md`** (root + the folder you are working in) before doing anything.
   Update both before ending the session.
2. **Phases in order.** A phase may only depend on earlier phases, never later ones. A phase
   is DONE only when its finish line in `MASTER-PLAN.md` passes. No half-done phases.
3. **Research before building.** Check `RESEARCH.md` first. If the fact is not there, open the
   real docs with Playwright MCP, then add the finding with date + source. Never build on a
   guess, and never use WebSearch (stale data).
4. **No fabrication, ever.** README claims, metrics, PMF evidence — everything must be
   verifiable. The rules disqualify fabricated evidence even after payout.
5. **Never run git commit/push, never create repos.** Rohit does all git himself. He also
   creates the GitHub repo (public, MIT license, must show real commit history).
6. **Product-grade only.** No temp fixes, no workarounds, no "quick hack for now". Do the
   proper fix or flag it to Rohit.
7. **Talk to Rohit in simple English.** Short sentences. No buzzwords, no idioms. Hindi is his
   first language.
8. **When time runs short, cut by the order in MASTER-PLAN.md** (Phase 4 first). NEVER cut the
   memory showcase — it is 40% of the score and the gate.
9. Clean code rules live in each folder's own CLAUDE.md. Follow them.

## Prior work to declare in the README (required by the rules)

- `pig-dot-dev/muscle-mem` (766★, "a cache for AI agents to learn and replay complex
  behaviors", quiet since Jun 2025). Our difference: Cairn is not a cache — it verifies every
  step, detects when the site changed, repairs only the broken step, and transfers knowledge
  to unseen sites. Say this plainly; it strengthens the originality score.
- Any scaffolding or planning docs written before Sep 1 (like these files).

## Submission checklist (verbatim-sourced from hack.sibyllabs.org/rules, 2026-08-31)

- [ ] Public GitHub repo, MIT or Apache-2.0, real commit history
- [ ] README: what it does, where memory is written/read (link exact file), which partner
      stacks and where, "how memory made this possible" note, Prior Work declaration
- [ ] Demo video 2–5 min with the unedited fresh-session recall beat (timestamp on screen)
- [ ] Two public posts tagging @sibylcap (+ Base if claimed): demo video + ≥1 build-log
- [ ] Submit from the private build page (from registration), mark ready before Sep 10
      23:59 UTC — prepare it 2 hours early
