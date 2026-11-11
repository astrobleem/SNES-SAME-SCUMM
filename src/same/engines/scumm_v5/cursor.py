"""Original host implementation of the generic DOS v5 built-in cursor contract.

Semantic reference: ScummVM engines/scumm/cursor.cpp resetCursors,
setBuiltinCursor and animateCursor; script_v5.cpp o5_cursorCommand.
Shapes below are constructed from geometric strokes, not copied renderer code.
Platform-specific cursors and Loom glyph/hotspot redefinitions are unsupported.

publish_cursor consumes existing C7 state and VideoService. Its position is an
already projected SCREEN-space hotspot, not the upper-left of the bitmap.
The shape stays 16x16, with an unscaled pixel hotspot. Room aspect-fit/camera
projection belongs to the caller; this module must not apply it a second time.
animation_index counts cursor-animation calls, not wall time or assumed FPS.
The interpreter retains responsibility for variable 52/53 writes and save state.
"""
from __future__ import annotations

from typing import Protocol, Sequence

from ...errors import EngineExecutionError
from ...video import VideoService


HOTSPOTS = ((8, 7), (8, 7), (1, 1), (5, 0))
COLORS = (15, 15, 7, 8)
TRANSPARENT = 255


class CursorState(Protocol):
    cursor_id: int
    cursor_state: int
    user_input_state: int
    cursor_visible: bool
    cursor_image: tuple[int, int]
    cursor_hotspot: tuple[int, int, int]


def _masks() -> tuple[bytes, ...]:
    shapes = [bytearray(256) for _ in range(4)]

    def stroke(shape: int, y: int, xs) -> None:
        for x in xs:
            shapes[shape][y * 16 + x] = 1

    # Crosshair: a one-pixel gap around the pointing center.
    for y in (*range(6), *range(9, 15)):
        stroke(0, y, (8,))
    stroke(0, 7, (*range(1, 7), *range(10, 16)))
    # Hourglass frame and the accumulated sand in its lower half.
    for y in (1, 13):
        stroke(1, y, range(1, 15))
    for y in range(2, 7):
        xs = (y - 1, y, 15 - y, 16 - y)
        stroke(1, y, xs)
        stroke(1, 14 - y, xs)
    stroke(1, 7, range(6, 10))
    for y in range(10, 13):
        stroke(1, y, range(17 - y, y - 1))
    # Arrow head, notch, and diagonal stem.
    for y in range(1, 9):
        stroke(2, y, range(1, y + 1))
    for y, xs in ((9, (*range(1, 5), 8, 9)), (10, range(1, 6)),
                  (11, (1, 5, 6)), (12, (5, 6)), (13, (6, 7)),
                  (14, (6, 7)), (15, (7, 8))):
        stroke(2, y, xs)
    # Raised index finger, three knuckles, thumb and palm outline.
    stroke(3, 0, range(3, 7))
    for y in range(1, 5):
        stroke(3, y, (3, 6))
    stroke(3, 5, (3, *range(6, 16)))
    for y in (6, 7, 8):
        stroke(3, y, (3, 6, 9, 12, 15))
    stroke(3, 8, range(3))
    for y in range(9, 12):
        stroke(3, y, (0, 3, 15))
    for y in range(12, 15):
        stroke(3, y, (0, 15))
    stroke(3, 15, range(16))
    return tuple(bytes(shape) for shape in shapes)


MASKS = _masks()


def _cursor_id(value: int) -> int:
    if type(value) is not int or not 0 <= value < 4:
        raise EngineExecutionError('v5 built-in cursor ID must be 0..3')
    return value


def cursor_pixels(cursor_id: int, *, animation_index: int = 0) -> bytes:
    """Return row-major INDEX8; color changes every two animation calls."""
    index = _cursor_id(cursor_id)
    if type(animation_index) is not int or animation_index < 0:
        raise EngineExecutionError('cursor animation index must be a nonnegative integer')
    color = COLORS[(animation_index // 2) & 3]
    return bytes(color if covered else TRANSPARENT for covered in MASKS[index])


def apply_cursor_command(state: CursorState, subop: int, values: Sequence[int] = ()) -> bool:
    """Apply already decoded C7 cursor operands; False delegates charset 13/14.

    Call before the interpreter mirrors state to variables 52/53. Unsupported
    redefinitions fail before mutating state, including a zero-valued override.
    """
    if subop in (13, 14):
        return False
    if subop in (10, 11):
        raise EngineExecutionError('v5 glyph/hotspot cursor overrides are unsupported')
    if subop not in (1, 2, 3, 4, 5, 6, 7, 8, 12):
        raise EngineExecutionError(f'unsupported v5 cursor command {subop}')
    if len(values) != (1 if subop == 12 else 0):
        raise EngineExecutionError('incorrect v5 cursor command operand count')
    if subop == 12:
        state.cursor_id = _cursor_id(values[0])
    elif subop in (1, 2):
        state.cursor_state = int(subop == 1)
    elif subop in (3, 4):
        state.user_input_state = int(subop == 3)
    elif subop in (5, 6):
        state.cursor_state += 1 if subop == 5 else -1
    else:
        state.user_input_state += 1 if subop == 7 else -1
    state.cursor_visible = state.cursor_state > 0
    return True


def publish_cursor(state: CursorState, video: VideoService, *, screen_x: int,
                   screen_y: int, animation_index: int = 0) -> None:
    """Connect existing C7 selection/visibility to the existing host service.

    Nondefault legacy override witnesses are rejected rather than ignored.
    Use apply_cursor_command to reject all new override requests (even zeros).
    No PRESENT is issued; publication remains the enclosing frame's job.
    """
    if state.cursor_image != (0, 0) or state.cursor_hotspot != (0, 0, 0):
        raise EngineExecutionError('stored cursor overrides are unsupported')
    pixels = cursor_pixels(state.cursor_id, animation_index=animation_index)
    hx, hy = HOTSPOTS[state.cursor_id]
    video.define_cursor(pixels, 16, 16, hotspot_x=hx, hotspot_y=hy,
                        transparent_index=TRANSPARENT)
    video.move_cursor(screen_x, screen_y)
    video.show_cursor(state.cursor_state > 0)
