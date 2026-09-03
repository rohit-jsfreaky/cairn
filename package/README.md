# Cairn — a browser memory for AI agents

**Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.**

Your AI walks a website once — signing in, clicking, reading — and Cairn writes down the
route. Every run after that follows the route instead: **one call, no page reading, no model
calls at all.** When the site changes, Cairn repairs the one step that moved and keeps the
rest.

```bash
pip install cairn-browser
playwright install chromium        # the browser is a separate download

cairn run --site github.com --task "count open issues"
cairn show github.com              # the route, step by step
cairn forget --site github.com     # make it forget
```

This is the engine. Most people want it wired into their AI instead, which is
[`cairn-browser-mcp`](https://pypi.org/project/cairn-browser-mcp/) — Cairn as MCP tools for
Claude Code, Cursor or Codex.

**No API key.** Cairn never calls a model; yours does the thinking. Memory is a local SQLite
file and needs no account.

Optional extra, for selling and buying trails between machines over x402 on Base:

```bash
pip install "cairn-browser[market]"
```

Full documentation, the design, and the deletion test that proves the memory is load-bearing:
**https://github.com/rohit-jsfreaky/cairn**

MIT licensed.
