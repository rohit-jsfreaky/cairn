# Cairn as MCP tools

**Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.**

This gives Claude Code, Cursor, Codex or any MCP client a browser that remembers. Your AI
walks a site once and Cairn writes down the route; every run after that is **one tool call,
no page reading, and zero model calls**. When the site changes, Cairn hands back the single
step that moved rather than the whole task.

```bash
pip install cairn-browser-mcp
playwright install chromium        # the browser is a separate download

claude mcp add cairn -- cairn-mcp
```

Then just ask, in your own words: *"go to github.com/microsoft/playwright and tell me how
many open issues it has."* The first time it explores. After that it is one call.

**No API key.** There is no model call anywhere in this package or anything it imports —
your AI does the thinking and Cairn supplies the browser and the memory.

Optional extra, so one agent can buy a trail from another over x402 on Base:

```bash
pip install "cairn-browser-mcp[market]"
```

The engine on its own is [`cairn-browser`](https://pypi.org/project/cairn-browser/).

Full documentation, the tool list, and the deletion test that proves the memory is
load-bearing: **https://github.com/rohit-jsfreaky/cairn**

MIT licensed.
