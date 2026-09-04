# PROGRESS — frontend/

> Working memory for this folder. Read first, update before ending every session.

## Current state — 2026-09-01

- Next.js app is live at `frontend/`. `npm run dev` works, typecheck and lint are clean.
- **The landing page is built** (`/`). This was Rohit's call on day 1, ahead of the Phase 4
  dashboard. The dashboard is still not started and still depends on `backend/`.
- The landing page uses NO backend, and as of 2026-09-03 **every number on it is measured**.
  They come from `package/benchmark.py`, which runs a real browser against the demo site and
  which anybody can run. The placeholders written on day 1 are gone.

## Done

- [x] Scaffold: Next.js 16.3.3, TypeScript strict, App Router, no `src/`, ESLint.
      `create-next-app@latest` pins a `next` version that is not published yet, so
      `package.json` was corrected to 16.3.3 by hand.
- [x] Tailwind v4.3 wired the way the current docs say (see ../RESEARCH.md).
- [x] Fonts: Shantell Sans (display) + Hanken Grotesk (body) via @fontsource.
- [x] Logo: three stones. Measured from a generated mark, then rebuilt as clean vector so
      `public/logo.svg`, `components/CairnMark.tsx`, `app/icon.png` and `app/apple-icon.png`
      are all the same shape.
- [x] Art: `public/art/hero-trail.png` (misty trail, empty sky for the headline) and
      `public/art/band-pebbles.png` (top-down pebbles, empty centre for the closing text).
      Both generated in ChatGPT.
- [x] Landing page sections: hero, intro, capability, three beats, speed, fresh session,
      repair, control, closing, footer.
- [x] Animation: Lenis smooth scroll driven by the GSAP ticker; GSAP ScrollTrigger reveals;
      SplitText word reveals on headings; DrawSVG on the repair arrow; count-up on numbers;
      per-card timelines inside the three beat cards.
- [x] **Apple corner + depth system.** Global `corner-shape: squircle` so every radius on the
      page is a superellipse, not a circular arc (Chromium 139+; plain radius is the fallback).
      Capsules opt back out. 4px-stepped radius scale following Apple's concentric rule
      (inner = outer − padding). Depth via layered INSET shadows — `surface`, `surface-raised`,
      `surface-floating`, `well` — matching Rohit's locked inner-shadow rule.
- [x] Official GreenSock skills installed at `.claude/skills/` and applied: `autoAlpha`,
      `SplitText autoSplit`, transform-only animation, `ScrollTrigger.refresh()` on font load.
- [x] Art direction, final: nature photography was dropped entirely — landscapes and stone
      texture both read as a travel brand, not software. The page now uses two generated
      abstract images: `hero-sky.png` (pale blue sky with soft clouds, open at the top for the
      headline) and `band-glow.png` (a blue glow rising from the bottom centre, fading to white
      at the edges). The closing band adds a crisp CSS dot grid on top of the glow, masked to
      the bright area, rather than baking the dots into the image.
- [x] Speed section rebuilt on the reference site's benchmark layout: left-aligned heading,
      a row per run with a bar and a value, hairline separators, and a segmented control
      underneath. The rows tell the real story — Monday learns, Tue/Wed/Fri replay,
      Thursday the site changed and one step was repaired.

## Design system (measured off the reference site, not guessed)

Aside.com was read with Playwright and its computed styles recorded in ../RESEARCH.md.
Ours follows the same shape with Cairn's own type and colour:

- Container `max-w-[1280px]` with `px-6`. Section rhythm `py-24 / py-32`. Hairline
  `border-b border-black/6` between sections, no heavy borders.
- Ink `#0a0b0c`, body `#737373`, faint `#a1a1a1`, bands `#f5f5f5` and `#fafafa`.
  ONE accent: moss `#2e7d55`, used only for eyebrows, ticks and the winning bar.
- Headings in Shantell Sans at weight 450–500, never bold. Lead text 18–20px.
- Product UI is built in real markup, not generated as pictures. Two attempts at generating
  a terminal screenshot in ChatGPT were both worse than the markup version and were dropped.

## Share card (OG image)

`app/opengraph-image.png` + `app/twitter-image.png`, both 1200x630, with matching
`.alt.txt` files. Next's file convention generates every tag automatically — verified in the
rendered head: og:image with width/height/alt, `twitter:card = summary_large_image`, plus the
favicon and apple-touch-icon.

Generated in ChatGPT with `public/art/logo-mark.png` attached so it used our real flat mark
instead of inventing one. Two attempts: the first turned the logo into realistic 3D pebbles
and was thrown away; the second kept the mark flat and rendered all four lines of text
correctly. Source was 1672x941, centre-cropped to the 1.91:1 OG ratio and resized.

Note: this is the one case where generating text inside an image worked. It only worked
because the exact strings were given, spelling was demanded explicitly, and the result was
checked word by word before use. Still check any regenerated card the same way.

## Copy audit — 2026-09-01 (six mismatches found and fixed)

The page had drifted into describing a different product, mostly by borrowing the reference
site's framing along with its layout. Fixed:

1. Hero eyebrow said **"A browser with a memory"**. Cairn is not a browser — it drives
   Playwright on the host AI's behalf. Now "Works inside Claude Code, Cursor and Codex".
2. Card three said **"Fixes itself."** and the repair transcript read as if Cairn worked the
   fix out alone. Per `package/PLAN.md` 1e, Cairn *detects* the break and hands that one step
   back to the host AI. Copy now says Cairn notices and remembers, the AI works it out.
3. **"A saved recording"** — we store a playbook (intent, postcondition, ranked locators), not
   a recording. "Recording" describes `muscle-mem`, the prior work we differ from.
4. **"forgotten. 7 steps removed."** — `forget_site` archives, never deletes (Sibyl's
   forgetting-vs-deleting doctrine). Now "archived. 7 steps forgotten."
5. The hero picture had browser chrome with a URL bar — the same "we are a browser" claim in
   image form. Replaced with a Cairn header: mark, site, "driven by Claude Code".
6. Memory path showed `~/.cairn/memory.db`. Sibyl's real path is `~/.sibyl-memory/memory.db`.

**Rule going forward:** copy the reference site's LAYOUT, never its POSITIONING. Aside is a
browser. We are a tool their AI picks up.

## Next action

Dashboard (Phase 4) — still blocked on `backend/`. Do not start it early.

## Blockers / must-fix before the repo is public

- ~~The landing page numbers (2m 41s → 4.1s, 31 tool calls, 39×) are placeholders~~ —
  **FIXED 2026-09-03.** Replaced with measured output from `package/benchmark.py`. The
  default metric also changed from time to tool calls: the benchmark has no model thinking
  time in it, so the clock (0.8s vs 0.4s) is true but uninteresting, while 9 tool calls
  becoming 1 and 3 page reads becoming 0 is the honest measure of what memory removes.
- ~~The install command `claude mcp add cairn -- uvx cairn-mcp` is a placeholder~~ — the
  real command is now in the README (`claude mcp add cairn -- <path>/.venv/Scripts/cairn-mcp.exe`,
  because nothing is published to PyPI yet). Check the page still matches the README.
- ~~`metadataBase` is not set in `app/layout.tsx`~~ — **FIXED 2026-09-03.** It now reads
  `NEXT_PUBLIC_SITE_URL` and falls back to localhost, so `next build` is warning-free and the
  share card resolves as soon as that variable is set to the real domain.
- ~~Footer links (GitHub, Prior work, License) point at `#`~~ — FIXED 2026-09-03. They
  point at the real repository, and external ones open in a new tab.

## Session log

- **2026-08-31** — folder created, plan written. No code yet.
- **2026-09-01** — Next.js app scaffolded, Tailwind v4 wired, landing page built end to end,
  Lenis + GSAP animation layer added. Rebuilt once after Rohit's feedback: the layout was
  measured off the reference site instead of eyeballed, gradient card art was replaced with
  real product UI on soft colour blobs, and the flat icon row was replaced with UI tiles.

- **2026-09-03 (Base on the page)** — new `Trails.tsx` section, placed between `Control` and
  `Closing` so the white/mist alternation still holds. It carries the part of the story the
  page was missing entirely: a trail can be left for another agent for free, or sold to one
  on another machine for a cent over x402. Terminal card walks the real flow — free
  catalogue, 402, settled on Base Sepolia, then one call with zero model calls.
  It says **Base Sepolia**, not "Base", on purpose: that is what actually runs, and the
  rules disqualify fabricated evidence. Footer gained a "Sharing and selling" link to it.
  `next build` clean.

- **2026-09-04 (the landing page tells the truth about installing)** — both packages went up
  on PyPI on Sep 3, so the page's install story was a day out of date and understated the
  product: it still told visitors to clone the repository.

  `CopyCommand` now hands over `pip install cairn-browser-mcp` instead of `git clone …`. That
  button had deliberately carried the long clone command for weeks, because a copy button that
  gives somebody a failing command is worse than a longer honest one — `uvx cairn-mcp` would
  have fetched nothing. The short version is finally the true one.

  The line under it names the two remaining steps in the same words the README uses:
  `playwright install chromium` for the browser, then `claude mcp add cairn -- cairn-mcp` in
  the folder you work in. "No API key, no account" is held on one line with `whitespace-nowrap`
  — it broke across a line break at the default desktop width, which is the width a judge sees.

  Added a **PyPI** link to the footer's Project column, next to GitHub.

  Checked on a real build (`next build` + `next start`), not in dev: reads as three tidy lines
  at desktop width, and at 390px there is no horizontal overflow (`scrollWidth === clientWidth
  === 375`). Typecheck clean.

- **2026-09-05 (the real domain, and the images)** — Rohit bought **cairnmcp.fun**.

  `metadataBase` now DEFAULTS to it rather than falling back to `http://localhost:3000`. That
  fallback was a real trap: a deploy that forgot the environment variable would publish
  `http://localhost:3000/opengraph-image` as its social card — a link broken everywhere except
  the machine that built it. `NEXT_PUBLIC_SITE_URL` still wins, so a preview deployment can
  point at itself. Added a canonical URL, `og:url`, `og:site_name`, `og:locale`, plus
  `robots.ts` and `sitemap.ts` that both read the same constant, so the domain cannot be right
  in one place and stale in another.

  **The page art is WebP now: 2,008 KB became 27 KB.** `hero-sky` 1,155 → 18 KB and
  `band-glow` 853 → 9 KB, at `cwebp -q 82 -m 6`, which measures ~50 dB PSNR — visually
  identical, and the built page was checked side by side to be sure.

  **The social cards were deliberately NOT converted to WebP**, though that is what was asked
  for. Next's own installed docs (`node_modules/next/dist/docs/.../opengraph-image.md`) list
  `.jpg .jpeg .png .gif` for `opengraph-image` and `twitter-image`, and `.ico .jpg .jpeg .png
  .svg` for icons — WebP is in neither, and social platforms handle it badly anyway.
  Converting them would have broken the exact thing the domain change exists to fix. They went
  to progressive JPEG instead: **651 KB → 62 KB each**, checked by eye for artefacts.

  `logo-mark.png` and `logo.svg` are referenced by nothing — the mark is drawn inline in
  `CairnMark`. Left in place as source assets for the posts and the video rather than deleted.

  Both `pyproject.toml` Homepages now point at the site. That only reaches the PyPI page on the
  NEXT release; 0.2.0 went out an hour earlier and cannot be re-uploaded.
