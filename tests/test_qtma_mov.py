from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from same.music import normalize_sequence_time_scale, sequence_trace
from same.music.importers import (
    QtmaMovieError, decode_qtma_events, extract_qtma_movie,
)


ROOT = Path(__file__).resolve().parents[1]
MOV = bytes.fromhex(
    (ROOT / "examples/resources/music/qtma_m13_movie.hex").read_text("ascii")
)
EVENTS = bytes.fromhex(
    (ROOT / "examples/resources/music/qtma_m2_fixture.hex").read_text("ascii")
)


class QtmaMovieTests(unittest.TestCase):
    def test_music_description_and_split_samples_reassemble_exact_events(self) -> None:
        self.assertEqual(len(MOV), 536)
        self.assertEqual(
            hashlib.sha256(MOV).hexdigest(),
            "feb16d388acb55624f53b2dec2e8d76393ce1b5381b1f3d8880e23c74fe78ae1",
        )
        track = extract_qtma_movie(MOV, source="m13.mov")
        self.assertEqual((track.track_index, track.time_scale, track.duration), (0, 125, 600))
        self.assertEqual(len(track.description_events), 184)
        self.assertEqual(
            [(item.index, item.offset, item.size, item.duration, item.description_index)
             for item in track.samples],
            [(0, 44, 28, 150, 1), (1, 72, 20, 450, 1)],
        )
        self.assertEqual(track.event_data, EVENTS)
        extracted = decode_qtma_events(
            track.event_data, source="m13.mov", time_scale=track.time_scale,
        )
        direct = decode_qtma_events(EVENTS, source="m13.mov", time_scale=125)
        self.assertEqual(sequence_trace(extracted), sequence_trace(direct))

    def test_description_and_sample_boundaries_keep_physical_identity(self) -> None:
        track = extract_qtma_movie(MOV, source="m15.mov")
        self.assertEqual(
            (track.description.index, track.description.offset,
             track.description.event_offset, track.description.size),
            (1, 212, 232, 204),
        )
        self.assertEqual(
            [(segment.logical_offset, segment.length,
              segment.provenance.sample_description,
              segment.provenance.sample, segment.provenance.byte_offset)
             for segment in track.event_source.segments],
            [(0, 184, 1, None, 232), (184, 28, 1, 0, 44),
             (212, 20, 1, 1, 72)],
        )
        at_description = track.event_source.resolve(0, 92, word_offset=0)
        at_sample_zero = track.event_source.resolve(184, 4, word_offset=46)
        at_sample_one = track.event_source.resolve(212, 4, word_offset=53)
        self.assertEqual(
            [(item.sample_description, item.sample, item.byte_offset,
              item.word_offset)
             for item in (at_description, at_sample_zero, at_sample_one)],
            [(1, None, 232, 0), (1, 0, 44, 46), (1, 1, 72, 53)],
        )

        sequence = decode_qtma_events(track.event_source, time_scale=125)
        self.assertEqual(
            [(part.part_id, part.provenance.sample,
              part.provenance.byte_offset, part.provenance.word_offset)
             for part in sequence.parts],
            [(0, None, 232, 0), (1, None, 324, 23)],
        )
        first_sample_one = next(
            event for event in sequence.events
            if event.provenance.sample == 1
        )
        self.assertEqual(
            (first_sample_one.provenance.byte_offset,
             first_sample_one.provenance.word_offset),
            (76, 54),
        )

    def test_m14_normalization_retains_segment_and_source_tick(self) -> None:
        movie = bytes.fromhex(
            (ROOT / "examples/resources/music/qtma_m14_movie_600.hex").read_text(
                "ascii"
            )
        )
        track = extract_qtma_movie(movie, source="m14.mov")
        source = decode_qtma_events(
            track.event_source, time_scale=track.time_scale,
        )
        normalized = normalize_sequence_time_scale(
            source, 125, policy="nearest_absolute",
        ).sequence
        boundary_event = next(
            event for event in normalized.events
            if event.provenance.word_offset == 54
        )
        self.assertEqual(
            (boundary_event.tick, boundary_event.provenance.track,
             boundary_event.provenance.sample_description,
             boundary_event.provenance.sample,
             boundary_event.provenance.byte_offset,
             boundary_event.provenance.word_offset,
             boundary_event.provenance.source_tick,
             boundary_event.provenance.source_time_scale),
            (63, 0, 1, 1, 76, 54, 300, 600),
        )

    def test_extended_unknown_atom_is_skipped_by_its_declared_size(self) -> None:
        self.assertEqual(MOV[20:36], bytes.fromhex("00000001776964650000000000000010"))
        self.assertEqual(extract_qtma_movie(MOV).samples[0].offset, 44)

    def test_64_bit_chunk_offsets_resolve_the_same_samples(self) -> None:
        raw = bytearray(MOV)
        stco_type = raw.index(b"stco")
        start = stco_type - 4
        replacement = (
            (24).to_bytes(4, "big") + b"co64" + bytes(4)
            + (1).to_bytes(4, "big") + (44).to_bytes(8, "big")
        )
        raw[start : start + 20] = replacement
        for kind in (b"stbl", b"minf", b"mdia", b"trak", b"moov"):
            atom_start = raw.index(kind) - 4
            size = int.from_bytes(raw[atom_start : atom_start + 4], "big")
            raw[atom_start : atom_start + 4] = (size + 4).to_bytes(4, "big")
        track = extract_qtma_movie(bytes(raw), source="co64.mov")
        self.assertEqual(track.event_data, EVENTS)
        self.assertEqual([sample.offset for sample in track.samples], [44, 72])

    def test_atom_size_sample_offset_flags_and_duration_fail_closed(self) -> None:
        cases: list[tuple[bytes, str]] = []
        bad = bytearray(MOV)
        bad[28:36] = (15).to_bytes(8, "big")
        cases.append((bytes(bad), "invalid_atom_size"))

        bad = bytearray(MOV)
        stco = bad.index(b"stco")
        bad[stco + 12 : stco + 16] = bytes(4)
        cases.append((bytes(bad), "sample_out_of_bounds"))

        bad = bytearray(MOV)
        stsd = bad.index(b"stsd")
        bad[stsd + 28] = 1
        cases.append((bytes(bad), "unsupported_music_flags"))

        bad = bytearray(MOV)
        mdhd = bad.index(b"mdhd")
        bad[mdhd + 20 : mdhd + 24] = (601).to_bytes(4, "big")
        cases.append((bytes(bad), "duration_mismatch"))

        cases.append((MOV[:-1], "atom_out_of_bounds"))
        for raw, code in cases:
            with self.subTest(code=code), self.assertRaises(QtmaMovieError) as caught:
                extract_qtma_movie(raw, source="bad.mov")
            self.assertEqual(caught.exception.code, code)
            self.assertIn("byte", str(caught.exception))

    def test_missing_track_and_unaligned_sample_are_rejected(self) -> None:
        with self.assertRaises(QtmaMovieError) as caught:
            extract_qtma_movie(MOV, music_track=1)
        self.assertEqual(caught.exception.code, "missing_music_track")

        bad = bytearray(MOV)
        stsz = bad.index(b"stsz")
        bad[stsz + 16 : stsz + 20] = (27).to_bytes(4, "big")
        with self.assertRaises(QtmaMovieError) as caught:
            extract_qtma_movie(bytes(bad))
        self.assertEqual(caught.exception.code, "unaligned_qtma_data")


if __name__ == "__main__":
    unittest.main()
