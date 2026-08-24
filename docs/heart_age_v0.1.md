# Cardio MIRAI Heart Age V0.1 -- Evidence-Based Cardiovascular Risk

## Scope

This is **not** the future "Cardio MIRAI AI Heart Age" (clinical + ECG +
echocardiography, multimodal). That remains schema-only
(`cardiomirai/heart_age/multimodal_schema.py`) with zero logic. This module
implements only the **Evidence-Based Cardiovascular Risk Age**, based on the
AHA PREVENT base equations, as a self-contained, independently-callable
component that does not modify or depend on ECG Core, Current AF Evidence,
lead gating, or the legacy PTB-XL atrial model in any way.

## 1. Coefficient provenance

**Primary source**: Khan SS, Matsushita K, Sang Y, et al. "Development and
Validation of the American Heart Association's PREVENT Equations."
*Circulation*. 2024;149:430-449. doi:10.1161/CIRCULATIONAHA.123.067626.

This environment could not access the paywalled full text or supplement as
machine-readable table content. Stated plainly rather than worked around.

**Verification actually performed** (in order of what was really done, not
an idealized description):

1. Located and downloaded the full source of two independently-authored,
   separately-maintained, MIT-licensed open-source R packages that both
   implement these equations, citing the same DOI:
   - `PooledCohort` (Byron Jaeger, Wake Forest University School of
     Medicine) -- https://github.com/bcjaeger/PooledCohort
   - `preventr` (Martin Mayer) -- https://github.com/martingmayer/preventr
2. Extracted both packages' actual compiled coefficient data (PooledCohort's
   committed `data-raw/coefs_prevent.xlsx`; preventr's compiled
   `R/sysdata.rda`, read directly via R) and diffed them programmatically.
   Every coefficient (23 rows x 10 outcome/sex columns x 2 time horizons =
   460 values) matched to 7 decimal places between the two independently-
   written packages.
3. Generated `_prevent_coefficients.py` programmatically from
   PooledCohort's spreadsheet (script: see the export logic that produced
   this file, run once and not re-run automatically -- if the coefficients
   ever need to change, regenerate from source rather than hand-edit).
4. Installed R (already present in this environment) and PooledCohort's
   actual source, stubbing only its `glue`-dependent argument-validation
   layer (not the math -- `glue` could not be installed offline; CRAN
   unreachable, apt blocked by unrelated broken packages in this sandbox).
   Ran `predict_10yr_cvd_risk` and `predict_30yr_cvd_risk` LIVE on 10
   diverse synthetic patients (both sexes, ages 30s/50s/70s, normotensive/
   hypertensive/smoker/diabetic/reduced-eGFR/treated combinations).
5. Ran the same 10 patients through this Python implementation.
   **Result: maximum absolute difference across all 20 values (10 patients
   x 2 horizons) was 4.91e-11** -- machine precision, not approximate
   agreement. These 10 patients and their R-executed reference values are
   locked into `tests/heart_age/test_prevent_equations.py` as a permanent
   regression oracle.
6. `preventr`'s own R function was NOT independently re-executed (its
   dependency, `dplyr`, could not be installed offline here) -- stated
   plainly. Given step 2's exact coefficient-level match, it would compute
   the same result by transitivity, but that is not the same as a second
   independent live execution, and this document does not claim it is.

**Only the Total CVD outcome's coefficients (women_cvd / men_cvd columns)
are included** in `_prevent_coefficients.py`. The BMI coefficients for this
outcome are exactly zero in the official table (BMI only enters the
HF-specific equation) -- rather than including them and relying on the
zero to prevent misuse, the Python implementation's function signature does
not accept a BMI parameter at all for Total CVD risk, structurally
preventing any future accidental cross-wire with HF-specific terms.

## 2. Complete implemented equation

Linear predictor (age-scale, sex-specific):

```
lp = coef_age * age_per_10
   + coef_age_sq * age_per_10^2                          [== 0 for the 10-year model]
   + coef_non_hdl * (non_hdl_mmol - 3.5)
   + coef_hdl * ((hdl_mmol - 1.3) / 0.3)
   + coef_sbp_low * ((min(sbp,110) - 110) / 20)
   + coef_sbp_high * ((max(sbp,110) - 130) / 20)
   + coef_diabetes * diabetes + coef_smoking * smoking
   + coef_egfr_low * ((min(egfr,60) - 60) / -15)
   + coef_egfr_high * ((max(egfr,60) - 90) / -15)
   + coef_bp_meds * bp_meds + coef_statin * statin
   + coef_treated_sbp * (sbp_high * bp_meds)
   + coef_treated_non_hdl * (non_hdl_transformed * statin)
   + [age x non_hdl, age x hdl, age x sbp_high, age x diabetes, age x smoking, age x egfr_low interaction terms]
   + const

risk = exp(lp) / (1 + exp(lp))
```

where `age_per_10 = (age_years - 55) / 10`, `non_hdl_mmol = (total_chol_mgdl
- hdl_chol_mgdl) * 0.02586`. The final logistic-form risk equation (rather
than a raw Cox baseline-survival formulation) is confirmed directly from
PooledCohort's own computation code, and matches the original paper's own
description of this as a deliberate simplification (reported R^2>=0.99
against the full model).

## 3. Risk Age methodology

Source: the Khan Lab's own official Risk Age calculator methodology page
(https://nwkhanlab.shinyapps.io/riskage/), citing Krishnan, Huang, Perak,
Coresh, Ndumele, Greenland, Lloyd-Jones, Khan. "PREVENT Risk Age Equations
and Population Distribution in US Adults." *JAMA Cardiology*. 2025.
doi:10.1001/jamacardio.2025.2427 -- and the Framingham risk-age precedents
it explicitly follows (D'Agostino et al., PMID 18212285; Marma &
Lloyd-Jones, PMID 19620502).

Reference/optimal profile (verbatim from the source): non-HDL-C 120 mg/dL,
HDL-C 50 mg/dL, SBP 110 mmHg, eGFR 90, no diabetes, non-smoker, no
antihypertensive therapy, no statin therapy.

Method: substitute this fixed profile into the base 10-year model. Every
non-age term collapses to a constant (diabetes/smoking/eGFR terms vanish
because the reference values sit exactly at the equation's own centering
points). Because the base 10-year model's age-squared coefficient is
exactly zero (asserted explicitly in code, not silently assumed), what
remains is `target_logit = slope * age_per_10 + intercept` -- a **linear**
equation in age, solved in closed form (not numerical root-finding).

**Boundary convention**: Risk Age is documented as valid only for the base
equations, whose official range is 30-79. This module applies that same
range to Risk Age's output (`<30` / `>79` labels) as a reasoned extension
of the source's own stated scope -- this is this implementation's own
documented reasoning, not a separately-published Risk-Age-specific
boundary number, and is called out as such rather than presented as a
directly-cited fact.

**Genuinely verified published example** (found via live search of the
Khan Lab's own page, not assumed or remembered): *"a 60 year-old woman with
... total cholesterol of 200 mg/dL, HDL cholesterol of 60 mg/dL, blood
pressure of 140 mmHg, and estimated GFR 90 ... would have a risk age of 64
years based on her absolute 10-year CVD risk of 5.3%."* This implementation
reproduces 5.33% (rounds to published 5.3%) and risk age 63.7 (rounds to
published 64) -- locked in as
`test_published_worked_example_khan_lab_risk_age_calculator`.

**A note on process integrity**: an earlier, discarded commit on this
branch had cited this exact same example without any record of it having
been genuinely verified in this environment. That commit was discarded
entirely (not cherry-picked) rather than trusted, and the example above was
independently re-found and re-verified from scratch before being used here.

## 4. Supported age ranges (NOT the same for both horizons)

| Model | Supported range | Behavior outside range |
|---|---|---|
| 10-year Total CVD risk | 30-79 | `risk_10yr_percent: null`, reason string returned |
| 30-year Total CVD risk | 30-59 | `risk_30yr_percent: null`, reason string returned |
| Risk Age | Derived from 10-year risk; `<30`/`>79` boundary labels | `risk_age_years: null`, `boundary_label` set |

A patient aged 65 gets a 10-year risk but explicitly NOT a 30-year risk --
tested directly (`test_30yr_unavailable_above_59_even_though_10yr_is_fine`).

## 5. Unit handling

`total_chol_mgdl_to_mmoll` / `hdl_mgdl_to_mmoll`: multiply by 0.02586 (the
standard cholesterol mg/dL<->mmol/L conversion factor, molar mass ~386.65
g/mol) -- confirmed as the exact constant PooledCohort's own code uses, not
a textbook value substituted without checking. Tested directly against a
manual-subtraction equivalence check and a plausible-range sanity check.

## 6. Isolation from existing systems

`cardiomirai/api.py` changed by exactly 3 lines (one import, one
`include_router` call). No ECG/AF/lead-validation/legacy-model function was
read, modified, or imported by anything in `cardiomirai/heart_age/`. PTB-XL
model artifacts confirmed sha256-identical to the pre-existing baseline
(same 5 hashes recorded throughout this entire engagement).

## 7. Known limitations

- Only the base equations are implemented (no optional HbA1c/UACR/SDI
  add-ons), per explicit V0.1 scope.
- `preventr` was not independently re-executed live (dependency
  unavailable offline) -- coefficient-level identity with PooledCohort is
  the actual evidence, stated as such.
- The Risk Age boundary convention (applying the base equations' 30-79
  range) is this implementation's own reasoned choice, not a directly-cited
  Risk-Age-specific number from the source.
- Frontend verified via Node.js DOM/fetch mocking, not a real browser.
