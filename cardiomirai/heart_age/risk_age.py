"""Evidence-Based Cardiovascular Risk Age.

Methodology source: the AHA PREVENT Risk Age calculator's own methodology
page (Northwestern Khan Lab, https://nwkhanlab.shinyapps.io/riskage/),
citing Krishnan, Huang, Perak, Coresh, Ndumele, Greenland, Lloyd-Jones, Khan.
"PREVENT Risk Age Equations and Population Distribution in US Adults."
JAMA Cardiology. 2025. doi:10.1001/jamacardio.2025.2427 -- and the classical
Framingham risk-age precedents it explicitly follows (D'Agostino et al.,
PMID 18212285; Marma & Lloyd-Jones, PMID 19620502).

This environment could not access the JAMA Cardiology paper's full text
(paywalled) to confirm a specific published numeric worked example. NO
specific "official" risk/age number is hardcoded anywhere in this module or
its tests as a result -- validation instead uses live cross-implementation
agreement (see test_prevent_equations.py) and closed-form mathematical
consistency checks (see test_risk_age.py), which do not depend on any
unverified external number.

Method (documented plainly since the source describes the concept, not a
line-by-line derivation): take the person's actual predicted risk from the
base 10-year Total CVD model, then find the age at which a SAME-SEX
individual with the "optimal" reference risk-factor profile would have that
identical predicted risk. Risk Age is explicitly documented as valid only
for the base 10-year equations -- this module does not offer a 30-year
Risk Age.

Reference/optimal profile (from the Khan Lab methodology page verbatim):
  non-HDL-C 120 mg/dL, HDL-C 50 mg/dL, SBP 110 mmHg, eGFR 90, no diabetes,
  non-smoker, no antihypertensive therapy, no statin therapy.

Closed-form derivation: substituting this fixed reference profile into the
PREVENT linear predictor collapses every non-age term to a single constant
(diabetes/smoking/eGFR-related terms vanish because their reference values
are exactly at the equations' own centering points; SBP and lipid terms
collapse to fixed numbers because they don't depend on age). What remains
is a closed-form function of age alone. The BASE 10-YEAR model's own
age-squared coefficient is exactly zero (confirmed directly in
_prevent_coefficients.py), so this reduces to a LINEAR equation in age,
solvable directly -- not root-finding, not an approximation.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._prevent_coefficients import BASE_10YR_CVD_COEFS
from .prevent_equations import Sex, _logistic

REFERENCE_NON_HDL_MGDL = 120.0
REFERENCE_HDL_MGDL = 50.0
REFERENCE_SBP_MMHG = 110.0
REFERENCE_EGFR = 90.0
# no diabetes, non-smoker, no antihypertensive therapy, no statin therapy (all False/0)

# Officially supported chronological age range for the PREVENT base equations
# (30-79). Risk Age is documented as valid only for the base equations, so
# this module applies the same boundary convention to its OUTPUT -- this is
# a reasoned extension the primary source's own scope implies, not a
# separately-published Risk Age-specific boundary number; documented here so
# that reasoning is visible rather than silently assumed.
RISK_AGE_MIN = 30.0
RISK_AGE_MAX = 79.0


def _reference_profile_terms() -> dict[str, float]:
    """The fixed (age-independent) transformed covariate values under the
    optimal reference profile -- computed once, reused for both sexes."""
    # REFERENCE_NON_HDL_MGDL is already non-HDL-C directly (not total-chol-minus-HDL);
    # the reference profile specifies non-HDL-C itself, so convert and center directly.
    non_hdl_mmol = (REFERENCE_NON_HDL_MGDL * 0.02586) - 3.5
    hdl_mmol = (REFERENCE_HDL_MGDL * 0.02586 - 1.3) / 0.3
    sbp_low = (min(REFERENCE_SBP_MMHG, 110.0) - 110.0) / 20.0
    sbp_high = (max(REFERENCE_SBP_MMHG, 110.0) - 130.0) / 20.0
    # diabetes, smoking, bp_meds, statin are all 0 for the reference profile.
    # eGFR = 90 is exactly at both piecewise centering points (60 and 90), so:
    egfr_low = (min(REFERENCE_EGFR, 60.0) - 60.0) / -15.0  # = 0
    egfr_high = (max(REFERENCE_EGFR, 60.0) - 90.0) / -15.0  # = 0
    return {
        "non_hdl": non_hdl_mmol,
        "hdl": hdl_mmol,
        "sbp_low": sbp_low,
        "sbp_high": sbp_high,
        "egfr_low": egfr_low,
        "egfr_high": egfr_high,
    }


def _reference_linear_predictor_coeffs(sex: Sex) -> tuple[float, float]:
    """Returns (slope, intercept) such that, under the reference profile,
    linear_predictor(age) = slope * ((age-55)/10) + intercept.

    Confirms and relies on coef_age_per_10_years_squared == 0 for the base
    10-year model (true for every outcome column in the verified table) --
    asserted explicitly rather than silently assumed, so a future change to
    the coefficient source would fail loudly here instead of silently
    producing a wrong Risk Age.
    """
    c = {name: table[sex] for name, table in BASE_10YR_CVD_COEFS.items()}
    if c["coef_age_per_10_years_squared"] != 0:
        raise AssertionError(
            "Risk Age's closed-form linear solve assumes the base 10-year model has no "
            "age-squared term, but the loaded coefficient table has a nonzero value. "
            "The closed-form derivation in this module would need to be redone as a "
            "quadratic solve if this ever changes."
        )

    ref = _reference_profile_terms()
    non_hdl, hdl, sbp_high = ref["non_hdl"], ref["hdl"], ref["sbp_high"]

    slope = (
        c["coef_age_per_10_years"]
        + c["coef_age_per_10yr_x_non_hdl_c_per_1_mmol_l"] * non_hdl
        + c["coef_age_per_10yr_x_hdl_c_per_0.3_mml_l"] * hdl
        + c["coef_age_per_10yr_x_sbp_gteq110_mm_hg_per_20_mmhg"] * sbp_high
        # age x diabetes, age x smoking, age x egfr_low all vanish: reference values are 0
    )
    intercept = (
        c["coef_non_hdl_c_per_1_mmol_l"] * non_hdl
        + c["coef_hdl_c_per_0.3_mmol_l"] * hdl
        + c["coef_sbp_lt110_per_20_mmhg"] * ref["sbp_low"]
        + c["coef_sbp_gteq110_per_20_mmhg"] * sbp_high
        + c["coef_egfr_lt60_per_15_ml"] * ref["egfr_low"]
        + c["coef_egfr_gteq60_per_15_ml"] * ref["egfr_high"]
        + c["const"]
    )
    return slope, intercept


@dataclass
class RiskAgeResult:
    risk_age_years: float | None  # None when outside the representable range
    boundary_label: str | None  # "<30" or ">79" when the solved age falls outside the range
    actual_risk: float
    reference_risk_at_boundary: tuple[float, float]  # (risk at age 30, risk at age 79) for transparency


def compute_risk_age(sex: Sex, actual_10yr_risk: float) -> RiskAgeResult:
    """Solve for the reference-profile age with the same predicted 10-year Total CVD risk."""
    if not (0.0 < actual_10yr_risk < 1.0):
        raise ValueError(f"actual_10yr_risk must be a probability in (0,1), got {actual_10yr_risk}")

    slope, intercept = _reference_linear_predictor_coeffs(sex)
    target_logit = _logit(actual_10yr_risk)

    # target_logit = slope * age_per_10 + intercept  =>  age_per_10 = (target_logit - intercept) / slope
    age_per_10 = (target_logit - intercept) / slope
    solved_age = age_per_10 * 10.0 + 55.0
    # Round before boundary comparison: the logit/logistic round-trip can leave
    # floating-point noise (e.g. 29.999999999999996 instead of exactly 30.0)
    # that would otherwise incorrectly trigger the boundary label for a case
    # that is mathematically exactly at the boundary. This was caught by
    # test_reference_profile_person_gets_risk_age_equal_to_chronological_age
    # at age=30 -- documented here rather than silently patched.
    solved_age = round(solved_age, 6)

    risk_at_30 = _logistic(slope * ((RISK_AGE_MIN - 55.0) / 10.0) + intercept)
    risk_at_79 = _logistic(slope * ((RISK_AGE_MAX - 55.0) / 10.0) + intercept)

    if solved_age < RISK_AGE_MIN:
        return RiskAgeResult(None, "<30", actual_10yr_risk, (risk_at_30, risk_at_79))
    if solved_age > RISK_AGE_MAX:
        return RiskAgeResult(None, ">79", actual_10yr_risk, (risk_at_30, risk_at_79))
    return RiskAgeResult(round(solved_age, 1), None, actual_10yr_risk, (risk_at_30, risk_at_79))


def _logit(p: float) -> float:
    import math
    return math.log(p / (1.0 - p))
