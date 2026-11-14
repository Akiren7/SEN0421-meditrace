# Frontend — Monitoring Dashboard (ARC-008)

React + TypeScript (Vite) dashboard of MediTrace. **Sprint 2 skeleton (PLN-06): runs on mock data only**
(`src/mock/`); live data via the REST API and `WS /ws/alarms` follows in Sprint 3.
Simulated data only — not for clinical use.

## Run

Node.js 22 LTS (20.19+ works). From this folder:

```bash
npm ci            # install the exact versions from package-lock.json
npm run dev       # http://localhost:5173
npm test          # Vitest (watch mode); CI uses: npm test -- --run
npm run build     # type-check (tsc -b) + production build into dist/
npm run lint      # oxlint
```

Optional: if the backend runs on port 8000 (`cd backend && uvicorn app.main:app --port 8000`), the
header badge shows `Backend: online` (the dev server forwards `/api/*` to it, see `vite.config.ts`).
Without the backend the dashboard works unchanged and the badge says `offline (mock data)`.

## Screens

| Route | Screen | Roles (A6 matrix) | Requirements |
| --- | --- | --- | --- |
| `/login` | Static demo login with role switch (no real authentication until ARC-005, Sprint 3) | all | REQ-009 (demo only) |
| `/patients` | Ward overview: one card per patient (HR, BP, SpO₂, status, time since last reading) | Doctor, Nurse | REQ-002, REQ-003, REQ-015 (display) |
| `/patients/:id` | Patient detail: latest values, alarms, 24-h charts (HR, BP, SpO₂) | Doctor, Nurse | REQ-014, REQ-023 |
| `/alarms` | Alarm screen: active alarms HIGH → MEDIUM → LOW, acknowledged alarms | Doctor, Nurse | REQ-005, REQ-007, REQ-022 |
| `/admin` | Device pairing (read-only mock) + role matrix | Admin | REQ-013 (display) |
| `/logs` | Hazard log (mock), audit log placeholder | Doctor, Auditor | REQ-012 (display) |

The red HIGH-alarm banner with the audible alert and its own *Acknowledge* buttons is shown on every
clinical screen. Screenshots and a description of each screen: `docs/test/ui-wireframes.md`.

## Structure

```text
src/
  types.ts            shared data contract (Reading, Alarm, HazardEvent, roles) — same field names as the backend
  lib/                pure logic: thresholds, status, alarms (sort/acknowledge), chart window, downsampling,
                      permissions (A6 matrix), Web Audio beep, performance timing
  mock/               simulated ward and 24-h history (replaced by API calls in Sprint 3)
  state/              React context: session (user/role) and ward (alarms, mute)
  components/ pages/  UI
  **/*.test.ts(x)     Vitest + React Testing Library tests, named "TC-xxx / REQ-xxx: …"
```

Traceability tags: tests start with `TC-xxx / REQ-xxx:`; implementing source carries `// Implements REQ-xxx`
(and `// Controls RISK-xxx`). See `docs/test/test-plan.md` §4.

## SOUP list (IEC 62304 §8.1.2)

All versions are pinned exactly in `package.json` (no `^`/`~` ranges); `package-lock.json` pins the full
dependency tree and CI installs it with `npm ci`.

**Runtime (shipped in the dashboard bundle)**

| Package | Version | Purpose |
| --- | --- | --- |
| react | 19.3.1 | UI library |
| react-dom | 19.3.1 | React renderer for the browser |
| react-router-dom | 7.18.5 | Client-side routing between the screens |
| recharts | 3.10.1 | 24-h time-series charts (REQ-014) |

**Development and test only (not shipped)**

| Package | Version | Purpose |
| --- | --- | --- |
| vite | 8.3.6 | Dev server and production build |
| @vitejs/plugin-react | 6.1.2 | React support for Vite |
| typescript | 7.0.2 | Type checking (`tsc -b`) |
| @types/react, @types/react-dom | 19.3.0 | React type definitions |
| @types/node | 24.19.2 | Node type definitions for `vite.config.ts` |
| vitest | 5.1.0 | Test runner (`npm test`) |
| jsdom | 31.0.1 | Browser-like DOM for tests |
| @testing-library/react | 16.3.3 | Rendering components in tests |
| @testing-library/dom | 10.4.2 | DOM queries (peer of @testing-library/react) |
| @testing-library/user-event | 14.6.10 | Simulated clicks/typing in tests (click counting for TC-022) |
| @testing-library/jest-dom | 7.0.1 | DOM assertions (`toBeInTheDocument`, …) |
| oxlint | 1.90.0 | Linter |

Known anomalies / notes: the production bundle is ~650 kB (mostly recharts) and Vite prints a
chunk-size warning; code splitting of the patient-detail route is planned for Sprint 3 if REQ-023
measurements require it.
