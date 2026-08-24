"""Physical SNES controller sampling and target-specific logical mappings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
from typing import Mapping


class SnesButton(IntFlag):
    NONE = 0
    B = 0x8000
    Y = 0x4000
    SELECT = 0x2000
    START = 0x1000
    UP = 0x0800
    DOWN = 0x0400
    LEFT = 0x0200
    RIGHT = 0x0100
    A = 0x0080
    X = 0x0040
    L = 0x0020
    R = 0x0010


@dataclass(frozen=True, slots=True)
class PhysicalSnapshot:
    held: int
    pressed: int
    released: int


class PhysicalController:
    def __init__(self) -> None:
        self._held = 0

    @property
    def held(self) -> int:
        return self._held

    def update(self, word: int) -> PhysicalSnapshot:
        word &= 0xFFF0
        previous = self._held
        self._held = word
        return PhysicalSnapshot(
            held=word,
            pressed=word & ~previous,
            released=previous & ~word,
        )


@dataclass(frozen=True, slots=True)
class LogicalSnapshot:
    held: frozenset[str]
    pressed: frozenset[str]
    released: frozenset[str]

    def to_dict(self) -> dict[str, list[str]]:
        return {
            "held": sorted(self.held),
            "pressed": sorted(self.pressed),
            "released": sorted(self.released),
        }


@dataclass(frozen=True, slots=True)
class InputProfile:
    name: str
    actions: Mapping[str, int]

    def map_snapshot(self, physical: PhysicalSnapshot) -> LogicalSnapshot:
        def active(word: int) -> frozenset[str]:
            return frozenset(
                action for action, mask in self.actions.items() if word & int(mask)
            )

        return LogicalSnapshot(
            held=active(physical.held),
            pressed=active(physical.pressed),
            released=active(physical.released),
        )


PROFILES: dict[str, InputProfile] = {
    "snes": InputProfile(
        "snes",
        {button.name.lower(): int(button) for button in SnesButton if button},
    ),
    "genesis_3button": InputProfile(
        "genesis_3button",
        {
            "up": SnesButton.UP,
            "down": SnesButton.DOWN,
            "left": SnesButton.LEFT,
            "right": SnesButton.RIGHT,
            "a": SnesButton.Y,
            "b": SnesButton.B,
            "c": SnesButton.A,
            "start": SnesButton.START,
        },
    ),
    "arcade_2button": InputProfile(
        "arcade_2button",
        {
            "up": SnesButton.UP,
            "down": SnesButton.DOWN,
            "left": SnesButton.LEFT,
            "right": SnesButton.RIGHT,
            "button1": int(SnesButton.B | SnesButton.Y),
            "button2": int(SnesButton.A | SnesButton.X),
            "coin": SnesButton.SELECT,
            "start": SnesButton.START,
        },
    ),
    "scumm": InputProfile(
        "scumm",
        {
            "up": SnesButton.UP,
            "down": SnesButton.DOWN,
            "left": SnesButton.LEFT,
            "right": SnesButton.RIGHT,
            "pointer_primary": SnesButton.B,
            "pointer_secondary": SnesButton.A,
            "skip": SnesButton.X,
            "menu": SnesButton.START,
            "pause": SnesButton.SELECT,
        },
    ),
    "agi": InputProfile(
        "agi",
        {
            "up": SnesButton.UP,
            "down": SnesButton.DOWN,
            "left": SnesButton.LEFT,
            "right": SnesButton.RIGHT,
            "accept": SnesButton.B,
            "cancel": SnesButton.A,
            "menu": SnesButton.START,
            "pause": SnesButton.SELECT,
        },
    ),
    "openbor": InputProfile(
        "openbor",
        {
            "up": SnesButton.UP,
            "down": SnesButton.DOWN,
            "left": SnesButton.LEFT,
            "right": SnesButton.RIGHT,
            "attack": SnesButton.Y,
            "jump": SnesButton.B,
            "special": SnesButton.A,
            "attack2": SnesButton.X,
            "start": SnesButton.START,
            "select": SnesButton.SELECT,
        },
    ),
}


def profile(name: str) -> InputProfile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise KeyError(f"unknown input profile {name!r}; choices: {', '.join(PROFILES)}") from exc
