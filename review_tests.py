"""Screened focused assertions for the headless Talk lifecycle review."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent


def test_fixture_uses_logical_talk_lifecycle_without_presentation():
    runtime = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
    matrix = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
    done = runtime.split("ScummV5_Op_Print__text_done:", 1)[1]
    done = done.split("ScummV5_Op_Print__text_no_talk:", 1)[0]
    fixture_prefix = done.split(".if SAME_BUILD_SCUMM_M23A", 1)[0]
    assert "SAME_SCUMM_C23_MESSAGE_COUNT" not in fixture_prefix
    assert "SAME_SCUMM_TALK_ACTIVE" not in fixture_prefix
    assert "ScummV5_Talk_Begin_Far" in done
    assert "ScummV5_Talk_FrameBegin_Far" in matrix
    assert "ScummV5_Talk_FrameEnd_Far" in matrix


def test_wait_for_message_is_checked_after_logical_completion():
    runtime = (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text()
    matrix = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
    assert "ScummV5_Op_Wait__message" in runtime
    assert "SAME_SCUMM_TALK_ACTIVE" in runtime
    assert "ScummV5_Talk_Stop_Far" in matrix
    assert "SAME_SCUMM_TALK_HAVE_MSG" in matrix
