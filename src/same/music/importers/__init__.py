"""Source-format importers that terminate at SAME's canonical music IR."""

from .qtma import QtmaDecodeError, decode_qtma_events
from .qtma_mov import (
    QtmaMovieDescription, QtmaMovieError, QtmaMovieSample, QtmaMusicTrack,
    extract_qtma_movie,
)
from .scumm_imuse import (
    ScummImuseImportError, ScummImuseTimeline, import_scumm_adlib_sequence,
)

__all__ = (
    "QtmaDecodeError", "QtmaMovieDescription", "QtmaMovieError",
    "QtmaMovieSample", "QtmaMusicTrack",
    "ScummImuseImportError", "ScummImuseTimeline", "decode_qtma_events",
    "extract_qtma_movie", "import_scumm_adlib_sequence",
)
