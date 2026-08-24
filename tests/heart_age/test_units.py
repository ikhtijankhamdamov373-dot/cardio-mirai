import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cardiomirai.heart_age.units import total_chol_mgdl_to_mmoll, hdl_mgdl_to_mmoll, non_hdl_mmoll


def test_cholesterol_conversion_factor():
    # 1 mmol/L cholesterol = 38.67 mg/dL is the standard clinical chemistry factor.
    assert abs(total_chol_mgdl_to_mmoll(38.67) - 1.0) < 0.001


def test_non_hdl_matches_manual_subtraction():
    # A mg/dL<->mmol/L mixup here is exactly the failure mode this test guards against:
    # non-HDL should be computed as (TC - HDL) in mg/dL, THEN converted -- verify the
    # result matches converting each independently and subtracting, since if someone
    # ever "fixes" this into convert-then-subtract by mistake, it should still agree
    # (linear conversion), but a genuine mg/dL vs mmol/L error would NOT agree.
    tc, hdl = 220.0, 50.0
    result = non_hdl_mmoll(tc, hdl)
    expected = total_chol_mgdl_to_mmoll(tc) - hdl_mgdl_to_mmoll(hdl)
    assert abs(result - expected) < 1e-9


def test_realistic_values_land_in_expected_mmol_range():
    # Sanity range check: typical adult total cholesterol 150-300 mg/dL should
    # convert to roughly 3.9-7.8 mmol/L -- catches a gross unit error immediately.
    assert 3.5 < total_chol_mgdl_to_mmoll(150) < 4.5
    assert 7.0 < total_chol_mgdl_to_mmoll(300) < 8.5
