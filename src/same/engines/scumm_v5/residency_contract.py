"""Compiler-side model of selector residency and canonical SCUMM identity.

This module is deliberately not imported by the production SNES runtime. It
consumes the compiler's selector-free directory and simulates a possible
binding contract for analysis, tests, and backend design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
from typing import Any, Iterable, Mapping


# Mirror the accepted backend allocator policy exactly. Reserved fixture IDs
# occupy $00-$4D; the allocator's candidate pool starts at $4E and is disjoint.
PRIMARY_SELECTOR_VALUES = tuple(range(0xD0, 0x100))
OVERFLOW_SELECTOR_VALUES = tuple(range(0xCF, 0x4D, -1))
DEFAULT_SELECTOR_POOL = PRIMARY_SELECTOR_VALUES + OVERFLOW_SELECTOR_VALUES
RESERVED_SELECTOR_VALUES = frozenset(range(0x00, 0x4E))
if (len(DEFAULT_SELECTOR_POOL) != 178
        or len(set(DEFAULT_SELECTOR_POOL)) != 178
        or set(DEFAULT_SELECTOR_POOL) & RESERVED_SELECTOR_VALUES):
    raise RuntimeError("SCUMM selector pool no longer matches backend allocator policy")


class PinReason(StrEnum):
    ACTIVE_SCRIPT_SLOT = "ACTIVE_SCRIPT_SLOT"
    YIELDED_SCRIPT = "YIELDED_SCRIPT"
    NESTED_PARENT = "NESTED_PARENT"
    ROOM_CONTINUATION = "ROOM_CONTINUATION"
    CUTSCENE_OVERRIDE = "CUTSCENE_OVERRIDE"
    ROOM_LIFECYCLE = "ROOM_LIFECYCLE"
    SENTENCE_EXECUTION = "SENTENCE_EXECUTION"
    SAVE_RESTORE_RECONSTRUCTION = "SAVE_RESTORE_RECONSTRUCTION"


class ResidencyError(RuntimeError):
    """Base class for explicit resolver-contract failures."""


class ResidencyExhausted(ResidencyError):
    """All available selectors are pinned or otherwise non-evictable."""


class UnknownProgramUnit(ResidencyError):
    """A canonical identity is absent from the compiler directory."""


class UnknownBundle(ResidencyError):
    """A bundle identity is absent from the compiler directory."""


class StaleSelectorReference(ResidencyError):
    """A byte selector/generation no longer denotes its original unit."""


class ActivationCapacityExhausted(ResidencyError):
    """The modeled VM activation-slot capacity has been reached."""


@dataclass(frozen=True, order=True, slots=True)
class ProgramUnitIdentity:
    """Stable compiler-owned identity; never a selector or ROM address."""

    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True, slots=True)
class BundleIdentity:
    """Compiler resource/loading group identity."""

    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, order=True, slots=True)
class Selector:
    """Temporary byte handle used by the current VM dispatch ABI."""

    value: int

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 0xFF:
            raise ValueError("selector must be an unsigned byte")

    @property
    def hex(self) -> str:
        return f"${self.value:02X}"

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True)
class DirectoryUnit:
    identity: ProgramUnitIdentity
    bundle: BundleIdentity
    local_index: int
    kind: str
    owner: Mapping[str, Any] = field(default_factory=dict)
    dispatch_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SelectorReference:
    """A diagnostic handle that detects selector reuse via generation."""

    program_unit: ProgramUnitIdentity
    selector: Selector
    generation: int


@dataclass(frozen=True, slots=True)
class Pin:
    token: str
    program_unit: ProgramUnitIdentity
    reason: str
    owner: str | None
    managed: bool


@dataclass(frozen=True, slots=True)
class ResidentBinding:
    program_unit: ProgramUnitIdentity
    selector: Selector
    generation: int
    pin_reasons: tuple[str, ...]
    last_used: int


@dataclass(slots=True)
class Activation:
    activation_id: str
    program_unit: ProgramUnitIdentity
    pc: int
    locals: tuple[int, ...]
    parent_activation_id: str | None
    room_ownership: str | None
    yielded: bool
    reference: SelectorReference
    activation_pin: Pin
    parent_pin: Pin | None = None
    yielded_pin: Pin | None = None
    extra_pins: list[Pin] = field(default_factory=list)
    order: int = 0


@dataclass(frozen=True, slots=True)
class Continuation:
    continuation_id: str
    program_unit: ProgramUnitIdentity
    reason: str
    activation_id: str | None
    pin: Pin


@dataclass(slots=True)
class _Binding:
    identity: ProgramUnitIdentity
    selector: Selector
    generation: int
    last_used: int


class ResolverDirectory:
    """Validated view of `selector_directory.json` with canonical identities."""

    def __init__(self, units: Mapping[str, DirectoryUnit],
                 bundles: Mapping[str, Iterable[str]],
                 global_scripts: Mapping[int, str]) -> None:
        self.units = dict(units)
        self.bundles = {key: tuple(value) for key, value in bundles.items()}
        self.global_scripts = dict(global_scripts)
        self.room_bundles: dict[int, str] = {}
        if len(self.units) != sum(len(value) for value in self.bundles.values()):
            raise ValueError("each SelectorUnit must occur in exactly one bundle")
        for number, identity in self.global_scripts.items():
            unit = self.units.get(identity)
            if unit is None or unit.kind != "GLOBAL":
                raise ValueError(f"global script {number} maps to invalid SelectorUnit {identity}")
        for bundle_name, unit_names in self.bundles.items():
            room_numbers = {self.units[name].owner.get("room")
                            for name in unit_names
                            if name in self.units
                            and self.units[name].kind != "GLOBAL"
                            and self.units[name].owner.get("room") is not None}
            if len(room_numbers) > 1:
                raise ValueError(f"bundle {bundle_name} spans multiple rooms")
            if room_numbers:
                room_number = int(next(iter(room_numbers)))
                if room_number in self.room_bundles:
                    raise ValueError(f"duplicate room bundle for room {room_number}")
                self.room_bundles[room_number] = bundle_name

    @classmethod
    def from_selector_directory(cls, document: Mapping[str, Any]) -> "ResolverDirectory":
        if document.get("selector_values_emitted") is not False:
            raise ValueError("resolver input must be selector-free")
        bundles: dict[str, tuple[str, ...]] = {}
        units: dict[str, DirectoryUnit] = {}
        global_scripts: dict[int, str] = {}
        for bundle_row in document.get("bundles", []):
            bundle_name = str(bundle_row["identity"])
            if bundle_name in bundles:
                raise ValueError(f"duplicate bundle identity: {bundle_name}")
            unit_rows = sorted(bundle_row.get("selector_units", []),
                               key=lambda item: int(item["local_bundle_index"]))
            identities = []
            for expected_index, row in enumerate(unit_rows):
                if int(row["local_bundle_index"]) != expected_index:
                    raise ValueError(f"non-contiguous local indices in {bundle_name}")
                if any(key in row for key in ("selector", "selector_value", "selector_id")):
                    raise ValueError("selector-free directory contains a selector value")
                identity = str(row["selector_unit_identity"])
                if identity in units:
                    raise ValueError(f"duplicate SelectorUnit identity: {identity}")
                kind = str(row["kind"])
                unit = DirectoryUnit(
                    ProgramUnitIdentity(identity), BundleIdentity(bundle_name),
                    expected_index, kind, dict(row.get("owner", {})),
                    dict(row.get("dispatch_metadata", {})),
                )
                units[identity] = unit
                identities.append(identity)
                if kind == "GLOBAL":
                    lookup = unit.dispatch_metadata.get("lookup_key", {})
                    if "script_number" not in lookup:
                        raise ValueError(f"global unit lacks script number: {identity}")
                    number = int(lookup["script_number"])
                    if number in global_scripts:
                        raise ValueError(f"duplicate global script number: {number}")
                    global_scripts[number] = identity
            bundles[bundle_name] = tuple(identities)
        if not bundles:
            raise ValueError("selector directory has no bundles")
        return cls(units, bundles, global_scripts)

    @classmethod
    def from_units(cls, bundle_units: Mapping[str, Iterable[str]], *,
                   kinds: Mapping[str, str] | None = None,
                   global_script_numbers: Mapping[int, str] | None = None) -> "ResolverDirectory":
        """Construct a small deterministic directory for copyright-free tests."""
        unit_kinds = kinds or {}
        units: dict[str, DirectoryUnit] = {}
        bundles: dict[str, tuple[str, ...]] = {}
        for bundle, identities in sorted(bundle_units.items()):
            names = tuple(identities)
            if len(set(names)) != len(names):
                raise ValueError(f"duplicate unit in bundle {bundle}")
            bundles[bundle] = names
            room_match = re.fullmatch(r"RoomBundle\((\d+)\)", bundle)
            for index, name in enumerate(names):
                if name in units:
                    raise ValueError(f"unit appears in multiple bundles: {name}")
                units[name] = DirectoryUnit(
                    ProgramUnitIdentity(name), BundleIdentity(bundle), index,
                    unit_kinds.get(name, "OTHER"),
                    ({"room": int(room_match.group(1))}
                     if room_match and unit_kinds.get(name) != "GLOBAL" else {}),
                )
        numbers = dict(global_script_numbers or {})
        return cls(units, bundles, numbers)

    def unit(self, identity: ProgramUnitIdentity | str) -> DirectoryUnit:
        name = _unit_name(identity)
        try:
            return self.units[name]
        except KeyError as exc:
            raise UnknownProgramUnit(name) from exc

    def bundle_units(self, bundle: BundleIdentity | str) -> tuple[str, ...]:
        name = _bundle_name(bundle)
        try:
            return self.bundles[name]
        except KeyError as exc:
            raise UnknownBundle(name) from exc

    def global_unit(self, script_number: int) -> ProgramUnitIdentity:
        try:
            return ProgramUnitIdentity(self.global_scripts[int(script_number)])
        except KeyError as exc:
            raise UnknownProgramUnit(f"GlobalScript({script_number})") from exc


def _unit_name(value: ProgramUnitIdentity | str) -> str:
    return value.value if isinstance(value, ProgramUnitIdentity) else str(value)


def _bundle_name(value: BundleIdentity | str) -> str:
    return value.value if isinstance(value, BundleIdentity) else str(value)


class ResidentBindingSimulator:
    """Deterministic selector binding, pinning, bundle, and activation model."""

    def __init__(self, capacity: int | None = None, *,
                 directory: ResolverDirectory | None = None,
                 selector_pool: Iterable[int] | None = None,
                 activation_capacity: int = 25) -> None:
        if selector_pool is None:
            if capacity is None:
                pool = DEFAULT_SELECTOR_POOL
            else:
                if capacity <= 0 or capacity > len(DEFAULT_SELECTOR_POOL):
                    raise ValueError("capacity must be between 1 and 178")
                pool = DEFAULT_SELECTOR_POOL[:capacity]
        else:
            pool = tuple(int(value) for value in selector_pool)
            if capacity is not None and capacity != len(pool):
                raise ValueError("capacity and selector_pool length disagree")
        if not pool or len(set(pool)) != len(pool):
            raise ValueError("selector pool must be nonempty and unique")
        if any(not 0 <= item <= 0xFF for item in pool):
            raise ValueError("selector values must be unsigned bytes")
        if set(pool) & RESERVED_SELECTOR_VALUES:
            raise ValueError("selector pool collides with current reserved backend values")
        if activation_capacity <= 0:
            raise ValueError("activation capacity must be positive")
        self.selector_pool = tuple(pool)
        self.capacity = len(self.selector_pool)
        self.activation_capacity = activation_capacity
        self.directory = directory
        self._unit_to_binding: dict[str, _Binding] = {}
        self._selector_to_unit: dict[int, str] = {}
        self._selector_generation = {value: 0 for value in self.selector_pool}
        self._pins: dict[str, dict[str, Pin]] = {}
        self._bundle_pins: dict[str, dict[str, Pin]] = {}
        self._loaded_bundles: set[str] = set()
        self._activations: dict[str, Activation] = {}
        self._continuations: dict[str, Continuation] = {}
        self._clock = 0
        self._next_pin = 0
        self._next_activation = 0
        self._trace: list[dict[str, Any]] = []
        self.active_room_bundle: str | None = None
        self.peak_bindings = 0

    def _record(self, event: str, **fields: Any) -> None:
        self._trace.append({"sequence": len(self._trace), "event": event, **fields})

    def _identity(self, value: ProgramUnitIdentity | str) -> ProgramUnitIdentity:
        name = _unit_name(value)
        if self.directory is not None:
            return self.directory.unit(name).identity
        if not name:
            raise UnknownProgramUnit("empty program identity")
        return ProgramUnitIdentity(name)

    def _new_pin(self, identity: ProgramUnitIdentity, reason: str,
                 owner: str | None, managed: bool) -> Pin:
        self._next_pin += 1
        pin = Pin(f"P{self._next_pin:06d}", identity, reason, owner, managed)
        self._pins.setdefault(identity.value, {})[pin.token] = pin
        self._record("pin", program_unit=identity.value, reason=reason,
                     owner=owner, token=pin.token)
        return pin

    def _pins_for_name(self, name: str) -> tuple[Pin, ...]:
        return tuple(self._pins.get(name, {}).values())

    def _touch(self, binding: _Binding) -> None:
        self._clock += 1
        binding.last_used = self._clock

    def _remove_binding(self, name: str, *, event: str) -> None:
        binding = self._unit_to_binding.pop(name)
        self._selector_to_unit.pop(binding.selector.value)
        self._record(event, program_unit=name, selector=binding.selector.hex,
                     generation=binding.generation)

    def _evictable(self) -> list[_Binding]:
        return sorted(
            (binding for name, binding in self._unit_to_binding.items()
             if not self._pins.get(name)),
            key=lambda binding: (binding.last_used,
                                 self.selector_pool.index(binding.selector.value),
                                 binding.identity.value),
        )

    def _ensure_capacity(self, required_new_bindings: int) -> None:
        free = self.capacity - len(self._selector_to_unit)
        victims = len(self._evictable())
        if required_new_bindings > free + victims:
            raise ResidencyExhausted(
                f"RESIDENCY_EXHAUSTED: need {required_new_bindings} bindings; "
                f"only {free} free and {victims} unpinned bindings are reclaimable"
            )

    def resolve(self, program_unit: ProgramUnitIdentity | str) -> Selector:
        identity = self._identity(program_unit)
        name = identity.value
        current = self._unit_to_binding.get(name)
        if current is not None:
            self._touch(current)
            self._record("reuse", program_unit=name, selector=current.selector.hex,
                         generation=current.generation)
            return current.selector

        free_value = next((value for value in self.selector_pool
                           if value not in self._selector_to_unit), None)
        if free_value is None:
            victims = self._evictable()
            if not victims:
                raise ResidencyExhausted(
                    "RESIDENCY_EXHAUSTED: every resident selector is pinned"
                )
            victim = victims[0]
            free_value = victim.selector.value
            self._remove_binding(victim.identity.value, event="evict")

        generation = self._selector_generation[free_value] + 1
        self._selector_generation[free_value] = generation
        selector = Selector(free_value)
        self._clock += 1
        binding = _Binding(identity, selector, generation, self._clock)
        self._unit_to_binding[name] = binding
        self._selector_to_unit[free_value] = name
        self.peak_bindings = max(self.peak_bindings, len(self._unit_to_binding))
        self._record("bind", program_unit=name, selector=selector.hex,
                     generation=generation)
        return selector

    bind = resolve

    def reference(self, program_unit: ProgramUnitIdentity | str) -> SelectorReference:
        identity = self._identity(program_unit)
        selector = self.resolve(identity)
        binding = self._unit_to_binding[identity.value]
        return SelectorReference(identity, selector, binding.generation)

    def validate_reference(self, reference: SelectorReference) -> bool:
        current_name = self._selector_to_unit.get(reference.selector.value)
        current = self._unit_to_binding.get(reference.program_unit.value)
        if (current_name != reference.program_unit.value or current is None
                or current.generation != reference.generation
                or current.selector != reference.selector):
            raise StaleSelectorReference(
                f"stale selector reference {reference.selector.hex}/g{reference.generation} "
                f"for {reference.program_unit.value}"
            )
        return True

    def pin(self, program_unit: ProgramUnitIdentity | str,
            reason: PinReason | str, *, owner: str | None = None,
            managed: bool = False) -> Pin:
        identity = self._identity(program_unit)
        reason_value = str(reason.value if isinstance(reason, PinReason) else reason)
        if not reason_value:
            raise ValueError("pin reason must be nonempty")
        self.resolve(identity)
        if owner is None:
            owner = "manual"
        return self._new_pin(identity, reason_value, owner, managed)

    def unpin(self, pin_or_unit: Pin | ProgramUnitIdentity | str,
              reason: PinReason | str | None = None) -> None:
        if isinstance(pin_or_unit, Pin):
            identity_name = pin_or_unit.program_unit.value
            pin = self._pins.get(identity_name, {}).get(pin_or_unit.token)
            if pin is None:
                raise ValueError(f"pin already released or unknown: {pin_or_unit.token}")
        else:
            identity_name = self._identity(pin_or_unit).value
            if reason is None:
                raise ValueError("unpin by identity requires a reason")
            reason_value = str(reason.value if isinstance(reason, PinReason) else reason)
            matches = [item for item in self._pins_for_name(identity_name)
                       if item.reason == reason_value]
            if not matches:
                raise ValueError(f"no {reason_value!r} pin for {identity_name}")
            pin = matches[0]
        del self._pins[identity_name][pin.token]
        if not self._pins[identity_name]:
            del self._pins[identity_name]
        self._record("unpin", program_unit=identity_name, reason=pin.reason,
                     owner=pin.owner, token=pin.token)

    def pins_for(self, program_unit: ProgramUnitIdentity | str) -> dict[str, int]:
        identity = self._identity(program_unit)
        result: dict[str, int] = {}
        for pin in self._pins_for_name(identity.value):
            result[pin.reason] = result.get(pin.reason, 0) + 1
        return dict(sorted(result.items()))

    def is_pinned(self, program_unit: ProgramUnitIdentity | str) -> bool:
        return bool(self._pins_for_name(self._identity(program_unit).value))

    def release_unit(self, program_unit: ProgramUnitIdentity | str) -> bool:
        identity = self._identity(program_unit)
        binding = self._unit_to_binding.get(identity.value)
        if binding is None:
            return True
        if self._pins_for_name(identity.value):
            self._record("release_retained_pinned", program_unit=identity.value,
                         selector=binding.selector.hex, pin_reasons=self.pins_for(identity))
            return False
        self._remove_binding(identity.value, event="release")
        return True

    def resolve_global(self, script_number: int) -> Selector:
        if self.directory is None:
            raise UnknownProgramUnit(
                "resolve_global requires a selector directory with a global index"
            )
        identity = self.directory.global_unit(script_number)
        self._record("resolve_global", script_number=int(script_number),
                     program_unit=identity.value)
        return self.resolve(identity)

    def unit_for_selector(self, selector: Selector | int) -> ProgramUnitIdentity | None:
        value = selector.value if isinstance(selector, Selector) else int(selector)
        name = self._selector_to_unit.get(value)
        return ProgramUnitIdentity(name) if name is not None else None

    def binding(self, program_unit: ProgramUnitIdentity | str) -> ResidentBinding | None:
        identity = self._identity(program_unit)
        item = self._unit_to_binding.get(identity.value)
        if item is None:
            return None
        return ResidentBinding(identity, item.selector, item.generation,
                               tuple(sorted(self.pins_for(identity))), item.last_used)

    def resident_snapshot(self) -> dict[str, Any]:
        """Ephemeral diagnostic view; unlike snapshot(), selectors are present."""
        return {
            "capacity": self.capacity,
            "bindings": [
                {"program_unit": name, "selector": binding.selector.hex,
                 "generation": binding.generation,
                 "pins": self.pins_for(name), "last_used": binding.last_used}
                for name, binding in sorted(self._unit_to_binding.items())
            ],
            "loaded_bundles": sorted(self._loaded_bundles),
            "trace": self.trace,
        }

    @property
    def trace(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._trace]

    def begin_activation(
        self,
        program_unit: ProgramUnitIdentity | str,
        *,
        pc: int = 0,
        locals: Iterable[int] = (),
        activation_id: str | None = None,
        parent_activation_id: str | None = None,
        room_ownership: str | None = None,
        extra_pin_reasons: Iterable[PinReason | str] = (),
    ) -> Activation:
        identity = self._identity(program_unit)
        if len(self._activations) >= self.activation_capacity:
            raise ActivationCapacityExhausted(
                f"activation slots exhausted ({self.activation_capacity})"
            )
        if activation_id is None:
            self._next_activation += 1
            activation_id = f"A{self._next_activation:04d}"
        elif activation_id.startswith("A") and activation_id[1:].isdigit():
            self._next_activation = max(self._next_activation, int(activation_id[1:]))
        if activation_id in self._activations:
            raise ValueError(f"activation already exists: {activation_id}")
        parent = None
        if parent_activation_id is not None:
            parent = self._activations.get(parent_activation_id)
            if parent is None:
                raise ValueError(f"missing parent activation: {parent_activation_id}")
        if room_ownership is None and self.directory is not None:
            unit = self.directory.unit(identity)
            if unit.kind != "GLOBAL" and unit.bundle.value != "GlobalBundle":
                room_ownership = unit.bundle.value

        reference = self.reference(identity)
        active_pin = self.pin(identity, PinReason.ACTIVE_SCRIPT_SLOT,
                              owner=f"activation:{activation_id}", managed=True)
        parent_pin = None
        if parent is not None:
            parent_pin = self.pin(parent.program_unit, PinReason.NESTED_PARENT,
                                  owner=f"child:{activation_id}", managed=True)
        extras = [self.pin(identity, reason, owner=f"activation-extra:{activation_id}",
                           managed=True)
                  for reason in extra_pin_reasons]
        self._clock += 1
        activation = Activation(
            activation_id, identity, int(pc), tuple(int(value) for value in locals),
            parent_activation_id, room_ownership, False, reference,
            active_pin, parent_pin, None, extras, self._clock,
        )
        self._activations[activation_id] = activation
        self._record("activation_begin", activation_id=activation_id,
                     program_unit=identity.value, pc=int(pc),
                     parent_activation_id=parent_activation_id,
                     room_ownership=room_ownership)
        return activation

    def mark_yielded(self, activation_id: str, yielded: bool = True) -> None:
        activation = self._activation(activation_id)
        if yielded and not activation.yielded:
            activation.yielded_pin = self.pin(
                activation.program_unit, PinReason.YIELDED_SCRIPT,
                owner=f"activation:{activation_id}", managed=True)
        elif not yielded and activation.yielded_pin is not None:
            self.unpin(activation.yielded_pin)
            activation.yielded_pin = None
        activation.yielded = yielded
        self._record("activation_yield" if yielded else "activation_resume",
                     activation_id=activation_id,
                     program_unit=activation.program_unit.value, pc=activation.pc)

    def update_activation(self, activation_id: str, *, pc: int | None = None,
                          locals: Iterable[int] | None = None) -> None:
        activation = self._activation(activation_id)
        if pc is not None:
            activation.pc = int(pc)
        if locals is not None:
            activation.locals = tuple(int(value) for value in locals)
        self._record("activation_state", activation_id=activation_id,
                     pc=activation.pc, locals=list(activation.locals))

    def end_activation(self, activation_id: str) -> None:
        activation = self._activations.pop(activation_id, None)
        if activation is None:
            raise ValueError(f"unknown activation: {activation_id}")
        self.unpin(activation.activation_pin)
        if activation.yielded_pin is not None:
            self.unpin(activation.yielded_pin)
        if activation.parent_pin is not None:
            self.unpin(activation.parent_pin)
        for pin in activation.extra_pins:
            self.unpin(pin)
        self._record("activation_end", activation_id=activation_id,
                     program_unit=activation.program_unit.value)

    def replace_activation(self, activation_id: str, *, pc: int = 0,
                           locals: Iterable[int] = ()) -> Activation:
        """Model nonrecursive same-program replacement without duplicate binds."""
        old = self._activation(activation_id)
        identity = old.program_unit
        room_owner = old.room_ownership
        parent_id = old.parent_activation_id
        self.end_activation(activation_id)
        replacement = self.begin_activation(
            identity, pc=pc, locals=locals, parent_activation_id=parent_id,
            room_ownership=room_owner)
        self._record("activation_replace", old_activation_id=activation_id,
                     new_activation_id=replacement.activation_id,
                     program_unit=identity.value)
        return replacement

    def _activation(self, activation_id: str) -> Activation:
        try:
            return self._activations[activation_id]
        except KeyError as exc:
            raise ValueError(f"unknown activation: {activation_id}") from exc

    def hold_continuation(self, continuation_id: str,
                          program_unit: ProgramUnitIdentity | str, *,
                          reason: PinReason | str,
                          activation_id: str | None = None) -> Continuation:
        if continuation_id in self._continuations:
            raise ValueError(f"continuation already held: {continuation_id}")
        if activation_id is not None:
            activation = self._activation(activation_id)
            identity = activation.program_unit
            if self._identity(program_unit) != identity:
                raise ValueError("continuation identity must match its activation")
        else:
            identity = self._identity(program_unit)
        reason_value = str(reason.value if isinstance(reason, PinReason) else reason)
        if reason_value not in {PinReason.ROOM_CONTINUATION.value,
                                PinReason.CUTSCENE_OVERRIDE.value}:
            raise ValueError("continuation reason must be ROOM_CONTINUATION or CUTSCENE_OVERRIDE")
        pin = self.pin(identity, reason_value,
                       owner=f"continuation:{continuation_id}", managed=True)
        item = Continuation(continuation_id, identity, reason_value, activation_id, pin)
        self._continuations[continuation_id] = item
        self._record("continuation_hold", continuation_id=continuation_id,
                     program_unit=identity.value, reason=reason_value,
                     activation_id=activation_id)
        return item

    def release_continuation(self, continuation_id: str) -> None:
        try:
            item = self._continuations.pop(continuation_id)
        except KeyError as exc:
            raise ValueError(f"unknown continuation: {continuation_id}") from exc
        self.unpin(item.pin)
        self._record("continuation_release", continuation_id=continuation_id,
                     program_unit=item.program_unit.value)

    def load_bundle(self, bundle: BundleIdentity | str) -> tuple[Selector, ...]:
        if self.directory is None:
            raise UnknownBundle("load_bundle requires a compiler directory")
        identity = _bundle_name(bundle)
        names = self.directory.bundle_units(identity)
        if identity in self._loaded_bundles:
            return tuple(self.resolve(name) for name in names)
        new_names = [name for name in names if name not in self._unit_to_binding]
        self._ensure_capacity(len(new_names))
        acquired = []
        for name in names:
            selector = self.resolve(name)
            pin = self.pin(name, PinReason.ROOM_LIFECYCLE,
                           owner=f"bundle:{identity}", managed=True)
            acquired.append((name, pin))
        self._bundle_pins[identity] = {name: pin for name, pin in acquired}
        self._loaded_bundles.add(identity)
        self._record("bundle_load", bundle=identity, selector_units=len(names))
        return tuple(self._unit_to_binding[name].selector for name in names)

    def release_bundle(self, bundle: BundleIdentity | str) -> None:
        identity = _bundle_name(bundle)
        if identity not in self._loaded_bundles:
            raise UnknownBundle(f"bundle is not loaded: {identity}")
        pins = self._bundle_pins.pop(identity)
        for name, pin in sorted(pins.items()):
            self.unpin(pin)
            self.release_unit(name)
        self._loaded_bundles.remove(identity)
        if self.active_room_bundle == identity:
            self.active_room_bundle = None
        self._record("bundle_release", bundle=identity,
                     remaining_bindings=len(self._unit_to_binding))

    def retire_room_activations(self, bundle: BundleIdentity | str) -> list[str]:
        identity = _bundle_name(bundle)
        if self.directory is None:
            raise UnknownBundle("room activation retirement requires a directory")
        room_unit_names = set(self.directory.bundle_units(identity))
        retiring = sorted(
            activation.activation_id for activation in self._activations.values()
            if activation.room_ownership == identity
            and activation.program_unit.value in room_unit_names
        )
        room_owned_units = set(self.directory.bundle_units(identity))
        for activation_id in retiring:
            self.end_activation(activation_id)
        # Outgoing room-owned continuations retire with their activations.
        # Global continuations are outside this set and remain pinned.
        retiring_continuations = sorted(
            continuation_id
            for continuation_id, continuation in self._continuations.items()
            if continuation.program_unit.value in room_owned_units
        )
        for continuation_id in retiring_continuations:
            self.release_continuation(continuation_id)
        self._record("room_activations_retired", bundle=identity,
                     activations=retiring,
                     continuations=retiring_continuations)
        return retiring

    def transition_room(self, outgoing: BundleIdentity | str,
                        incoming: BundleIdentity | str) -> dict[str, Any]:
        """Run EXCD, retire old room activations, then bind/run incoming ENCD.

        The old bundle remains resident through EXCD. It is released before
        the incoming bundle is bound; global activation/continuation pins stay.
        """
        old_name, new_name = _bundle_name(outgoing), _bundle_name(incoming)
        if old_name not in self._loaded_bundles:
            raise UnknownBundle(f"outgoing room bundle is not loaded: {old_name}")
        if self.directory is None:
            raise UnknownBundle("room transition requires a compiler directory")
        start_count = len(self._unit_to_binding)
        transition_peak = start_count
        activation_count_start = len(self._activations)
        activation_peak = activation_count_start
        exit_units = [name for name in self.directory.bundle_units(old_name)
                      if self.directory.unit(name).kind == "ROOM_EXIT"]
        for name in exit_units:
            activation = self.begin_activation(name, room_ownership=old_name)
            activation_peak = max(activation_peak, len(self._activations))
            self._record("room_exit_run", bundle=old_name,
                         program_unit=name, bundle_resident=True)
            self.end_activation(activation.activation_id)
            transition_peak = max(transition_peak, len(self._unit_to_binding))
        self.retire_room_activations(old_name)
        self.release_bundle(old_name)
        transition_peak = max(transition_peak, len(self._unit_to_binding))
        self.load_bundle(new_name)
        transition_peak = max(transition_peak, len(self._unit_to_binding))
        entry_units = [name for name in self.directory.bundle_units(new_name)
                       if self.directory.unit(name).kind == "ROOM_ENTRY"]
        for name in entry_units:
            activation = self.begin_activation(name, room_ownership=new_name)
            activation_peak = max(activation_peak, len(self._activations))
            self._record("room_entry_run", bundle=new_name,
                         program_unit=name, bundle_resident=True)
            self.end_activation(activation.activation_id)
            transition_peak = max(transition_peak, len(self._unit_to_binding))
        self.active_room_bundle = new_name
        result = {
            "outgoing_bundle": old_name,
            "incoming_bundle": new_name,
            "binding_count_before": start_count,
            "binding_count_after": len(self._unit_to_binding),
            "peak_binding_count": transition_peak,
            "activation_slots_at_start": activation_count_start,
            "peak_activation_slots": activation_peak,
            "old_bundle_released_before_incoming_bind": True,
            "globals_preserved": sorted(
                name for name in self._unit_to_binding
                if self.directory.unit(name).kind == "GLOBAL"
                and self._pins_for_name(name)),
        }
        self._record("room_transition_complete", **result)
        return result

    def begin_room(self, bundle: BundleIdentity | str) -> None:
        name = _bundle_name(bundle)
        self.load_bundle(name)
        entries = [unit for unit in self.directory.bundle_units(name)
                   if self.directory.unit(unit).kind == "ROOM_ENTRY"]
        for unit in entries:
            activation = self.begin_activation(unit, room_ownership=name)
            self._record("room_entry_run", bundle=name,
                         program_unit=unit, bundle_resident=True)
            self.end_activation(activation.activation_id)
        self.active_room_bundle = name

    def begin_global(self, script_number: int, *, pc: int = 0,
                     locals: Iterable[int] = (), yielded: bool = False,
                     activation_id: str | None = None,
                     parent_activation_id: str | None = None) -> Activation:
        if self.directory is None:
            raise UnknownProgramUnit("global activation requires a compiler directory")
        identity = self.directory.global_unit(script_number)
        self._record("global_lookup", script_number=script_number,
                     program_unit=identity.value)
        activation = self.begin_activation(
            identity, pc=pc, locals=locals, activation_id=activation_id,
            parent_activation_id=parent_activation_id)
        if yielded:
            self.mark_yielded(activation.activation_id)
        return activation

    def snapshot(self) -> dict[str, Any]:
        """Portable state: canonical identities and semantic pins, no selectors."""
        activations = []
        for item in sorted(self._activations.values(), key=lambda value: value.order):
            activations.append({
                "activation_id": item.activation_id,
                "program_unit": item.program_unit.value,
                "pc": item.pc,
                "locals": list(item.locals),
                "parent_activation_id": item.parent_activation_id,
                "room_ownership": item.room_ownership,
                "yielded": item.yielded,
                "extra_pin_reasons": sorted(pin.reason for pin in item.extra_pins),
            })
        continuations = [{
            "continuation_id": item.continuation_id,
            "program_unit": item.program_unit.value,
            "reason": item.reason,
            "activation_id": item.activation_id,
        } for item in sorted(self._continuations.values(),
                             key=lambda value: value.continuation_id)]
        portable_pins = [{
            "program_unit": pin.program_unit.value,
            "reason": pin.reason,
            "owner": pin.owner,
        } for pins in self._pins.values() for pin in pins.values()
            if not pin.managed]
        return {
            "schema": "same_scumm_residency_portable_snapshot_v1",
            "loaded_bundles": sorted(self._loaded_bundles),
            "active_room_bundle": self.active_room_bundle,
            "activations": activations,
            "continuations": continuations,
            "portable_pins": sorted(portable_pins, key=lambda item: (
                item["program_unit"], item["reason"], item["owner"] or "")),
        }

    @classmethod
    def restore(cls, snapshot: Mapping[str, Any], *,
                directory: ResolverDirectory,
                selector_pool: Iterable[int] = DEFAULT_SELECTOR_POOL,
                prebind: Iterable[ProgramUnitIdentity | str] = (),
                activation_capacity: int = 25) -> "ResidentBindingSimulator":
        """Reconstruct semantic state in a fresh pool; selectors are reassigned."""
        if snapshot.get("schema") != "same_scumm_residency_portable_snapshot_v1":
            raise ValueError("unsupported portable residency snapshot schema")
        simulator = cls(directory=directory, selector_pool=selector_pool,
                        activation_capacity=activation_capacity)
        for identity in prebind:
            simulator.resolve(identity)
        for bundle in snapshot.get("loaded_bundles", []):
            simulator.load_bundle(bundle)

        activations = list(snapshot.get("activations", []))
        # Hold reconstruction pins before rebuilding parent/child chains.
        reconstruction_pins = {}
        for row in activations:
            identity = simulator._identity(row["program_unit"])
            if identity.value not in reconstruction_pins:
                reconstruction_pins[identity.value] = simulator.pin(
                    identity, PinReason.SAVE_RESTORE_RECONSTRUCTION,
                    owner=f"restore:{identity.value}", managed=True)
        for row in activations:
            activation = simulator.begin_activation(
                row["program_unit"], pc=int(row["pc"]), locals=row["locals"],
                activation_id=row["activation_id"],
                parent_activation_id=row.get("parent_activation_id"),
                room_ownership=row.get("room_ownership"),
                extra_pin_reasons=row.get("extra_pin_reasons", []),
            )
            if row.get("yielded"):
                simulator.mark_yielded(activation.activation_id)
        for row in snapshot.get("continuations", []):
            simulator.hold_continuation(
                row["continuation_id"], row["program_unit"],
                reason=row["reason"], activation_id=row.get("activation_id"))
        for row in snapshot.get("portable_pins", []):
            simulator.pin(row["program_unit"], row["reason"],
                           owner=row.get("owner"), managed=False)
        for pin in reconstruction_pins.values():
            simulator.unpin(pin)
        simulator.active_room_bundle = snapshot.get("active_room_bundle")
        simulator._record("portable_restore_complete",
                          active_activations=len(simulator._activations),
                          loaded_bundles=sorted(simulator._loaded_bundles))
        return simulator

    def trace_report(self) -> dict[str, Any]:
        return {
            "schema": "same_scumm_residency_trace_v1",
            "selector_capacity": self.capacity,
            "peak_bindings": self.peak_bindings,
            "final_binding_count": len(self._unit_to_binding),
            "trace": self.trace,
        }


def simulate_analysis_directory(
    directory: ResolverDirectory,
    selector_demand: Mapping[str, Any],
    dependency_graph: Mapping[str, Any],
    *,
    selector_pool: Iterable[int] = DEFAULT_SELECTOR_POOL,
    activation_capacity: int = 25,
) -> dict[str, Any]:
    """Exercise compiler-known room/global residency scenarios deterministically.

    This is a conservative binding-policy simulation, not a gameplay trace or
    proof that every selected global can actually be live at once.
    """
    pool = tuple(selector_pool)
    globals_by_number = sorted(directory.global_scripts.items())
    global_units = [unit for _, unit in globals_by_number]
    room_bundle_by_number = directory.room_bundles
    room_sizes = {
        room: len(directory.bundle_units(bundle))
        for room, bundle in sorted(room_bundle_by_number.items())
    }
    if not room_sizes:
        raise ValueError("analysis directory contains no room bundles")
    largest_room = min(room_sizes, key=lambda room: (-room_sizes[room], room))
    room_rows = {int(item["room"]): item
                 for item in selector_demand.get("room_selector_reports", [])}
    dynamic_room_candidates = {
        room: list(row.get("dynamic_global_candidate_selector_units", []))
        for room, row in room_rows.items()
    }
    dynamic_room = min(room_sizes, key=lambda room: (
        -int(room_rows.get(room, {}).get("dynamic_candidate_universe_count", 0)),
        -room_sizes[room], room))
    dynamic_global_candidates = [str(item) for item in
        selector_demand.get("global_selector_summary", {}).get(
            "dynamic_candidate_universe", [])]
    global_number_by_identity = {identity: number
                                 for number, identity in globals_by_number}

    steady_rows = []
    max_steady = 0
    max_room_with_globals = 0
    for room, bundle in sorted(room_bundle_by_number.items()):
        sim = ResidentBindingSimulator(directory=directory, selector_pool=pool,
                                       activation_capacity=activation_capacity)
        sim.begin_room(bundle)
        steady = len(sim._unit_to_binding)
        max_steady = max(max_steady, steady)
        global_count = min(activation_capacity, len(global_units))
        active = []
        continuation_id = None
        for index, unit in enumerate(global_units[:global_count]):
            activation = sim.begin_activation(unit, pc=index * 3,
                                              locals=(index, room))
            active.append(activation.activation_id)
            if index == 0:
                sim.mark_yielded(activation.activation_id)
                continuation_id = f"steady:{room}:global:{index}"
                sim.hold_continuation(
                    continuation_id, unit, reason=PinReason.ROOM_CONTINUATION,
                    activation_id=activation.activation_id)
        modeled_peak = len(sim._unit_to_binding)
        max_room_with_globals = max(max_room_with_globals, modeled_peak)
        for activation_id in reversed(active):
            sim.end_activation(activation_id)
        if continuation_id is not None:
            sim.release_continuation(continuation_id)
        sim.release_bundle(bundle)
        steady_rows.append({
            "room": room,
            "bundle": bundle,
            "selector_units": room_sizes[room],
            "steady_binding_count": steady,
            "modeled_global_activation_count": global_count,
            "peak_with_modeled_globals": modeled_peak,
            "selector_capacity_sufficient": modeled_peak <= len(pool),
            "epistemic": "CONSERVATIVE_MODELED_UPPER_BOUND",
        })

    # Collect only compiler-discovered room-local LoadRoom edges. A pair is a
    # lifecycle-capacity scenario, not a claim that the game took that path.
    semantic_to_unit = selector_demand.get("semantic_to_selector_index", {})
    transition_pairs: set[tuple[int, int]] = set()
    for edge in dependency_graph.get("edges", []):
        if edge.get("kind") not in {"load_room", "load_room_with_ego"}:
            continue
        if edge.get("resolution") not in {"STATIC", "CONDITIONAL_STATIC"}:
            continue
        source_unit_name = semantic_to_unit.get(edge.get("source"))
        target_unit_name = semantic_to_unit.get(edge.get("target"))
        if source_unit_name not in directory.units or target_unit_name not in directory.units:
            continue
        source_room = directory.unit(source_unit_name).owner.get("room")
        target_room = directory.unit(target_unit_name).owner.get("room")
        if source_room is None or target_room is None or int(source_room) == int(target_room):
            continue
        old_room, new_room = int(source_room), int(target_room)
        if old_room in room_bundle_by_number and new_room in room_bundle_by_number:
            transition_pairs.add((old_room, new_room))

    transition_rows = []
    max_transition_peak = 0
    for old_room, new_room in sorted(transition_pairs):
        sim = ResidentBindingSimulator(directory=directory, selector_pool=pool,
                                       activation_capacity=activation_capacity)
        old_bundle = room_bundle_by_number[old_room]
        new_bundle = room_bundle_by_number[new_room]
        sim.begin_room(old_bundle)
        active = []
        local_units = [name for name in directory.bundle_units(old_bundle)
                       if directory.unit(name).kind == "ROOM_LOCAL"]
        # EXCD occupies a slot before the old room-owned local is retired.
        reserved_slots = 1 + bool(local_units)
        live_global_count = min(max(0, activation_capacity - reserved_slots),
                                len(global_units))
        for index, unit in enumerate(global_units[:live_global_count]):
            activation = sim.begin_activation(unit, pc=index * 2,
                                              locals=(old_room, new_room))
            active.append(activation.activation_id)
            if index == 0:
                sim.mark_yielded(activation.activation_id)
                sim.hold_continuation(
                    f"transition:{old_room}:{new_room}", unit,
                    reason=PinReason.ROOM_CONTINUATION,
                    activation_id=activation.activation_id)
        local_activation_id = None
        if local_units and len(active) < activation_capacity:
            local_activation = sim.begin_activation(
                local_units[0], pc=6, locals=(old_room,), room_ownership=old_bundle)
            local_activation_id = local_activation.activation_id
        transition = sim.transition_room(old_bundle, new_bundle)
        max_transition_peak = max(max_transition_peak, transition["peak_binding_count"])
        if local_activation_id is not None:
            assert local_activation_id not in sim._activations
        globals_preserved = all(
            activation_id in sim._activations for activation_id in active)
        for activation_id in reversed(active):
            sim.end_activation(activation_id)
        sim.release_continuation(f"transition:{old_room}:{new_room}")
        sim.release_bundle(new_bundle)
        transition_rows.append({
            "outgoing_room": old_room,
            "incoming_room": new_room,
            "source_edge_resolution": "STATIC_OR_CONDITIONAL_STATIC",
            "modeled_global_activation_count": live_global_count,
            "retired_room_local_activation": local_activation_id is not None,
            "live_globals_preserved": globals_preserved,
            "peak_binding_count": transition["peak_binding_count"],
            "peak_activation_slots": transition["peak_activation_slots"],
            "old_bundle_released_before_new_bind": transition[
                "old_bundle_released_before_incoming_bind"],
            "selector_capacity_sufficient": transition["peak_binding_count"] <= len(pool),
        })

    # Stress the largest bundle through a compiler-discovered outgoing load
    # edge, keeping a yielded global and a 25-slot global live set across it.
    largest_outgoing = [pair for pair in transition_pairs if pair[0] == largest_room]
    room40_destination = None
    if largest_outgoing:
        room40_destination = min(
            (new for _, new in largest_outgoing),
            key=lambda room: (-room_sizes[room], room))
    largest_bundle = room_bundle_by_number[largest_room]
    global_sim = ResidentBindingSimulator(directory=directory, selector_pool=pool,
                                          activation_capacity=activation_capacity)
    global_sim.begin_room(largest_bundle)
    active_global_ids = []
    dynamic_identity = None
    dynamic_number = None
    global_candidates_for_largest = [
        str(item) for item in selector_demand.get("room_selector_reports", [])
        if int(item["room"]) == largest_room
        for item in item.get("dynamic_global_candidate_selector_units", [])
    ]
    preferred_candidates = global_candidates_for_largest or dynamic_global_candidates
    globals_before_dynamic_dispatch = max(0, activation_capacity - 2)
    candidate_identity = next((name for name in preferred_candidates
                               if name in global_number_by_identity
                               and name not in global_units[:globals_before_dynamic_dispatch]),
                              None)
    # In case the directory's candidate list is smaller than its available
    # globals, choose the first unused known global without guessing a target.
    if candidate_identity is None:
        candidate_identity = next((name for name in global_units
                                   if name not in global_units[:globals_before_dynamic_dispatch]),
                                  None)
    if candidate_identity is not None:
        dynamic_identity = candidate_identity
        dynamic_number = global_number_by_identity[candidate_identity]
    for index, unit in enumerate(global_units[:globals_before_dynamic_dispatch]):
        activation = global_sim.begin_activation(unit, pc=100 + index,
                                                locals=(largest_room, index))
        active_global_ids.append(activation.activation_id)
        if index == 0:
            global_sim.mark_yielded(activation.activation_id)
            global_sim.hold_continuation(
                "largest-room-yielded-global", unit,
                reason=PinReason.ROOM_CONTINUATION,
                activation_id=activation.activation_id)
    if dynamic_number is not None and len(active_global_ids) < activation_capacity:
        global_sim.resolve_global(dynamic_number)
        dynamic_activation = global_sim.begin_global(
            dynamic_number, pc=777, locals=(largest_room, dynamic_number))
        active_global_ids.append(dynamic_activation.activation_id)
    largest_room_peak = len(global_sim._unit_to_binding)
    transition_detail = None
    yielded_global_preserved = False
    if room40_destination is not None:
        transition_detail = global_sim.transition_room(
            largest_bundle, room_bundle_by_number[room40_destination])
        yielded_id = active_global_ids[0] if active_global_ids else None
        yielded_global_preserved = bool(
            yielded_id is not None
            and yielded_id in global_sim._activations
            and global_sim._activations[yielded_id].yielded
            and global_sim.validate_reference(
                global_sim._activations[yielded_id].reference)
        )
        if not yielded_global_preserved:
            raise AssertionError("yielded global binding did not survive room transition")
    for activation_id in reversed(active_global_ids):
        if activation_id in global_sim._activations:
            global_sim.end_activation(activation_id)
    if "largest-room-yielded-global" in global_sim._continuations:
        global_sim.release_continuation("largest-room-yielded-global")
    if global_sim.active_room_bundle in global_sim._loaded_bundles:
        global_sim.release_bundle(global_sim.active_room_bundle)

    # The dynamic candidate universe is resolved one requested target at a
    # time in the room with the largest compiler-reported candidate union.
    dynamic_bundle = room_bundle_by_number[dynamic_room]
    dynamic_sim = ResidentBindingSimulator(directory=directory, selector_pool=pool,
                                          activation_capacity=activation_capacity)
    dynamic_sim.begin_room(dynamic_bundle)
    dynamic_targets = dynamic_room_candidates.get(dynamic_room, [])
    if not dynamic_targets:
        dynamic_targets = dynamic_global_candidates
    unique_targets = sorted({str(item) for item in dynamic_targets
                             if str(item) in global_number_by_identity})
    selected_targets = []
    if unique_targets:
        indexes = sorted({0, len(unique_targets) // 2, len(unique_targets) - 1})
        selected_targets = [unique_targets[index] for index in indexes]
    dynamic_peaks = []
    for index, identity in enumerate(selected_targets):
        script_number = global_number_by_identity[identity]
        activation = dynamic_sim.begin_global(
            script_number, pc=20 + index, locals=(dynamic_room, script_number))
        dynamic_peaks.append(len(dynamic_sim._unit_to_binding))
        dynamic_sim.end_activation(activation.activation_id)
        dynamic_sim.release_unit(identity)
    dynamic_room_peak = max(dynamic_peaks, default=len(dynamic_sim._unit_to_binding))
    dynamic_sim.release_bundle(dynamic_bundle)

    snapshot_restore = None
    if globals_by_number:
        script_number, snapshot_identity = globals_by_number[0]
        save_sim = ResidentBindingSimulator(directory=directory, selector_pool=pool,
                                           activation_capacity=activation_capacity)
        saved_activation = save_sim.begin_global(
            script_number, pc=0x123, locals=(0x11, 0x22, 0x33), yielded=True,
            activation_id="portable-global")
        save_sim.hold_continuation(
            "portable-room-continuation", snapshot_identity,
            reason=PinReason.ROOM_CONTINUATION,
            activation_id=saved_activation.activation_id)
        portable_state = save_sim.snapshot()
        before_selector = save_sim.binding(snapshot_identity).selector.hex
        restore_prebind = [unit for _, unit in globals_by_number[1:50]]
        restored_sim = ResidentBindingSimulator.restore(
            portable_state, directory=directory, selector_pool=pool,
            prebind=restore_prebind, activation_capacity=activation_capacity)
        restored_activation = restored_sim._activation("portable-global")
        after_selector = restored_activation.reference.selector.hex
        snapshot_restore = {
            "program_unit_identity": snapshot_identity,
            "pc": restored_activation.pc,
            "locals": list(restored_activation.locals),
            "yielded": restored_activation.yielded,
            "continuations": sorted(restored_sim._continuations),
            "portable_state_equal": portable_state == restored_sim.snapshot(),
            "original_ephemeral_selector": before_selector,
            "restored_ephemeral_selector": after_selector,
            "selector_reassignment_demonstrated": before_selector != after_selector,
            "portable_snapshot_contains_selector_fields": any(
                key in {"selector", "selector_value", "generation"}
                for row in portable_state.get("activations", [])
                for key in row
            ),
        }

    largest_bundle_count = max(room_sizes.values())
    active_global_ceiling = min(activation_capacity, len(global_units))
    conservative_bound = largest_bundle_count + active_global_ceiling
    source_coverage = selector_demand.get("source_coverage", {})
    unparsed_rooms = int(source_coverage.get("rooms_inventoried", len(room_sizes))) - int(
        source_coverage.get("rooms_parsed", len(room_sizes)))
    report = {
        "schema": "same_scumm_residency_simulation_v1",
        "selector_capacity": len(pool),
        "selector_pool_policy": {
            "primary_first": ["$D0", "$FF"],
            "overflow_next": ["$CF", "$4E"],
            "usable_values": len(pool),
            "reserved_collision_policy": "pool is disjoint from current reserved $00-$4D values",
        },
        "room_policy": "eagerly bind each SelectorUnit in the active room bundle",
        "global_policy": "lazy lookup; bind only a requested available global",
        "room_bundle_count": len(room_sizes),
        "global_selector_unit_count": len(global_units),
        "room_steady_states": steady_rows,
        "largest_room": {
            "room": largest_room,
            "bundle": largest_bundle,
            "selector_units": largest_bundle_count,
            "modeled_peak_with_live_globals_and_dynamic_lookup": largest_room_peak,
            "yielded_global_preserved_across_transition": yielded_global_preserved,
            "dynamic_global_resolved_on_demand": dynamic_identity,
            "dynamic_global_script_number": dynamic_number,
            "transition_to_compiler_discovered_room": room40_destination,
            "transition_result": transition_detail,
            "trace": global_sim.trace,
        },
        "room_transition_scenarios": {
            "compiler_discovered_static_or_conditional_load_edges": len(transition_rows),
            "peak_binding_count": max_transition_peak,
            "largest_peak_examples": sorted(
                transition_rows,
                key=lambda item: (-item["peak_binding_count"],
                                  item["outgoing_room"], item["incoming_room"]))[:10],
            "all_scenarios_kept_within_capacity": all(
                item["selector_capacity_sufficient"] for item in transition_rows),
        },
        "dynamic_candidate_scenario": {
            "room": dynamic_room,
            "room_selector_units": room_sizes[dynamic_room],
            "candidate_universe_count": int(room_rows.get(dynamic_room, {}).get(
                "dynamic_candidate_universe_count", len(unique_targets))),
            "global_targets_resolved_sequentially": selected_targets,
            "max_additional_global_bindings_at_once": min(1, len(selected_targets)),
            "peak_resident_bindings": dynamic_room_peak,
            "all_candidates_prebound": False,
            "dynamic_candidate_universe_is_not_simultaneous_residency": True,
        },
        "capacity": {
            "largest_room_bundle": {
                "value": largest_bundle_count,
                "epistemic": "STATIC_LOWER_BOUND" if unparsed_rooms > 0 else "EXACT",
                "unparsed_room_count": max(0, unparsed_rooms),
            },
            "largest_simulated_resident_set": {
                "value": max(max_steady, max_room_with_globals, max_transition_peak,
                             largest_room_peak, dynamic_room_peak),
                "epistemic": "SIMULATED_SCENARIO_MAXIMUM",
            },
            "conservative_modeled_upper_bound": {
                "value": conservative_bound,
                "epistemic": "CONSERVATIVE_UPPER_BOUND",
                "calculation": f"{largest_bundle_count} room units + "
                               f"{active_global_ceiling} distinct active global slots",
                "room_lifecycle_temporary_units_extra": 0,
                "reason_lifecycle_units_are_in_bundle": True,
            },
            "selector_capacity_sufficient_for_modeled_bound": conservative_bound <= len(pool),
            "proven_concurrent_live_unit_maximum": {
                "value": None, "epistemic": "UNKNOWN",
                "reason": "source dependencies do not establish simultaneous runtime liveness",
            },
            "unknown_factors": [
                "actual scheduler liveness and replacement timing",
                "independent selector snapshots outside C4 activations",
                "three inventoried but unparsed room resources",
                "runtime loading/resolver policy is not implemented natively",
            ],
        },
        "directory_global_count": len(directory.global_scripts),
        "dynamic_global_candidate_universe_count": len(dynamic_global_candidates),
        "dynamic_candidate_union_maximum": int(selector_demand.get(
            "room_capacity_summary", {}).get("largest_dynamic_candidate_universe", 0)),
        "dynamic_candidates_prebound": False,
        "portable_snapshot_restore": snapshot_restore,
        "selector_exhausted_in_modeled_scenarios": False,
    }
    return report
