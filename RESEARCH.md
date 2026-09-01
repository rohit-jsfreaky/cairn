# RESEARCH — verified facts only

Rule: every entry has a **date** and a **source** (the page actually opened). If a fact you
need is not here, open the real docs with Playwright MCP and add it. Never use WebSearch
(stale). Never build on a guess.

## Sibyl Memory API (2026-08-31, docs.sibyllabs.org/memory/concepts)

Local-first, file-based. SQLite + FTS5 full-text search. Zero embeddings. Python SDK.

```python
from sibyl_memory_client import MemoryClient
memory = MemoryClient.local("~/.sibyl-memory/memory.db")
memory.set_entity("project", "atlas", {"status": "active"})   # WARM — things it knows
memory.get_entity("project", "atlas")
memory.write_event(acted=["deployed atlas v1.2"])             # COLD — journal, time order
memory.search_entities("atlas")                               # FTS5 across everything
```

| tier | intent | API |
|---|---|---|
| HOT state | what you're working on right now | `set_state(key, body)` / `get_state(key)` |
| WARM entities | things the agent knows about | `set_entity(kind, name, body)` / `get_entity` |
| COLD journal | what happened, in time order | `write_event(...)` / `read_events(...)` |
| REFERENCE | documents looked up by name | `set_reference(key, body)` / `get_reference` |
| ARCHIVE | frozen, recoverable | `archive_entity(kind, name)` |

- Entity unique per `(tenant_id, category, name)` — enforced at schema level. A site cannot
  have two conflicting playbooks. Use this in the pitch.
- `archive_entity` = recoverable. `delete_entity` = permanent. Archive dead locators, never
  delete them (matches Sibyl's own forgetting-vs-deleting doctrine).
- Multi-tenant via `tenant_id` — use separate tenants for the two-agent coordination demo.

## Cairn memory design (decided 2026-08-31, see contexts/sibyl-labs-hackathon.md in hackathon_ideas)

- WARM `set_entity("playbook", "<domain>", ...)` — steps with **intent + postcondition +
  ranked locators (role / text / css / structural) + health score**
- WARM `set_entity("site_knowledge", "<domain>", ...)` — durable facts that survive redesigns
  (needs 2FA, rate limits, account email)
- COLD `write_event` — every run, every drift detection, every repair (timestamped)
- Recall path = deterministic replay + postcondition checks, LLM nearly idle. Explore/repair
  path = LLM drives. This gives the huge tokens metric contrast for the demo.

## Package versions (verified on PyPI/npm registries, 2026-08-31)

| package | version |
|---|---|
| sibyl-memory-client | 0.7.0 |
| sibyl-memory-cli | 0.3.23 |
| sibyl-memory-mcp | 0.1.14 |
| playwright (python) | 1.62.0 |
| fastapi | 0.141.1 |
| x402 (python SDK — it exists) | 2.21.0 |
| next | 16.3.3 |
| @phosphor-icons/react | 2.1.10 |

## x402 / Base (2026-08-31, docs.x402.org + docs.base.org + faucet.circle.com)

- Buyer prerequisites: "a crypto wallet with USDC". Facilitator settles onchain on behalf of
  the server — agent only signs. Public x402.org facilitator is free and explicitly for
  testnet/dev.
- Test USDC: Circle faucet is "public and permissionless… no account required", 20 USDC per
  address per 2 h, Base Sepolia supported. No card, no KYC, ₹0.
- Testnet = Base Sepolia, production = Base mainnet. Same code, config change.

## Event rules (2026-08-31, hack.sibyllabs.org/rules — full copy in
hackathon_ideas/contexts/sibyl-labs-hackathon.md)

Gate (delete-the-memory test) → 100-pt rubric (40/25/20/15) → +10 PMF (verifiable only) →
×1.15 / ×1.25 partner multiplier. Teams 1–5, solo OK. Partners optional. No crypto experience
needed. Prizes in USDC on Base; they help winners set up a wallet.

## Prior art (2026-08-31, github search)

- **pig-dot-dev/muscle-mem** — 766★, "a cache for AI agents to learn and replay complex
  behaviors", Python, quiet since Jun 2025. Declare in README. Our delta: verification,
  step-level self-repair, cross-site transfer, Sibyl tiers.
- **engram.com** — "AI That Learns From You". Reason the Engram name was dropped.

## Model policy (locked 2026-08-31)

**No Anthropic API, ever.** The main path uses no model at all — the host AI (Claude Code /
Codex / Cursor) is the brain, reached through `mcp/`. Warm replay is deterministic Python.
If a standalone brain is ever needed (optional `package/src/cairn/model.py`, or CI tests),
it goes through **OpenRouter** only, as a plain HTTP call behind one interface. No model SDK
is a required dependency, and Cairn must always run fully with zero API keys set.

Anthropic list prices checked 2026-08-31 (claude.com/pricing) for reference only, since this
is the cost we are avoiding: Haiku 4.5 $1/$5 per Mtok, Sonnet 5 $2/$10, Opus 5 $5/$25,
Fable 5 $10/$50.

## Where the users actually are (verified 2026-08-31) — the distribution picture

**One plug, many sockets.** We ship ONE MCP server. Every one of these already accepts MCP
servers, so they cost us install docs, not code. Do NOT write a separate build per agent.

### OpenClaw — `openclaw/openclaw`, **388k stars**, TypeScript, updated continuously
Docs: docs.openclaw.ai. "Your own personal AI assistant. Any OS. Any Platform."
- ✅ **"Connect MCP servers"** is in their tools docs → our server plugs straight in.
- Extension paths: **tools · skills · plugins** (docs.openclaw.ai/tools, /tools/skills,
  /plugins) plus **ClawHub** and a Skills Registry (5,400+ community skills, see
  `VoltAgent/awesome-openclaw-skills`, 52k stars).
- ⚠️ **They already have browser control** — docs list Web browser, Browser
  (OpenClaw-managed), Chrome Extension, Browser control API, Browser login. So our pitch to
  OpenClaw users is NOT "here is a browser". It is **"your browser stops re-learning the same
  site every time."** Their users already browse with their agent, so they already have the pain.
- They also have a memory plugin category (Memory wiki, Memory LanceDB, Provider Memory) —
  memory is an accepted, understood need in that community.
- Note: MCP is not mentioned in their 112k-char README, but it is in the docs nav and the repo
  has ~91 commits / 1.1k issues referencing "mcp server".

### Others that accept MCP
Claude Code (Rohit's daily driver — make this one perfect first), Cursor, Codex.

## Hermes Agent — a target worth taking seriously (verified on PyPI, 2026-08-31)

`hermes-agent` 0.19.0, by **Nous Research**, MIT. docs: hermes-agent.nousresearch.com

> "The self-improving AI agent… the only agent with a built-in learning loop — it creates
> skills from experience, improves them during use… and builds a deepening model of who you
> are across sessions."

Facts that matter to Cairn:
- **Sibyl officially supports it.** `sibyl setup` connects to Claude Code, Codex **and Hermes**;
  `sibyl-memory-hermes` 0.3.16 ships a plugin implementing Hermes v0.13's `MemoryProvider` ABC
  into `$HERMES_HOME/plugins/sibyl/`, enabled via `memory: provider: sibyl` in
  `~/.hermes/config.yaml`. Building for Hermes = building inside the sponsor's own world.
- **Model-agnostic, OpenRouter explicitly supported** — matches our OpenRouter-only policy
  with zero friction.
- **Built-in cron scheduler**, runs unattended on a $5 VPS, reachable from Telegram/Discord/
  Slack. Unattended repeated web tasks are the single strongest case for Cairn: nobody is
  watching at 3am, so an AI improvising a click is unacceptable — deterministic replay is.
- Compatible with the **agentskills.io** open standard — possible export format for playbooks,
  worth a look if Phase 2 goes fast.
- Philosophically adjacent: Hermes creates skills from experience; Cairn creates *web* skills
  from experience. Complement, not competitor.

**OPEN:** does Hermes load MCP servers directly? If yes, Cairn's MCP server works there with
zero extra code (just install docs). If no, a thin Hermes plugin adapter is needed. Check the
Hermes docs before Phase 2e.

## Playwright MCP — why Cairn is not competing with it (positioning, 2026-08-31)

Playwright MCP gives an AI hands. It has **no memory**: run 2 costs exactly what run 1 cost —
same tool calls, same page snapshots dumped into the context window, same price, forever.
Cairn is built ON Playwright and adds the memory layer: explore once, then replay.

Three concrete wins to say out loud in the pitch and README:
1. **Repeat cost** — run 2+ is one tool call instead of ~30.
2. **Context window** — the host AI receives a result, not 30 page snapshots. This is Sibyl's
   own thesis ("the goal is the smallest correct context", 228 vs 11,892 tokens).
3. **Determinism** — replay is code, so it does the same thing every time. Required for
   scheduled/unattended runs, where an improvising AI is a liability.

**Also note for the judges:** an AI writing prose notes about a site into memory is the
"trivial notepad" the rules say scores at the floor. A Cairn playbook is an *executable,
self-verifying, self-repairing procedure*. That gap is the difference between the bottom of
the band and the top.

## MCP SDK candidates (verified on PyPI, 2026-08-31)

- `mcp` 2.1.1 — official Model Context Protocol SDK
- `fastmcp` 3.4.7 — "the fast, Pythonic way to build MCP servers and clients"
- Decide in Phase 2a after opening both docs; record the choice and reason here.

## Tailwind v4.3 + Next.js 16 install (2026-09-01, tailwindcss.com/docs/installation/framework-guides/nextjs AND nextjs.org/docs/app/getting-started/css, page dated Aug 25 2026)

Both official docs agree, and both still require the PostCSS file:

1. `npx create-next-app@latest <name> --typescript --eslint --app`
2. `npm install tailwindcss @tailwindcss/postcss postcss`
3. `postcss.config.mjs` with `plugins: { "@tailwindcss/postcss": {} }`
4. `@import "tailwindcss";` at the top of `app/globals.css`

What DID go away in v4 is `tailwind.config.js`. Theme tokens now live in CSS:
`@theme { --color-mint-500: ...; --font-display: ...; }` and each token generates its
utilities (`bg-mint-500`, `font-display`). Source: tailwindcss.com/docs/theme.

**Gotcha (2026-09-01):** `create-next-app@latest` wrote `"next": "16.3.4"` into package.json,
but the newest version published on npm is 16.3.3, so `npm install` failed with ETARGET.
Fix: pin 16.3.3 by hand. Check `npm view next version` before trusting the generator.

## Reference landing page — aside.com, computed styles read with Playwright (2026-09-01)

Read off the live DOM, not guessed. Used as the structural model for `frontend/`.

| thing | measured value |
|---|---|
| body font | Geist; display font is a custom licensed face |
| h1 | 48px / 52px line, weight **400**, letter-spacing −0.48px |
| h2 | 44px / 48px line, weight **450**, letter-spacing normal |
| lead paragraph | 20px / 28px, weight 400 |
| body paragraph | 18px / 28px |
| eyebrow link | 16px, weight 500, accent colour |
| container max-width | 1536px (also 896px for centred text blocks) |
| section vertical padding | 96px most often, then 64 / 128 / 144 |
| grid gaps | 24px |
| section divider | `border-b` at 6% black — hairlines, never heavy rules |
| hero | an INSET card: 16px page gutter, `rounded-3xl` (33.6px), `shadow-xl`, product shot cropped by the card's bottom edge |

Palette is stock Tailwind neutral plus one accent, converted from their `lab()` values:
ink `#090b0c`, secondary `#737373`, tertiary `#a1a1a1`, bands `#f5f5f5` / `#fafafa`,
accent `#0084d1`. Buttons: one style only, a solid black pill.

**The thing that matters most:** their card art is NOT abstract gradient. Each card holds a
piece of real product UI, drawn large and cropped by the card edge, sitting on a soft colour
blob. Downloaded and inspected: `1.webp`, `3.webp`, `banner.webp`.

## Animation stack (verified in node_modules, 2026-09-01)

- `lenis` 1.3.26. React usage: `import { ReactLenis } from "lenis/react"` plus
  `import "lenis/dist/lenis.css"`. To share one clock with GSAP, pass
  `options={{ autoRaf: false }}` and drive it from `gsap.ticker` — this exact pattern is in
  the package README (github.com/darkroomengineering/lenis/tree/main/packages/react).
- `gsap` 3.15.0 + `@gsap/react` 2.1.2. `useGSAP()` needs `"use client"` in the App Router and
  handles cleanup itself (gsap.com/resources/React).
- **Every plugin now ships free inside the `gsap` npm package.** Confirmed by listing
  `node_modules/gsap/`: ScrollTrigger, SplitText, DrawSVGPlugin, MorphSVGPlugin, Flip,
  ScrambleText, MotionPath, ScrollSmoother, Observer, Draggable, Inertia.
  `SplitText.create(el, { type: "lines,words", mask: "lines", aria: "auto" })`.
- **DrawSVG gotcha:** it cannot measure a path when the SVG uses
  `preserveAspectRatio="none"` together with `vector-effect="non-scaling-stroke"` — the browser
  refuses to report path length. Either keep the SVG proportional, or animate the shape with
  `scaleY` instead.

## Generating art with ChatGPT — what works and what does not (2026-09-01)

Worked well: photographic scenes and abstract texture (the misty trail hero, the top-down
pebble band). Prompt for pale, low contrast, and an empty area where text will sit.

Failed twice: anything containing UI text. A generated "light mode terminal" looked clearly
worse than the same thing built in markup, and a 3D render of a browser window did not fit the
page either. **Rule for this project: photography and texture from ChatGPT, product UI in
real markup.**

## Apple's corner system, and how to get it on the web (2026-09-01)

Apple does not draw circular corners. It draws a **superellipse** (a squircle), which is why
its cards and icons read smoother than a normal `border-radius`.

**CSS can now do this natively.** Source: squircle.js.org/blog/squircles-in-css (12 Jun 2026)
and MDN `corner-shape`.

- `corner-shape` sets the corner *curve*; `border-radius` still sets the corner *size*.
  Neither works alone — `corner-shape` with a zero radius does nothing.
- Keyword mapping: `round` = `superellipse(1)` (today's circular corner), **`squircle` =
  `superellipse(2)` = the iOS look**, `bevel` = `superellipse(0)`, `scoop` = `superellipse(-1)`,
  `square` = `superellipse(infinity)`. `superellipse(K)` draws `x^(2K) + y^(2K) = 1`.
- **Support:** Chromium 139+ only. Safari and Firefox do not support it and have announced no
  timeline; roughly 65% of users. MDN lists it as Limited availability / experimental.
- **This is why it is safe anyway:** the fallback is a plain rounded corner, which is what we
  would have shipped regardless. Verified live in Chrome 145: `CSS.supports('corner-shape',
  'squircle')` is true and the computed value is `squircle`.

**Concentric nesting.** From Apple's own docs (developer.apple.com/documentation/swiftui —
`Edge.Corner.Style.concentric` and `ConcentricRectangle`): "the system calculates the corner
radius to equal the container shape's corner radius minus the distance between" it and the
container. So **inner radius = outer radius − padding**, and if there is a border, subtract
that too (16px outer + 8px padding + 1px border → 7px inner, not 8).

**Depth.** Apple's card depth is a lit top edge and a hairline drawn *inside* the shape, so the
curve stays crisp, plus layered soft shadows rather than one hard one (technique: Josh Comeau,
"Designing Beautiful Shadows"). In CSS that is stacked `inset` box-shadows — a white top
highlight and a 1px inner hairline — before any outer shadow.

Applied in `frontend/app/globals.css` as: a global `corner-shape: squircle` in the base layer
(with `.rounded-full` opted back to `round`, because a pill should stay a pill), a 4px-stepped
radius scale, and the `surface` / `surface-raised` / `surface-floating` / `well` utilities.

## Animation skills + libraries (2026-09-01)

**Installed the official GreenSock skills** into `.claude/skills/` (project-local, not global):
`git clone https://github.com/greensock/gsap-skills` → copied its `skills/` folder. Eight
skills: gsap-core, timeline, scrolltrigger, plugins, react, frameworks, utils, performance.
The repo also confirms: after Webflow's acquisition, **every GSAP plugin is free**, including
commercial use, straight from the public npm package.

Things the skills changed in our code:
- Prefer `autoAlpha` over `opacity` (it manages `visibility` too).
- Animate transform/opacity only; never width/height/top/left. Our bars animate `scaleX`.
- `SplitText` should use `autoSplit: true` with an `onSplit` callback so it re-splits on resize
  and after the web font loads.
- Call `ScrollTrigger.refresh()` when layout actually changes — we call it once on
  `document.fonts.ready`, because the display font changes every line height.

**anime.js — checked (animejs.com) and NOT adopted.** Its v4 feature list (timeline, scroll
observer, stagger, SVG morph / line drawing / motion path, draggable, spring, scope) maps
one-to-one onto GSAP plugins we already have installed and free. Adding it would mean two
animation engines doing the same job, for a bigger bundle. Revisit only if a specific effect
turns out to be genuinely unavailable in GSAP.

## aside.com closing banner — how it is actually built (2026-09-01)

Inspected the live DOM. It is not a photo and not CSS: it is one background image on a
rounded card.

```
<div class="bg-landing-banner rounded-2xl bg-cover bg-center px-6 py-16 sm:py-24 xl:py-32">
   background-image: url(https://aside.com/images/bg-banner.png)   /* 2400 × 1100 */
```

The image itself is a soft azure glow rising from the bottom centre in a wide cone, fading
through pale ice blue to near white at the top edge and both top corners, plus a fine dot grid
visible only inside the bright area. Card radius computes to 22.4px.

Cairn copies the structure but draws the dot grid in CSS (a 16px `radial-gradient` dot pattern
masked with `radial-gradient(ellipse 62% 95% at 50% 108%)`) so it stays crisp at any width
instead of being baked into a raster at one size.

## OPEN QUESTIONS (do not build on assumptions for these)

1. Does Base **Sepolia** count for the partner bonus, or mainnet only? → asked in Discord,
   no answer yet. Phase 4b blocked until answered.
2. Pre-Sep-1 scaffolding OK if declared as prior work? → asked in Discord.
3. ~~Anthropic API key + budget~~ — CLOSED: no Anthropic, see Model policy above.
4. Exact x402 Python SDK usage (package `x402` 2.21.0) — open its docs before Phase 5.
5. sibyl-memory-client: confirm Windows path handling for `MemoryClient.local()` on Day 0.
