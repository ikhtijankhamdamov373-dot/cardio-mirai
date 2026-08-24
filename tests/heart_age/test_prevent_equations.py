"""Cross-implementation validation against PooledCohort (Byron Jaeger, Wake
Forest), executed live in R in this environment (see docs/heart_age_v0.1.md
for the exact R invocation). These are not invented/remembered numbers --
they are the literal output of running PooledCohort's predict_10yr_cvd_risk
and predict_30yr_cvd_risk on these exact 10 patients, captured once and
locked in here as a permanent regression oracle.

preventr (Martin Mayer) was not independently re-executed here (its own
dependency, dplyr, could not be installed offline in this environment --
CRAN unreachable, apt blocked by unrelated broken packages) -- but its
coefficient tables were separately confirmed byte-identical (7 decimal
places) to PooledCohort's own source data, so by transitivity it computes
the same result given the same well-verified formula. This is stated
explicitly rather than presented as an independent live execution it wasn't.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cardiomirai.heart_age.prevent_equations import PreventInputs, total_cvd_risk_10yr, total_cvd_risk_30yr

# 10 diverse patients spanning both sexes, ages 30s/50s/70s, normotensive/
# hypertensive, smoker, diabetes, reduced eGFR, statin/antihypertensive use.
PATIENTS = [
    dict(age_years=35, sex="female", total_chol_mgdl=180, hdl_chol_mgdl=55, sbp_mmhg=115, on_antihypertensive_therapy=False, on_statin_therapy=False, has_diabetes=False, current_smoker=False, egfr_ml_min_1_73m2=95),
    dict(age_years=35, sex="male", total_chol_mgdl=190, hdl_chol_mgdl=45, sbp_mmhg=125, on_antihypertensive_therapy=False, on_statin_therapy=False, has_diabetes=False, current_smoker=True, egfr_ml_min_1_73m2=90),
    dict(age_years=52, sex="female", total_chol_mgdl=220, hdl_chol_mgdl=50, sbp_mmhg=135, on_antihypertensive_therapy=True, on_statin_therapy=False, has_diabetes=False, current_smoker=False, egfr_ml_min_1_73m2=80),
    dict(age_years=52, sex="male", total_chol_mgdl=210, hdl_chol_mgdl=40, sbp_mmhg=150, on_antihypertensive_therapy=True, on_statin_therapy=True, has_diabetes=True, current_smoker=False, egfr_ml_min_1_73m2=70),
    dict(age_years=58, sex="female", total_chol_mgdl=200, hdl_chol_mgdl=60, sbp_mmhg=140, on_antihypertensive_therapy=False, on_statin_therapy=False, has_diabetes=False, current_smoker=False, egfr_ml_min_1_73m2=90),
    dict(age_years=61, sex="male", total_chol_mgdl=240, hdl_chol_mgdl=35, sbp_mmhg=160, on_antihypertensive_therapy=True, on_statin_therapy=False, has_diabetes=True, current_smoker=True, egfr_ml_min_1_73m2=55),
    dict(age_years=70, sex="female", total_chol_mgdl=195, hdl_chol_mgdl=65, sbp_mmhg=118, on_antihypertensive_therapy=False, on_statin_therapy=True, has_diabetes=False, current_smoker=False, egfr_ml_min_1_73m2=65),
    dict(age_years=72, sex="male", total_chol_mgdl=175, hdl_chol_mgdl=48, sbp_mmhg=145, on_antihypertensive_therapy=True, on_statin_therapy=True, has_diabetes=False, current_smoker=False, egfr_ml_min_1_73m2=50),
    dict(age_years=45, sex="female", total_chol_mgdl=230, hdl_chol_mgdl=42, sbp_mmhg=128, on_antihypertensive_therapy=False, on_statin_therapy=False, has_diabetes=True, current_smoker=True, egfr_ml_min_1_73m2=100),
    dict(age_years=30, sex="male", total_chol_mgdl=165, hdl_chol_mgdl=52, sbp_mmhg=108, on_antihypertensive_therapy=False, on_statin_therapy=False, has_diabetes=False, current_smoker=False, egfr_ml_min_1_73m2=110),
]

# Captured directly from a live PooledCohort R execution (see module docstring).
R_REFERENCE_10YR = [0.0042161764, 0.0182937145, 0.0444493491, 0.1647158066, 0.0460873558, 0.3647735158, 0.0778051883, 0.2164186608, 0.1058056419, 0.0034389739]
R_REFERENCE_30YR = [0.0338919686, 0.1235437682, 0.2632654269, 0.5474538427, 0.2419937724, 0.6124044444, 0.2784107020, 0.4158118362, 0.4345692600, 0.0243905188]

TOLERANCE = 1e-6  # far tighter than clinically meaningful; observed max diff was ~5e-11


@pytest.mark.parametrize("i", range(10))
def test_10yr_matches_pooledcohort(i):
    inputs = PreventInputs(**PATIENTS[i])
    py_result = total_cvd_risk_10yr(inputs)
    diff = abs(py_result - R_REFERENCE_10YR[i])
    assert diff < TOLERANCE, f"Patient {i+1}: Python={py_result} R={R_REFERENCE_10YR[i]} diff={diff}"


@pytest.mark.parametrize("i", range(10))
def test_30yr_matches_pooledcohort(i):
    inputs = PreventInputs(**PATIENTS[i])
    py_result = total_cvd_risk_30yr(inputs)
    diff = abs(py_result - R_REFERENCE_30YR[i])
    assert diff < TOLERANCE, f"Patient {i+1}: Python={py_result} R={R_REFERENCE_30YR[i]} diff={diff}"


def test_risk_increases_with_worse_risk_factors_a_basic_face_validity_check():
    """Not a numeric oracle -- a sanity check that the equation moves in the
    clinically expected direction, independent of any external reference."""
    baseline = PreventInputs(age_years=55, sex="male", total_chol_mgdl=180, hdl_chol_mgdl=55, sbp_mmhg=115, on_antihypertensive_therapy=False, on_statin_therapy=False, has_diabetes=False, current_smoker=False, egfr_ml_min_1_73m2=95)
    worse = PreventInputs(age_years=55, sex="male", total_chol_mgdl=180, hdl_chol_mgdl=55, sbp_mmhg=115, on_antihypertensive_therapy=False, on_statin_therapy=False, has_diabetes=True, current_smoker=True, egfr_ml_min_1_73m2=95)
    assert total_cvd_risk_10yr(worse) > total_cvd_risk_10yr(baseline)
