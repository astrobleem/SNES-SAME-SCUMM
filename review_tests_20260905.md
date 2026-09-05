# Focused review tests

Source-only tests are in `tests/test_scumm_v5_engine.py`:

- `test_headless_fixture_retains_logical_message_lifetime_without_presentation`
- `test_headless_long_encoded_text_keeps_logical_cursor_and_controls`
- `test_headless_long_talk_begin_preserves_logical_lifetime`
- `test_talk_continuation_preserves_frame_caller_width_abi`
- `test_scheduler_saves_the_selected_slot_after_nested_execution`
- `test_scheduler_reasserts_byte_index_width_before_each_slot_scan`
- `test_sentence_fetch_witness_resets_per_launch`

Command:

`PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q`

Result: 122 tests passed. `git diff --check` and
`python3 -m py_compile tools/validate_scumm_startup42_nexen.py` also pass.

The ROM and runtime report are intentionally excluded from this review branch.
