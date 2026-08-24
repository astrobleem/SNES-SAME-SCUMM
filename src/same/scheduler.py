"""A deterministic frame scheduler shared by host tests and the 65816 design."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable


class Phase(IntEnum):
    BEGIN_FRAME = 0
    INPUT = 1
    GUEST = 2
    TRANSLATE = 3
    AUDIO = 4
    COMMIT = 5
    END_FRAME = 6


class Affinity(IntEnum):
    HOST = 0
    SCPU = 1
    SA1 = 2
    SPC = 3


TaskCallback = Callable[["FrameContext", int], int]


@dataclass(slots=True)
class FrameContext:
    frame: int
    state: dict[str, Any]
    events: Any


@dataclass(slots=True)
class Task:
    name: str
    phase: Phase
    affinity: Affinity
    budget: int
    callback: TaskCallback
    priority: int = 100
    period: int = 1
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 48:
            raise ValueError("task name must contain 1..48 characters")
        if self.budget <= 0:
            raise ValueError(f"task {self.name}: budget must be positive")
        if self.period <= 0:
            raise ValueError(f"task {self.name}: period must be positive")


@dataclass(slots=True)
class TaskRun:
    name: str
    phase: str
    affinity: str
    budget: int
    consumed: int
    overrun: int


@dataclass(slots=True)
class FrameReport:
    frame: int
    tasks: list[TaskRun] = field(default_factory=list)

    @property
    def overruns(self) -> list[TaskRun]:
        return [task for task in self.tasks if task.overrun]

    @property
    def consumed(self) -> int:
        return sum(task.consumed for task in self.tasks)


class FrameScheduler:
    """Static, deterministic task ordering.

    SAME v1 intentionally does not dynamically move tasks between processors.  A
    target manifest chooses an affinity; measurement can justify a later change.
    """

    def __init__(self) -> None:
        self._tasks: list[Task] = []
        self._names: set[str] = set()

    def register(self, task: Task) -> None:
        if task.name in self._names:
            raise ValueError(f"duplicate task name: {task.name}")
        self._names.add(task.name)
        self._tasks.append(task)
        self._tasks.sort(key=lambda item: (int(item.phase), item.priority, item.name))

    def task(self, name: str) -> Task:
        for task in self._tasks:
            if task.name == name:
                return task
        raise KeyError(name)

    def run_frame(self, context: FrameContext) -> FrameReport:
        report = FrameReport(frame=context.frame)
        for task in self._tasks:
            if not task.enabled or context.frame % task.period:
                continue
            consumed = int(task.callback(context, task.budget))
            if consumed < 0:
                raise ValueError(f"task {task.name} returned negative consumption")
            report.tasks.append(
                TaskRun(
                    name=task.name,
                    phase=task.phase.name,
                    affinity=task.affinity.name,
                    budget=task.budget,
                    consumed=consumed,
                    overrun=max(0, consumed - task.budget),
                )
            )
        return report

    def describe(self) -> list[dict[str, int | str | bool]]:
        return [
            {
                "name": task.name,
                "phase": task.phase.name,
                "affinity": task.affinity.name,
                "budget": task.budget,
                "priority": task.priority,
                "period": task.period,
                "enabled": task.enabled,
            }
            for task in self._tasks
        ]
