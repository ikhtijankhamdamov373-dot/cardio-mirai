# Cardio MIRAI ACS — URGENT FIX: Real ECG Image Digitization Failure

**Research prototype. Not a medical device. Not clinically validated.**
Branch: `feature/acs-demo-mvp`, commit `a39b137`. Not merged. Not deployed. Not pushed.

---

## Root cause

`crop_layout_panels()` divided the **raw image's pixel dimensions** into 3 equal rows and 4 equal columns, and assumed the grid started at pixel (0,0). Any real photograph has margins around the printed grid, and the format you described has a **4th row** (the long Lead II rhythm strip) beneath the 3 diagnostic rows. Dividing the raw image into thirds therefore misaligned every single panel boundary — the crop for "row 2" would actually land partway between the real row 2 and row 3, etc.

**This is more dangerous than the error message you saw.** I reproduced it directly before fixing anything: on a realistic test image with a genuine 2.8mm elevation I'd drawn into V2/V3/V4, the old code reported **0.95–1.0 confidence on every lead** while measuring:
- V2/V3/V4 (should show ~2.8mm): measured **0.0mm**
- aVL (should show ~0mm): measured **0.52mm**
- aVR (should show ~0mm): measured **0.24mm**

High confidence, completely wrong numbers. Your actual upload apparently hit a version of this misalignment severe enough that too few columns cleared the confidence threshold at all, producing the clean "could not be digitized" error — but the silent-wrong-answer version is the one that should worry you more, and it's now fixed the same way.

## Exact fix

1. **New `detect_grid_bounding_box()`**: finds where the red/pink printed grid actually is in the image, using the same colour-difference technique already used for trace isolation (grid is reddish, everything else — margins, black machine text — is not). Panel geometry is now built from this detected box, not the raw image.
2. **New layout `"standard_3x4_rhythm_strip"`**: divides the *detected grid box* into 4 rows, uses only the first 3 as diagnostic panels, and explicitly never treats the 4th (rhythm strip) as a 13th panel. The original `"standard_3x4"` (no strip) is kept for that case. This is now the **default** layout, matching what you described as the common real-world format.
3. **Panel insets**: each panel is cropped with a small margin at the top-left to exclude the lead-label text and calibration-pulse regions from the extraction ROI — deterministic geometry, not OCR.
4. **Continuity-tracked trace extraction**: previously, a column's position was the average of *every* dark pixel found — if a stray fragment of label text leaked past the inset, it corrupted the average. Now each column's chosen position is the connected dark segment closest to the *previous* column's position, since the genuine trace is continuous and text fragments aren't.
5. **UI simplified** to UPLOAD ECG → ANALYZE ECG, as you asked — calibration and layout are applied automatically, with the 7-step detail moved under a collapsed "Show Analysis Details" disclosure.
6. **Honest calibration labeling**: renamed the always-`true` `calibration_confirmed_by_user` field to `calibration_source: "default" | "user_confirmed"`, so the response never claims OCR read the printed values unless it actually did (it doesn't, in this fix — the standard values are applied as a labeled default).

`cardiomirai/acs/core.py` (the guideline engine) was **not touched**. No new dependencies were needed.

## Test results

**New realistic fixture**: `tests/fixtures/realistic_ecg_3x4_rhythm.png` — genuinely includes a red grid, printed lead labels, calibration pulses, bottom machine/patient text, and a real 4th-row rhythm strip. This is not another simplified synthetic image; it specifically includes everything the earlier fixtures omitted.

**Backend: 116/116 passing** (112 prior + 4 new):
- `test_realistic_3x4_with_rhythm_strip_digitizes_correctly` — 12/12 leads extracted, correct measurements (not just "a result came back")
- `test_realistic_image_calibration_labeled_as_default_not_ocr`
- `test_rhythm_strip_row_is_not_treated_as_a_13th_diagnostic_panel`
- `test_default_layout_is_rhythm_strip_aware`

All 15 previous image-pipeline tests re-verified passing (one shared constant, `MAX_ASPECT_RATIO`, was widened from 3.2 to 4.0 since 3-row-only images are legitimately more elongated than 4-row ones — needed to keep the earlier, simpler fixtures passing under the new sanity check).

**Frontend: 23/23 passing** (1 test updated for the simplified upload flow).

**`next build`**: clean.

## Screenshot/result from the corrected pipeline

I can't produce an actual screenshot image (no headless browser in this sandbox, as established in earlier sessions), but here is the **exact live output**, from a real running `uvicorn` server, on the realistic fixture — not a mocked test, an actual HTTP call:

```
=== Realistic fixture through a real running server ===
analysis_source: uploaded_ecg_image
detected_leads: 12 of 12
calibration_source: default | 25.0 mm/s, 10.0 mm/mV
criteria_met: True | urgency: EMERGENCY | group: Anteroseptal | rule: ACS-CORE-002
contributing: [{'lead': 'V2', 'st_elevation_mm': 2.83}, {'lead': 'V3', 'st_elevation_mm': 2.83}, {'lead': 'V4', 'st_elevation_mm': 2.83}]
I: 0.0 | aVL: 0.0 | aVR: 0.0 (should all be ~0)
```

The injected ground truth was 2.8mm elevation in V2/V3/V4 and 0mm everywhere else. The corrected pipeline measured 2.83mm in exactly the right three leads and ~0.0mm everywhere else — matching the automated test suite's assertions exactly.

## What I still can't promise you

- This has now been tested against a **realistic synthetic fixture**, not a genuine photograph. Real photos will have JPEG compression, uneven lighting, and printer/scanner artifacts my drawn fixture doesn't have. The colour-based grid/ink separation and grid-pitch detection may need further tuning against an actual photographed image before you'd want to rely on it beyond a demo.
- If your actual uploaded image has a different rhythm-strip height ratio, additional margin structure, or a slightly different panel arrangement than what I modeled (equal quarters of the detected grid box), it may still misbehave — the fix targets the specific format you described, not a fully general layout engine.

## Not done

- No merge, deploy, or push — as instructed.
- Have not re-tested the PDF path against a realistic (labeled/rhythm-strip) PDF specifically — only the earlier simple PDF fixture.

---

Bundle with this fix is attached below.
