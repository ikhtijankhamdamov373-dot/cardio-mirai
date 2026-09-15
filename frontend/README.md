# Cardio MIRAI — Frontend (Phase 1)

Next.js 14 + TypeScript + Tailwind. Isolated from the existing FastAPI
backend, which is untouched by this folder.

## Local development

```bash
cd frontend
cp .env.example .env.local     # then set NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev                    # http://localhost:3000
```

## Environment variables

| Variable | Purpose | Example |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Origin of the FastAPI backend. Used server-side only (rewrites + health route) — never sent to the browser as a raw fetch target. | `https://cardio-mirai.onrender.com` |
| `NEXT_PUBLIC_LEGACY_SITE_URL` | URL of the current production site, linked from the ECG AI migration notice until that page is ported. | `https://cardiomirai.com` |

Never commit `.env.local` — it's covered by `.gitignore`.

## API routing strategy

The browser only ever calls same-origin paths:
- `/api/health` → `app/api/health/route.ts`, a Next.js route that calls the
  backend server-to-server (no CORS involved, no backend host exposed).
- `/api/backend/*` → rewritten by `next.config.js` to
  `${NEXT_PUBLIC_API_BASE_URL}/api/*` (e.g. `/api/backend/analyze-wfdb` →
  `<backend>/api/analyze-wfdb`).

`lib/api.ts` is the single place that knows these paths — no component
should ever construct a backend URL directly.

## Tests

```bash
npm test          # Jest + Testing Library, 12 tests
npm run build     # production build + TypeScript check
```

## Deployment preview (does not touch cardiomirai.com)

1. Deploy this `frontend/` folder to a separate Vercel project (or a second
   Render static/site service) — e.g. `cardio-mirai-frontend-preview`.
2. Set `NEXT_PUBLIC_API_BASE_URL` to the existing Render backend URL in the
   preview project's environment settings.
3. Test the preview URL end-to-end (nav, homepage health badge, ECG AI
   migration notice link, contact form).
4. `cardiomirai.com` DNS is only repointed here after explicit approval —
   this step is not part of Phase 1.

## Rollback

Deleting the preview deployment has zero effect on production, since
production continues serving the unmodified `index.html` /
`cardiomirai.api:app` the whole time.
