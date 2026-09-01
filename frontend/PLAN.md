# PLAN — frontend/ (Phase 4, Sep 6–7)

Finish line in `../MASTER-PLAN.md`. Needs backend SSE + snapshot routes (Phase 3) working.
In the demo video this screen sits BESIDE the Claude Code terminal: the terminal shows the
agent, this shows the memory.

### 3a. Skeleton + design system (Sep 5)
- create-next-app (TS, Tailwind, App Router), strip ALL boilerplate.
- Fonts (@fontsource Shantell Sans + Hanken Grotesk), Phosphor icons, color tokens,
  inner-shadow card primitive. Dark, warm, opinionated — this is the look of the demo video.
- `lib/api.ts` + `lib/api-types.ts` mirroring backend schemas.
- ✅ empty layout with the four zones, styled, typecheck clean.

### 3b. Live run view (Sep 5–6)
- SSE hook → agent step list (left panel): intent, action, verify ✓/✗, repair badge with
  before/after locator.
- Memory panel (right): entity cards appear on writes, glow on reads, drift diff on repair.
- ✅ panels fill correctly during a real run against the demo site.

### 3c. Metrics + controls (Sep 6)
- Metric cards comparing last cold run vs last warm run (time, LLM tokens, steps replayed,
  repairs) — from `GET /runs/{id}`.
- Controls: task picker, RUN, variant A/B toggle, FORGET with a confirm.
- ✅ the full 4-beat demo (cold → warm → break+repair → forget → slow) can be driven from
  this screen alone, no terminal on camera.

### 3d. Polish pass (Sep 6)
- Empty states, loading states, error toast if backend is down.
- 60-second stranger test (the Phase 3 finish line): screen-record run 1 → run 2, show it to
  someone with zero context. They must be able to say what happened.

### Deliberately NOT building
More pages, auth, settings, mobile layout, mock-data mode. One page, real data, beautiful.
