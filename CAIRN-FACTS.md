# Cairn — every fact in one place

Written for the demo video, the posts and the submission. **Everything here is measured or
checked against the code.** Nothing is rounded up, nothing is guessed. If a number is not in
this file, do not say it on camera.

Last updated 2026-09-05.

---

## 1. The name and the line

**Cairn.** A cairn is a small pile of stones hikers leave on a trail, so the next traveller
knows the way.

> **Your AI can use websites. But it forgets how, every single time. Cairn makes it remember.**

- Site: **cairnmcp.fun**
- Install: `pip install cairn-browser-mcp` then `playwright install chromium`
- Add to Claude Code: `claude mcp add cairn -- cairn-mcp`
- Licence: MIT. Python 3.11+.
- Two published packages: `cairn-browser` (the engine) and `cairn-browser-mcp` (the MCP server).

---

## 2. The problem, in one paragraph

An AI agent can already use a website: it opens the page, reads the whole thing, works out
which button to press, presses it. It does that well. Then the session ends and all of it is
gone. Tomorrow the same request costs exactly the same — the same page read, the same
reasoning, the same tokens. Every AI browsing tool today is a very good tool with no memory.

## 3. What Cairn is

A browser that remembers, handed to an AI as an **MCP server**. Claude Code, Cursor, Codex,
or anything that speaks MCP.

**Cairn is a tool, not an agent.** It has no brain and no API key of its own. The user's AI
does the thinking. Cairn supplies the browser and the memory. That is why it needs no model
key, installs in one command, and a judge can run it inside their own Claude Code.

---

## 4. How it works — the four beats

**1. Cold run (the first time).** The AI explores: `cairn_act` to click and type, `cairn_read`
to look, `cairn_save` when the task is done. Cairn writes down every move and turns it into a
**trail** — steps, each with up to nine ways to find its control, and a check that proves the
step landed.

**2. Warm run (every time after).** One `cairn_run` call. Cairn replays the trail, verifies
each step, and hands back the answer. **Zero model calls.** Plain deterministic Python.

**3. Repair (when the site changes).** Cairn does not throw the trail away. It finds the one
step that broke, asks the AI about **that step only**, stores the fix, and keeps everything
else. A redesign costs one repaired step, not a fresh exploration.

**4. Forget.** `cairn forget --site github.com`. The memory for that site is wiped and the
next run raises `NoTrailError` — it does not quietly fall back to exploring. It stops and says
the memory is gone. Slow again, honestly.

### The tool surface

17 MCP tools: `cairn_run`, `cairn_act`, `cairn_read`, `cairn_save`, `cairn_repair`,
`cairn_sites`, `cairn_show`, `cairn_map`, `cairn_forget`, `cairn_note`, `cairn_profile`,
`cairn_login`, `cairn_login_done`, `cairn_share`, `cairn_borrow`, `cairn_commons`, `cairn_buy`.

Behind `cairn_act` and `cairn_read` sit **35 actions and 14 read kinds**. Both tool
descriptions are *generated* from those registries, so a capability cannot exist without being
discoverable.

---

## 5. Where the memory lives — Sibyl Memory

**Every read and write goes through one file: `package/src/cairn/store.py`.** Nothing else in
the project imports the memory client, and a test enforces that by walking the source. A judge
finds all of it in ten seconds.

| tier | Sibyl call | what Cairn keeps there |
|---|---|---|
| **warm** | `set_entity("playbook", …)` | the route: steps, locators, checks, health |
| **warm** | `set_entity("site_knowledge", …)` | what survives a redesign — needs a login, sends a code, where the number really is |
| **warm** | `set_entity("site_map", …)` | every page it has looked at and the controls on them |
| **cold** | `write_event(…)` | every run, drift, repair, share, borrow and purchase, in order |

- **Identity is a Sibyl tenant.** One agent's memory is genuinely invisible to another.
- **The shared pool is one fixed tenant, `cairn-commons`.** Sharing, borrowing and buying a
  trail are all copies between tenants. There is no other channel between two Cairn agents.
- Entities are unique per `(tenant, category, name)` at the schema level, so one site and one
  task can never hold two conflicting routes. That is why the fast path is safe to trust
  without a model call to check it.

### Why memory is load-bearing, not a speed-up

Take the Sibyl layer out and what is left is a Playwright wrapper that reads a page from
scratch every time — which is what every AI already does, and the thing Cairn exists to stop.
Four abilities exist **only** because of the memory layer:

1. **A route outlives the session.** The `playbook` entity is what turns a browsing session
   into something a later run can execute.
2. **The route gets better every run, and that is stored, not recomputed.** Each locator keeps
   its hit and miss record. That is why a changed site costs one repaired step: Cairn knows
   which way of finding the control died and which still holds. Wipe it and there is nothing
   to repair *from*.
3. **A second task on a known site is cheaper than the first.** The site map means a new task
   starts from pages Cairn has already stood on. The first task paid for it; every later one
   spends it.
4. **Agents can hand routes to each other.** Identity is a tenant, so sharing is a memory
   operation and nothing else.

**The deletion test is one command:** `cairn forget --site <domain>`.

---

## 6. The numbers — measured, with the caveats

All of these are reproducible. The scripts are in the repo:
`package/benchmark_agents.py`, `package/benchmark_tools.py`, `package/benchmark_sites.py`.

### 6a. THE HEADLINE — a real job, done ten times

Three multi-step journeys on public sites. Every run is a **fresh Claude session** with
nothing carried over but Cairn's memory. Sonnet 5, medium effort. Against
`@playwright/mcp@0.0.80` and `chrome-devtools-mcp@1.8.0`, pinned. 90 sessions, $9.10.

The journeys:
- **github.com** — open microsoft/playwright, click the Issues tab, report the open count
- **books.toscrape.com** — open the Travel category, open the first book, read its price
- **quotes.toscrape.com** — open the first author's About page, read their birth date

| journey (10 runs each) | **Cairn** | Playwright MCP | Chrome DevTools MCP |
|---|---|---|---|
| github.com | **28 calls · 1.36M** | 83 · 3.38M | 33 · 1.68M |
| quotes.toscrape.com | **27 calls · 1.32M** | 60 · 2.57M | 60 · 2.62M |
| books.toscrape.com | **41 calls · 1.93M** | 56 · 2.77M | 56 · 2.81M |
| **all three** | **96 calls · 4.61M tokens** | 199 · 8.73M | 149 · 7.10M |

**52% fewer tool calls and 47% fewer tokens than Playwright MCP.**
**36% fewer calls and 35% fewer tokens than Chrome DevTools MCP.**
All three tools answered correctly 30 times out of 30.

Cairn wins every journey. What the totals hide is the shape, which is the real point:

| journey | Cairn, run by run |
|---|---|
| github.com | 10, then **2, 2, 2, 2, 2, 2, 2, 2, 2** |
| quotes.toscrape.com | 9, then **2, 2, 2, 2, 2, 2, 2, 2, 2** |
| books.toscrape.com | 10, 7, 10, then **2, 2, 2, 2, 2, 2, 2** |

Playwright's github row is `8, 8, 18, 7, 9, 9, 7, 6, 5, 6`. It never gets cheaper, because
it is not trying to remember. **Cairn pays once and then costs 2 calls, however many steps
the journey has.**

Honest notes: Cairn costs the most on run 1 — it does the job AND learns the site. On
`books.toscrape.com` it had to learn three times before it settled (runs 1, 2 and 3), which
is why that row is 41 and not 27.

### 6b. The same thing measured on one-page lookups, where Cairn barely wins

Six public sites. One task each. **Ten runs per site, every run a fresh session** with nothing
carried over but Cairn's memory. Model: Sonnet 5, medium effort. Compared against
`@playwright/mcp@0.0.80` and `chrome-devtools-mcp@1.8.0`, pinned.

| site | Cairn | Playwright MCP | Chrome DevTools MCP |
|---|---|---|---|
| pkg.go.dev | **25 calls · 1.23M tokens** | 55 · 2.26M | 60 · 2.50M |
| github.com | **35 · 1.61M** | 51 · 2.16M | 60 · 2.53M |
| en.wikipedia.org | 25 · 1.23M | **20 · 1.02M** | 45 · 1.96M |
| pypi.org | 30 · **1.42M** | 30 · 1.47M | 30 · 1.51M |
| docs.python.org | 26 · 1.27M | **20 · 1.02M** | 30 · 1.40M |
| huggingface.co | 47 · 2.05M | **30 · 1.51M** | 30 · 1.55M |
| **all six** | **188 calls · 8.81M** | 206 · 9.44M | 255 · 11.45M |

**Read it honestly:**
- Cairn wins overall: **188 calls against 206 and 255**, and fewer tokens than both.
- On a learned site a warm run is **2 tool calls**, and one of those two is the harness
  loading the tool schema — not Cairn. The other tools pay that call too.
- **Cairn loses on `en.wikipedia.org` and `docs.python.org`, and that is in the table on
  purpose.** On a small page Playwright's `navigate` reply already contains the heading, so it
  costs 2 calls as well. There is nothing left for memory to save, and Cairn never earns back
  the 7 calls it spent learning. **On "open one page, read one visible fact", Cairn is not
  cheaper.** It wins when the page is big or the task has more than one step.
- `huggingface.co` is the one site that never settled — it stays at 4–5 calls per run. Cause
  not yet found. It is in the table because leaving it out would make the table a lie.
- Cairn's cold run costs MORE than the others. It is doing the job *and* learning the site.

### 6c. Determinism — the finding nobody was looking for

Ten runs on `pkg.go.dev`: Cairn's nine warm runs all cost between **93,513 and 103,887
tokens** — about 10k apart. Playwright's ten runs ranged over **147k**, Chrome DevTools' over
**187k**, including runs where the model got confused by a page it had already read nine
times.

Replay is deterministic Python with no thinking in it, so the same task costs the same every
time. **A tool whose price you can predict is a different product from one whose price you
cannot.**

### 6d. Tool cost, with no model involved

`benchmark_tools.py` drives the same three MCP servers with a fixed script — no model, no
randomness, free to reproduce. Six sites:

| | tool calls | bytes handed to the AI |
|---|---|---|
| Cairn, run 1 | 24 | 114,493 |
| **Cairn, run 2** | **6** | **3,604** |
| Playwright MCP, run 2 | 18 | 891,845 |
| Chrome DevTools MCP, run 2 | 18 | 851,721 |

A learned site costs **3,604 bytes instead of 891,845**. On `pkg.go.dev` alone, one reading
costs Playwright MCP 506,608 bytes and a warm Cairn 615.

*What this does not prove: that a real agent saves that much — a script has no brain. What it
does prove is the size of what each tool hands back, which no amount of cleverness changes.*

### 6e. Breadth

`benchmark_sites.py`, 26 public websites, cold then warm: **24 of 26 replayed warm**,
72 → 24 tool calls, 24 → 0 page reads, 556,576 → 3,027 bytes (**99.5% less**), **0 model
calls** on the warm run.

### 6f. Tests

**655 engine tests + 133 MCP tests, all green.** Ruff clean in both packages. CI runs on
Ubuntu, macOS and Windows.

---

## 7. Base — the partner stack

Cairn sells a trail to another agent over **x402**, an HTTP standard for machine-to-machine
payments. The buyer's agent gets a `402`, pays in USDC on **Base Sepolia**, and the trail is
released.

- All x402 code is in **one file**: `package/src/cairn/payments.py`. Nothing else imports
  x402, web3 or eth_account — enforced by a test.
- Real settled transaction:
  `0xd7de79f7f9bd41491d1419bd87e64ce10b674570204c3b0f379ced3a23173e14` on
  `sepolia.basescan.org`.
- The buyer held no ETH: in x402 the facilitator submits the transaction and pays the gas.
- Replay never touches this. The warm path may not import `payments` or `shop` — enforced by a
  test — so replay stays offline, deterministic and free.

---

## 8. What is honest to say, and what is not

**Say:**
- A learned site is one tool call and zero model calls.
- Delete the memory and Cairn is slow again — `cairn forget` proves it in one command.
- Over ten repeats on six real sites, Cairn used fewer tool calls and fewer tokens than both
  competitors.
- It is deterministic: same task, same cost, every run.
- On a small page with a one-line answer, Cairn is **not** cheaper.

**Do not say:**
- "10x faster", "39x cheaper", or any number not in section 6.
- That it beats every tool on every site. It does not, and the table says so.
- Anything about compaction or long sessions — we have not measured it.

---

## 9. Prior work (required in the README)

- **`pig-dot-dev/muscle-mem`** (766★, "a cache for AI agents to learn and replay complex
  behaviors", quiet since Jun 2025). **The difference:** Cairn is not a cache. It verifies
  every step, detects when the site changed, repairs only the broken step, and hands knowledge
  to other agents.
- The planning documents in this repo written before 2026-09-01.

---

## 10. Where things live

| path | what |
|---|---|
| `package/src/cairn/store.py` | **every Sibyl Memory call.** The only file that imports the client |
| `package/src/cairn/payments.py` | **every x402 call.** The only file that imports x402 |
| `package/src/cairn/executor.py` | the warm path: replay, verify, repair |
| `package/src/cairn/operations.py` | the cold path: look, act, read, save |
| `package/src/cairn/distill.py` | raw trace → trail |
| `mcp/src/cairn_mcp/server.py` | the 17 MCP tools |
| `package/tests/test_deletion_gate.py` | the judges' deletion test, automated |

---

## 11. A suggested order for the video

1. **The problem.** An AI reads a whole page to click one button. Tomorrow it does it again.
2. **First run.** Cairn explores with the AI and saves the trail. Show it costing more.
3. **Second run — the beat that matters.** Fresh session, timestamp on screen, one
   `cairn_run`, answer returned, no page reading. Unedited.
4. **Break the site.** A control moves. Cairn repairs one step and remembers the fix.
5. **The numbers.** Section 6a and 6b.
6. **Delete the memory.** `cairn forget --site …` on camera, then the same run is slow again.
   This is the proof that memory is the product.
7. **Agents share.** One agent leaves a trail, another picks it up — or buys it on Base.
