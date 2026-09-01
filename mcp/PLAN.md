# PLAN — mcp/ (Phase 2, Sep 4–5)

Finish line in `../MASTER-PLAN.md`. Start after Phase 1 passes. This is the main deliverable —
it is NOT cuttable.

### 2a. Research (timebox 30 min)
- Open the `mcp` (2.1.1) and `fastmcp` (3.4.7) docs with Playwright. Pick one, note the choice
  and reason in `../RESEARCH.md`.
- Look at how `sibyl-memory-mcp` structures its server — same sponsor, good reference.

### 2b. Cold-path tools
- `cairn_look`, `cairn_act`, `cairn_save` wired to `cairn.operations` + `cairn.distill`.
- Session handling: one browser session per MCP connection, cleaned up properly on exit.
- ✅ in Claude Code, asking it to do the demo task works: it looks, acts, and saves a playbook.

### 2c. Warm-path tools
- `cairn_run`, `cairn_sites`, `cairn_show`, `cairn_forget`.
- Repair inside `cairn_run`: when a step breaks, return a precise repair request so the host AI
  fixes only that step, then persist it.
- ✅ the whole four-beat flow works from Claude Code with no terminal.

### 2d. Tool description pass
- Rewrite every description so the host AI reliably picks `cairn_run` (warm) over the cold
  tools when a playbook already exists. Test by asking vaguely: "get my invoice from that
  portal" — it should go straight to `cairn_run`.
- ✅ three vague prompts in a row route correctly.

### 2e. Install path + adoption
- `claude mcp add` line, plus config snippets for Codex and Cursor.
- **OpenClaw (388k★) — confirmed: docs.openclaw.ai lists "Connect MCP servers", so our server
  plugs in with install docs only, no extra code.** Note their users ALREADY have browser
  tools (Browser control API, Chrome Extension, etc.), so the message there is not "here is a
  browser" but "your browser stops re-learning the same site". They also run ClawHub + a
  5,400-skill registry — a good place to be seen. See ../RESEARCH.md.
- **Hermes Agent (Nous Research) — check this before writing the install docs.** Sibyl
  officially supports Hermes, so it is inside the sponsor's own world. First find out whether
  Hermes loads MCP servers directly: if yes, we get it free and only need install docs; if no,
  a thin plugin adapter (mirror how `sibyl-memory-hermes` installs into
  `$HERMES_HOME/plugins/`). Hermes is the strongest home for Cairn because it runs
  **unattended on a cron schedule** — exactly where deterministic replay beats an improvising
  AI. See ../RESEARCH.md.
- README install section, tested by following it literally in a clean folder.
- Share in the hackathon Discord — one non-Rohit person installs and runs it. That is real,
  verifiable PMF evidence (and the rules require evidence a judge can check in 5 minutes).
- ✅ Phase 2 finish line: clean Claude Code session learns a site, quit, fresh session replays
  it in seconds, `cairn_forget` makes it slow again.
