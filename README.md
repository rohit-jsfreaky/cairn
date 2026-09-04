# Cairn — a browser memory for AI agents

[![tests](https://github.com/rohit-jsfreaky/cairn/actions/workflows/test.yml/badge.svg)](https://github.com/rohit-jsfreaky/cairn/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/cairn-browser-mcp?label=cairn-browser-mcp)](https://pypi.org/project/cairn-browser-mcp/)

**Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.**

Cairn gives Claude Code, Cursor, Codex or any MCP client a browser that remembers. Your AI
walks a website once — signing in, clicking, reading — and Cairn writes down the route. Every
run after that follows the route instead: **one tool call, no page reading, no model calls at
all.** When the site changes, Cairn repairs the one step that moved and keeps the rest.

A cairn is a small pile of stones hikers leave on a trail, so the next traveller knows the
way. Agents can leave them for each other too — see [Sharing](#sharing-a-trail).

[Install](#install) · [Quick start](#quick-start) · [How it works](#how-it-works) ·
[Sharing](#sharing-a-trail) · [Selling](#selling-a-trail) · [Forgetting](#forgetting) ·
[Troubleshooting](#when-something-goes-wrong) · [Prior work](#prior-work)

---

## Install

Python 3.11 or newer.

```bash
pip install cairn-browser-mcp
playwright install chromium      # the browser is a separate download, ~150 MB
```

Then point your AI at it. For Claude Code, from the folder you want to work in:

```bash
claude mcp add cairn -- cairn-mcp
```

Cursor and Codex take the same command in their own MCP config. Cairn is one stdio server
with no arguments, so anything that speaks MCP will run it.

Check the install at any time — it names anything missing and the command that fixes it:

```bash
cairn doctor
```

**No API key.** Cairn never calls a model — yours does the thinking. Memory is a local SQLite
file, and no account is needed for that either.

Selling and buying trails needs a web server and a wallet library, which nobody who just
wants a browser with a memory should have to install. They are an optional extra:

```bash
pip install "cairn-browser-mcp[market]"
```

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
Monday          0.7s           9           3            0   learning the site
Tuesday         0.4s           1           0            0   from memory
Wednesday       0.3s           1           0            0   from memory
Thursday       12.3s           3           0            0   the site changed, one step repaired
Friday          0.3s           1           0            0   from memory
```

The clock is the least interesting column. This benchmark has no model thinking in it, and
thinking time is what memory actually removes. **Nine tool calls became one. Three page reads
became none.**

Then a **different** task on the same site — nothing replayed, all three exploring from
scratch. The only difference is what Cairn had already seen:

```
                time  tool calls  page reads  model calls
blind           0.6s          10           3            0   the way it worked before the map
with map        0.3s           8           1            0   pages Cairn had already walked
once more       0.3s           7           0            0   and now that page is mapped too
```

This is the number that matters if you have many tasks on one site. Task one is still a first
visit. Task two is not, and neither is anything after it.

### What is actually stored

Not a recording, and not notes. Each step keeps:

- **what it was for**, in plain words — `"open this month's invoice"`
- **up to nine ways to find the control**: test id, link target, label, role, placeholder,
  alt text, title, visible text, CSS — ranked by which have actually worked
- **a check that proves it landed** — the URL changed, the file downloaded, the field holds
  what was typed, the row count is what it should be

The checks are the difference between this and a macro recorder. A recorder clicks and hopes.
Cairn notices when a click did nothing, and says the site changed.

### The map: what it saw on the way

A trail is one route. A site is bigger than one route, and most of what an agent needs is
somewhere else on it.

So Cairn also keeps a **map**: every page it has actually looked at, and what was on it. That
costs nothing — the page had already been read, and Cairn was throwing it away.

```bash
cairn map github.com                       # every page it has seen
cairn map github.com --path /issues        # the controls that were on one of them
```

This is the difference between the first task and the second on the same site. Ask for
something new on a site Cairn has walked, and your AI is handed the pages it already knows
before it starts hunting:

```json
{ "known": true, "needs_task": true,
  "pages_known": [
    { "path": "/vendor/requests", "title": "Requests", "controls": 14, "seen": "2 hours ago" },
    { "path": "/vendor/reports",  "title": "Reports",  "controls": 9,  "seen": "2 hours ago" } ] }
```

And the map is not only a hint. Each control comes back with a `use` string —
`role=button|Sign in`, `href=/settings` — which `cairn_act` takes directly as its `ref`. That
is the difference between knowing a button is there and not having to read the page to press
it. A page Cairn has already walked costs no reading at all.

It matters most where one site carries many tasks — an end-to-end test suite, an admin
console, a portal you work in every day. Test one is still a first visit. Tests two to fifty
are not.

Every page carries when it was seen, and Cairn says so out loud: this is what was there last
time, not a promise about now. The same honesty as a locator, for the same reason.

Ids are generalised, so `/invoices/2026-09` and `/invoices/2026-10` are one page rather than
twelve. The map is capped and cannot grow without end. `cairn forget` takes it with
everything else.

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

**What travels:** the steps, every ranked locator with the evidence it earned, the checks, the
hard-won notes about the site — *"the tab badge is cached, trust the Open count"* — and the
**map**. Bob does not just inherit one route; he inherits the shape of the site, so his next
task there is cheap too. Sharing tells you exactly which pages went, and `cairn map` shows
their contents before you share.

**What never travels:** anything typed into a field, and which account was used. A shared login
step arrives asking *you* for your own credentials, resolved from your machine. Sharing tells
you exactly which notes became visible and which values were held back.

When a borrower repairs a broken step, the fix can be contributed back into the original, so a
route improves across agents who never spoke to each other.

## Selling a trail

Sharing works when two agents sit on one machine and read one file. Two agents on different
machines share nothing but a network — and nobody publishes for strangers unless it is worth
their while. So a trail can be sold.

```bash
# alice, who already knows the site
cairn share posthog.com
cairn sell --port 8402                  # needs CAIRN_PAY_TO

# bob, on another machine, with his own memory
cairn buy http://alice:8402 --site posthog.com     # needs CAIRN_WALLET_KEY
cairn run --site posthog.com --task "…"            # one call
```

Browsing the shop is free — you have to see what you are buying:

```
GET /trails/posthog.com          200  what is for sale, how many clean runs behind each
GET /trails/posthog.com/weekly   402  Payment Required
                                 200  the trail, once a payment settles
```

That is [x402](https://x402.org), an HTTP standard for machine-to-machine payments: the server
answers **402** with what it wants, the client signs a USDC authorisation and retries, a
facilitator settles it on chain. It costs **$0.01 on Base**, which is less than the model
calls exploring the site would burn.

**What travels is the route, not an account.** Everything typed into a field is stripped
before it leaves, exactly as it is for free sharing — so a bought sign-in step arrives asking
*you* for your own credentials.

**The trail never goes on chain.** Only the payment does. A receipt proves a purchase
happened; it is not a copy of what was bought. Forget the site and the route is gone, while
the transaction stays public forever and still cannot bring it back.

## Partner stacks

| stack | what it does here | where |
|---|---|---|
| **[Sibyl Memory](https://hack.sibyllabs.org)** | every trail, every site fact, every run, share, purchase and repair | [`package/src/cairn/store.py`](package/src/cairn/store.py) — the only file that imports the memory client |
| **[Base](https://base.org)** | the x402 payment that a trail is sold for, in USDC on Base Sepolia | [`package/src/cairn/payments.py`](package/src/cairn/payments.py) — the only file that imports x402 |

Both are one file each, and a test walks the source to keep it that way. The onchain action
is a real settled payment for a real resource: without it the shop answers 402 and the buyer
gets nothing.

**A real purchase, on chain:**
[`0xd7de79f7…3e14`](https://sepolia.basescan.org/tx/0xd7de79f7f9bd41491d1419bd87e64ce10b674570204c3b0f379ced3a23173e14)
— 0.01 USDC from the buying agent to the selling agent, Base Sepolia block 46345013. The
buyer held no ETH; in x402 the facilitator submits the transaction and pays the gas, and the
buyer only signs.

That purchase is still subject to the deletion test. Run `cairn forget` on the buyer and the
trail is gone, while the receipt stays in the journal with that transaction hash on it — a
receipt proves a purchase happened, it is not a copy of what was bought. The chain never
becomes a way around the memory.

Base Sepolia rather than mainnet, and the README says so rather than implying otherwise. The
free public x402 facilitator supports testnet only, and test USDC comes from the Circle
faucet with no account. Moving to mainnet is configuration — `CAIRN_NETWORK`,
`CAIRN_FACILITATOR`, `CAIRN_PAY_TO` — not a code change.

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
| **warm** `site_map` | every page it has looked at, and the controls that were on them |
| **cold** `write_event` | every run, drift, repair, share, borrow and purchase, in order |

Entities are unique per `(tenant, category, name)` at the schema level, so a site can never
hold two conflicting routes for the same task. Agent identity is a tenant, which is what makes
one agent's memory genuinely invisible to another.

## How memory made this possible

Memory is not a speed-up bolted onto a working agent. It is the product. Take the Sibyl layer
out and what is left is a Playwright wrapper that reads a page from scratch every time — which
is the thing every AI already does, and the thing Cairn exists to stop.

Three specific abilities exist **only** because of the memory layer:

**A route outlives the session.** The warm `playbook` entity is what turns a browsing session
into something a later run can execute. Entities are unique per `(tenant, category, name)` at
the schema level, so one site and one task can never hold two conflicting routes — the fast
path is safe to trust without a single model call to check it.

**The route gets better every time it runs — that is stored, not recomputed.** Each step keeps
up to nine ways to find its control, ranked by which have actually worked, plus a health score
and the checks that prove the step landed. Every run writes that ranking back. This is why a
changed site costs one repaired step instead of a fresh exploration: Cairn knows which locator
died and which still holds, because the outcome of every previous run is in memory. Wipe it and
there is nothing to repair *from* — only re-learning.

**A second task on a known site is cheaper than the first.** Cairn keeps a map of every page
it has looked at, so a new task starts from what is already known rather than from a blank
page. This is memory doing work for a job it was never recorded for — the first task paid for
it, every later one spends it. Delete the map and every task on a site is a first visit again.

**Agents can hand routes to each other.** Identity is a Sibyl tenant, so one agent's memory is
genuinely invisible to another. Sharing, borrowing, and buying a trail over x402 are all moves
inside the memory layer — a copy from one tenant to the `cairn-commons` tenant and back. There
is no other channel between two Cairn agents. Remove the layer and they cannot coordinate at
all.

Underneath, the cold tier (`write_event`) records every run, drift, repair, share, borrow and
purchase in order. That is what makes health scores and `cairn show` true rather than guessed.

**The deletion test is one command.** `cairn forget --site github.com` and the next run raises
`NoTrailError` — it does not quietly fall back to exploring, it stops and says the memory is
gone. Slow again, honestly. That is what load-bearing means here.

## Forgetting

```bash
cairn forget --site github.com
```

Cairn now has nothing to follow for that site and has to learn it again. That is the point:
**the memory is load-bearing, not a cache in front of something that works anyway.**

That includes the map. A judge who deletes the memory and finds Cairn still knows the site's
pages has found a gate that does not hold, so `cairn map` comes back empty too — there is a
test for exactly that in `package/tests/test_deletion_gate.py`.

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

**`cairn_map(site, path?)`** — what Cairn already saw on a site: the pages, then the controls
on any one of them. Read from memory, so it costs no page load.

**`cairn_read(kind, ref?)`** — 14 kinds: the control list, text, all_text, value, checked,
visible, enabled, editable, attribute, count, url, title, console errors, failed requests.

It handles the things that actually break recorded flows: shadow DOM, iframes, `div`s
pretending to be buttons, content that loads late, cookie banners that appear whenever they
feel like it, confirm dialogs, new tabs, and file pickers with no visible input. There is a
page in the repo containing all nine at once, and a test that walks every one.

`evaluate` is the escape hatch — run your own JavaScript when a site does something nobody
anticipated. It is deliberately never recorded into a route, because a step made of code
cannot be repaired.

## When something goes wrong

Start here:

```bash
cairn doctor
```

It checks everything Cairn needs that is not Python code — the browser, the profile, the
memory file, a writable downloads folder, and the optional market extra — and prints the
exact command to fix whatever is missing. It exits non-zero only if something essential is
broken, so it is safe to put in a setup script.

```
  ok    python     3.13
  ok    cairn      0.1.0
  ok    browser    chrome
  ok    profile    opens with bundled Chromium
  ok    memory     3 site(s) remembered
  ok    downloads  /home/you/.cairn/downloads
  --    market     not installed
        Only needed to sell or buy trails: pip install "cairn-browser-mcp[market]"

  Everything Cairn needs is here.
```

The five things that actually go wrong:

**"Cairn has no browser to drive yet."**
`pip install` brings the Python code, not a browser — Chromium is a separate ~150 MB
download. Run `playwright install chromium`. This is the most common first-run failure and
nothing is wrong with your setup.

**"Cairn cannot open a window here: this machine has no screen."**
Signing in happens in a real window a person types into, so `cairn login` cannot work over
plain SSH or in a container. Either sign in on a computer with a desktop and copy
`~/.cairn/browser-profile` across, or forward a display with `ssh -X`. Normal runs are
headless and unaffected.

**"Cairn could not open its browser profile."**
Two different causes produce the identical message from the browser, and Cairn will not
guess between them: another Cairn run or a sign-in window still has the profile open, or the
profile is in a state no browser will accept. Close any other run first. If that was not it,
deleting `~/.cairn/browser-profile` fixes it — at the cost of signing you out everywhere.

To run two agents at the same time, give each its own profile instead of sharing one:

```bash
CAIRN_PROFILE=~/.cairn/profile-b cairn-mcp
```

**A captcha.**
Cairn stops and says so. It does **not** mark the trail broken and does not try to solve it —
a captcha is a human check, and pretending otherwise would throw away good steps for a page
the run never reached. Open the site yourself, clear the check once, and run again.

**"Cairn needs the password for … and never stores it."**
By design: a trail records *that* a password is typed, never the value. Provide it on the
machine that replays, either as an environment variable
(`CAIRN_SECRET_BILLING_ACME_COM_PASSWORD`) or in `~/.cairn/secrets.json`:

```json
{ "billing.acme.com": { "password": "..." } }
```

Neither is ever written to memory. Export a trail and grep it — there is nothing to find.

## Development

Working on Cairn itself, rather than using it:

```bash
git clone https://github.com/rohit-jsfreaky/cairn
cd cairn
python -m venv .venv

# Install the market extra too, or the 47 tests covering the Base payment path
# are skipped and the run still says "all passed".
.venv/Scripts/python -m pip install -e "package[dev,market]" -e "mcp[dev]"   # Windows
# .venv/bin/python -m pip install -e "package[dev,market]" -e "mcp[dev]"     # macOS / Linux

.venv/Scripts/python -m playwright install chromium

cd package && ../.venv/Scripts/python -m pytest      # 539 tests
cd mcp     && ../.venv/Scripts/python -m pytest      #  98 tests
../.venv/Scripts/python -m ruff check src/ tests/
```

Opening Claude Code **inside the clone** needs no `claude mcp add` — the checked-in
`.mcp.json` offers the server straight away, on any operating system.

```
package/   the engine — browser, memory, replay, repair, sharing, CLI
mcp/       the MCP server: 15 tools over the engine
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
