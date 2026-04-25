# Treehouse — Landing Site

Minimalistic marketing page for [Treehouse](../). Pure static landing — does not interact with the CLI or dashboard.

## Run

```bash
cd site
npm install
npm run dev      # http://localhost:3001
```

## Build

```bash
npm run build
npm run start    # http://localhost:3001
```

## Deploy

The site is a zero-config Next.js app. To ship to Vercel:

```bash
cd site
npx vercel        # first run: interactive login + project link
npx vercel --prod # subsequent prod deploys
```

Set `NEXT_PUBLIC_SITE_URL` to the final canonical URL (e.g. `https://treehouse.sh`)
in the Vercel project settings so OpenGraph and Twitter card URLs resolve to the
absolute production domain. If unset, the build falls back to `VERCEL_URL` and
finally to `http://localhost:3001`.

`app/opengraph-image.tsx` and `app/icon.tsx` are generated at build time via
`next/og` and fetch JetBrains Mono from GitHub raw — the build needs outbound
network access (Vercel build environments have it).
