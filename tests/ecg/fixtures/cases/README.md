# Cardio MIRAI ECG validation suite

Every case here is a real (or realistic) clinical scenario that a past version
of the engine got right (or was fixed to get right). The intent, per the
ECG Core V1.1 review: **every future engine change must keep every existing
case passing**, so a fix to one rhythm type can't silently regress another
without being caught immediately -- not "gain one capability while silently
losing another."

## Adding a new case

1. Create `fixtures/cases/<case_id>/` (e.g. `fixtures/cases/patient_001/`,
   `fixtures/cases/true_af_01/`, `fixtures/cases/flutter_01/`,
   `fixtures/cases/pac_pvc_01/`, `fixtures/cases/bbb_01/`,
   `fixtures/cases/av_block_01/`, `fixtures/cases/noisy_01/`).
2. Add the WFDB record: `<record>.hea` + `<record>.dat`, and `<record>.atr`
   if real manual annotations exist (strongly preferred when available --
   it upgrades the case from "plausible" to "objectively verified against
   ground truth for R-peaks/T-waves").
3. Add a `case.json` manifest (see `patient_002/case.json` for a fully
   worked example) with:
   - `record`, `demographics` -- what to POST to `/api/analyze-wfdb`.
   - `clinical_reference` -- what a human reviewer found, for context.
   - `expectations` -- QUALITATIVE targets (ranges/categories), not exact
     hardcoded numbers. This mirrors the explicit instruction from the
     Patient 2 investigation: the engine should never be tuned to hit one
     precise number on one recording.
   - `annotation_validation` (optional) -- only meaningful if a real `.atr`
     file is present; checks R-peak sensitivity and T-wave-false-positive
     rate against real ground truth, not just plausibility.
4. That's it -- `test_regression_suite.py` auto-discovers every
   `case.json` under `fixtures/cases/`. No new Python code needed unless
   the case needs a new `expectations` key (extend `_LEAD_GATE_CHECKS` /
   the checks in `test_case_qualitative_expectations` if so).

## Licensing / data handling note

Only add real patient or public-database recordings here if you have the
right to redistribute them inside this repository (e.g. PhysioNet's
license terms for the specific database, or a de-identified/consented
recording you control). If a case can't be committed for licensing
reasons, keep the `case.json` manifest and expectations documented, but
source the actual waveform from an external, access-controlled location
in CI rather than committing it here.
