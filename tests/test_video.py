from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from same.video import (
    CursorState,
    DirtyRegion,
    HostEvidenceBackend,
    IndexedSurface,
    PixelFormat,
    PresentRecord,
    PresentRequest,
    Rect,
    VideoService,
)


class SpyVideoBackend:
    def __init__(self) -> None:
        self.requests: list[PresentRequest] = []
        self.host = HostEvidenceBackend()

    def present(self, request: PresentRequest) -> PresentRecord:
        self.requests.append(request)
        return self.host.present(request)


class FailingVideoBackend:
    def present(self, request: PresentRequest) -> PresentRecord:
        raise RuntimeError("synthetic present failure")


class VideoTests(unittest.TestCase):
    def test_default_and_explicit_host_backends_are_record_identical(self) -> None:
        default = VideoService(4, 3)
        explicit_backend = HostEvidenceBackend()
        explicit = VideoService(4, 3, backend=explicit_backend)
        self.assertIsInstance(default.backend, HostEvidenceBackend)
        self.assertIs(explicit.backend, explicit_backend)
        for video in (default, explicit):
            video.fill(7, Rect(1, 1, 2, 2))
            video.set_palette(7, ((1, 2, 3),))
        self.assertEqual(default.present(19), explicit.present(19))
        self.assertEqual(default.generation, 1)
        self.assertEqual(explicit.generation, 1)

    def test_spy_backend_receives_exact_ephemeral_request_without_copy(self) -> None:
        backend = SpyVideoBackend()
        video = VideoService(4, 3, backend=backend)
        video.present(4)
        video.fill(2, Rect(1, 1, 2, 1))
        video.move_cursor(3, 2)
        video.show_cursor(True)
        before_hash = video.surface.hash()
        record = video.present(5)

        self.assertEqual(len(backend.requests), 2)
        request = backend.requests[-1]
        self.assertIs(request.surface, video.surface)
        self.assertIs(request.cursor, video.cursor)
        self.assertIsInstance(request.dirty, tuple)
        self.assertEqual(request.dirty, (Rect(1, 1, 2, 1),))
        self.assertEqual((request.frame, request.generation), (5, 1))
        self.assertEqual(record, PresentRecord(5, 1, before_hash, request.dirty))
        self.assertEqual(video._dirty.rects, ())

        # A request retains its immutable rectangle snapshot even after future
        # service mutations; cursor remains the synchronous current object.
        video.set_pixel(0, 0, 9)
        self.assertEqual(request.dirty, (Rect(1, 1, 2, 1),))
        self.assertEqual(video._dirty.rects, (Rect(0, 0, 1, 1),))

    def test_backend_failure_preserves_dirty_history_generation_and_pixels(self) -> None:
        video = VideoService(4, 3, backend=FailingVideoBackend())
        video.fill(6, Rect(1, 1, 2, 2))
        pending = video._dirty.rects
        pixels = video.surface.visible_bytes()
        framebuffer_hash = video.surface.hash()
        with self.assertRaisesRegex(RuntimeError, "synthetic present failure"):
            video.present(8)
        self.assertEqual(video._dirty.rects, pending)
        self.assertEqual(video.presented, [])
        self.assertEqual(video.generation, 0)
        self.assertEqual(video.surface.visible_bytes(), pixels)
        self.assertEqual(video.surface.hash(), framebuffer_hash)

        video.backend = HostEvidenceBackend()
        record = video.present(9)
        self.assertEqual(record.dirty, pending)
        self.assertEqual(video._dirty.rects, ())
        self.assertEqual(video.present(10).dirty, ())

    def test_cursor_is_backend_state_but_not_framebuffer_or_dirty_state(self) -> None:
        backend = SpyVideoBackend()
        video = VideoService(4, 3, backend=backend)
        video.present(0)
        before_hash = video.surface.hash()
        video.define_cursor(bytes((0, 1, 1, 0)), 2, 2, transparent_index=0)
        video.move_cursor(3, 2)
        video.show_cursor(True)
        record = video.present(1)
        self.assertEqual(record.sha256, before_hash)
        self.assertEqual(record.dirty, ())
        self.assertIs(backend.requests[-1].cursor, video.cursor)
        self.assertEqual((video.cursor.x, video.cursor.y, video.cursor.visible), (3, 2, True))

    def test_logical_mutation_does_not_enter_backend_dirty_request(self) -> None:
        backend = SpyVideoBackend()
        video = VideoService(4, 3, backend=backend)
        video.present(0)
        logical = IndexedSurface(4, 3)
        logical.fill(4)
        logical.set_pixel(1, 2, 8)
        logical.set_palette(8, ((1, 2, 3),))
        video.present(1)
        self.assertEqual(backend.requests[-1].dirty, ())

    def test_legacy_surface_has_explicit_tight_owned_layout(self) -> None:
        first = IndexedSurface(320, 200)
        second = IndexedSurface(320, 200)
        self.assertEqual((first.width, first.height, first.pitch), (320, 200, 320))
        self.assertIs(first.format, PixelFormat.INDEX8)
        self.assertFalse(first.readonly)
        self.assertIsInstance(first.pixels, bytearray)
        self.assertEqual(len(first.pixels), 320 * 200)
        self.assertEqual(len(first.palette), 256)
        self.assertIsNot(first.palette, second.palette)
        self.assertFalse(hasattr(first, "_dirty"))
        self.assertFalse(hasattr(first, "consume_dirty"))
        self.assertFalse(hasattr(first, "mark_dirty"))

    def test_writable_padded_wrapped_surface_preserves_padding(self) -> None:
        backing = bytearray((0xCC,)) * (12 * 3)
        surface = IndexedSurface.wrap(8, 3, 12, backing)
        self.assertIs(surface.pixels, backing)
        self.assertEqual(surface.pitch, 12)
        self.assertIs(surface.format, PixelFormat.INDEX8)
        self.assertFalse(surface.readonly)

        self.assertEqual(surface.fill(0), Rect(0, 0, 8, 3))
        self.assertEqual(surface.visible_bytes(), bytes(8 * 3))
        for y in range(3):
            self.assertEqual(backing[y * 12 + 8 : y * 12 + 12], bytes((0xCC,)) * 4)

        self.assertEqual(surface.set_pixel(7, 2, 9), Rect(7, 2, 1, 1))
        self.assertEqual(backing[2 * 12 + 7], 9)
        self.assertEqual(surface.fill(5, Rect(-2, 1, 5, 3)), Rect(0, 1, 3, 2))
        self.assertEqual(
            surface.visible_bytes(),
            bytes(8)
            + bytes((5, 5, 5, 0, 0, 0, 0, 0))
            + bytes((5, 5, 5, 0, 0, 0, 0, 9)),
        )
        for y in range(3):
            self.assertEqual(backing[y * 12 + 8 : y * 12 + 12], bytes((0xCC,)) * 4)

    def test_immutable_wrapped_surface_mutations_fail_transactionally(self) -> None:
        original = bytes(range(16))
        surface = IndexedSurface.wrap(8, 2, 8, original)
        self.assertTrue(surface.readonly)
        self.assertIs(surface.pixels, original)

        with self.assertRaisesRegex(TypeError, "surface pixel storage is read-only"):
            surface.set_pixel(0, 0, 7)
        with self.assertRaisesRegex(TypeError, "surface pixel storage is read-only"):
            surface.fill(3)
        with self.assertRaisesRegex(TypeError, "surface pixel storage is read-only"):
            surface.fill(4, Rect(1, 0, 3, 1))
        self.assertEqual(original, bytes(range(16)))

    def test_wrapped_surface_accepts_byte_memoryview_without_copying(self) -> None:
        backing = bytearray((1, 2, 3, 0xCC, 4, 5, 6, 0xCC))
        supplied = memoryview(backing)
        surface = IndexedSurface.wrap(3, 2, 4, supplied)
        self.assertIs(surface.pixels, supplied)
        surface.set_pixel(2, 1, 9)
        self.assertEqual(backing, bytearray((1, 2, 3, 0xCC, 4, 5, 9, 0xCC)))
        self.assertEqual(surface.visible_bytes(), bytes((1, 2, 3, 4, 5, 9)))

    def test_wrapped_palette_is_validated_and_shared(self) -> None:
        palette = [(0, 0, 0)] * 256
        surface = IndexedSurface.wrap(1, 1, 1, bytearray(1), palette=palette)
        self.assertIs(surface.palette, palette)
        surface.set_palette(3, ((1, 2, 3),))
        self.assertEqual(palette[3], (1, 2, 3))

    def test_wrapped_layout_and_palette_validation_fail_closed(self) -> None:
        valid_palette = [(0, 0, 0)] * 256
        cases = (
            ((0, 1, 1, bytearray(1)), {}, ValueError),
            ((1, 0, 1, bytearray(1)), {}, ValueError),
            ((-1, 1, 1, bytearray(1)), {}, ValueError),
            ((1, -1, 1, bytearray(1)), {}, ValueError),
            ((2, 1, 1, bytearray(2)), {}, ValueError),
            ((2, 2, 2, bytearray(3)), {}, ValueError),
            ((1, 1, 1, object()), {}, TypeError),
            ((1, 1, 1, memoryview(bytearray(4)).cast("H")), {}, TypeError),
            ((1, 1, 1, bytearray(1)), {"palette": valid_palette[:-1]}, ValueError),
            (
                (1, 1, 1, bytearray(1)),
                {"palette": valid_palette[:-1] + [(0, 0, 256)]},
                ValueError,
            ),
        )
        for arguments, keywords, error in cases:
            with self.subTest(arguments=arguments, keywords=keywords):
                with self.assertRaises(error):
                    IndexedSurface.wrap(*arguments, **keywords)

    def test_padded_and_tight_surfaces_have_identical_legacy_hash(self) -> None:
        tight = IndexedSurface(3, 2)
        tight.pixels[:] = bytes((1, 2, 3, 4, 5, 6))
        padded_storage = bytearray((1, 2, 3, 0xCC, 0xCC, 4, 5, 6, 0xCC, 0xCC))
        padded = IndexedSurface.wrap(3, 2, 5, padded_storage, palette=tight.palette)
        self.assertEqual(tight.visible_bytes(), padded.visible_bytes())
        self.assertEqual(tight.hash(), padded.hash())
        padded_storage[3:5] = b"\xAA\xBB"
        padded_storage[8:10] = b"\xDD\xEE"
        self.assertEqual(tight.hash(), padded.hash())

    def test_raw_blit_uses_source_and_destination_pitch(self) -> None:
        source = bytes((1, 2, 3, 0xAA, 0xAA, 4, 5, 6, 0xBB, 0xBB))
        destination_storage = bytearray((0xCC,)) * (8 * 4)
        destination = IndexedSurface.wrap(5, 4, 8, destination_storage)
        changed = destination.blit(
            source,
            source_width=3,
            source_height=2,
            source_pitch=5,
            x=1,
            y=1,
        )
        self.assertEqual(changed, Rect(1, 1, 3, 2))
        self.assertEqual(destination_storage[9:12], bytes((1, 2, 3)))
        self.assertEqual(destination_storage[17:20], bytes((4, 5, 6)))
        for y in range(4):
            self.assertEqual(destination_storage[y * 8 + 5 : y * 8 + 8], b"\xCC" * 3)
        self.assertEqual(source[3:5], b"\xAA\xAA")
        self.assertEqual(source[8:10], b"\xBB\xBB")

    def test_raw_keyed_blit_clips_with_both_pitches(self) -> None:
        storage = bytearray((0xCC,)) * (5 * 3)
        destination = IndexedSurface.wrap(3, 3, 5, storage)
        destination.fill(9)
        changed = destination.blit(
            bytes((1, 0, 2, 0xEE, 3, 4, 0, 0xEE)),
            source_width=3,
            source_height=2,
            source_pitch=4,
            x=-1,
            y=1,
            transparent_index=0,
        )
        self.assertEqual(changed, Rect(0, 1, 2, 2))
        self.assertEqual(destination.visible_bytes(), bytes((9, 9, 9, 9, 2, 9, 4, 9, 9)))
        for y in range(3):
            self.assertEqual(storage[y * 5 + 3 : y * 5 + 5], b"\xCC\xCC")

        changed = destination.blit(
            bytes(4),
            source_width=2,
            source_height=2,
            x=1,
            y=0,
            transparent_index=0,
        )
        self.assertEqual(changed, Rect(1, 0, 2, 2))

    def test_blit_surface_reads_padded_readonly_source_without_copying_palette(self) -> None:
        source_palette = [(1, 2, 3)] * 256
        source_storage = bytes((1, 2, 3, 0xAA, 0xAA, 4, 5, 6, 0xBB, 0xBB))
        source = IndexedSurface.wrap(3, 2, 5, source_storage, palette=source_palette)
        destination_palette = [(9, 8, 7)] * 256
        destination_storage = bytearray((0xCC,)) * (6 * 3)
        destination = IndexedSurface.wrap(
            4, 3, 6, destination_storage, palette=destination_palette
        )
        destination.fill(0)
        changed = destination.blit_surface(source, x=1, y=1)
        self.assertEqual(changed, Rect(1, 1, 3, 2))
        self.assertEqual(destination.visible_bytes(), bytes((0, 0, 0, 0, 0, 1, 2, 3, 0, 4, 5, 6)))
        self.assertFalse(hasattr(source, "consume_dirty"))
        self.assertIs(destination.palette, destination_palette)
        self.assertIsNot(destination.palette, source.palette)
        self.assertEqual(source_storage[3:5], b"\xAA\xAA")
        self.assertEqual(source_storage[8:10], b"\xBB\xBB")
        for y in range(3):
            self.assertEqual(destination_storage[y * 6 + 4 : y * 6 + 6], b"\xCC\xCC")

    def test_blit_surface_source_then_destination_clipping_order(self) -> None:
        source = IndexedSurface(4, 3)
        source.pixels[:] = bytes(range(1, 13))

        exact = IndexedSurface(10, 5)
        changed = exact.blit_surface(source, source_rect=Rect(-1, 0, 4, 2), x=5, y=1)
        self.assertEqual(changed, Rect(6, 1, 3, 2))
        self.assertEqual(exact.visible_bytes()[16:19], bytes((1, 2, 3)))
        self.assertEqual(exact.visible_bytes()[26:29], bytes((5, 6, 7)))

        cases = (
            (Rect(0, -1, 2, 3), 1, 1, Rect(1, 2, 2, 2)),
            (Rect(2, 0, 4, 2), 1, 1, Rect(1, 1, 2, 2)),
            (Rect(0, 2, 2, 3), 1, 1, Rect(1, 1, 2, 1)),
            (Rect(0, 0, 4, 3), -2, 0, Rect(0, 0, 2, 3)),
            (Rect(0, 0, 4, 3), 0, -1, Rect(0, 0, 4, 2)),
            (Rect(0, 0, 4, 3), 6, 0, Rect(6, 0, 2, 3)),
            (Rect(0, 0, 4, 3), 0, 4, Rect(0, 4, 4, 1)),
        )
        for source_rect, x, y, expected in cases:
            with self.subTest(source_rect=source_rect, x=x, y=y):
                destination = IndexedSurface(8, 5)
                self.assertEqual(
                    destination.blit_surface(source, source_rect=source_rect, x=x, y=y),
                    expected,
                )

        destination = IndexedSurface(8, 5)
        self.assertIsNone(
            destination.blit_surface(source, source_rect=Rect(-5, 0, 2, 2), x=0, y=0)
        )
        self.assertIsNone(destination.blit_surface(source, x=20, y=0))

    def test_keyed_blit_surface_accepts_readonly_source_and_source_rect(self) -> None:
        source = IndexedSurface.wrap(
            3,
            2,
            4,
            bytes((1, 0, 2, 0xEE, 3, 4, 0, 0xEE)),
        )
        destination = IndexedSurface(3, 3)
        destination.fill(9)
        changed = destination.blit_surface(
            source,
            source_rect=Rect(0, 0, 3, 2),
            x=-1,
            y=1,
            transparent_index=0,
        )
        self.assertEqual(changed, Rect(0, 1, 2, 2))
        self.assertEqual(destination.visible_bytes(), bytes((9, 9, 9, 9, 2, 9, 4, 9, 9)))

    def test_blit_surface_readonly_destination_fails_transactionally(self) -> None:
        source = IndexedSurface(2, 2)
        source.fill(7)
        destination = IndexedSurface.wrap(3, 3, 3, bytes(range(9)))
        before = destination.visible_bytes()
        with self.assertRaisesRegex(TypeError, "surface pixel storage is read-only"):
            destination.blit_surface(source, x=1, y=1)
        self.assertEqual(destination.visible_bytes(), before)

    def test_blit_surface_snapshots_overlapping_storage(self) -> None:
        surface = IndexedSurface(6, 1)
        surface.pixels[:] = bytes((1, 2, 3, 4, 5, 6))
        changed = surface.blit_surface(surface, source_rect=Rect(0, 0, 4, 1), x=2)
        self.assertEqual(changed, Rect(2, 0, 4, 1))
        self.assertEqual(surface.visible_bytes(), bytes((1, 2, 1, 2, 3, 4)))

    def test_padded_surface_pillow_conversion_excludes_padding(self) -> None:
        palette = [(index, index, index) for index in range(256)]
        tight = IndexedSurface(3, 2)
        tight.palette[:] = palette
        tight.pixels[:] = bytes((1, 2, 3, 4, 5, 6))
        padded = IndexedSurface.wrap(
            3,
            2,
            5,
            bytearray((1, 2, 3, 0xCC, 0xCC, 4, 5, 6, 0xDD, 0xDD)),
            palette=palette,
        )
        tight_image = tight.to_image()
        padded_image = padded.to_image()
        self.assertEqual((padded_image.mode, padded_image.size), ("P", (3, 2)))
        self.assertEqual(padded_image.tobytes(), bytes((1, 2, 3, 4, 5, 6)))
        self.assertEqual(tight_image.tobytes(), padded_image.tobytes())
        tight_png = BytesIO()
        padded_png = BytesIO()
        tight_image.save(tight_png, format="PNG")
        padded_image.save(padded_png, format="PNG")
        self.assertEqual(tight_png.getvalue(), padded_png.getvalue())

    def test_surface_mutations_return_clipped_memory_rectangles(self) -> None:
        surface = IndexedSurface(8, 6)
        self.assertEqual(surface.set_pixel(2, 3, 7), Rect(2, 3, 1, 1))
        self.assertEqual(surface.fill(3, Rect(-4, 2, 10, 3)), Rect(0, 2, 6, 3))
        self.assertIsNone(surface.fill(1, Rect(20, 20, 2, 2)))
        self.assertEqual(
            surface.blit(bytes((1, 2, 3, 4)), source_width=2, source_height=2, x=7, y=5),
            Rect(7, 5, 1, 1),
        )
        self.assertFalse(hasattr(surface, "consume_dirty"))

    def test_legacy_hash_stream_and_cursor_exclusion_are_exact(self) -> None:
        surface = IndexedSurface(3, 2)
        surface.set_palette(1, [(1, 2, 3), (250, 128, 64)])
        surface.pixels[:] = bytes((0, 1, 2, 2, 1, 0))
        serialized = (
            (3).to_bytes(2, "little")
            + (2).to_bytes(2, "little")
            + b"".join(bytes(rgb) for rgb in surface.palette)
            + bytes((0, 1, 2, 2, 1, 0))
        )
        expected = "04500d0905c9df798d76366bc7af0ed507b4f8693ad9f7d35188957cffbea63b"
        self.assertEqual(len(serialized), 778)
        self.assertEqual(sha256(serialized).hexdigest(), expected)
        self.assertEqual(surface.hash(), expected)

        cursor = CursorState(
            width=2,
            height=2,
            x=1,
            y=1,
            visible=True,
            transparent_index=0,
            pixels=bytes((0, 2, 2, 0)),
        )
        surface.to_image(cursor)
        self.assertEqual(surface.hash(), expected)

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

    def test_negative_fill_and_pitched_blit_clipping_are_exact(self) -> None:
        surface = IndexedSurface(5, 4)
        surface.fill(9)

        surface.fill(1, Rect(-2, -1, 4, 3))
        self.assertEqual(
            bytes(surface.pixels),
            bytes((1, 1, 9, 9, 9, 1, 1, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9, 9)),
        )

        source = bytes(
            (
                10, 11, 12, 13, 0xEE, 0xEE,
                20, 21, 22, 23, 0xEE, 0xEE,
                30, 31, 32, 33, 0xEE, 0xEE,
            )
        )
        surface.blit(
            source,
            source_width=4,
            source_height=3,
            source_pitch=6,
            x=-1,
            y=2,
        )
        self.assertEqual(
            bytes(surface.pixels),
            bytes((1, 1, 9, 9, 9, 1, 1, 9, 9, 9, 11, 12, 13, 9, 9, 21, 22, 23, 9, 9)),
        )

    def test_pitched_keyed_blit_is_exact(self) -> None:
        surface = IndexedSurface(5, 4)
        surface.fill(9)
        surface.blit(
            bytes((0, 1, 2, 0xEE, 3, 0, 4, 0xEE)),
            source_width=3,
            source_height=2,
            source_pitch=4,
            x=1,
            y=1,
            transparent_index=0,
        )
        self.assertEqual(
            bytes(surface.pixels),
            bytes((9, 9, 9, 9, 9, 9, 9, 1, 2, 9, 9, 3, 9, 4, 9, 9, 9, 9, 9, 9)),
        )

    def test_present_consumes_dirty_rects(self) -> None:
        video = VideoService(16, 16)
        initial = video.present(6)
        self.assertEqual(initial.dirty, (Rect(0, 0, 16, 16),))
        video.fill(4, Rect(2, 3, 5, 6))
        record = video.present(7)
        self.assertEqual(record.frame, 7)
        self.assertEqual(record.dirty, (Rect(2, 3, 5, 6),))
        self.assertEqual(video.present(8).dirty, ())

    def test_dirty_region_preserves_order_duplicates_and_tuple_contract(self) -> None:
        dirty = DirtyRegion()
        first = Rect(5, 2, 3, 4)
        second = Rect(0, 0, 1, 1)
        dirty.add(first)
        dirty.add(second)
        dirty.add(None)
        dirty.add(first)
        self.assertEqual(dirty.rects, (first, second, first))
        consumed = dirty.consume()
        self.assertIsInstance(consumed, tuple)
        self.assertEqual(consumed, (first, second, first))
        self.assertEqual(dirty.consume(), ())

    def test_initial_and_ordered_dirty_sequence_is_exact(self) -> None:
        video = VideoService(4, 3)
        video.fill(1, Rect(-1, 1, 3, 3))
        video.blit(
            bytes((2, 3, 4, 5)),
            source_width=2,
            source_height=2,
            x=3,
            y=-1,
        )
        video.set_palette(1, ((10, 20, 30),))
        video.set_pixel(2, 2, 5)
        video.define_cursor(bytes((0, 6, 6, 0)), 2, 2, transparent_index=0)
        video.move_cursor(3, 2)
        video.show_cursor(True)

        record = video.present(11)
        self.assertEqual(
            record.dirty,
            (
                Rect(0, 0, 4, 3),
                Rect(0, 1, 2, 2),
                Rect(3, 0, 1, 1),
                Rect(0, 0, 4, 3),
                Rect(2, 2, 1, 1),
            ),
        )
        self.assertEqual(video.present(12).dirty, ())

    def test_display_facade_tracks_every_operation_in_exact_order(self) -> None:
        video = VideoService(6, 5)
        source = IndexedSurface(2, 2)
        source.pixels[:] = bytes((7, 8, 9, 10))
        self.assertEqual(video.fill(1, Rect(-2, 1, 4, 2)), Rect(0, 1, 2, 2))
        self.assertEqual(video.set_pixel(3, 2, 4), Rect(3, 2, 1, 1))
        self.assertEqual(
            video.blit(bytes((5, 6)), source_width=2, source_height=1, x=5, y=0),
            Rect(5, 0, 1, 1),
        )
        self.assertEqual(video.blit_surface(source, x=1, y=3), Rect(1, 3, 2, 2))
        video.set_palette(2, ((1, 2, 3),))
        self.assertEqual(video.mark_dirty(Rect(-1, 4, 3, 2)), Rect(0, 4, 2, 1))
        self.assertEqual(
            video.present(0).dirty,
            (
                Rect(0, 0, 6, 5),
                Rect(0, 1, 2, 2),
                Rect(3, 2, 1, 1),
                Rect(5, 0, 1, 1),
                Rect(1, 3, 2, 2),
                Rect(0, 0, 6, 5),
                Rect(0, 4, 2, 1),
            ),
        )

    def test_display_facade_ignores_clipped_noops(self) -> None:
        video = VideoService(4, 3)
        video.present(0)
        self.assertIsNone(video.fill(3, Rect(-100, -100, 2, 2)))
        self.assertIsNone(
            video.blit(bytes((1,)), source_width=1, source_height=1, x=20, y=20)
        )
        self.assertEqual(video.present(1).dirty, ())

    def test_all_transparent_display_blit_keeps_bounding_invalidation(self) -> None:
        video = VideoService(4, 3)
        video.present(0)
        before = video.surface.visible_bytes()
        changed = video.blit(
            bytes(4),
            source_width=2,
            source_height=2,
            x=1,
            y=1,
            transparent_index=0,
        )
        self.assertEqual(changed, Rect(1, 1, 2, 2))
        self.assertEqual(video.surface.visible_bytes(), before)
        self.assertEqual(video.present(1).dirty, (Rect(1, 1, 2, 2),))

    def test_display_palette_validation_is_transactional(self) -> None:
        video = VideoService(4, 3)
        video.present(0)
        before = list(video.surface.palette)
        with self.assertRaisesRegex(ValueError, "palette write exceeds"):
            video.set_palette(255, ((1, 2, 3), (4, 5, 6)))
        self.assertEqual(video.surface.palette, before)
        self.assertEqual(video.present(1).dirty, ())
        video.set_palette(255, ((1, 2, 3),))
        self.assertEqual(video.present(2).dirty, (Rect(0, 0, 4, 3),))

    def test_cursor_changes_do_not_dirty_display(self) -> None:
        video = VideoService(4, 3)
        video.present(0)
        video.define_cursor(bytes((0, 1, 1, 0)), 2, 2, transparent_index=0)
        video.move_cursor(3, 2)
        video.show_cursor(True)
        self.assertEqual(video.present(1).dirty, ())

    def test_logical_surface_mutations_do_not_dirty_display(self) -> None:
        video = VideoService(4, 3)
        logical = IndexedSurface(4, 3)
        logical.fill(1)
        logical.set_pixel(2, 1, 3)
        logical.blit(bytes((4, 5)), source_width=2, source_height=1, x=0, y=2)
        logical.set_palette(0, ((7, 8, 9),))
        self.assertEqual(video.present(0).dirty, (Rect(0, 0, 4, 3),))
        self.assertEqual(video.present(1).dirty, ())

    def test_failed_readonly_display_mutation_does_not_dirty(self) -> None:
        video = VideoService(3, 3)
        video.present(0)
        video.surface = IndexedSurface.wrap(3, 3, 3, bytes(range(9)))
        before = video.surface.visible_bytes()
        with self.assertRaisesRegex(TypeError, "surface pixel storage is read-only"):
            video.set_pixel(0, 0, 7)
        self.assertEqual(video.surface.visible_bytes(), before)
        self.assertEqual(video.present(1).dirty, ())

    def test_png_output(self) -> None:
        video = VideoService(4, 4)
        video.set_palette(0, [(0, 0, 0), (255, 255, 255)])
        video.fill(1)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "frame.png"
            video.write_png(path)
            with Image.open(path) as image:
                self.assertEqual(image.size, (4, 4))

    def test_png_bytes_with_and_without_cursor_are_exact(self) -> None:
        video = VideoService(4, 3)
        video.set_palette(
            0,
            ((0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)),
        )
        video.surface.pixels[:] = bytes((1, 1, 1, 1, 1, 2, 2, 1, 1, 3, 3, 1))
        video.define_cursor(bytes((0, 2, 2, 0)), 2, 2, transparent_index=0)
        video.move_cursor(1, 1)
        video.show_cursor(True)
        framebuffer_hash = video.surface.hash()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            without_cursor = root / "without-cursor.png"
            with_cursor = root / "with-cursor.png"
            video.write_png(without_cursor, include_cursor=False)
            video.write_png(with_cursor, include_cursor=True)
            self.assertEqual(
                sha256(without_cursor.read_bytes()).hexdigest(),
                "fbb97dd8d61c7a192ae147b67abbb61fccafca206309e77834012aa2fce8dcf2",
            )
            self.assertEqual(
                sha256(with_cursor.read_bytes()).hexdigest(),
                "86214297f8274d9ef7da46cb0bf67234595c0c1a29e2d9c6fe6d970c48fe6347",
            )
            with Image.open(without_cursor) as image:
                self.assertEqual((image.mode, image.size), ("P", (4, 3)))
            with Image.open(with_cursor) as image:
                self.assertEqual((image.mode, image.size), ("RGBA", (4, 3)))
        self.assertEqual(video.surface.hash(), framebuffer_hash)


if __name__ == "__main__":
    unittest.main()
