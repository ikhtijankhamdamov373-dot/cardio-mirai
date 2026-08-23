"""PREVENT base-model coefficients (Total CVD outcome only), 10-year and 30-year.

GENERATED PROGRAMMATICALLY -- do not hand-edit. Regenerate from the source
spreadsheet if these ever need to change; hand-editing risks exactly the kind
of transcription error this file exists to eliminate.

Provenance (see docs/heart_age_v0.1.md for the full account):
  - Primary source: Khan et al., "Development and Validation of the American
    Heart Association's PREVENT Equations," Circulation. 2024;149:430-449,
    doi:10.1161/CIRCULATIONAHA.123.067626. This environment could not access
    the paywalled full text/supplement as machine-readable content -- stated
    plainly, not overstated.
  - Cross-validated via two independently-authored, separately-maintained
    open-source implementations of the same official coefficient tables:
      * PooledCohort (Byron Jaeger, Wake Forest University School of
        Medicine) -- https://github.com/bcjaeger/PooledCohort
      * preventr (Martin Mayer) -- https://github.com/martingmayer/preventr
    Every coefficient below was confirmed IDENTICAL to 7 decimal places
    between the two packages' own source data (PooledCohort's committed
    data-raw/coefs_prevent.xlsx and preventr's compiled sysdata.rda, the
    latter read directly via R). This file's numeric values were extracted
    programmatically from PooledCohort's spreadsheet -- see the export
    script referenced in docs/heart_age_v0.1.md -- not hand-typed.
  - Only the Total CVD outcome columns (women_cvd / men_cvd) are included.
    ASCVD/HF/CHD/stroke-specific columns are deliberately excluded from this
    file: the HF outcome carries nonzero BMI terms that do not apply to the
    Total CVD equation, and omitting the other columns entirely (rather than
    including them with a "do not use" comment) removes any chance of a
    future accidental cross-wire.
"""

from __future__ import annotations

BASE_10YR_CVD_COEFS: dict[str, dict[str, float]] = {
    "coef_age_per_10_years": {"female": 0.7939329, "male": 0.7688528},
    "coef_age_per_10_years_squared": {"female": 0, "male": 0},
    "coef_non_hdl_c_per_1_mmol_l": {"female": 0.0305239, "male": 0.0736174},
    "coef_hdl_c_per_0.3_mmol_l": {"female": -0.1606857, "male": -0.0954431},
    "coef_sbp_lt110_per_20_mmhg": {"female": -0.2394003, "male": -0.4347345},
    "coef_sbp_gteq110_per_20_mmhg": {"female": 0.3600781, "male": 0.3362658},
    "coef_diabetes": {"female": 0.8667604, "male": 0.7692857},
    "coef_current_smoking": {"female": 0.5360739, "male": 0.4386871},
    "coef_bmi_lt30_per_5_kg_m2": {"female": 0, "male": 0},
    "coef_bmi_gt30_per_5_kg_m2": {"female": 0, "male": 0},
    "coef_egfr_lt60_per_15_ml": {"female": 0.6045917, "male": 0.5378979},
    "coef_egfr_gteq60_per_15_ml": {"female": 0.0433769, "male": 0.0164827},
    "coef_anti_hypertensive_use": {"female": 0.3151672, "male": 0.288879},
    "coef_statin_use": {"female": -0.1477655, "male": -0.1337349},
    "coef_treated_sbp_gteq110_mm_hg_per_20_mm_hg": {"female": -0.0663612, "male": -0.0475924},
    "coef_treated_non_hdl_c": {"female": 0.1197879, "male": 0.150273},
    "coef_age_per_10yr_x_non_hdl_c_per_1_mmol_l": {"female": -0.0819715, "male": -0.0517874},
    "coef_age_per_10yr_x_hdl_c_per_0.3_mml_l": {"female": 0.0306769, "male": 0.0191169},
    "coef_age_per_10yr_x_sbp_gteq110_mm_hg_per_20_mmhg": {"female": -0.0946348, "male": -0.1049477},
    "coef_age_per_10yr_x_diabetes": {"female": -0.27057, "male": -0.2251948},
    "coef_age_per_10yr_x_current_smoking": {"female": -0.078715, "male": -0.0895067},
    "coef_age_per_10yr_x_bmi_gteq30_per_5_kg_m2": {"female": 0, "male": 0},
    "coef_age_per_10yr_x_egfr_lt60_per_15_ml": {"female": -0.1637806, "male": -0.1543702},
    "coef_sdi_decile_between_4_and_6": {"female": 0, "male": 0},
    "coef_sdi_decile_between_7_and_10": {"female": 0, "male": 0},
    "coef_miss_sdi": {"female": 0, "male": 0},
    "coef_ln_acr": {"female": 0, "male": 0},
    "coef_miss_ln_acr": {"female": 0, "male": 0},
    "coef_hba1c_minus_5.3_x_diabetes": {"female": 0, "male": 0},
    "coef_hba1c_minus_5.3_x_1_minus_diabetes": {"female": 0, "male": 0},
    "coef_miss_hba1c": {"female": 0, "male": 0},
    "const": {"female": -3.307728, "male": -3.031168},
}

BASE_30YR_CVD_COEFS: dict[str, dict[str, float]] = {
    "coef_age_per_10_years": {"female": 0.5503079, "male": 0.4627309},
    "coef_age_per_10_years_squared": {"female": -0.0928369, "male": -0.0984281},
    "coef_non_hdl_c_per_1_mmol_l": {"female": 0.0409794, "male": 0.0836088},
    "coef_hdl_c_per_0.3_mmol_l": {"female": -0.1663306, "male": -0.1029824},
    "coef_sbp_lt110_per_20_mmhg": {"female": -0.1628654, "male": -0.2140352},
    "coef_sbp_gteq110_per_20_mmhg": {"female": 0.3299505, "male": 0.2904325},
    "coef_diabetes": {"female": 0.6793894, "male": 0.5331276},
    "coef_current_smoking": {"female": 0.3196112, "male": 0.2141914},
    "coef_bmi_lt30_per_5_kg_m2": {"female": 0, "male": 0},
    "coef_bmi_gt30_per_5_kg_m2": {"female": 0, "male": 0},
    "coef_egfr_lt60_per_15_ml": {"female": 0.1857101, "male": 0.1155556},
    "coef_egfr_gteq60_per_15_ml": {"female": 0.0553528, "male": 0.0603775},
    "coef_anti_hypertensive_use": {"female": 0.2894, "male": 0.232714},
    "coef_statin_use": {"female": -0.075688, "male": -0.0272112},
    "coef_treated_sbp_gteq110_mm_hg_per_20_mm_hg": {"female": -0.056367, "male": -0.0384488},
    "coef_treated_non_hdl_c": {"female": 0.1071019, "male": 0.134192},
    "coef_age_per_10yr_x_non_hdl_c_per_1_mmol_l": {"female": -0.0751438, "male": -0.0511759},
    "coef_age_per_10yr_x_hdl_c_per_0.3_mml_l": {"female": 0.0301786, "male": 0.0165865},
    "coef_age_per_10yr_x_sbp_gteq110_mm_hg_per_20_mmhg": {"female": -0.0998776, "male": -0.1101437},
    "coef_age_per_10yr_x_diabetes": {"female": -0.3206166, "male": -0.2585943},
    "coef_age_per_10yr_x_current_smoking": {"female": -0.1607862, "male": -0.1566406},
    "coef_age_per_10yr_x_bmi_gteq30_per_5_kg_m2": {"female": 0, "male": 0},
    "coef_age_per_10yr_x_egfr_lt60_per_15_ml": {"female": -0.1450788, "male": -0.1166776},
    "coef_sdi_decile_between_4_and_6": {"female": 0, "male": 0},
    "coef_sdi_decile_between_7_and_10": {"female": 0, "male": 0},
    "coef_miss_sdi": {"female": 0, "male": 0},
    "coef_ln_acr": {"female": 0, "male": 0},
    "coef_miss_ln_acr": {"female": 0, "male": 0},
    "coef_hba1c_minus_5.3_x_diabetes": {"female": 0, "male": 0},
    "coef_hba1c_minus_5.3_x_1_minus_diabetes": {"female": 0, "male": 0},
    "coef_miss_hba1c": {"female": 0, "male": 0},
    "const": {"female": -1.318827, "male": -1.148204},
}

