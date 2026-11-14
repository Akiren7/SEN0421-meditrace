# MediTrace — Traceability matrix

> **Generated file — do not edit by hand.** Produced by the Compliance Reporter (ARC-009, REQ-016) with `python -m tools.trace.trace`. Sources: `docs/SRS.md`, `# Implements REQ-xxx` tags, `TC-xxx / REQ-xxx` test tags and the pytest JUnit result.

- Generated: 2026-11-14 09:16:03 UTC
- Source commit: `b689864`
- Test results: `report.xml`

## Summary

- 1/17 Must requirements have a passing test
- 23 requirements evaluated (OK: 1, NO TEST: 22)
- Test results from report.xml: 12 passed, 0 failed, 0 skipped

## Matrix

| REQ | Priority | Risks | Implemented in | Tests | Status |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | Must | – | – | – | **NO TEST** |
| REQ-002 | Must | RISK-002 | – | – | **NO TEST** |
| REQ-003 | Must | RISK-001 | – | – | **NO TEST** |
| REQ-004 | Must | RISK-003 | – | – | **NO TEST** |
| REQ-005 | Must | RISK-003 | – | – | **NO TEST** |
| REQ-006 | Must | RISK-004 | – | – | **NO TEST** |
| REQ-007 | Must | RISK-005 | – | – | **NO TEST** |
| REQ-008 | Must | RISK-006 | – | – | **NO TEST** |
| REQ-009 | Must | RISK-006 | – | – | **NO TEST** |
| REQ-010 | Must | RISK-007 | – | – | **NO TEST** |
| REQ-011 | Must | RISK-007 | – | – | **NO TEST** |
| REQ-012 | Must | RISK-001, RISK-002, RISK-003, RISK-004, RISK-005, RISK-006, RISK-007, RISK-008, RISK-009, RISK-010 | – | – | **NO TEST** |
| REQ-013 | Must | RISK-008 | – | – | **NO TEST** |
| REQ-014 | Should | – | – | – | **NO TEST** |
| REQ-015 | Must | RISK-005, RISK-009 | – | – | **NO TEST** |
| REQ-016 | Must | RISK-010 | `tools/trace/trace.py` | TC-016 ×11 (11 passed) | OK |
| REQ-017 | Optional | – | – | – | **NO TEST** |
| REQ-018 | Should | RISK-003 | – | – | **NO TEST** |
| REQ-019 | Must | RISK-002 | – | – | **NO TEST** |
| REQ-020 | Should | RISK-003 | – | – | **NO TEST** |
| REQ-022 | Should | RISK-005 | – | – | **NO TEST** |
| REQ-023 | Should | – | – | – | **NO TEST** |
| REQ-024 | Must | RISK-001, RISK-005 | – | – | **NO TEST** |

Reserved IDs (not evaluated): REQ-021.

## Status legend

| Status | Meaning |
| --- | --- |
| OK | At least one test, all pytest tests passed in the given JUnit result |
| OK (frontend, not in JUnit) | Only Vitest tests reference the requirement; their result is not in the JUnit file in v0 |
| FAILING | At least one test failed or errored |
| NO TEST | No test references the requirement |
| NOT IMPLEMENTED | Tests exist but no `Implements REQ-xxx` tag in the code |
| NO RESULT | Tests exist but no passing result is available (not run, skipped or missing from the JUnit file) — RCM-010 |

## Tagged tests

| Test | Tag | Result |
| --- | --- | --- |
| `tests/test_trace.py::test_cli_exits_zero_even_when_srs_is_missing` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_failing_test_in_junit_makes_requirement_failing` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_frontend_vitest_names_count_as_tests` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_generation_time_is_utc` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_implements_tags_are_collected_per_requirement` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_markdown_output_and_cli_exit_code` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_must_requirement_without_test_is_no_test` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_no_junit_or_skipped_test_is_never_reported_ok` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_parametrized_cases_are_merged_and_any_failure_wins` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_srs_ids_priorities_and_risks_are_parsed` | TC-016 / REQ-016 | passed |
| `tests/test_trace.py::test_tags_are_read_from_test_docstrings_untagged_ignored` | TC-016 / REQ-016 | passed |
