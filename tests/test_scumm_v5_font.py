from __future__ import annotations

import unittest

from same.engines.scumm_v5.font import GLYPH_COUNT, decode_charset, encode_charset
from same.errors import ResourceError


def _copyright_free_charset() -> bytes:
    # Native v5 CHAR: max width, height, 256 little-endian glyph offsets,
    # followed by one deliberately tiny glyph at code 65.  Remaining entries
    # are absent.  This exercises the real source decoder and cooked schema.
    header = bytearray(4 + 15 + 256 * 4)
    offset = len(header)
    header[19 + 65 * 4:23 + 65 * 4] = offset.to_bytes(4, "little")
    # advance, width, height, x origin, y origin, then 1bpp MSB-first rows.
    result = header + bytes((3, 2, 0, 0, 0xA0))
    result[0:4] = len(result).to_bytes(4, "little")
    return bytes(result)


class ScummV5FontTests(unittest.TestCase):
    def test_complete_record_round_trip_and_source_identity(self) -> None:
        source = _copyright_free_charset()
        raw = encode_charset(source, logical_id=0, source_id=1)
        record = decode_charset(raw, expected_logical_id=0)
        self.assertEqual(len(record.glyphs), GLYPH_COUNT)
        self.assertEqual(record.source_length, len(source))
        glyph = record.glyphs[65]
        self.assertIsNotNone(glyph)
        assert glyph is not None
        self.assertEqual((glyph.advance, glyph.width, glyph.height), (3, 3, 2))
        self.assertEqual(glyph.pixels, bytes((1, 0, 1, 0, 0, 0)))

    def test_record_validation_is_fail_closed(self) -> None:
        raw = bytearray(encode_charset(_copyright_free_charset(), logical_id=0,
                                       source_id=1))
        raw[0] ^= 1
        with self.assertRaises(ResourceError):
            decode_charset(bytes(raw))


if __name__ == "__main__":
    unittest.main()
