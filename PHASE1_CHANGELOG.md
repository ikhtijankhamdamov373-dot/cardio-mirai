# Cardio MIRAI — Phase 1 Change Log

Branch: `feature/nextjs-phase-1` (7 commits on top of `main`, not merged, not deployed publicly)

## Update: Preview verification round — no public deployment yet

You asked for a preview deployment with screenshots, Lighthouse, and
mobile/desktop views. Two things I could not do from this sandbox, stated
plainly rather than faked:

1. **No public preview URL.** I have no deployment credentials of my own
   (no Vercel/Render API access). A Vercel and a Render connector exist in
   your organization's catalog but aren't connected to your account yet —
   connect one and I can likely trigger a real deployment directly, or use
   the manual steps below.
2. **No screenshots or Lighthouse score.** This sandbox's network is
   restricted to package registries; it cannot reach Chrome's binary
   download servers, so no headless browser can be installed here to render
   pages or run Lighthouse. Both become possible once a real URL exists.

### What I verified instead — both servers live in this sandbox

Backend (`uvicorn`, port 8000) and frontend (`next start`, production
build, port 3000, `NEXT_PUBLIC_API_BASE_URL` pointed at the local backend)
were both actually run, not just built:

```
Backend direct:              GET /api/health          -> {"ok": true}
Frontend server-side proxy:  GET /api/health           -> {"ok": true}   (frontend -> backend chain confirmed)

Every page, HTTP status:
/              -> 200
/about         -> 200
/contact       -> 200
/ecg-ai        -> 200
/calculators   -> 200
/knowledge     -> 200
/research      -> 200
/ai-assistant  -> 200
```

`npx next build` also passed clean (TypeScript check + static generation,
same as the prior round).

### Get a real preview URL (manual, ~2 minutes) — DNS untouched

```bash
git clone https://github.com/ikhtijankhamdamov373-dot/cardio-mirai.git
cd cardio-mirai
git remote add phase1-bundle /path/to/cardio-mirai-phase1.bundle
git fetch phase1-bundle feature/nextjs-phase-1:feature/nextjs-phase-1
git checkout feature/nextjs-phase-1
cd frontend
npx vercel --cwd . # or: vercel deploy (requires a free Vercel account, first run prompts login)
```

When prompted, set `NEXT_PUBLIC_API_BASE_URL` to your Render backend URL
in the Vercel project's environment settings. This creates a project-scoped
preview URL (e.g. `cardio-mirai-frontend-xxxxx.vercel.app`) — `cardiomirai.com`
DNS is untouched by this.

Once that URL exists, either:
- Run `npx lighthouse <url> --view` yourself for the score, and your
  browser's screenshot/device-toolbar for mobile/desktop views, or
- Share the URL here — if you have Claude for Chrome connected, I can
  navigate it directly and capture real screenshots and a Lighthouse-style
  audit.

### Folder structure (frontend, verified against the actual filesystem)

```
frontend/
├── app/
│   ├── about/page.tsx
│   ├── ai-assistant/page.tsx
│   ├── api/health/route.ts
│   ├── calculators/page.tsx
│   ├── contact/page.tsx
│   ├── ecg-ai/page.tsx
│   ├── globals.css
│   ├── knowledge/page.tsx
│   ├── layout.tsx
│   ├── page.tsx
│   └── research/page.tsx
├── components/
│   ├── layout/ (BackendStatus, DeveloperCard, Footer, Navbar)
│   └── ui/ (Badge, Button, Card, ComingSoon, Disclaimer, PageStatus)
├── lib/api.ts
├── __tests__/ (3 files, 12 tests)
├── jest.config.js, jest.setup.js
├── next.config.js, tailwind.config.ts, tsconfig.json, postcss.config.js
├── package.json, package-lock.json
└── README.md
```

(One note: an earlier setup command left a stray, empty, never-tracked
directory named literally `frontend/{app` due to a shell brace-expansion
quirk in this sandbox. It was never committed and has been deleted.)

### Still true from the last round (unaffected by this verification pass)

- 17/17 backend tests passing, 12/12 frontend tests passing
- `main` untouched — confirmed via `git diff main..feature/nextjs-phase-1 --stat` against `render.yaml`, `requirements.txt`, and all model artifacts (empty diff)
- No merge to `main`, no production DNS change, no public deployment

---

## Update: Backend stabilization (this round)

Per your instructions, backend fixes were completed before any preview
deployment. Preview deployment has **not** happened — nothing beyond this
branch/bundle has changed.

### Priority 1 — Model path resolution: FIXED, verified live

`MODEL_DIR` previously pointed at `<project_root>/models/`, which doesn't
exist — artifacts ship at the project root. This meant `/api/analyze-wfdb`
was returning `424` ("model files not found") in production.

**Fix:** `_resolve_model_dir()` in `cardiomirai/api.py` checks, in order:
1. `CARDIO_MIRAI_MODEL_DIR` env override (optional)
2. `<project_root>/models/` (the documented location)
3. `<project_root>` (where the files actually are today)

...and uses whichever directory actually has all required artifact files.
**No files were moved.** Verified two ways:
- 3 new unit tests (`test_model_dir_resolves_without_moving_artifacts`,
  `test_model_dir_prefers_documented_models_subfolder`,
  `test_model_dir_respects_env_override`) — all passing.
- Live manual check against a real running `uvicorn` server: `/api/health`
  returns `{"ok": true}`, `/api/analyze-wfdb` returns a real result
  (`record: valid_record, af_detection_score: 69.0`) from an uploaded
  synthetic WFDB record.

### Priority 2 — Upload security hardening: IMPLEMENTED, verified live

All added to `cardiomirai/api.py`, same endpoint, same request/response
shape, only more specific error messages for previously-vague failures:

| Control | Implementation |
| --- | --- |
| Upload size limits | Per-file (20 MB) + per-request total (50 MB), both env-configurable (`CARDIO_MIRAI_MAX_FILE_SIZE_BYTES`, `CARDIO_MIRAI_MAX_TOTAL_UPLOAD_BYTES`), enforced while streaming — no unbounded reads |
| ZIP-slip protection | Every archive member's resolved path is verified to stay inside the extraction sandbox (`_resolve_within`) before being written; unsafe members are skipped and logged, never extracted |
| Archive validation | Corrupt/invalid ZIPs → clear `400`, not an unhandled exception; member-count cap (500) and uncompressed-size cap (100 MB) guard against zip bombs |
| Filename sanitization | `_safe_name()` strips null bytes, path separators, and rejects `.`/`..`/empty names — applied to top-level uploads *and* every ZIP member |
| Supported file checks | Only `.hea`/`.dat`/`.zip` accepted; anything else rejected **before** being written to disk |
| Safe temp directories | Confirmed existing `TemporaryDirectory()` already creates a process-private (`0o700`) dir, always removed on exit — no uploaded file persists beyond the request |
| No internal error exposure | Exceptions logged in full server-side only; client never sees temp-directory paths or raw exception text |
| Restricted CORS | `allow_origins=["*"]` → explicit allowlist (`cardiomirai.com`, `www.cardiomirai.com`, local dev origins), configurable via `CARDIO_MIRAI_CORS_ORIGINS` |

**Verified live:**
```
=== unsupported extension (.exe) ===
HTTP 400 — {"detail":"Unsupported file type '.exe'. Allowed types: .dat, .hea, .zip."}

=== CORS: disallowed origin (evil-attacker.example) ===
HTTP 200 — no Access-Control-Allow-Origin header returned

=== CORS: allowed origin (cardiomirai.com) ===
HTTP 200 — access-control-allow-origin: https://cardiomirai.com
```

### Test results — this round

**`pytest tests/test_api.py -v`: 17/17 passed**
- 3 model-path resolution tests (new)
- 6 original endpoint tests (health, valid pair, incomplete record, ZIP, health-of-model-path)
- 8 new security tests: oversized file (413), oversized total (413), unsupported extension rejected pre-save, filename sanitization (path traversal + null byte), malicious ZIP with traversal member neutralized, invalid ZIP → clear 400, too-many-members ZIP rejected, error messages don't leak temp paths

**Frontend — unaffected:** `npm test` still 17/17 → 12/12 passing (re-run after backend changes to confirm no regression); `npm run build` unaffected (frontend wasn't touched this round).

### Security summary

- **Before this round:** wildcard CORS, no size limits, no zip-slip protection, no archive validation, raw exception text (including temp paths) returned to clients, model artifacts effectively unreachable in production.
- **After this round:** explicit CORS allowlist, enforced per-file/per-request size caps, zip-slip-safe extraction with member/size caps, corrupt-archive handling, sanitized filenames throughout, generic client-facing error messages with full detail logged server-side only, and a working model-inference path.
- **Still out of scope / not touched:** authentication/authorization (endpoint remains open, as it was before — no instruction to add auth), rate limiting, virus/malware content scanning of uploaded files (only extension + structural validation), HTTPS/TLS (handled by Render, not application code).

### Updated architecture note

No structural change — `cardiomirai/api.py` remains the single backend
module. The only new pieces are the constants block, `_resolve_model_dir`,
`_resolve_within`, `UploadValidationError`, and the hardened bodies of
`_safe_name`, `_save_uploads`, `_extract_zip_files`, and `analyze_wfdb`.
`frontend/` is unaffected by this round of changes.

### Endpoint verification

| Endpoint | Status |
| --- | --- |
| `GET /api/health` | ✅ `{"ok": true}` |
| `POST /api/analyze-wfdb` (valid `.hea`/`.dat`) | ✅ real result with `af_detection_score` |
| `POST /api/analyze-wfdb` (valid `.zip`) | ✅ |
| `POST /api/analyze-wfdb` (incomplete record) | ✅ `400` |
| `POST /api/analyze-wfdb` (unsupported extension) | ✅ `400`, rejected pre-save |
| `POST /api/analyze-wfdb` (oversized file/request) | ✅ `413` |
| `POST /api/analyze-wfdb` (malicious ZIP, path traversal) | ✅ neutralized, no file written outside sandbox |
| `POST /api/analyze-wfdb` (corrupt ZIP) | ✅ `400`, no crash |

### Deployment status

**Not deployed.** Per your instruction, no preview deployment has been
created. Everything above was verified locally in this sandbox, against a
real running `uvicorn` process, and via the pytest suite. `main` remains
completely untouched — confirmed with `git diff main..feature/nextjs-phase-1 --stat`
against `render.yaml`, `requirements.txt`, and all model artifact files:
empty diff.

---

## Original Phase 1 record (scaffold + legacy URL fix)

## How to apply this to your actual GitHub repo

I don't have push credentials to `ikhtijankhamdamov373-dot/cardio-mirai`,
so the work is packaged as a git bundle containing both `main` and
`feature/nextjs-phase-1` with full commit history.

```bash
# from a fresh clone of your repo
git clone https://github.com/ikhtijankhamdamov373-dot/cardio-mirai.git
cd cardio-mirai
git remote add phase1-bundle /path/to/cardio-mirai-phase1.bundle
git fetch phase1-bundle feature/nextjs-phase-1:feature/nextjs-phase-1
git checkout feature/nextjs-phase-1
git push origin feature/nextjs-phase-1   # pushes the branch, not main
```

`main` is not touched by this bundle — only the new branch is pushed.

## Commits (in order)

1. **`test(backend): add API test suite for existing FastAPI endpoints`**
   Additive only. 6 tests against the real `cardiomirai/api.py`, unmodified.
2. **`fix(legacy): use relative path for WFDB backend URL`**
   One line in `index.html`: `http://127.0.0.1:8000/api/analyze-wfdb` → `/api/analyze-wfdb`.
3. **`feat(frontend): Phase 1 Next.js/Tailwind scaffold`**
   Everything under `frontend/`.
4. **`docs(frontend): add README`**

## Files changed (45 total, all additive except the 1-line fix)

- **Modified:** `index.html` (1 line — see commit 2)
- **Created:** `frontend/**` (Next.js app), `tests/**` (backend tests), `requirements-dev.txt`, `.gitignore` additions
- **Untouched, verified with `git diff --stat`:** `cardiomirai/` (all backend logic and endpoints), `render.yaml`, `requirements.txt`, all `.pkl`/`model_metadata.json`/`feature_columns.json` model artifacts

## Local run commands

Backend (unchanged):
```bash
pip install -r requirements.txt
uvicorn cardiomirai.api:app --reload --host 127.0.0.1 --port 8000
```

Backend tests (new):
```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Frontend (new):
```bash
cd frontend
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm install
npm run dev                  # http://localhost:3000
```

## Environment variables (frontend/.env.example, no secrets committed)

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Backend origin, used server-side by rewrites + health route |
| `NEXT_PUBLIC_LEGACY_SITE_URL` | Legacy site URL, linked from the ECG AI migration notice |

## Test results (run in this environment)

**Backend — `pytest tests/test_api.py -v`: 6/6 passed (this section reflects the original Phase 1 scaffold; see updated 17/17 results above)**
- `test_health_endpoint_returns_ok`
- `test_valid_wfdb_hea_dat_pair_is_analyzed`
- `test_hea_without_matching_dat_is_rejected`
- `test_zip_containing_valid_record_is_analyzed`
- `test_unsupported_single_file_is_rejected`
- `test_current_endpoint_has_no_enforced_size_limit` (documents a gap, doesn't fix it)

**Frontend — `npm test`: 12/12 passed** (homepage rendering, nav links + responsive toggle, API client timeout/error handling)

**Frontend — `npm run build`: passed** (TypeScript check + static generation, 12 routes, no errors)

## Preview deployment instructions

1. Push `feature/nextjs-phase-1` to GitHub (see above).
2. Create a **new, separate** Vercel project (or second Render service) pointed at the `frontend/` subdirectory of that branch.
3. Set `NEXT_PUBLIC_API_BASE_URL` in that project's env settings to your existing Render backend URL (the same one `render.yaml` already deploys).
4. Test the preview URL: homepage health badge, all 8 nav links, ECG AI migration notice → link to `cardiomirai.com`, contact form.
5. `cardiomirai.com` DNS is **not** touched by any of this — repointing it is a separate step requiring your explicit approval.

## Explicit confirmation: production is unchanged

- `git diff main..feature/nextjs-phase-1 --stat -- cardiomirai/ render.yaml requirements.txt *.pkl *.json` → **empty diff**, verified above.
- The only change to a file the live Render service reads is the 1-line URL fix in `index.html`, isolated in its own commit, not yet merged to `main`.
- `main` has not been touched; nothing has been pushed; no DNS or deployment changed.

## Two findings surfaced during initial testing — now resolved (see update above)

1. ~~**`MODEL_DIR` mismatch**~~ — **Fixed**, see "Priority 1" above.
2. ~~**No upload size limit or zip-slip protection**~~ — **Fixed**, see "Priority 2" above.

## Next steps (your call)

- Review this round's changes and test output; merge `feature/nextjs-phase-1` into `main` when satisfied.
- Preview deployment (frontend on a separate Vercel/Render project, `cardiomirai.com` DNS untouched) is ready whenever you give the go-ahead.
- ECG interface port remains a separate subphase, not started, per your instruction to hold it until the backend is verified — which it now is.
