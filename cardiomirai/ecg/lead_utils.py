"""Lead-name canonicalization and unique-anatomical-lead counting.

Real-world WFDB headers frequently label channels in ways that don't map
1:1 to distinct anatomical leads -- e.g. a raw and a pre-filtered copy of
the same physical lead ("ECG I", "ECG I filtered"), or vendor-specific
aliases ("MLII" for a modified limb-lead II). Counting such channels as
independent leads silently overstates how much anatomical information is
actually available, which is exactly what caused Patient 2's case to be
reported as "2 usable leads" when only Lead I was actually present.

This module is the single place responsible for turning a list of raw
channel/signal names into canonical anatomical lead identifiers.
"""

from __future__ import annotations

import re

STANDARD_LEADS: tuple[str, ...] = ("I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6")

# Known aliases -> canonical standard lead name.
_ALIASES: dict[str, str] = {
    "MLII": "II",
    "ML2": "II",
    "MLI": "I",
    "ML1": "I",
    "AVR": "aVR",
    "AVL": "aVL",
    "AVF": "aVF",
    "V1'": "V1",
}

# Qualifier words that describe *processing*, not a different anatomical
# source, and should be stripped before matching a canonical lead name.
_PROCESSING_QUALIFIERS = (
    "filtered",
    "raw",
    "unfiltered",
    "denoised",
    "smoothed",
    "processed",
    "cleaned",
)


def canonicalize_lead_name(raw_name: str) -> str:
    """Map a raw channel/signal name to a canonical anatomical lead id.

    Returns the canonical name (e.g. "I", "V5") when recognized, or the
    cleaned-up original string if it doesn't match a known lead so callers
    can still treat genuinely unknown channels as distinct from each other.
    """

    if not raw_name:
        return raw_name

    name = raw_name.strip()
    # Drop a leading "ECG " / "Lead " label some devices prepend.
    name = re.sub(r"^(ecg|lead)\s+", "", name, flags=re.IGNORECASE)
    # Drop trailing processing qualifiers like "filtered", "raw", etc.
    lowered = name.lower()
    for qualifier in _PROCESSING_QUALIFIERS:
        if lowered.endswith(qualifier):
            name = name[: -(len(qualifier))].strip()
            lowered = name.lower()

    name = name.strip()
    if not name:
        return raw_name.strip()

    if name in STANDARD_LEADS:
        return name
    if name.upper() in _ALIASES:
        return _ALIASES[name.upper()]
    for standard in STANDARD_LEADS:
        if name.upper() == standard.upper():
            return standard

    # Not a recognized standard lead -- return the cleaned name as-is so
    # two genuinely different unknown channels aren't merged together.
    return name


def unique_lead_names(lead_names: list[str]) -> list[str]:
    """Return canonical lead names, de-duplicated, preserving first-seen order."""

    seen: list[str] = []
    for raw in lead_names:
        canonical = canonicalize_lead_name(raw)
        if canonical not in seen:
            seen.append(canonical)
    return seen


def channel_to_canonical_map(lead_names: list[str]) -> dict[int, str]:
    """Map each channel index to its canonical anatomical lead name."""

    return {idx: canonicalize_lead_name(name) for idx, name in enumerate(lead_names)}


def unique_lead_count(lead_names: list[str]) -> int:
    return len(unique_lead_names(lead_names))


def has_unique_leads(lead_names: list[str], required: set[str]) -> tuple[bool, set[str]]:
    """Check whether every lead in `required` is present as a unique anatomical lead.

    Returns (all_present, missing_leads).
    """

    available = set(unique_lead_names(lead_names))
    missing = required - available
    return (len(missing) == 0, missing)
