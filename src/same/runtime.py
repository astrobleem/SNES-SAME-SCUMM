"""Host-side SAME frame simulation.

This is not a SNES emulator.  It validates target declarations, packet routing,
input edges, task order, and budget behavior before target code is assembled.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .abi import (
    AudioOpcode,
    DebugOpcode,
    Endpoint,
    InputOpcode,
    KernelOpcode,
    Service,
    TimeOpcode,
    VideoOpcode,
)
from .events import EventBus
from .input import PhysicalController, profile
from .scheduler import Affinity, FrameContext, FrameReport, FrameScheduler, Phase, Task
from .target import TargetManifest, load_target


@dataclass(slots=True)
class BackendState:
    backdrop: int = 0
    music_track: int | None = None
    sfx_events: list[dict[str, int]] = field(default_factory=list)
    traces: list[dict[str, int | str]] = field(default_factory=list)
    service_counts: dict[str, int] = field(default_factory=dict)

    def dispatch(self, packet: object) -> None:
        service_name = packet.service_name
        self.service_counts[service_name] = self.service_counts.get(service_name, 0) + 1
        if packet.service == Service.VIDEO and packet.opcode == VideoOpcode.SET_BACKDROP:
            self.backdrop = packet.arg0 & 0x7FFF
        elif packet.service == Service.AUDIO and packet.opcode == AudioOpcode.MUSIC_PLAY:
            self.music_track = packet.arg0 & 0xFFFF
        elif packet.service == Service.AUDIO and packet.opcode == AudioOpcode.MUSIC_STOP:
            self.music_track = None
        elif packet.service == Service.AUDIO and packet.opcode == AudioOpcode.SFX_PLAY:
            self.sfx_events.append({"id": packet.arg0 & 0xFFFF, "parameters": packet.arg1})
        elif packet.service == Service.DEBUG:
            self.traces.append(packet.to_dict())


class SameRuntime:
    def __init__(self, target: TargetManifest, event_capacity: int = 64) -> None:
        self.target = target
        self.events = EventBus(event_capacity)
        self.scheduler = FrameScheduler()
        self.controller = PhysicalController()
        self.input_profile = profile(target.input_profile)
        self.backend = BackendState()
        self.state: dict[str, object] = {
            "guest_ticks": {},
            "last_input_word": 0,
            "last_logical": {"held": [], "pressed": [], "released": []},
        }
        self._input_word = 0
        self._install_tasks()

    @classmethod
    def from_path(cls, path: Path, event_capacity: int = 64) -> "SameRuntime":
        return cls(load_target(path), event_capacity)

    def _install_tasks(self) -> None:
        def begin(context: FrameContext, budget: int) -> int:
            self.events.emit(
                service=Service.TIME,
                opcode=TimeOpcode.FRAME_TICK,
                arg0=context.frame,
                source=Endpoint.KERNEL,
            )
            return 1

        self.scheduler.register(
            Task("same.begin", phase=Phase.BEGIN_FRAME, affinity=Affinity.HOST, budget=8, callback=begin, priority=0)
        )

        def input_task(context: FrameContext, budget: int) -> int:
            physical = self.controller.update(self._input_word)
            logical = self.input_profile.map_snapshot(physical)
            self.state["last_input_word"] = physical.held
            self.state["last_logical"] = logical.to_dict()
            if physical.pressed or physical.released or context.frame == 0:
                self.events.emit(
                    service=Service.INPUT,
                    opcode=InputOpcode.SNAPSHOT,
                    arg0=physical.held,
                    arg1=((physical.pressed & 0xFFFF) << 16)
                    | (physical.released & 0xFFFF),
                    source=Endpoint.SCPU,
                )
            return 8

        self.scheduler.register(
            Task("same.input", phase=Phase.INPUT, affinity=Affinity.SCPU, budget=32, callback=input_task, priority=0)
        )

        for lane in self.target.lanes:
            def lane_callback(
                context: FrameContext,
                budget: int,
                lane_name: str = lane.name,
                lane_phase: str = lane.phase.name,
            ) -> int:
                guest_ticks = self.state["guest_ticks"]
                assert isinstance(guest_ticks, dict)
                guest_ticks[lane_name] = int(guest_ticks.get(lane_name, 0)) + 1
                # The host model consumes a deterministic fraction.  Real target gates
                # replace this callback with measured execution.
                consumed = max(1, min(budget, (len(lane_name) * 17 + context.frame) % budget + 1))
                if lane_phase == "TRANSLATE" and context.frame == 0:
                    self.events.emit(
                        service=Service.VIDEO,
                        opcode=VideoOpcode.SET_BACKDROP,
                        arg0=0x001F,
                        source=Endpoint.TARGET,
                    )
                if lane_phase == "AUDIO" and context.frame == 0:
                    self.events.emit(
                        service=Service.AUDIO,
                        opcode=AudioOpcode.MUSIC_PLAY,
                        arg0=1,
                        source=Endpoint.TARGET,
                        destination=Endpoint.SPC,
                    )
                if context.frame and context.frame % 60 == 0:
                    self.events.emit(
                        service=Service.KERNEL,
                        opcode=KernelOpcode.HEARTBEAT,
                        arg0=context.frame,
                        arg1=sum(ord(ch) for ch in lane_name),
                        source=Endpoint.TARGET,
                    )
                return consumed

            self.scheduler.register(
                Task(
                    lane.name,
                    phase=lane.phase,
                    affinity=lane.affinity,
                    budget=lane.budget,
                    callback=lane_callback,
                    priority=lane.priority,
                    period=lane.period,
                )
            )

        def commit(context: FrameContext, budget: int) -> int:
            consumed = 0
            for packet in self.events.ring.drain(maximum=budget):
                self.backend.dispatch(packet)
                consumed += 1
            return consumed

        self.scheduler.register(
            Task("same.commit", phase=Phase.COMMIT, affinity=Affinity.SCPU, budget=64, callback=commit, priority=65535)
        )

        def end(context: FrameContext, budget: int) -> int:
            if self.events.ring.snapshot():
                self.events.emit(
                    service=Service.DEBUG,
                    opcode=DebugOpcode.COUNTER,
                    arg0=len(self.events.ring),
                    source=Endpoint.KERNEL,
                )
            return 1

        self.scheduler.register(
            Task("same.end", phase=Phase.END_FRAME, affinity=Affinity.HOST, budget=8, callback=end, priority=65535)
        )

    def run_frame(self, frame: int, input_word: int = 0) -> FrameReport:
        self._input_word = input_word & 0xFFFF
        context = FrameContext(frame=frame, state=self.state, events=self.events)
        return self.scheduler.run_frame(context)

    def simulate(self, frames: int, input_words: Iterable[int] = ()) -> dict[str, object]:
        if frames <= 0:
            raise ValueError("frames must be positive")
        words = list(input_words)
        reports = [
            self.run_frame(frame, words[frame] if frame < len(words) else 0)
            for frame in range(frames)
        ]
        return {
            "target": self.target.to_dict(),
            "frames": frames,
            "scheduler": self.scheduler.describe(),
            "frame_reports": [
                {
                    "frame": report.frame,
                    "consumed": report.consumed,
                    "overruns": [asdict(task) for task in report.overruns],
                    "tasks": [asdict(task) for task in report.tasks],
                }
                for report in reports
            ],
            "state": self.state,
            "backend": {
                "backdrop": self.backend.backdrop,
                "music_track": self.backend.music_track,
                "sfx_events": self.backend.sfx_events,
                "traces": self.backend.traces,
                "service_counts": self.backend.service_counts,
            },
            "event_queue": {
                "remaining": len(self.events.ring),
                "next_sequence": self.events.next_sequence,
                "stats": asdict(self.events.ring.stats),
            },
        }
