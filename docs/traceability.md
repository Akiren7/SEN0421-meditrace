# MediTrace — Traceability matrix

> **Generated file — do not edit by hand.** Produced by the Compliance Reporter (ARC-009, REQ-016) with `python -m tools.trace.trace`. Sources: `docs/SRS.md`, `# Implements REQ-xxx` tags, `TC-xxx / REQ-xxx` test tags and the pytest JUnit result.

- Generated: 2026-11-14 17:31:54 UTC
- Source commit: `475b820`
- Test results: `report.xml`

## Summary

- 10/17 Must requirements have a passing test
- 23 requirements evaluated (OK: 9, OK (frontend, not in JUnit): 5, NO TEST: 9)
- Test results from report.xml: 132 passed, 0 failed, 0 skipped

## Matrix

| REQ | Priority | Risks | Implemented in | Tests | Status |
| --- | --- | --- | --- | --- | --- |
| REQ-001 | Must | – | `backend/app/ingestion/router.py`<br>`simulator/simulator.py` | TC-001 ×14 (14 passed) | OK |
| REQ-002 | Must | RISK-002 | `backend/app/alarm/engine.py`<br>`backend/app/ingestion/router.py`<br>`backend/app/ingestion/validation.py` | TC-002 ×11, TC-015 ×1 (12 passed) | OK |
| REQ-003 | Must | RISK-001 | `backend/app/alarm/engine.py` | TC-003 ×7, TC-015 ×1 (8 passed) | OK |
| REQ-004 | Must | RISK-003 | – | – | **NO TEST** |
| REQ-005 | Must | RISK-003 | `backend/app/alarm/engine.py`<br>`frontend/src/components/HighAlarmBanner.tsx`<br>`frontend/src/lib/alarms.ts` | TC-005 ×4 (4 frontend) | OK (frontend, not in JUnit) |
| REQ-006 | Must | RISK-004 | – | – | **NO TEST** |
| REQ-007 | Must | RISK-005 | `frontend/src/components/AckControl.tsx`<br>`frontend/src/lib/alarms.ts` | TC-007 ×4 (4 frontend) | OK (frontend, not in JUnit) |
| REQ-008 | Must | RISK-006 | – | – | **NO TEST** |
| REQ-009 | Must | RISK-006 | – | – | **NO TEST** |
| REQ-010 | Must | RISK-007 | `backend/app/ingestion/router.py`<br>`backend/app/storage/crypto.py`<br>`backend/app/storage/repository.py` | TC-010 ×15 (15 passed) | OK |
| REQ-011 | Must | RISK-007 | – | – | **NO TEST** |
| REQ-012 | Must | RISK-001, RISK-002, RISK-003, RISK-004, RISK-005, RISK-006, RISK-007, RISK-008, RISK-009, RISK-010 | `backend/app/hazard/log.py` | TC-012 ×2 (2 passed) | OK |
| REQ-013 | Must | RISK-008 | `backend/app/ingestion/router.py`<br>`backend/app/ingestion/validation.py`<br>`backend/app/storage/repository.py` | TC-001 ×1, TC-013 ×6 (7 passed) | OK |
| REQ-014 | Should | – | `frontend/src/components/VitalChart.tsx`<br>`frontend/src/lib/chart.ts` | TC-014 ×3 (3 frontend) | OK (frontend, not in JUnit) |
| REQ-015 | Must | RISK-005, RISK-009 | `backend/app/alarm/engine.py` | TC-015 ×19 (19 passed) | OK |
| REQ-016 | Must | RISK-010 | `tools/trace/trace.py` | TC-016 ×11 (11 passed) | OK |
| REQ-017 | Optional | – | – | – | **NO TEST** |
| REQ-018 | Should | RISK-003 | – | – | **NO TEST** |
| REQ-019 | Must | RISK-002 | – | – | **NO TEST** |
| REQ-020 | Should | RISK-003 | `backend/app/storage/crypto.py` | TC-020 ×1 (1 passed) | OK |
| REQ-022 | Should | RISK-005 | `frontend/src/components/AckControl.tsx`<br>`frontend/src/components/HighAlarmBanner.tsx` | TC-022 ×2 (2 frontend) | OK (frontend, not in JUnit) |
| REQ-023 | Should | – | `frontend/src/lib/chart.ts`<br>`frontend/src/lib/downsample.ts` | TC-023 ×2 (2 frontend) | OK (frontend, not in JUnit) |
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
| `frontend/src/lib/alarms.test.ts::TC-005 / REQ-005` | TC-005 / REQ-005 | frontend, not in JUnit |
| `frontend/src/lib/alarms.test.ts::TC-005 / REQ-005` | TC-005 / REQ-005 | frontend, not in JUnit |
| `frontend/src/lib/alarms.test.ts::TC-007 / REQ-007` | TC-007 / REQ-007 | frontend, not in JUnit |
| `frontend/src/lib/alarms.test.ts::TC-007 / REQ-007` | TC-007 / REQ-007 | frontend, not in JUnit |
| `frontend/src/lib/chart.test.ts::TC-014 / REQ-014` | TC-014 / REQ-014 | frontend, not in JUnit |
| `frontend/src/lib/chart.test.ts::TC-014 / REQ-014` | TC-014 / REQ-014 | frontend, not in JUnit |
| `frontend/src/lib/chart.test.ts::TC-014 / REQ-014` | TC-014 / REQ-014 | frontend, not in JUnit |
| `frontend/src/lib/downsample.test.ts::TC-023 / REQ-023` | TC-023 / REQ-023 | frontend, not in JUnit |
| `frontend/src/lib/downsample.test.ts::TC-023 / REQ-023` | TC-023 / REQ-023 | frontend, not in JUnit |
| `frontend/src/pages/AlarmsPage.test.tsx::TC-005 / REQ-005` | TC-005 / REQ-005 | frontend, not in JUnit |
| `frontend/src/pages/AlarmsPage.test.tsx::TC-005 / REQ-005` | TC-005 / REQ-005 | frontend, not in JUnit |
| `frontend/src/pages/AlarmsPage.test.tsx::TC-007 / REQ-007` | TC-007 / REQ-007 | frontend, not in JUnit |
| `frontend/src/pages/AlarmsPage.test.tsx::TC-007 / REQ-007` | TC-007 / REQ-007 | frontend, not in JUnit |
| `frontend/src/pages/AlarmsPage.test.tsx::TC-022 / REQ-022` | TC-022 / REQ-022 | frontend, not in JUnit |
| `frontend/src/pages/AlarmsPage.test.tsx::TC-022 / REQ-022` | TC-022 / REQ-022 | frontend, not in JUnit |
| `tests/test_alarm_engine.py::test_alarm_can_be_raised_again_after_values_return_to_normal` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_artefact_does_not_reset_a_running_confirmation` | TC-002 / REQ-002 | passed |
| `tests/test_alarm_engine.py::test_artefact_never_masks_a_critical_value` | TC-015 / REQ-015, REQ-002 | passed |
| `tests/test_alarm_engine.py::test_blood_pressure_has_no_critical_bypass_in_v1` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_change_equal_to_the_limit_is_not_an_artefact` | TC-002 / REQ-002 | passed |
| `tests/test_alarm_engine.py::test_confirmation_count_is_configurable` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_critical_boundaries` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_critical_value_gives_immediate_high` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_custom_artefact_limits` | TC-002 / REQ-002 | passed |
| `tests/test_alarm_engine.py::test_custom_default_thresholds` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_data_loss_alarm_at_10_s_not_at_9_s_and_not_duplicated` | TC-003 / REQ-003 | passed |
| `tests/test_alarm_engine.py::test_data_loss_check_rejects_naive_time` | TC-003 / REQ-003 | passed |
| `tests/test_alarm_engine.py::test_data_loss_is_raised_again_after_data_returned` | TC-003 / REQ-003 | passed |
| `tests/test_alarm_engine.py::test_data_loss_is_tracked_per_patient` | TC-003 / REQ-003 | passed |
| `tests/test_alarm_engine.py::test_data_loss_timeout_is_configurable` | TC-003 / REQ-003 | passed |
| `tests/test_alarm_engine.py::test_engine_rejects_invalid_parameters` | TC-015 / REQ-015, REQ-003 | passed |
| `tests/test_alarm_engine.py::test_events_serialize_with_contract_field_names` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_four_violations_no_alarm_fifth_gives_one_medium` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_inconsistent_thresholds_are_rejected` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_isolated_spike_raises_only_low_events` | TC-002 / REQ-002 | passed |
| `tests/test_alarm_engine.py::test_medium_alarm_is_raised_once_per_episode` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_medium_escalates_to_high_and_high_is_kept_until_normal` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_no_data_loss_without_known_patients` | TC-003 / REQ-003 | passed |
| `tests/test_alarm_engine.py::test_non_critical_boundaries` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_normal_reading_resets_the_counter` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_per_patient_override_changes_the_outcome` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_rate_check_needs_a_recent_previous_reading` | TC-002 / REQ-002 | passed |
| `tests/test_alarm_engine.py::test_reading_rejects_naive_timestamp` | TC-003 / REQ-003 | passed |
| `tests/test_alarm_engine.py::test_spo2_drop_is_flagged_but_rise_is_not` | TC-002 / REQ-002 | passed |
| `tests/test_alarm_engine.py::test_sudden_hr_jump_is_flagged_and_not_counted` | TC-002 / REQ-002 | passed |
| `tests/test_alarm_engine.py::test_threshold_change_keeps_running_confirmation` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_unknown_patient_has_no_active_alarm` | TC-015 / REQ-015 | passed |
| `tests/test_alarm_engine.py::test_vitals_are_confirmed_independently` | TC-015 / REQ-015 | passed |
| `tests/test_ingestion.py::test_boundary_hr_20_and_300_are_accepted` | TC-002 / REQ-002 | passed |
| `tests/test_ingestion.py::test_every_hazard_event_has_required_fields` | TC-012 / REQ-012 | passed |
| `tests/test_ingestion.py::test_hazard_log_maps_every_event_type_to_its_risk` | TC-012 / REQ-012 | passed |
| `tests/test_ingestion.py::test_hr_350_is_invalid_with_hazard_event` | TC-002 / REQ-002 | passed |
| `tests/test_ingestion.py::test_pair_then_post_is_accepted` | TC-013 / REQ-013 | passed |
| `tests/test_ingestion.py::test_patient_id_with_different_name_conflicts` | TC-013 / REQ-013 | passed |
| `tests/test_ingestion.py::test_plausibility_limits_are_inclusive` | TC-002 / REQ-002 | passed |
| `tests/test_ingestion.py::test_readings_query_validation` | TC-001 / REQ-001 | passed |
| `tests/test_ingestion.py::test_repairing_device_to_other_patient_conflicts` | TC-013 / REQ-013 | passed |
| `tests/test_ingestion.py::test_same_pairing_again_is_idempotent` | TC-013 / REQ-013 | passed |
| `tests/test_ingestion.py::test_second_device_for_same_patient_conflicts` | TC-013 / REQ-013 | passed |
| `tests/test_ingestion.py::test_several_violations_give_one_hazard_event` | TC-002 / REQ-002 | passed |
| `tests/test_ingestion.py::test_tampered_reading_gives_clear_error_not_wrong_data` | TC-010 / REQ-010 | passed |
| `tests/test_ingestion.py::test_timestamps_are_stored_in_utc` | TC-001 / REQ-001 | passed |
| `tests/test_ingestion.py::test_unknown_device_is_rejected_with_hazard_event` | TC-013 / REQ-013 | passed |
| `tests/test_ingestion.py::test_valid_reading_stored_and_returned_newest_first` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_artefact_scenario_produces_out_of_range_spikes` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_boundary_scenario_covers_limits` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_deterioration_scenario_trends_down` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_disconnect_scenario_stops_one_device` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_generate_reading_is_deterministic_and_checks_input` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_normal_scenario_stays_inside_non_critical_limits` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_readings_follow_the_data_contract` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_run_against_real_api` | TC-001 / REQ-001, REQ-013 | passed |
| `tests/test_simulator.py::test_run_sends_one_reading_per_patient_per_second` | TC-001 / REQ-001 | passed |
| `tests/test_simulator.py::test_unpaired_scenario_adds_unknown_device` | TC-001 / REQ-001 | passed |
| `tests/test_storage.py::test_blind_index_depends_on_separate_key` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_blind_index_finds_exact_name_not_partial` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_blind_index_handles_turkish_dotted_and_dotless_i` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_blind_index_search_does_not_decrypt_all_rows` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_cipher_uses_fresh_nonce_and_checks_input` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_ciphertext_moved_to_other_patient_raises` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_decrypt_round_trip` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_development_mode_api_works_without_keys` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_encryption_overhead_p95` | TC-020 / REQ-020 | passed |
| `tests/test_storage.py::test_persistent_database_requires_keys` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_raw_database_contains_no_plaintext` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_settings_validate_keys` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_settings_without_keys_use_ephemeral_keys` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_tampered_ciphertext_raises` | TC-010 / REQ-010 | passed |
| `tests/test_storage.py::test_utc_timestamps_survive_storage` | TC-001 / REQ-001 | passed |
| `tests/test_storage.py::test_wrong_key_cannot_decrypt` | TC-010 / REQ-010 | passed |
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
