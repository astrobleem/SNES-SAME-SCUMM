"""Opt-in access to a user-provided Fate demo corpus for integration tests."""

from __future__ import annotations

import os
from pathlib import Path
import unittest


def require_fate_demo_archive(testcase: unittest.TestCase) -> Path:
    """Return the configured corpus or skip only when none was requested."""
    configured = os.environ.get("SAME_FATE_DEMO_ARCHIVE")
    if configured is None:
        testcase.skipTest(
            "optional Fate demo integration: set SAME_FATE_DEMO_ARCHIVE to run"
        )
    path = Path(configured).expanduser()
    testcase.assertTrue(
        path.is_file(),
        f"SAME_FATE_DEMO_ARCHIVE was set but is not a file: {path}",
    )
    return path
