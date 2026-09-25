from __future__ import annotations

from pathlib import Path
import unittest

from same.music import (
    ByteSourceSegment, Provenance, SegmentedByteSource,
    SegmentedSourceError,
)
from same.music.importers import QtmaDecodeError, decode_qtma_events


ROOT = Path(__file__).resolve().parents[1]
EVENTS = bytes.fromhex(
    (ROOT / "examples/resources/music/qtma_m2_fixture.hex").read_text("ascii")
)


def _segment(start: int, length: int, physical: int) -> ByteSourceSegment:
    return ByteSourceSegment(
        start, length, Provenance("segmented.fixture", byte_offset=physical),
    )


class SegmentedMusicSourceTests(unittest.TestCase):
    def test_gap_overlap_and_incomplete_coverage_fail_closed(self) -> None:
        cases = (
            ((_segment(0, 4, 100), _segment(5, 3, 200)), "coverage_gap"),
            ((_segment(0, 5, 100), _segment(4, 4, 200)), "coverage_overlap"),
            ((_segment(0, 4, 100),), "coverage_gap"),
            ((_segment(0, 9, 100),), "coverage_out_of_bounds"),
        )
        for segments, code in cases:
            with self.subTest(code=code), self.assertRaises(
                SegmentedSourceError,
            ) as caught:
                SegmentedByteSource(
                    bytes(8), Provenance("segmented.fixture"), segments,
                )
            self.assertEqual(caught.exception.code, code)

    def test_qtma_event_cannot_cross_a_source_segment_boundary(self) -> None:
        source = SegmentedByteSource(
            EVENTS, Provenance("segmented.fixture"), (
                _segment(0, 4, 1000),
                _segment(4, len(EVENTS) - 4, 2000),
            ),
        )
        with self.assertRaises(QtmaDecodeError) as caught:
            decode_qtma_events(source, time_scale=125)
        self.assertEqual(caught.exception.code, "framing_crosses_segment")
        self.assertEqual(caught.exception.word_offset, 0)

    def test_resolver_maps_logical_word_to_physical_byte(self) -> None:
        source = SegmentedByteSource(
            bytes(12), Provenance("segmented.fixture", track=7), (
                ByteSourceSegment(
                    0, 4, Provenance(
                        "segmented.fixture", track=7, sample_description=2,
                        byte_offset=900,
                    ),
                ),
                ByteSourceSegment(
                    4, 8, Provenance(
                        "segmented.fixture", track=7, sample_description=2,
                        sample=11, byte_offset=40,
                    ),
                ),
            ),
        )
        resolved = source.resolve(8, 4, word_offset=2)
        self.assertEqual(
            (resolved.track, resolved.sample_description, resolved.sample,
             resolved.byte_offset, resolved.word_offset),
            (7, 2, 11, 44, 2),
        )


if __name__ == "__main__":
    unittest.main()
