# Device Simulator — ARC-001

Sends HR, systolic/diastolic BP and SpO₂ once per second per patient (REQ-001).
Scenarios are derived from the risk analysis. All patients and values are synthetic — never use real patient data.

## Run

Start the backend first (from `backend/`: `uvicorn app.main:app --reload`, or `docker compose up` from the repository root), then from the repository root:

> Without `DATA_KEY` / `INDEX_KEY` the backend runs in development mode with an **in-memory** database: every restart (also every code change with `--reload`) starts empty, so restart the simulator too — it pairs its devices again at start-up. Set both keys (see `.env.example`) for persistent data.

```bash
python simulator/simulator.py --url http://localhost:8000 --patients 5 --scenario normal
python simulator/simulator.py --scenario deterioration --patients 3 --duration 180
python simulator/simulator.py --scenario disconnect --disconnect-after 15 --duration 40
```

Options: `--url`, `--patients`, `--scenario`, `--duration` (seconds, default: until Ctrl+C), `--seed` (reproducible noise), `--disconnect-after`, `--verbose` (print every reading). Only the standard library and `httpx` are needed (`pip install -r backend/requirements.txt`).

The simulator first pairs device `SIM-DEV-00n` with patient `SIM-P00n` (`POST /devices/pair`) and then posts one reading per patient per second (`POST /readings`). Every reading that is not `accepted` is printed; a summary is printed at the end.

## Scenarios

| Scenario | Behaviour | Tests / risk |
| --- | --- | --- |
| `normal` | Baseline HR 65–90, BP ≈ 120/80, SpO₂ 96–98.5 with small noise; always inside the non-critical alarm limits (no alarm expected) | REQ-001 |
| `deterioration` | After 10 s SpO₂ falls 0.12 points/s: below 92 % after ≈ 50 s (MEDIUM), below 85 % after ≈ 110 s (critical, HIGH); HR rises slowly | REQ-015, RISK-005/009 |
| `artefact` | ≈ 8 % of readings are artefacts: implausible spikes (e.g. HR 350, SpO₂ 20) or a sudden plausible HR jump of +45 bpm | REQ-002, RISK-002, RCM-002b |
| `disconnect` | Device 1 stops sending after `--disconnect-after` seconds; the others continue | REQ-003, RISK-001 |
| `unpaired` | An extra device `SIM-DEV-UNPAIRED` that was never paired also sends readings (expected: HTTP 422 + hazard event) | REQ-013, RISK-008 |
| `boundary` | Cycles through values exactly on and just outside the plausibility and alarm limits | REQ-002, REQ-015 |

`boundary` is listed in the SRS acceptance criteria of REQ-001 (in addition to the five scenarios of the Sprint 2 task).

## For tests

`generate_reading(state, scenario, t)` is a pure function (no network, deterministic for a given seed), used by `tests/test_simulator.py` (TC-001).
