# Cardio MIRAI ACS — ECG Photo/PDF Digitization MVP: Final Report

**Research prototype. Not a medical device. Not clinically validated.**
Branch: `feature/acs-demo-mvp`, commit `c9b00f8`. Not merged. Not deployed. Not pushed.

---

## A. JPG/PNG working?

**YES.** Live-verified end-to-end this session: real pixel-based extraction, real ECG Core measurement, real ACS Core result, on both a positive (STEMI-criteria-met) and a differently-drawn image (safely refused / genuinely different result).

## B. PDF working?

**YES, for single-page PDFs.** Rendered via PyMuPDF at 300 DPI, then goes through the identical image pipeline. **Multi-page PDFs are explicitly refused** — no page classifier exists to identify which page (if any) contains the ECG, and the task explicitly required this rather than guessing.

## C. Supported ECG layouts

**Only `standard_3x4`** (I/aVR/V1/V4, II/aVL/V2/V5, III/aVF/V3/V6 — the near-universal printed layout). Any other layout value is explicitly refused with a clear error, never guessed at or approximated.

## D. Calibration method

**User-confirmed, not auto-inferred**, exactly as the task explicitly permitted for this MVP: the frontend requires an explicit "Confirm 25 mm/s, 10 mm/mV" click before digitization proceeds. The one thing genuinely auto-detected from the image is the **pixel-to-millimetre scale** (grid pitch), via periodicity analysis of the row intensity projection — a real signal-processing technique, not a guess. If that detection is unreliable (inconsistent peak spacing), the whole request is refused rather than using a bad estimate.

## E. Lead segmentation method

**Fixed proportional cropping** into a 3×4 grid based on the confirmed layout — not automatic label OCR or detection. This is the task's own explicitly stated acceptable simplification for today's MVP ("if automatic label detection is unreliable, implement a SAFE MANUAL LAYOUT CONFIRMATION step").

## F. Waveform extraction method

**Colour-based trace isolation** (a real bug fix made this session — grayscale alone couldn't separate the pink/red printed grid from black/blue ink; using the actual colour channels can, and is a standard real-world technique) followed by per-column centreline extraction, then conversion to millivolts using the confirmed gain and detected grid pitch, then resampling to 250 Hz to match what the existing ECG Core expects.

## G. Whether waveform is genuinely derived from uploaded pixels

**Yes — proven, not asserted.** `test_changing_the_image_changes_the_result` (and its manual verification before commit) shows two different uploaded images produce two different outcomes: an image with a drawn 2.8mm ST-elevation pattern in V2/V3/V4 correctly returns `criteria_met: true` / `EMERGENCY` / measured elevation of 2.87mm (within noise of the 2.8mm ground truth I drew), while a differently-drawn image without that pattern does not. The response also includes a downsampled genuine waveform preview (`preview_waveforms`) rendered as real sparklines in the UI — not placeholder data.

## H. Whether all 12 leads can be extracted

**Yes, when panel confidence is adequate.** Confirmed on the clean anterior-pattern test image: all 12 canonical lead names extracted with confidence 1.0 each. On a lower-quality or unrealistically uniform synthetic image, some or all leads are correctly excluded rather than measured unreliably — this is the intended fail-safe behavior, not a defect.

## I. Whether actual image-derived ST measurements reach the ACS engine

**Yes.** The endpoint calls the exact same `measure_array_to_lead_inputs()` → `evaluate_stemi_criteria()` path used by the real-WFDB pipeline — refactored this session specifically so all three ingestion sources (synthetic manual entry, real digital ECG, image-derived ECG) share one measurement/engine path rather than three separate algorithms.

## J. API endpoint

`POST /api/acs/analyze-ecg-image` (new, in `cardiomirai/acs/api.py`).

## K. Files changed

**New:**
- `cardiomirai/acs/image_ingestion.py`
- `tests/test_acs_image_ecg.py`
- `frontend/components/acs/ImageEcgResultDisplay.tsx`
- 8 synthetic test fixtures in `tests/fixtures/` (PNG/PDF)

**Modified:**
- `cardiomirai/acs/api.py` — added the new endpoint (additive)
- `cardiomirai/acs/ecg_ingestion.py` — refactored to extract the shared `measure_array_to_lead_inputs()` function (existing WFDB-path tests re-verified passing after this change)
- `requirements.txt` — added the two new dependencies (see L)
- `frontend/lib/acsApi.ts` — added `analyzeEcgImage()` and `ImageAnalysisResult` type
- `frontend/components/acs/EcgInputStep.tsx` — enabled the photo/PDF input with the full confirm → digitize → preview workflow
- `frontend/__tests__/acsTriageFlow.test.tsx` — 1 new test, 1 updated (photo input is now genuinely enabled)

**Untouched**: `cardiomirai/acs/core.py` (the guideline engine — zero changes), all AF/Atrial Health/PREVENT code, all model artifacts, the real-WFDB endpoint's behavior (re-verified by its 26 tests still passing).

## L. Dependencies added

`opencv-python-headless`, `pymupdf` — both added explicitly to `requirements.txt`. **Important finding**: `opencv-python-headless` was already present in this sandbox, but only as an incidental dependency of an unrelated tool (`camelot-py`) — it was **not** declared in `requirements.txt`. Had I used it without adding it there, the code would have worked in this sandbox by accident and then failed on the actual Render deployment, which installs strictly from `requirements.txt`. Caught and fixed this session.

## M. Tests passed/failed

**Backend: 112/112 passing** (97 prior + 15 new in `test_acs_image_ecg.py`, covering Task 15's full A–H scenario matrix plus the critical differential-result proof).
**Frontend: 23/23 passing** (22 prior + 1 new; 1 existing test updated since the photo input's disabled-state assumption is no longer true).
**`next build`**: clean, same 14 routes.
**Zero failures** in the final committed state.

## N. Known limitations

- **No rhythm-strip handling**: panels are cropped as if the image is exactly 3 rows tall; a 4th rhythm-strip row (common on many real printouts) would skew the row boundaries.
- **No perspective correction**: only mild rotation is tolerated (≤8°); anything beyond that is refused rather than corrected.
- **No automatic layout or lead-label detection**: only the single, user-confirmed "standard_3x4" layout is implemented.
- **Calibration relies on genuine grid-pitch detection succeeding**: if the printed grid isn't visible or is inconsistent, the whole upload is refused — there's no manual pixels-per-mm override for that specific case in today's MVP.
- **Only tested against synthetic fixtures**, not a genuine photographed or scanned real ECG. Real photographs will have JPEG compression artifacts, uneven lighting, and less uniform grid rendering than my drawn test images — the quality gate and grid-detection thresholds have not been tuned against real-world images and may need adjustment.
- **Mimic auto-detection** (LVH/LBBB/RBBB) depends on the same measurement quality as the WFDB path — likely less reliable on image-derived signals given the extra noise introduced by pixel-based extraction.

## O. Exact presentation workflow

1. `/acs` → Emergency Cardiology → Step 2 (ECG Input)
2. "Take / Upload ECG Photo" card → select a JPG/PNG/PDF file
3. Original image preview renders
4. Click "Confirm 25 mm/s, 10 mm/mV"
5. Click "Standard 3×4" (only enabled layout option)
6. Click "Digitize ECG" — the 7-step checklist marks off as processing completes
7. Digitization summary appears: leads extracted, calibration used, detected grid pitch, heart rate, QRS beats
8. "DIGITIZED / DETECTED TRACE PREVIEW" — real per-lead sparklines of the extracted waveform
9. ACS result: EMERGENCY ECG FINDING / STEMI criteria not detected, with the same explainability panel (measured value vs. threshold, contiguous group, rule ID) as the other two paths

## P. Exact claims that are scientifically safe to make

- "This prototype genuinely extracts a waveform from the pixels of an uploaded ECG image or single-page PDF, using real image-processing techniques (grid-pitch detection, colour-based trace isolation)."
- "The extracted measurements are fed into the same guideline-cited deterministic ACS engine used for real digital ECGs."
- "Changing the uploaded image changes the result — this has been tested and verified."
- "This is a research prototype; it is not clinically validated and has not been tested against real patient images."

## Q. Exact claims I MUST NOT make

- That this pipeline has been validated against real patient ECG photographs — it has only been tested against synthetic drawn test images.
- That automatic layout or lead-label detection exists — it does not; layout is always user-confirmed.
- That calibration is fully automatic — paper speed and gain are always user-confirmed; only the pixel-to-mm scale is detected, and even that refuses rather than guesses when unreliable.
- That this works for any ECG layout, rotation, or image quality — only one layout, mild rotation, and images clearing the quality gate are supported.
- That "ECG meets guideline STEMI criteria" from an image means a myocardial infarction has been diagnosed — the same STEMI-criteria-vs-clinical-diagnosis distinction from the earlier phases applies here without exception.

---

**No deployment, merge, or push has occurred.** This report and the bundle below are for independent review, exactly as instructed.
