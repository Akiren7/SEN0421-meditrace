"""MediTrace Device Simulator v1 (ARC-001, REQ-001).

Pairs N simulated bedside devices with N simulated patients and then sends one
reading per patient per second to the backend::

    python simulator/simulator.py --url http://localhost:8000 --patients 5 --scenario normal

Scenarios (derived from the risk register):

``normal``         realistic values with small noise, inside all non-critical
                   alarm limits (no alarm expected).
``deterioration``  SpO2 falls slowly below 92 % (MEDIUM) and then below 85 %
                   (critical, HIGH) - REQ-015.
``artefact``       random spikes: implausible values (REQ-002, RISK-002) and
                   sudden plausible jumps (rate-of-change check RCM-002b).
``disconnect``     the first device stops sending after ``--disconnect-after``
                   seconds - data-loss alarm REQ-003, RISK-001.
``unpaired``       an extra device that was never paired also sends readings -
                   REQ-013, RISK-008.
``boundary``       cycles through values exactly on and just outside the
                   plausibility and alarm limits - REQ-002 / REQ-015 boundaries.

Only the standard library and ``httpx`` are used. All patients and values are
synthetic: never use real patient data.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    import httpx

SCENARIOS: tuple[str, ...] = (
    "normal",
    "deterioration",
    "artefact",
    "disconnect",
    "unpaired",
    "boundary",
)
VITALS: tuple[str, ...] = ("hr", "sys_bp", "dia_bp", "spo2")

# ``normal`` stays strictly inside the non-critical alarm limits of A6
# (HR 50-120, SpO2 >= 92, systolic 90-180) with a safety margin.
NORMAL_LIMITS: dict[str, tuple[int, int]] = {
    "hr": (55, 110),
    "sys_bp": (100, 160),
    "dia_bp": (60, 95),
    "spo2": (94, 100),
}

ARTEFACT_PROBABILITY = 0.08
IMPLAUSIBLE_SPIKES: tuple[tuple[str, int], ...] = (
    ("hr", 350),
    ("hr", 0),
    ("spo2", 20),
    ("sys_bp", 400),
    ("dia_bp", 5),
)
PLAUSIBLE_JUMP_HR = 45  # sudden +45 bpm in 1 s: plausible value, suspicious change

DETERIORATION_START_S = 10  # seconds of normal values before SpO2 starts falling
DETERIORATION_RATE = 0.12  # SpO2 points lost per second
DETERIORATION_FLOOR = 78

# Each case: (hr, sys_bp, dia_bp, spo2) - on/just outside a limit.
BOUNDARY_CASES: tuple[tuple[int, int, int, int], ...] = (
    (20, 120, 80, 97),  # HR lowest plausible
    (300, 120, 80, 97),  # HR highest plausible
    (19, 120, 80, 97),  # HR implausible
    (301, 120, 80, 97),  # HR implausible
    (75, 120, 80, 50),  # SpO2 lowest plausible
    (75, 120, 80, 100),  # SpO2 highest plausible
    (75, 120, 80, 49),  # SpO2 implausible
    (75, 40, 20, 97),  # systolic and diastolic lowest plausible
    (75, 300, 200, 97),  # systolic and diastolic highest plausible
    (75, 120, 120, 97),  # systolic not greater than diastolic -> implausible
    (75, 121, 120, 97),  # systolic just greater than diastolic
    (50, 90, 60, 92),  # exactly on the lower non-critical alarm limits: no violation
    (120, 180, 80, 92),  # exactly on the upper non-critical alarm limits: no violation
    (40, 120, 80, 85),  # exactly on the critical limits: non-critical violation, not critical
    (150, 120, 80, 85),  # exactly on the upper critical HR limit: non-critical only
)


@dataclass(frozen=True)
class PatientState:
    """Static description of one simulated patient/device pair."""

    patient_id: str
    device_id: str
    patient_name: str
    start: datetime
    seed: int
    hr: float = 75.0
    sys_bp: float = 120.0
    dia_bp: float = 80.0
    spo2: float = 97.0
    paired: bool = True
    disconnect_after: float | None = None

    def baseline(self) -> dict[str, float]:
        """Baseline vital values of this patient."""
        return {"hr": self.hr, "sys_bp": self.sys_bp, "dia_bp": self.dia_bp, "spo2": self.spo2}


def build_states(
    patients: int,
    scenario: str,
    *,
    seed: int = 42,
    start: datetime | None = None,
    disconnect_after: float = 15.0,
) -> list[PatientState]:
    """Create the simulated patients for a scenario (plus the rogue device for ``unpaired``)."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; choose one of {', '.join(SCENARIOS)}")
    if patients < 1:
        raise ValueError("at least one patient is required")
    start = (start or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    rng = random.Random(seed)
    states = []
    for i in range(1, patients + 1):
        states.append(
            PatientState(
                patient_id=f"SIM-P{i:03d}",
                device_id=f"SIM-DEV-{i:03d}",
                patient_name=f"Simulated Patient {i:03d}",
                start=start,
                seed=seed,
                hr=rng.uniform(65, 90),
                sys_bp=rng.uniform(112, 130),
                dia_bp=rng.uniform(72, 84),
                spo2=rng.uniform(96, 98.5),
                disconnect_after=disconnect_after if scenario == "disconnect" and i == 1 else None,
            )
        )
    if scenario == "unpaired":
        states.append(
            PatientState(
                patient_id="SIM-P999",
                device_id="SIM-DEV-UNPAIRED",
                patient_name="Unpaired Device",
                start=start,
                seed=seed,
                paired=False,
            )
        )
    return states


def _clamp(value: float, low: int, high: int) -> int:
    return int(min(max(round(value), low), high))


def _normal_values(state: PatientState, rng: random.Random) -> dict[str, int]:
    noise = {"hr": 2.5, "sys_bp": 3.0, "dia_bp": 2.0, "spo2": 0.6}
    values = {
        name: _clamp(base + rng.gauss(0, noise[name]), *NORMAL_LIMITS[name])
        for name, base in state.baseline().items()
    }
    if values["sys_bp"] <= values["dia_bp"]:  # cannot happen with the limits above; keep it safe
        values["sys_bp"] = values["dia_bp"] + 30
    return values


# Implements REQ-001
def generate_reading(state: PatientState, scenario: str, t: int) -> dict[str, Any] | None:
    """Return the reading of ``state`` at second ``t`` (0, 1, 2, ...) or ``None``.

    Pure function: no I/O, and the same ``(state, scenario, t)`` always gives
    the same reading (the noise generator is seeded from seed, device and t).
    ``None`` means the device sends nothing at that second (``disconnect``).
    The dict uses the field names of the shared data contract (A6).
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}")
    if t < 0:
        raise ValueError("t must be >= 0")
    if state.disconnect_after is not None and t >= state.disconnect_after:
        return None

    rng = random.Random(f"{state.seed}:{state.device_id}:{t}")
    values = _normal_values(state, rng)

    if scenario == "deterioration":
        # SpO2 falls until the floor; HR rises with it (compensation) and stops
        # rising when SpO2 stops falling, so HR stays below the critical 150 bpm
        # and the scenario only tests the SpO2 alarms.
        drop = min(
            max(0.0, t - DETERIORATION_START_S) * DETERIORATION_RATE,
            state.spo2 - DETERIORATION_FLOOR,
        )
        spo2 = state.spo2 - drop + rng.gauss(0, 0.4)
        values["spo2"] = _clamp(spo2, DETERIORATION_FLOOR, 100)
        values["hr"] = _clamp(state.hr + drop * 1.2 + rng.gauss(0, 2.0), 40, 140)
    elif scenario == "artefact" and rng.random() < ARTEFACT_PROBABILITY:
        if rng.random() < 0.6:
            vital, spike = rng.choice(IMPLAUSIBLE_SPIKES)
            values[vital] = spike
        else:
            values["hr"] = min(values["hr"] + PLAUSIBLE_JUMP_HR, 300)
    elif scenario == "boundary":
        case = BOUNDARY_CASES[t % len(BOUNDARY_CASES)]
        values = dict(zip(VITALS, case, strict=True))

    timestamp = state.start + timedelta(seconds=t)
    return {
        "device_id": state.device_id,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        **values,
    }


@dataclass
class RunSummary:
    """Counts of server responses during a run."""

    sent: int = 0
    outcomes: Counter[str] = field(default_factory=Counter)

    def add(self, outcome: str) -> None:
        """Count one sent reading and the server's answer."""
        self.sent += 1
        self.outcomes[outcome] += 1

    def __str__(self) -> str:
        parts = ", ".join(f"{key}={value}" for key, value in sorted(self.outcomes.items()))
        return f"sent={self.sent} ({parts})"


def _outcome(response: httpx.Response) -> str:
    if response.status_code in (200, 201):
        try:
            return str(response.json().get("status", response.status_code))
        except ValueError:
            return str(response.status_code)
    if response.status_code == 422:
        return "rejected"
    return f"http_{response.status_code}"


def pair_all(client: httpx.Client, states: list[PatientState], log: Callable[[str], None]) -> None:
    """Pair every device that should be paired (POST /devices/pair)."""
    for state in states:
        if not state.paired:
            log(f"{state.device_id}: intentionally NOT paired (scenario unpaired)")
            continue
        response = client.post(
            "/devices/pair",
            json={
                "device_id": state.device_id,
                "patient_id": state.patient_id,
                "patient_name": state.patient_name,
            },
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(
                f"pairing {state.device_id} failed: HTTP {response.status_code} {response.text}"
            )
        log(f"{state.device_id} -> {state.patient_id}: {response.json()['status']}")


def run(
    client: httpx.Client,
    states: list[PatientState],
    scenario: str,
    *,
    duration: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    log: Callable[[str], None] = print,
    verbose: bool = False,
) -> RunSummary:
    """Pair the devices, then send one reading per patient per second.

    ``duration`` is the number of seconds to simulate (``None`` = until Ctrl+C).
    Ticks are scheduled on a monotonic clock so that the rate stays 1 Hz even
    when a request takes a few milliseconds. Network errors are counted and the
    run continues (the backend may be restarting).
    """
    import httpx  # local import: generate_reading() is usable without httpx

    summary = RunSummary()
    t = 0
    try:
        pair_all(client, states, log)
        t0 = clock()
        while duration is None or t < duration:
            delay = t0 + t - clock()
            if delay > 0:
                sleep(delay)
            for state in states:
                reading = generate_reading(state, scenario, t)
                if reading is None:
                    continue
                try:
                    outcome = _outcome(client.post("/readings", json=reading))
                except httpx.HTTPError as exc:
                    outcome = "network_error"
                    log(f"t={t}s {state.device_id}: {type(exc).__name__}")
                summary.add(outcome)
                if verbose or outcome != "accepted":
                    values = " ".join(f"{name}={reading[name]}" for name in VITALS)
                    log(f"t={t}s {state.device_id} {values} -> {outcome}")
            t += 1
    except KeyboardInterrupt:
        log("stopped by user")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MediTrace device simulator (ARC-001)")
    parser.add_argument("--url", default="http://localhost:8000", help="backend base URL")
    parser.add_argument("--patients", type=int, default=5, help="number of simulated patients")
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument(
        "--duration", type=int, default=None, help="seconds to run (default: until Ctrl+C)"
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed (reproducible runs)")
    parser.add_argument(
        "--disconnect-after",
        type=float,
        default=15.0,
        help="seconds before the first device stops sending (scenario disconnect)",
    )
    parser.add_argument("--verbose", action="store_true", help="print every reading")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import httpx

    args = parse_args(argv)
    try:
        states = build_states(
            args.patients, args.scenario, seed=args.seed, disconnect_after=args.disconnect_after
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        f"MediTrace simulator: {args.patients} patient(s), "
        f"scenario={args.scenario}, url={args.url}"
    )
    try:
        with httpx.Client(base_url=args.url, timeout=5.0) as client:
            summary = run(
                client, states, args.scenario, duration=args.duration, verbose=args.verbose
            )
    except (httpx.HTTPError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
