# Cardio MIRAI ACS — Demo MVP Deliverable Report

**Research prototype. Not a medical device. Not for clinical use.**

## Branch name

`feature/acs-demo-mvp`, branched from `feature/nextjs-phase-1` (1 commit ahead). Not merged. Bundle includes this branch plus `feature/nextjs-phase-1` and `origin/main` for full history.

## Files created / modified

**Created (18 files):**
- `cardiomirai/acs/__init__.py`, `cardiomirai/acs/core.py`, `cardiomirai/acs/api.py` — backend
- `tests/test_acs_core.py` — backend tests
- `frontend/app/acs/page.tsx`, `frontend/app/acs/demo/page.tsx` — routes
- `frontend/components/acs/AcsTriageFlow.tsx`, `PatientForm.tsx`, `EcgInputStep.tsx`, `QualityGate.tsx`, `ResultDisplay.tsx`, `PlatformArchitecture.tsx`, `RuralWorkflowVisual.tsx`, `ResearchPatternsSection.tsx` — components
- `frontend/lib/acsApi.ts` — API client
- `frontend/__tests__/acsTriageFlow.test.tsx` — frontend tests

**Modified (3 files, minimal/additive diffs only):**
- `cardiomirai/api.py` — **10 lines added, 0 removed**: mounts the ACS router
- `frontend/components/layout/Navbar.tsx` — 1 line added: "Emergency Cardiology" nav item
- `frontend/__tests__/navbar.test.tsx` — updated expected-links list to match

**Untouched**: `cardiomirai/wfdb_loader.py`, model artifacts, `render.yaml`, `requirements.txt`, all AF/Atrial Health code, existing `/api/analyze-wfdb` and `/api/health` endpoints.

## Architecture summary

Backend: a new, isolated `cardiomirai/acs` package containing pure-function deterministic rule logic (`core.py`, no ML, no I/O) and a FastAPI router (`api.py`) mounted at `/api/acs/*`. The only change to the existing `cardiomirai/api.py` is a 10-line router-include block — verified by diff.

Frontend: a new `/acs` route tree using the existing design system (Card, Badge, Button, Disclaimer components — nothing new invented). State lives in one orchestrating client component (`AcsTriageFlow`), calling the backend through the same same-origin proxy pattern (`/api/backend/acs/*`) already established in Phase 1.

## ACS Core rules actually implemented

| Rule | What it does | Test coverage |
|---|---|---|
| ACS-CORE-001 | General-lead STEMI threshold (≥1mm, ≥2 contiguous leads, excludes LVH/LBBB) | Exact boundary + just-below tests |
| ACS-CORE-002 | Age/sex-specific V2–V3 thresholds | All 3 age/sex branches at exact boundary + just-below; missing age/sex raises an error rather than defaulting |
| ACS-CORE-003 | Mimic/clinical-correlation safeguard | Each of the 8 named mimics individually tested; asymptomatic+mimic suppresses the raw threshold result |
| ACS-CORE-005 | FMC-to-ECG 10-minute timing | Exact boundary, 1-second-over, missing-timestamp-raises |
| ACS-CORE-008 | Serial ECG indication | Both care settings tested separately; asserts their LOE values differ (C-LD vs. B-NR) rather than being merged |

## Rules deliberately NOT implemented (and why)

- **ACS-CORE-004** (ESC's symptomatic-LBBB-equivalent rule) — out of tonight's explicit scope; only 001/002/003/005/008 were requested
- **ACS-CORE-006 / ACS-CORE-007** (reperfusion/transfer timing) — explicitly excluded per your instruction; regional pathway not validated
- **ACS-CORE-010** (ESC 0h/1h and 0h/2h algorithms) — explicitly excluded; assay-specific numeric cutoffs remain unresolved in Matrix v1.2. The NSTE-ACS card shows only the general ACC/AHA 1–2h window, clearly source-labeled

## Test results

**Backend**: `pytest tests/ -q` → **50/50 passed** (17 pre-existing + 33 new). Includes a runtime-output safety scan across 4 representative scenarios (STEMI-positive, nondiagnostic, mimic-present, poor-quality), checking every returned string value against all 5 prohibited phrases — not just a source-code grep.

**Frontend**: `npx jest --ci` → **18/18 passed** (12 pre-existing + 6 new). Includes a full rendered-DOM text scan for the same 5 phrases after a nondiagnostic result.

**Build**: `next build` → clean, 14 routes, TypeScript checks pass, includes `/acs` and `/acs/demo`.

**Existing functionality**: confirmed unbroken by a dedicated test (`test_existing_wfdb_endpoint_still_works_after_acs_mount`) plus the full pre-existing 17-test AF/WFDB suite passing unmodified.

## Demo URL / route

`/acs/demo` (also reachable via `/acs` directly, or Home → Emergency Cardiology in the nav).

## 60–90 second live-demo sequence

1. Open Cardio MIRAI → click **Emergency Cardiology** in the nav
2. Land on **Cardio MIRAI ACS** — point out the RESEARCH PROTOTYPE badge and the three-module architecture (Preventive Cardiology / Atrial Intelligence / Emergency Cardiology)
3. Click **DEMO CASE** — synthetic-patient banner appears, auto-advances to Step 2 (ECG Input) with the two input pathways visible (digital upload, photo — both honestly labeled)
4. Click **Analyze**
5. **ECG Quality** card shows all 4 checks passing
6. Result: **EMERGENCY ECG FINDING / ECG meets guideline STEMI criteria**, with V2/V3/V4 measurements and contiguous-lead group shown
7. Scroll to **Why was this flagged?** — measured value vs. required threshold, per lead, with the guideline source line
8. Scroll past the NSTE-ACS card and collapsed Research Patterns section to the **Rural Uzbekistan Workflow** visual to close

## Known limitations (tell the audience, or fix before wider use)

1. **Contiguous-lead grouping is a simplified fixed lookup table**, not a validated anatomical-contiguity engine — sufficient for the demo fixture, not for arbitrary real ECGs with unusual lead configurations.
2. **No real ECG digitization exists yet** — both the digital-upload and photo pathways are honestly labeled as prototype/unavailable; only the manual-entry path and the Demo Case actually exercise the deterministic engine, by design, so nothing is fabricated.
3. **ACS-CORE-004 (ESC's LBBB rule) is not implemented** — only the ACC/AHA asymptomatic-LBBB rule is live. If someone asks about the symptomatic-LBBB case, it's in the spec but not in tonight's build.
4. **The manual-entry demo panel is a debugging/interactivity aid**, not a designed clinical input UI — fine for Q&A after the main demo, but would need real design work before any pilot use.
5. **Backend must be reachable** for `/acs` to produce a result — if deploying the frontend separately (per the earlier Vercel plan), confirm `NEXT_PUBLIC_API_BASE_URL` points at a live backend with this branch's code before presenting live; otherwise, demo from a local `npm run dev` + local `uvicorn` pair to remove that dependency.

## Issues to fix before any deployment beyond tonight's demo

1. Two of three published corrections to the 2025 ACC/AHA guideline still have unconfirmed content (Matrix v1.2, Part 1) — should be resolved before this becomes anything more than a demo.
2. The contiguous-lead lookup table (limitation #1 above) needs a real anatomical-contiguity implementation before any non-synthetic ECG is run through it.
3. No authentication/authorization on `/api/acs/*` — same posture as the existing `/api/analyze-wfdb`, consistent but worth deciding on deliberately before real patient data ever touches this.
