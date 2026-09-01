# CLAUDE.md — frontend/ (the judge screen)

A Next.js dashboard with ONE job: make the memory visibly load-bearing. A judge who watches
it for 60 seconds must think "it remembered — that is why it got fast" without anyone
explaining. Pitch & presentation is 15% of the score and this screen is most of it.

Read `PLAN.md` for what to build, `PROGRESS.md` for where we are. Root rules in
`../CLAUDE.md` apply. Depends on `backend/` (Phase 2) — the backend API is the only data
source.

## Stack

Next.js 16 (App Router) · TypeScript strict · Tailwind ·
fonts via @fontsource: **Shantell Sans** (display) + **Hanken Grotesk** (body) ·
icons: **@phosphor-icons/react** · charts: tiny inline SVG, no chart library.

## Rohit's locked design rules (do not argue with these)

- NO Inter, NO generic SaaS fonts. NO Lucide, NO Material icons.
- Shantell Sans for display type, Hanken Grotesk for body, via @fontsource.
- Depth comes from layered INNER shadows, not drop shadows.
- Opinionated and polished beats neutral and safe. Taste wins scores.

## The one architecture rule

Thin client. Zero business logic, zero direct Sibyl access, zero LLM calls. Everything comes
from the backend API (SSE + REST). If the frontend needs data the API does not give, add the
route to the backend — do not compute it here.

## The screen (one page — resist adding more pages)

```
┌─────────────────────────────────────────────────────┐
│  metric cards: RUN 1 vs RUN 2 · time · LLM tokens   │
│                · steps replayed · repairs           │
├───────────────────────────┬─────────────────────────┤
│  AGENT (live)             │  MEMORY (live)          │
│  step list as it happens: │  entities appearing on  │
│  intent, action, verify   │  run 1 (writes), read   │
│  ✓/✗, repair badge        │  markers on run 2,      │
│                           │  drift + repair diffs   │
├───────────────────────────┴─────────────────────────┤
│  controls: task picker · RUN · variant A/B toggle   │
│  ("break the site") · FORGET (wipe memory)          │
└─────────────────────────────────────────────────────┘
```

The variant toggle and the FORGET button are demo props — they must look inviting enough
that a judge wants to press them. Pressing FORGET and watching the agent go slow again IS
the gate test, live.

## Clean code rules

- TypeScript strict, no `any`. API response types generated or hand-mirrored from
  `backend/schemas.py` in ONE file (`lib/api-types.ts`).
- Small components, one per file, colocated under `components/`. State via plain hooks —
  no state library for one page.
- One `lib/api.ts` for all fetch/SSE — components never call fetch directly.
- No dead code, no leftover boilerplate from create-next-app, no unused deps.

## Definition of done

Renders correctly during a REAL run (not mock data) + typecheck clean + PROGRESS.md updated.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
