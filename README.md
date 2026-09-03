# Cairn — a browser memory for AI agents

**Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.**

Cairn gives Claude Code, Cursor, Codex or any MCP client a browser that remembers. Your AI
walks a website once — signing in, clicking, reading — and Cairn writes down the route. Every
run after that follows the route instead: **one tool call, no page reading, no model calls at
all.** When the site changes, Cairn repairs the one step that moved and keeps the rest.

A cairn is a small pile of stones hikers leave on a trail, so the next traveller knows the
way. Agents can leave them for each other too — see [Sharing](#sharing-a-trail).

[Install](#install) · [Quick start](#quick-start) · [How it works](#how-it-works) ·
[Sharing](#sharing-a-trail) · [Forgetting](#forgetting) · [Prior work](#prior-work)

---

## Install

Python 3.11 or newer. Nothing is published to PyPI yet, so install from a clone:

```bash
git clone https://github.com/rohit-jsfreaky/cairn
cd cairn

python -m venv .venv
.venv/Scripts/python -m pip install -e package -e mcp   # Windows
# .venv/bin/python -m pip install -e package -e mcp     # macOS / Linux

.venv/Scripts/python -m playwright install chromium
```

Then point your AI at it. For Claude Code, from the folder you want to work in:

```bash
claude mcp add cairn -- /absolute/path/to/cairn/.venv/Scripts/cairn-mcp.exe
```

Cursor and Codex take the same command in their own MCP config. Cairn is one stdio server
with no arguments, so anything that speaks MCP will run it.

**No API key.** Cairn never calls a model — yours does the thinking. Memory is a local SQLite
file, and no account is needed for that either.

## Quick start

Ask your AI for something on a website, in your own words:

> Go to github.com/microsoft/playwright and tell me how many open issues it has.

The first time, it explores: opening the page, looking at the controls, reading the number.
Then it saves what it did.

Ask again tomorrow and it is one call:

```json
{ "ok": true, "steps_replayed": 2, "duration_ms": 1391,
  "model_calls": 0, "pages_read": 0,
  "answers": { "open issues": "117" } }
```

Prefer a terminal? Everything works without an MCP client:

```bash
cairn sites                              # what it remembers
cairn run --site github.com --task "count open issues"
cairn show github.com                    # the route, step by step
cairn forget --site github.com           # make it forget
```

## How it works

Two paths, and only the first one costs anything.

| | what happens | cost |
|---|---|---|
| **First run** | Your AI drives the browser through Cairn. Cairn watches, and turns what happened into a route. | many calls, slow |
| **Every run after** | Cairn replays the route itself, checking each step landed. | **one call, zero model calls** |

Measured on the demo site in this repo — run `python package/benchmark.py` yourself:

```
                time  tool calls  page reads  model calls
Monday          0.8s           9           3            0   learning the site
Tuesday         0.4s           1           0            0   from memory
Wednesday       0.4s           1           0            0   from memory
Thursday        6.4s           3           0            0   the site changed, one step repaired
Friday          0.5s           1           0            0   from memory
```

The clock is the least interesting column. This benchmark has no model thinking in it, and
thinking time is what memory actually removes. **Nine tool calls became one. Three page reads
became none.**

### What is actually stored

Not a recording, and not notes. Each step keeps:

- **what it was for**, in plain words — `"open this month's invoice"`
- **up to nine ways to find the control**: test id, link target, label, role, placeholder,
  alt text, title, visible text, CSS — ranked by which have actually worked
- **a check that proves it landed** — the URL changed, the file downloaded, the field holds
  what was typed, the row count is what it should be

The checks are the difference between this and a macro recorder. A recorder clicks and hopes.
Cairn notices when a click did nothing, and says the site changed.

### When a site changes

The nine locators are why most redesigns cost nothing: lose the CSS id, keep the accessible
name, and the step still lands. When every route to one control is genuinely gone, Cairn stops
at that step, hands your AI the current page, and asks only about **that one control**. The fix
is saved. The rest of the route is untouched.

If more than half the steps break, the site was rebuilt rather than adjusted. Cairn throws the
route away and keeps what it knows about the site, which makes relearning cheaper than the
first visit.

## Sharing a trail

Memory is per agent. Two agents can share one, and neither can see into the other's.

```bash
# alice, who already knows the site
cairn --agent alice share github.com

# bob, who has never opened it
cairn --agent bob run --site github.com     # unknown — but alice left a trail
cairn --agent bob borrow github.com
cairn --agent bob run --site github.com --task "count open issues"   # one call
```

Bob was never taught anything. He inherited a working, self-checking route and ran it on a site
he had never seen.

**What travels:** the steps, every ranked locator with the evidence it earned, the checks, and
the hard-won notes about the site — *"the tab badge is cached, trust the Open count"*.

**What never travels:** anything typed into a field, and which account was used. A shared login
step arrives asking *you* for your own credentials, resolved from your machine. Sharing tells
you exactly which notes became visible and which values were held back.

When a borrower repairs a broken step, the fix can be contributed back into the original, so a
route improves across agents who never spoke to each other.

## Where the memory lives

Every read and write goes through **one file**:

```
package/src/cairn/store.py
```

Nothing else in the project imports the memory client, and a test enforces that by walking the
source. Memory is [Sibyl Memory](https://hack.sibyllabs.org), used across three tiers:

| tier | what Cairn keeps there |
|---|---|
| **warm** `playbook` | the route: steps, locators, checks, health |
| **warm** `site_knowledge` | what survives a redesign — needs a login, sends a code, where the number really is |
| **cold** `write_event` | every run, drift, repair, share and borrow, in order |

Entities are unique per `(tenant, category, name)` at the schema level, so a site can never
hold two conflicting routes for the same task. Agent identity is a tenant, which is what makes
one agent's memory genuinely invisible to another.

## Forgetting

```bash
cairn forget --site github.com
```

Cairn now has nothing to follow for that site and has to learn it again. That is the point:
**the memory is load-bearing, not a cache in front of something that works anyway.**

Forgetting archives rather than deletes, and it is honest about its edges:

- It **withdraws** anything you shared for that site.
- It **cannot** reach a copy another agent already borrowed, and says so rather than leaving
  you to find out.
- It **remembers that you forgot**. If somebody else has a route for the site, Cairn will not
  quietly hand it to you — you have to ask for it on purpose. Walking the site again clears
  that.

Replay never reads the shared memory. Only a deliberate `borrow` copies a route to you, which
is what makes it yours to forget.

## Signing in

Cairn keeps **one browser profile**, so you sign in to a site once — by hand, in a real window
you can see:

```bash
cairn login --site posthog.com
```

Chrome opens. Sign in however the site asks: a password, Google, a code on your phone. Cairn
never types a password and never automates an SSO button. When you are done, it closes.

**Passwords are never stored in memory.** A step that needs one records only that a password
goes here; the value is looked up at replay time from an environment variable or
`~/.cairn/secrets.json`. Export a route and grep it — there is nothing to find.

Being signed in is not the same as remembering. Delete the memory and Cairn is still signed
in, and still has no idea what to click.

## What it can do

Cairn is Playwright underneath, exposed as two tools rather than thirty-five, because tool
choice is the most fragile part of an agent's day.

**`cairn_act(intent, action, ref?, value?)`** — 35 actions: click, double_click, hover, fill,
type, clear, press, check, uncheck, set_checked, select, upload, scroll_to, drag, focus, blur,
tap, select_text, dispatch_event, goto, back, forward, reload, scroll, wait_for, new_tab,
switch_tab, dismiss_when_seen, set_time, screenshot, evaluate, and more.

**`cairn_read(kind, ref?)`** — 14 kinds: the control list, text, all_text, value, checked,
visible, enabled, editable, attribute, count, url, title, console errors, failed requests.

It handles the things that actually break recorded flows: shadow DOM, iframes, `div`s
pretending to be buttons, content that loads late, cookie banners that appear whenever they
feel like it, confirm dialogs, new tabs, and file pickers with no visible input. There is a
page in the repo containing all nine at once, and a test that walks every one.

`evaluate` is the escape hatch — run your own JavaScript when a site does something nobody
anticipated. It is deliberately never recorded into a route, because a step made of code
cannot be repaired.

## Development

```bash
cd package && ../.venv/Scripts/python -m pytest      # 479 tests
cd mcp     && ../.venv/Scripts/python -m pytest      #  80 tests
../.venv/Scripts/python -m ruff check src/ tests/
```

```
package/   the engine — browser, memory, replay, repair, sharing, CLI
mcp/       the MCP server: 14 tools over the engine
frontend/  the landing page
```

## Prior work

- **[pig-dot-dev/muscle-mem](https://github.com/pig-dot-dev/muscle-mem)** — "a cache for AI
  agents to learn and replay complex behaviors". The closest existing idea. Cairn differs in
  that it is not a cache: every step carries a check, so it can tell a changed site from a
  working one, repair the single step that moved, and hand a working route to another agent.
- **[@playwright/mcp](https://github.com/microsoft/playwright-mcp)** — the accessibility-tree
  snapshot approach, which Cairn's page reading is built on.
- The planning documents in this repository were written before the build began.

## License

MIT. See [LICENSE](LICENSE).
