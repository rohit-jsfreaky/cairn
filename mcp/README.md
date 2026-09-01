# Cairn MCP server

Cairn as MCP tools, so the AI you already use gets a browser that remembers websites.

**One plug, many sockets.** MCP is a shared standard, so this one server works in Claude
Code, Cursor, Codex and anything else that speaks MCP. Adding another client costs install
instructions, never another build.

## What your AI gets

| tool | when it is used |
|---|---|
| `cairn_run` | **first, always.** One call does the whole task on a site Cairn knows. |
| `cairn_repair` | only when `cairn_run` says one step broke |
| `cairn_sites` | what Cairn already knows how to do |
| `cairn_show` | the trail for one site, step by step |
| `cairn_forget` | make Cairn forget a site |
| `cairn_login` `cairn_login_done` | you sign in yourself; Cairn keeps the session |
| `cairn_note` | remember a fact about a site that is not a step |
| `cairn_open` `cairn_look` `cairn_act` `cairn_save` | only for a site Cairn has never seen |

The split is the whole point. Exploring a site is many calls and a lot of reading. It
happens **once**. Every time after that, `cairn_run` does the same task in one call with no
page reads and no model calls at all.

## Install

Cairn is not published to PyPI yet, so install it from this repo.

```bash
git clone https://github.com/rohit-jsfreaky/cairn
cd cairn

python -m venv .venv
.venv/Scripts/python -m pip install -e package -e mcp     # Windows
# .venv/bin/python -m pip install -e package -e mcp       # macOS / Linux

.venv/Scripts/playwright install chromium
```

Then point your editor at it.

### Claude Code

```bash
claude mcp add cairn -- /absolute/path/to/cairn/.venv/Scripts/cairn-mcp.exe
```

Use the `cairn-mcp` console script, not `python -m cairn_mcp`. Claude Code's own argument
parser swallows the `-m` and fails with `error: unknown option '-m'`. The console script
takes no arguments, so there is nothing to swallow.

Check it connected:

```bash
claude mcp list
```

### Cursor

`~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "cairn": {
      "command": "/absolute/path/to/cairn/.venv/Scripts/cairn-mcp.exe",
      "args": []
    }
  }
}
```

### Codex

`~/.codex/config.toml`:

```toml
[mcp_servers.cairn]
command = "/absolute/path/to/cairn/.venv/Scripts/cairn-mcp.exe"
args = []
```

### Other agents

MCP is a shared standard, so anything that speaks it can use Cairn with install
instructions only — never another build. Two worth naming:

- **OpenClaw** (388k stars) lists "Connect MCP servers" in its docs, so this server plugs
  straight in. Note that OpenClaw users already have browser tools, so the reason to add
  Cairn there is not "here is a browser" — it is "your browser stops re-learning the same
  site every time".
- **Hermes Agent** (Nous Research) is officially supported by Sibyl and runs unattended on
  a cron schedule. That is the strongest case for deterministic replay: at 3am nobody is
  watching, so an AI improvising a click is a liability. **Open question:** whether Hermes
  loads MCP servers directly or needs a small plugin adapter. Not yet checked.

### Once it is published

```bash
claude mcp add cairn -- uvx cairn-mcp
```

That line is on the landing page already. It does **not** work yet — the package is not
published. Use the local install above until it is.

## Making sure your AI actually uses it

Connecting the server is not the same as your AI choosing it. Claude Code has `curl` and a
shell right there, and for a task like "download this invoice" it may reach for those
instead — they look like the shortest path, even though they cannot sign in, cannot click,
and remember nothing.

Cairn's tool descriptions rule that out explicitly, but tool choice is a judgement call, so
the reliable fix is one line in the `CLAUDE.md` of whatever project you work in:

```markdown
For anything on a website — invoices, dashboards, portals, forms, downloads — use the
Cairn MCP tools, starting with `cairn_run`. Do not use curl, WebFetch or shell commands
for website work.
```

Cursor: put the same line in `.cursorrules`. Codex: in `AGENTS.md`.

You can also just say it in the prompt — "use cairn to download this month's invoice" —
which is the quickest way to check the server is wired up correctly.

## Try it

Start the practice site that ships with the repo:

```bash
.venv/Scripts/python package/tests/demo_site/app.py     # http://127.0.0.1:8787
```

Then, in your editor:

1. **"Download this month's invoice from http://127.0.0.1:8787"**
   Cairn does not know the site, so your AI explores it — several tool calls, reading each
   page. At the end it calls `cairn_save`.

2. **Quit your editor. Open it again. Ask for the same thing.**
   One `cairn_run` call. No page reads. No thinking. That is the whole product.

3. **"Now do it against http://127.0.0.1:8787/?variant=b"**
   The site has been redesigned and the download button moved. Cairn replays five steps,
   notices the sixth is broken, and hands your AI that one step. It picks the new control,
   calls `cairn_repair`, and the run finishes. Next time it is clean again.

4. **"Forget 127.0.0.1:8787"**
   Then ask for the invoice again. Cairn reports it knows nothing and your AI has to
   explore from scratch. That is the deletion test: take the memory away and the fast path
   is gone.

## Notes

- **No API key. No account.** Nothing here calls a model, and Sibyl Memory works locally
  with no credentials.
- Memory is a single file at `~/.sibyl-memory/memory.db`. Nothing is uploaded.
- The browser runs headless and keeps **one shared profile** at `~/.cairn/browser-profile`,
  so you stay signed in between runs. Being signed in is not the same as remembering: the
  profile holds who you are, Sibyl memory holds what Cairn knows. Wipe the memory and Cairn
  is still logged in but has to explore the site again from scratch.
- For a login that cannot be automated (Google, SSO, a one-time code), use `cairn_login`,
  sign in yourself in the window that opens, then `cairn_login_done`. Once per site.
- Logs go to stderr only. stdout belongs to the MCP transport.
