"""SCUMM logical input state fed exclusively by SAME input events."""

from __future__ import annotations

from dataclasses import dataclass, field

from ...services import InputEvent, InputEventType

_BUTTON_ACTIONS = {
    "pointer_primary": "primary",
    "pointer_secondary": "secondary",
    "pointer0": "primary",
    "pointer1": "secondary",
}
_COMMAND_ACTIONS = {"skip", "menu", "pause"}


@dataclass(slots=True)
class ScummV5InputState:
    frame: int = -1
    cursor_x: int = 0
    cursor_y: int = 0
    held_buttons: set[str] = field(default_factory=set)
    pressed_buttons: set[str] = field(default_factory=set)
    released_buttons: set[str] = field(default_factory=set)
    commands: list[str] = field(default_factory=list)
    text: list[str] = field(default_factory=list)
    quit_requested: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "frame": self.frame,
            "cursor": [self.cursor_x, self.cursor_y],
            "held_buttons": sorted(self.held_buttons),
            "pressed_buttons": sorted(self.pressed_buttons),
            "released_buttons": sorted(self.released_buttons),
            "commands": list(self.commands),
            "text": list(self.text),
            "quit_requested": self.quit_requested,
        }


class ScummV5InputAdapter:
    """Translate portable SAME events into SCUMM-family logical input."""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("SCUMM logical input dimensions must be positive")
        self.width = width
        self.height = height
        self.state = ScummV5InputState(cursor_x=width // 2, cursor_y=height // 2)

    def begin_frame(self, frame: int) -> None:
        if frame == self.state.frame:
            return
        self.state.frame = frame
        self.state.pressed_buttons.clear()
        self.state.released_buttons.clear()
        self.state.commands.clear()
        self.state.text.clear()
        self.state.quit_requested = False

    def clear_clicked_status(self) -> None:
        """Clear transient click/key edges without releasing held buttons."""
        self.state.pressed_buttons.clear()
        self.state.released_buttons.clear()
        self.state.commands.clear()
        self.state.text.clear()

    def _clamp(self) -> None:
        self.state.cursor_x = max(0, min(self.width - 1, self.state.cursor_x))
        self.state.cursor_y = max(0, min(self.height - 1, self.state.cursor_y))

    def _button(self, button: str, pressed: bool) -> None:
        if pressed:
            if button not in self.state.held_buttons:
                self.state.pressed_buttons.add(button)
            self.state.held_buttons.add(button)
        else:
            if button in self.state.held_buttons:
                self.state.released_buttons.add(button)
            self.state.held_buttons.discard(button)

    def consume(self, event: InputEvent) -> ScummV5InputState:
        self.begin_frame(event.frame)
        if event.type is InputEventType.POINTER_MOVE:
            self.state.cursor_x = int(event.x)
            self.state.cursor_y = int(event.y)
            self._clamp()
        elif event.type is InputEventType.POINTER_BUTTON:
            button = _BUTTON_ACTIONS.get(event.action)
            if button is not None:
                self._button(button, event.pressed)
        elif event.type is InputEventType.DIGITAL:
            button = _BUTTON_ACTIONS.get(event.action)
            if button is not None:
                self._button(button, event.pressed)
            elif event.pressed and event.action in {"left", "right", "up", "down"}:
                self.state.cursor_x += 2 * ((event.action == "right") - (event.action == "left"))
                self.state.cursor_y += 2 * ((event.action == "down") - (event.action == "up"))
                self._clamp()
            elif event.pressed and event.action in _COMMAND_ACTIONS:
                self.state.commands.append(event.action)
        elif event.type is InputEventType.TEXT:
            if event.text:
                self.state.text.append(event.text)
        elif event.type is InputEventType.QUIT:
            self.state.quit_requested = True
        return self.state
