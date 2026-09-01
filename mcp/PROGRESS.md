# PROGRESS — mcp/

> Working memory for this folder. Read first, update before ending every session.

## Current state — 2026-08-31

- **Promoted to Phase 2 — this is now the main deliverable, not a cuttable extra.**
- Not started. Blocked (correctly) on Phase 1.
- Plan locked in `PLAN.md`. SDK candidates verified: `mcp` 2.1.1, `fastmcp` 3.4.7.

## Done

(nothing yet)

## Next action

2a from PLAN.md — after `package/` Phase 1 passes.

## Decisions made

- **2026-08-31 (Rohit):** Cairn is a tool, not an agent with its own brain. The host AI
  (Claude Code / Codex / Cursor) thinks; Cairn supplies browser + memory. No Anthropic API.
  OpenRouter only if a standalone brain is ever needed, and never on the warm path.
  This moved MCP from Phase 4a to Phase 2.
- Seven tools: look / act / save (cold) + run / sites / show / forget (warm).
- Thin wrapper over `package/` only. Never touches backend or frontend.
- Never print to stdout (breaks stdio MCP transport) — stderr logging only.

## Blockers

- Phase 1 not done.

## Session log

- **2026-08-31** — folder created; then rewritten as Phase 2 after the product-shape decision.
