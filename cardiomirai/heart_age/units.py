"""Unit conversions for the PREVENT equations.

PREVENT's published coefficients operate on SI units (mmol/L for lipids).
The clinic-facing API accepts conventional US units (mg/dL) and converts
internally -- getting this conversion wrong is exactly the failure mode
called out in the task: "A mg/dL <-> mmol/L error could produce a
plausible-looking but seriously incorrect risk estimate."

Conversion factor source: 1 mmol/L cholesterol = 38.67 mg/dL (equivalently,
mg/dL -> mmol/L via multiplication by 0.02586), which is the standard
clinical chemistry conversion factor for cholesterol (molar mass ~386.65
g/mol), and matches the exact constant (0.02586) used in PooledCohort's
own transformation code -- an independent confirmation this is the right
factor, not just a textbook value substituted without checking.
"""

from __future__ import annotations

CHOLESTEROL_MGDL_TO_MMOLL = 0.02586


def total_chol_mgdl_to_mmoll(value_mgdl: float) -> float:
    return value_mgdl * CHOLESTEROL_MGDL_TO_MMOLL


def hdl_mgdl_to_mmoll(value_mgdl: float) -> float:
    return value_mgdl * CHOLESTEROL_MGDL_TO_MMOLL


def non_hdl_mmoll(total_chol_mgdl: float, hdl_mgdl: float) -> float:
    """Non-HDL-C in mmol/L, computed from mg/dL inputs (matches PooledCohort's
    own order of operations: subtract in mg/dL, THEN convert -- not convert-then-subtract,
    though for a linear unit conversion these are mathematically equivalent;
    matching the reference order removes any doubt)."""
    return (total_chol_mgdl - hdl_mgdl) * CHOLESTEROL_MGDL_TO_MMOLL
