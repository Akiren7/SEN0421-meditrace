"""Plausibility and pairing checks of Ingestion & Validation (ARC-002).

Design decision 1 (A6): every reading is validated *before* it can reach the
Alarm Engine. Integrity level 3 (IEEE 1012): changes here need an independent
review and branch coverage >= 80 %.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.storage.repository import Repository

# Inclusive plausibility limits (REQ-002). A value equal to a limit is plausible.
PLAUSIBLE_RANGES: dict[str, tuple[int, int, str]] = {
    "hr": (20, 300, "bpm"),
    "spo2": (50, 100, "%"),
    "sys_bp": (40, 300, "mmHg"),
    "dia_bp": (20, 200, "mmHg"),
}


@dataclass(frozen=True)
class PlausibilityResult:
    """Outcome of the plausibility check; ``reasons`` is empty for a valid reading."""

    reasons: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """True when no rule was violated."""
        return not self.reasons


# Implements REQ-002
# Controls RISK-002
def check_plausibility(vitals: Mapping[str, int]) -> PlausibilityResult:
    """Apply the REQ-002 rules (RCM-002) to one reading.

    Rules: HR 20-300 bpm, SpO2 50-100 %, systolic 40-300 mmHg, diastolic
    20-200 mmHg (all inclusive) and systolic > diastolic. The reasons name the
    violated rule but not the measured value, so they can go into the hazard
    log without exposing health data in clear text.
    """
    reasons = []
    for name, (low, high, unit) in PLAUSIBLE_RANGES.items():
        value = vitals[name]
        if not low <= value <= high:
            reasons.append(f"{name} outside plausible range {low}-{high} {unit}")
    if vitals["sys_bp"] <= vitals["dia_bp"]:
        reasons.append("sys_bp not greater than dia_bp")
    return PlausibilityResult(tuple(reasons))


# Implements REQ-013
# Controls RISK-008
def check_pairing(repository: Repository, device_id: str) -> str | None:
    """Return the patient paired with ``device_id``, or ``None`` if the device is unpaired.

    A reading is attributed to a patient *only* through this pairing - never
    through data sent by the device - so a reading cannot be attached to the
    wrong patient (RISK-008).
    """
    return repository.get_device_patient(device_id)
