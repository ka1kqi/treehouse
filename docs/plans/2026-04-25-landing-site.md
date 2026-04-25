# Treehouse Landing Site — Implementation Plan

**Goal:** Build a single-page marketing site for Treehouse — minimalistic, high-end, futuristic. Centerpiece is an interactive ASCII dot field that visually mirrors the project's concept (parallel agents, isolated sandboxes, merging back).

**Scope:** Static landing page only. No interaction with the CLI; the page describes the tool and points users at install + GitHub. The existing `web/` directory (the dashboard) is untouched.

**Stack:** Next.js 15, TypeScript, Tailwind, single `<canvas>` for the hero. No UI libraries.

---

## Status

| Phase | Status |
|---|---|
| 0 — Decisions | ✅ done |
| 1 — Scaffold | ✅ done |
| 2 — Static skeleton | ✅ done |
| 3 — Static dot field | ✅ done |
| 4 — Animated agents | ✅ done |
| 5 — Mouse interaction | ✅ done |
| 6 — Polish & a11y | ✅ done (reduced-motion, copy CTA, OG metadata, focus rings, OG image, favicon, twitter card) |
| 7 — Deploy | ⏳ ready to ship — `npx vercel --cwd site` (interactive auth required by user) |

## Decisions (Phase 0)

| Decision | Choice | Reasoning |
|---|---|---|
| Project location | `site/` (new sibling dir at repo root) | Keeps the dashboard at `web/` untouched; zero risk of cross-coupling. Two separate Next.js apps with their own `package.json`. |
| Accent color | Muted green `#7fd6a8` | Matches the dashboard's leaf palette (`--leaf-light` / `--sage` family in `web/app/globals.css`). Ties brand together without making the landing feel like a clone of the dashboard. |
| Mono font | JetBrains Mono | Already used in the dashboard, loaded from Google Fonts. Same family establishes brand kinship. |
| Background | `#0a0a0a` (near-black, not pure black) | Pure black reads as a void; `#0a0a0a` reads as deliberate. Matches the project's "deep forest at dusk" tone. |
| Foreground text | `#e8e8e8` | Off-white. Pure white is too harsh on near-black. |
| Hairline color | `rgba(255,255,255,0.08)` | Section dividers. Just barely visible, no card-like weight. |
| Dev port | `3001` | Dashboard runs on `:3000`. Pin in `package.json` to avoid collisions during local dev. |
| Hosting | Vercel (default) | Zero-config Next.js deploy. Fallback: static export for any host. |

---

## Phases

### Phase 1 — Scaffold (~30 min)
- `mkdir site && cd site`
- `npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --eslint --import-alias "@/*"`
- Strip boilerplate: empty `app/page.tsx`, replace `app/globals.css` with minimal resets + base tokens, delete sample SVGs.
- Pin JetBrains Mono in `app/layout.tsx` via Google Fonts.
- Pin dev port to `3001` in `package.json` scripts.
- **Ship gate:** `npm run dev` shows blank near-black page on `:3001`, mono font loads, no console errors.

### Phase 2 — Static skeleton (~1 hr)
Lay down all copy and section rhythm. No animation yet.
- Tailwind config: extend with `bg #0a0a0a`, `fg #e8e8e8`, `accent #7fd6a8`, `hairline rgba(255,255,255,0.08)`.
- `app/page.tsx` top-to-bottom:
  - **Hero:** placeholder div (static black) with eyebrow `TREEHOUSE / v0.1`, H1 `Parallel runtime isolation for multi-agent coding.`, sub, two bare CTAs (`[ pip install treehouse ]`, `[ github ↗ ]`).
  - **The problem:** one large sentence.
  - **How it works:** three columns numbered `01 / 02 / 03` (ISOLATE / OBSERVE / MERGE).
  - **Commands:** two-column monospace table, hairline top + bottom only.
  - **Footer:** single line `TREEHOUSE  ·  MIT  ·  2026`.
- 1100px max-width container, generous whitespace, hairline section dividers.
- **Ship gate:** page reads top-to-bottom as a real landing page, intentional even without the canvas.

### Phase 3 — Static ASCII dot field (~1 hr)
Get the visual in place before motion.
- New client component `app/components/DotField.tsx` rendering a `<canvas>`.
- Sized to the hero via `ResizeObserver`, `devicePixelRatio`-aware.
- ~14px grid, each cell drawn as `·` at ~20% opacity in mono.
- Position absolutely behind hero copy. Headline uses `mix-blend-mode: difference` to stay legible.
- **Ship gate:** calm static dot grid behind the hero; H1 reads cleanly.

### Phase 4 — Animated agents (~1.5 hr)
- 4–6 `Agent` objects: `{position, velocity, trail: Cell[]}`. Slow drift (~30px/sec).
- Each agent activates cells along its path. Activation decays over ~1.5s, brightening cells `·` → `•` with opacity falloff.
- When two agents' trails activate the same cell within ~200ms: flash as `○` at 100% opacity in accent color for ~200ms (the "merge" moment).
- `requestAnimationFrame` loop with delta-time so 60Hz / 120Hz monitors look identical.
- **Ship gate:** ambient motion that reads as deliberate, not busy. Reduce agent count or speed if it feels noisy.

### Phase 5 — Mouse interaction (~45 min)
- `pointermove` listener tracks cursor in canvas-local coords.
- Cells within ~120px of cursor: smooth cosine radial falloff brightens them and bumps up the density scale (`·` → `•` → `○`). No springs.
- Agents' velocity gets a small inverse-distance nudge away from the cursor (clamped, so paths stay coherent).
- **Ship gate:** moving the mouse feels alive — local cells respond, agents veer subtly, no jitter.

### Phase 6 — Polish & a11y (~30 min)
- `prefers-reduced-motion`: render a single static frame, skip the rAF loop.
- Install CTA: clicking copies `pip install treehouse` to clipboard, label flips to `copied` for 1.5s.
- GitHub link points at the actual repo.
- `app/layout.tsx`: real `metadata` (title, description, OG image).
- 1px accent focus rings on CTAs.
- Explicit canvas `width`/`height` to prevent CLS.
- **Ship gate:** Lighthouse perf ≥ 95, a11y ≥ 95, no console warnings, reduced-motion behaves.

### Phase 7 — Deploy (~30 min)
- ✅ `site/README.md` with install, dev, build, **deploy** sections.
- ✅ `app/opengraph-image.tsx` (1200×630, JetBrains Mono fetched at build time from GitHub raw, brand-matched dot field + accent merge dots).
- ✅ `app/twitter-image.tsx` re-exports OG image so Twitter cards use it.
- ✅ `app/icon.tsx` (32×32 favicon — accent ○ on `#0a0a0a`).
- ✅ `app/layout.tsx` `metadataBase` driven by `NEXT_PUBLIC_SITE_URL` → `VERCEL_URL` → localhost; `twitter` card set to `summary_large_image`.
- ⏳ Vercel: `npx vercel --cwd site` — needs interactive auth, hand to user.
- Custom domain optional. After domain is set, set `NEXT_PUBLIC_SITE_URL` in Vercel env so OG URLs resolve absolute.
- **Ship gate:** public URL renders identically to local, animates, CTAs work, OG image previews correctly on Twitter/Slack/Discord.

---

## Total scope
~5 hours focused work, deployable after Phase 6. Phases 1–2 alone produce a respectable static landing; later phases add the texture that makes it feel high-end.

## Out of scope
- Mobile-first layout (assume desktop, narrow on tablet).
- Any wiring to the FastAPI server or CLI.
- Blog, docs, multi-page navigation.
- Auth, analytics, cookie banners.
