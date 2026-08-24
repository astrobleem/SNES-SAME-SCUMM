from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from same.video import IndexedSurface, Rect, VideoService


class VideoTests(unittest.TestCase):
    def test_fill_blit_transparency_and_hash(self) -> None:
        surface = IndexedSurface(8, 8)
        surface.fill(2)
        surface.blit(
            bytes([0, 3, 3, 0]),
            source_width=2,
            source_height=2,
            x=3,
            y=3,
            transparent_index=0,
        )
        self.assertEqual(surface.pixels[3 * 8 + 3], 2)
        self.assertEqual(surface.pixels[3 * 8 + 4], 3)
        self.assertEqual(len(surface.hash()), 64)

    def test_present_consumes_dirty_rects(self) -> None:
        video = VideoService(16, 16)
        video.surface.consume_dirty()
        video.surface.fill(4, Rect(2, 3, 5, 6))
        record = video.present(7)
        self.assertEqual(record.frame, 7)
        self.assertEqual(record.dirty, (Rect(2, 3, 5, 6),))
        self.assertEqual(video.surface.consume_dirty(), ())

    def test_png_output(self) -> None:
        video = VideoService(4, 4)
        video.surface.set_palette(0, [(0, 0, 0), (255, 255, 255)])
        video.surface.fill(1)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "frame.png"
            video.write_png(path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (4, 4))


if __name__ == "__main__":
    unittest.main()
