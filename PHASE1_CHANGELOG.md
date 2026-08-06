# Cardio MIRAI — Phase 1 Change Log

Branch: `feature/nextjs-phase-1` (4 commits on top of `main`, not merged)

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

**Backend — `pytest tests/test_api.py -v`: 6/6 passed**
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

## Two findings surfaced during testing (not acted on — need your decision)

1. **`MODEL_DIR` mismatch**: `cardiomirai/api.py` looks for model artifacts in `<repo_root>/models/`, but they live at the repo root itself. This likely means `/api/analyze-wfdb` is returning a 424 "model not found" error in production right now, independent of anything in this branch. Tests above only pass because they monkeypatch `MODEL_DIR` for the test run — production code is untouched. Let me know if you'd like this fixed (either move the files or fix the path) as its own isolated commit.
2. **No upload size limit or zip-slip protection** on `/api/analyze-wfdb`. Confirmed by test. Per your instruction not to modify existing endpoints, I left this as-is and documented it rather than patching it silently. This would need to be its own approved subphase since it changes endpoint behavior (some currently-accepted uploads would start being rejected).

## Next steps (your call)

- Review the preview deployment, then decide on the two findings above.
- When ready, the ECG interface port is the next subphase (safeguard #6) — a full port of the existing upload/analyze UI into `frontend/app/ecg-ai/page.tsx`, replacing today's migration-notice placeholder.
