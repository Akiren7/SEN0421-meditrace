# ADR-001 — Searching encrypted patient names with an HMAC blind index

| Field | Value |
| --- | --- |
| Status | **Accepted** (Sprint 2, 14.11.2026) |
| Decided by | Bahadır Duran (Backend & Security Developer); reviewed in the PLN-04 pull request |
| Issues | PLN-05 (#5), closes process issue **RSK-06** |
| Requirements / risks | REQ-010 (AES-256-GCM at rest), RISK-007 (health-data leak), RISK-008 (wrong patient) |
| Components | ARC-007 Encrypted Data Layer (`backend/app/storage/crypto.py`, `repository.py`) |

## Context

REQ-010 requires patient identity data to be stored encrypted with AES-256-GCM. GCM uses a fresh random nonce for every value, so the same name gives a different ciphertext every time. This is what makes the encryption secure, but it also means the database cannot compare or search encrypted names (`WHERE name = ...` never matches).

The ward still needs to find a patient by name (e.g. an admin pairing a device, later the dashboard search). In Progress Report 1 this conflict was recorded as process issue **RSK-06** (open).

## Options considered

| # | Option | Pros | Cons |
| - | ------ | ---- | ---- |
| A | **Decrypt all rows** and filter in Python | Any search (partial, fuzzy) possible; no extra column | Every search decrypts every patient's name (all identity data in memory for one lookup, against KVKK data minimisation); cost grows with the number of patients; makes the encryption almost pointless during a search |
| B | **Search by patient number only** (no name search) | Simplest; nothing extra stored | Poor usability; a nurse often knows the name, not the number; does not close RSK-06 |
| C | **Deterministic encryption** of the name (e.g. AES-SIV) | Exact match in SQL | Same name → same ciphertext under the *data* key; mixes search and confidentiality in one key; not the AES-256-GCM required by REQ-010 |
| D | **HMAC blind index**: store `HMAC-SHA256(INDEX_KEY, normalize(name))` next to the GCM ciphertext | Exact-match search in SQL through an index; only matching rows are decrypted; name itself stays AES-256-GCM; separate key | Exact match only; equal names have equal index values (frequency is visible to someone with DB access); key rotation needs re-indexing |

## Decision

**Option D — HMAC-SHA256 exact-match blind index.**

- `patients.name_enc` = AES-256-GCM(`DATA_KEY`, name, associated data = patient ID).
- `patients.name_index` = hex `HMAC-SHA256(INDEX_KEY, normalize_name(name))`, indexed column.
- `normalize_name`: Unicode NFC, trim, collapse inner whitespace, case-fold, and fold Turkish `I/ı/İ/i` to `i` (Python's `casefold()` is not locale aware: `"YILMAZ"` → `"yilmaz"` but `"Yılmaz"` → `"yılmaz"`). Nothing else is normalised (`ş` ≠ `s`).
- `Repository.find_patient_by_name(name)` computes the index of the search term, selects matching rows, and decrypts **only those rows**. It returns a list, because two patients may have the same name.
- **No partial or fuzzy search** (no prefix, no "contains", no typo tolerance).
- `INDEX_KEY` is a separate 32-byte key from `DATA_KEY`; the backend refuses to start if they are equal. Neither key is committed to the repository (`.env.example` holds dummy values only).

## Consequences

- RSK-06 is **closed**: REQ-010 (encryption) and patient search no longer conflict.
- The search UI (Sprint 3, dashboard) must ask for the full name (or the patient number) and show all matches; the user confirms the patient from the decrypted details (same-name patients, RISK-008).
- Someone with database access but without `INDEX_KEY` cannot reverse the index, but can see that two rows have the same name. Accepted for a single ward (RISK-007 residual risk unchanged, 3×1 = 3).
- Folding `ı`/`i` means e.g. "Işık" and "Isik" have the same index → both are shown; acceptable (false positive, never a false negative for case/I variants).
- **Key rotation:** changing `INDEX_KEY` requires recomputing `name_index` for every patient (decrypt name with `DATA_KEY`, HMAC with the new key). Changing `DATA_KEY` requires re-encrypting all `_enc` columns. A rotation script is not in scope for v1.0; recorded as an open point.
- Verified by `tests/test_storage.py` (TC-010): exact name found, partial name not found, normalised variants found, Turkish I variants found, only matching rows decrypted, another key gives another index.
