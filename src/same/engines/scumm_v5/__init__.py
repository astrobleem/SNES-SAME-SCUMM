"""Native SCUMM v5 engine module for SAME."""

from .engine import ScummV5Engine
from .audio import SameScore, ScummV5AudioAdapter
from .input import ScummV5InputAdapter, ScummV5InputState
from .policy import POLICY_SCHEMA, ScummV5GamePolicy, parse_game_policy
from .resources import LucasartsScummV5ResourceProvider
from .room import ScummV5Room, ScummV5RoomAdapter, ScummV5RoomObject, decode_room
from .text import ScummTextControl, ScummTextGlyph, decode_scumm_v5_text
from .video import ScummV5Charset, ScummV5VideoAdapter, decode_cursor, decode_scene

__all__ = [
    "LucasartsScummV5ResourceProvider",
    "POLICY_SCHEMA",
    "SameScore",
    "ScummV5Engine",
    "ScummV5GamePolicy",
    "ScummV5InputAdapter",
    "ScummV5InputState",
    "ScummV5Room",
    "ScummV5RoomAdapter",
    "ScummV5RoomObject",
    "ScummV5Charset",
    "ScummV5AudioAdapter",
    "ScummV5VideoAdapter",
    "ScummTextControl",
    "ScummTextGlyph",
    "decode_cursor",
    "decode_room",
    "decode_scene",
    "decode_scumm_v5_text",
    "parse_game_policy",
]
