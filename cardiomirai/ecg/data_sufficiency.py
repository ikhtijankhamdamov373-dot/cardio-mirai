"""Shared {value, status, confidence, method, reason} wrapper.

status is one of: "available", "unavailable", "indeterminate", "low_confidence", "reliable".
Using one shared constructor (instead of each function inventing its own
"unavailable"/"not met"/"criteria not met" string) is what lets the
frontend treat "missing data" and "negative finding" as genuinely distinct
render states, rather than both collapsing into the same prose.
"""

from __future__ import annotations

from typing import Any, Literal

Status = Literal["available", "unavailable", "indeterminate", "low_confidence", "reliable"]


def measurement(
    value: Any,
    status: Status,
    confidence: float | None = None,
    method: str | None = None,
    reason: str | None = None,
) -> dict:
    if status == "available" and reason is not None:
        # A reason is only meaningful when something is NOT fully available;
        # keep the shape consistent so callers don't have to special-case it.
        pass
    return {
        "value": value,
        "status": status,
        "confidence": confidence,
        "method": method,
        "reason": reason,
    }


def unavailable(reason: str, method: str | None = None) -> dict:
    return measurement(value=None, status="unavailable", confidence=None, method=method, reason=reason)


def available(value: Any, confidence: float | None = None, method: str | None = None) -> dict:
    return measurement(value=value, status="available", confidence=confidence, method=method, reason=None)
