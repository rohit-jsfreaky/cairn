# Cairn

**Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.**

A cairn is a small pile of stones hikers leave on a trail, so the next traveller knows the
way. Cairn walks a website once, leaves markers, and every later run follows the markers
instead of re-exploring. When the site changes, it repairs only the broken step and saves the
fix.

Built for the [Sibyl Labs Hackathon](https://hack.sibyllabs.org) (build window Sep 1–10, 2026).

> **Status: in progress.** The landing page is built. The engine is being written now.
> Nothing here claims to work yet — see [Build status](#build-status) for exactly what is and
> is not done. Every number currently shown on the landing page is a placeholder for layout
> and is marked as such below.

---

## What it does

Cairn is a **tool, not an agent.** The AI you already use — Claude Code, Cursor, Codex — does
the thinking. Cairn gives it a browser plus a memory.

| | what happens | cost |
|---|---|---|
| **Cold run** | Your AI explores the site through Cairn's tools. Cairn watches and writes a playbook to memory. | many tool calls, slow |
| **Warm run** | One `cairn_run` call. Cairn replays the playbook itself — deterministic Python, **zero model calls**. | one tool call, fast |
| **Repair** | A step's postcondition fails. Cairn hands that one step back to your AI, then saves the answer. | one step re-explored, not the whole trail |
| **Forget** | `cairn forget --site <domain>` archives the trail. Replay has nothing left to follow. | — |

The contrast is visible in your own editor transcript. That is the demo.

**No Anthropic API key. No account. No signup.** A warm run uses no model at all, so repeat
runs cost nothing. If a model is ever needed for an optional standalone mode, it goes through
OpenRouter only, and is never on the main path.

## Where the memory lives

Every read and write to Sibyl Memory happens in **one file**:

```
package/src/cairn/store.py
```

That is deliberate. A judge should be able to find every memory call in ten seconds, not
hunt through the codebase. Nothing else in the project talks to Sibyl directly.

How the tiers are used:

| Sibyl tier | what Cairn stores |
|---|---|
| **WARM** `set_entity("playbook", domain)` | the steps: intent, postcondition, ranked locators, health score |
| **WARM** `set_entity("site_knowledge", domain)` | facts that survive a redesign (needs 2FA, rate limits, account email) |
| **COLD** `write_event(...)` | every run, every drift detected, every repair, in time order |

Entities are unique per `(tenant_id, category, name)`, enforced by Sibyl's schema, so a site
can never hold two conflicting playbooks. Forgetting **archives**, it does not delete —
matching Sibyl's own forgetting-vs-deleting doctrine.

## How memory made this possible

Without a memory layer, this project is just Playwright with extra steps. Run 2 would cost
exactly what run 1 cost — same page reads, same guessing, same tokens, forever.

The memory is what turns exploring into replaying. It is not a notepad of prose about a
website; it is an **executable, self-verifying, self-repairing procedure** that a second,
completely fresh process can pick up and run with no model involved. Delete it and Cairn has
nothing to replay — it degrades to a slow browser tool.

## The deletion test

The hackathon rules say the memory must be load-bearing: delete it, and the project must stop
doing what it claims. Ours is a one-line check.

```bash
cairn run "download this month's invoice" --site billing.example.com   # fast, from memory
cairn forget --site billing.example.com                               # wipe it
cairn run "download this month's invoice" --site billing.example.com   # nothing to follow
```

Automated in `package/tests/test_deletion_gate.py`. It needs **no API key**, so anyone can run
it in ten seconds.

## Repo map

| folder | what |
|---|---|
| `package/` | the engine — browser, memory, replay, verification, repair, CLI, tests |
| `mcp/` | **the product** — Cairn as MCP tools for Claude Code / Cursor / Codex |
| `backend/` | thin FastAPI server: run lifecycle, live event stream |
| `frontend/` | Next.js — the landing page, and the dashboard that makes memory visible |

Plans live in `MASTER-PLAN.md` and each folder's `PLAN.md`. Live state is in `PROGRESS.md`.

## Build status

| phase | what | state |
|---|---|---|
| 0 | Setup, prove Sibyl round-trips across a fresh process | in progress |
| 1 | `package/` — the engine | not started |
| 2 | `mcp/` — the MCP server | not started |
| 3 | `backend/` | not started |
| 4 | `frontend/` dashboard | not started |
| 5 | Base x402 playbook transfer | blocked, cuttable |
| — | `frontend/` landing page | **done** |

**Honesty note.** The landing page shows example figures (`2m 41s → 4.1s`, `31 tool calls`,
`39×`) and an install command that is not published yet. These are placeholders for layout
only. They will be replaced with numbers from real runs, or removed, before this project is
submitted. Nothing in this repo should be read as a measured result until this note says so.

## Partner stacks

- **Sibyl Memory** — the memory layer, core to the project, not optional. See
  [Where the memory lives](#where-the-memory-lives).
- **Base (x402)** — planned for Phase 5: one agent buys another agent's playbook and runs it
  warm immediately. Cuttable, and currently blocked on whether Base Sepolia counts. **Not
  built. Do not count it unless this line says it is done.**

## Prior work

- **[pig-dot-dev/muscle-mem](https://github.com/pig-dot-dev/muscle-mem)** (766★) — "a cache
  for AI agents to learn and replay complex behaviors", quiet since Jun 2025. The closest
  existing idea and the reason this section exists. **How Cairn differs:** muscle-mem is a
  cache. Cairn verifies every step against a postcondition, detects when the site itself has
  changed, repairs only the broken step, persists that repair, and stores ranked locators
  rather than a recording.
- **Planning documents written before the build window opened.** `CLAUDE.md`,
  `MASTER-PLAN.md`, `RESEARCH.md`, the folder plans and the empty scaffold were written on
  2026-08-31, before Sep 1. They are declared here as prior work. No functional code existed
  before the window opened.
- **Design reference.** The landing page layout follows the structural pattern of
  [aside.com](https://aside.com) — its spacing scale, type sizes and section rhythm were
  measured and adapted. The words, the product and the artwork are ours.
- **Third-party tooling, not committed.** The official [GSAP AI
  skills](https://github.com/greensock/gsap-skills) (MIT) are cloned into `.claude/skills/`
  and gitignored. GSAP itself is a dependency of the frontend.

## License

MIT — see [LICENSE](LICENSE).
