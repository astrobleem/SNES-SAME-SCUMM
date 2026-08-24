"""Structured SCUMM v5 text byte streams shared by semantics and rendering."""

from __future__ import annotations

from dataclasses import dataclass

from ...errors import ResourceError


_CONTROL_CODES_WITHOUT_ARGUMENTS = frozenset((1, 2, 3, 8))


@dataclass(frozen=True, slots=True)
class ScummTextGlyph:
    code: int

    def to_dict(self) -> dict[str, object]:
        return {"kind": "glyph", "code": self.code}


@dataclass(frozen=True, slots=True)
class ScummTextControl:
    code: int
    arguments: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {"kind": "control", "code": self.code, "arguments": list(self.arguments)}


ScummTextToken = ScummTextGlyph | ScummTextControl


def decode_scumm_v5_text(data: bytes | bytearray) -> tuple[ScummTextToken, ...]:
    """Decode a terminated v5 message without interpreting renderer policy."""

    raw = bytes(data)
    tokens: list[ScummTextToken] = []
    offset = 0
    while offset < len(raw):
        value = raw[offset]
        offset += 1
        if value == 0:
            return tuple(tokens)
        if value != 0xFF:
            tokens.append(ScummTextGlyph(value))
            continue
        if offset >= len(raw):
            raise ResourceError("SCUMM text ends after an $FF control marker")
        code = raw[offset]
        offset += 1
        argument_count = 0 if code in _CONTROL_CODES_WITHOUT_ARGUMENTS else 2
        if offset + argument_count > len(raw):
            raise ResourceError(f"SCUMM text control ${code:02X} is truncated")
        arguments = tuple(raw[offset : offset + argument_count])
        offset += argument_count
        tokens.append(ScummTextControl(code, arguments))
    raise ResourceError("SCUMM text has no zero terminator")


def control_argument_count(code: int) -> int:
    """Return the number of encoded argument bytes following an $FF control."""

    return 0 if code in _CONTROL_CODES_WITHOUT_ARGUMENTS else 2
