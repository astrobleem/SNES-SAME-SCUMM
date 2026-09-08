"""Replaceable source-device performance models."""

from .scumm_adlib import (
    AdlibCaptureCalibration, AdlibPatch, ScummV5AdlibDevice,
    extract_scumm_adlib_patches,
)

__all__ = (
    "AdlibCaptureCalibration", "AdlibPatch", "ScummV5AdlibDevice",
    "extract_scumm_adlib_patches",
)
