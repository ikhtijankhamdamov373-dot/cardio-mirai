"""Per-category lead-completeness checks.

Fixes the false-negative pattern found across _detect_stemi,
_detect_chamber_enlargement, assess_lvh, _detect_ischemia_and_infarction,
and (partially) _analyze_t_waves: each of these could emit a confident
negative ("No STEMI criteria met", "No chamber enlargement criteria met",
etc.) without checking whether the *specific* leads that category actually
requires were present -- and, for Patient 2, without noticing that "2
channels" were both the same anatomical lead.

Every requirement below is expressed as the *unique anatomical leads*
needed, via lead_utils, not raw channel counts.
"""

from __future__ import annotations

from dataclasses import dataclass

from .lead_utils import unique_lead_names

# What each interpretive category needs to be assessed AT ALL. This is a
# minimum-viable set (enough to attempt the existing rule logic), not a
# claim that these leads make the assessment maximally sensitive.
CATEGORY_REQUIREMENTS: dict[str, set[str]] = {
    "stemi": {"I", "II", "III", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"},
    "ischemia": {"II", "III", "aVF", "V2", "V3", "V4", "I", "aVL", "V5", "V6"},
    "infarction": {"V1", "V2", "V3", "V4", "II", "III", "aVF", "I", "aVL", "V5", "V6"},
    "qrs_axis": {"I", "aVF"},
    "p_axis": {"I", "aVF"},
    "t_axis": {"I", "aVF"},
    "lvh_sokolow": {"V1", "V5", "V6"},
    "lvh_cornell": {"aVL", "V3"},
    "chamber_enlargement_atrial": {"II"},
    "bbb_morphology": {"V1", "V6"},
}

# "Full" 12-lead requirement, used for the summary usable-leads count.
STANDARD_12_LEAD: set[str] = {"I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"}


@dataclass
class LeadAvailability:
    unique_leads: list[str]
    unique_lead_count: int
    total_channels: int
    is_duplicate_channel_set: bool  # True when channel count > unique lead count

    def available_for(self, category: str) -> tuple[bool, set[str]]:
        """Return (fully_available, missing_leads) for a named interpretive category.

        For lvh/stemi/ischemia/infarction, "fully available" means AT LEAST
        ONE of the recognized sub-criteria (e.g. Sokolow-Lyon OR Cornell for
        LVH) has its required leads -- matching how the underlying rules
        actually work -- while still reporting exactly what's missing for
        transparency.
        """

        available = set(self.unique_leads)
        if category == "lvh":
            sokolow_ok = CATEGORY_REQUIREMENTS["lvh_sokolow"].issubset(available)
            cornell_ok = CATEGORY_REQUIREMENTS["lvh_cornell"].issubset(available)
            if sokolow_ok or cornell_ok:
                return True, set()
            missing = (CATEGORY_REQUIREMENTS["lvh_sokolow"] | CATEGORY_REQUIREMENTS["lvh_cornell"]) - available
            return False, missing
        if category not in CATEGORY_REQUIREMENTS:
            raise KeyError(f"Unknown lead-requirement category: {category}")
        required = CATEGORY_REQUIREMENTS[category]
        missing = required - available
        return (len(missing) == 0, missing)

    def unavailable_reason(self, category: str) -> str | None:
        ok, missing = self.available_for(category)
        if ok:
            return None
        if self.is_duplicate_channel_set:
            return (
                f"Not assessable -- insufficient unique leads ({self.unique_lead_count} unique anatomical lead(s) "
                f"from {self.total_channels} channels; missing {', '.join(sorted(missing))})."
            )
        return f"Not assessable -- insufficient leads (missing {', '.join(sorted(missing))})."


def assess_lead_availability(lead_names: list[str]) -> LeadAvailability:
    unique = unique_lead_names(lead_names)
    return LeadAvailability(
        unique_leads=unique,
        unique_lead_count=len(unique),
        total_channels=len(lead_names),
        is_duplicate_channel_set=len(lead_names) > len(unique),
    )
