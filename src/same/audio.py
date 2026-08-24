"""CPU-independent audio translation laboratory.

Milestone A implements an SN76489 state machine and deterministic WAV renderer.
It lets SAME validate the PSG half of a Genesis target without a 68000, Z80, SPC,
or game ROM.  YM2612 writes are retained by the generic trace format but are not
synthesized in this milestone.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math
import struct
import wave
from typing import Iterable, Iterator

from .errors import SameError

GENESIS_PSG_CLOCK = 3_579_545
DEFAULT_SAMPLE_RATE = 44_100


class AudioTraceError(SameError):
    pass


@dataclass(frozen=True, slots=True)
class ChipWrite:
    at: float
    chip: str
    value: int
    port: int = 0
    address: int | None = None

    def __post_init__(self) -> None:
        if self.at < 0 or not math.isfinite(self.at):
            raise AudioTraceError("chip write time must be finite and non-negative")
        if self.chip not in {"sn76489", "ym2612"}:
            raise AudioTraceError(f"unsupported chip {self.chip!r}")
        if self.value < 0 or self.value > 0xFF:
            raise AudioTraceError("chip write value must fit u8")
        if self.port < 0 or self.port > 1:
            raise AudioTraceError("chip port must be 0 or 1")
        if self.address is not None and not 0 <= self.address <= 0xFF:
            raise AudioTraceError("chip address must fit u8")

    def to_dict(self) -> dict[str, int | float | str | None]:
        return {
            "at": self.at,
            "chip": self.chip,
            "port": self.port,
            "address": self.address,
            "value": self.value,
        }


def read_trace(path: Path) -> list[ChipWrite]:
    writes: list[ChipWrite] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AudioTraceError(f"cannot read audio trace {path}: {exc}") from exc
    previous = -1.0
    for line_number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AudioTraceError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(obj, dict):
            raise AudioTraceError(f"{path}:{line_number}: record is not an object")
        write = ChipWrite(
            at=float(obj.get("at", 0)),
            chip=str(obj.get("chip", "")),
            port=int(obj.get("port", 0)),
            address=(None if obj.get("address") is None else int(obj["address"])),
            value=int(obj.get("value", -1)),
        )
        if write.at < previous:
            raise AudioTraceError(f"{path}:{line_number}: writes are not time ordered")
        previous = write.at
        writes.append(write)
    return writes


def write_trace(path: Path, writes: Iterable[ChipWrite]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(write.to_dict(), sort_keys=True) + "\n" for write in writes),
        encoding="utf-8",
    )


class SN76489:
    """Register-level SN76489/Sega PSG model suitable for trace validation."""

    def __init__(self, clock_hz: int = GENESIS_PSG_CLOCK) -> None:
        if clock_hz <= 0:
            raise ValueError("clock_hz must be positive")
        self.clock_hz = clock_hz
        self.tone_period = [0x3FF, 0x3FF, 0x3FF]
        self.volume = [15, 15, 15, 15]
        self.noise_control = 0
        self.latched_channel = 0
        self.latched_volume = False
        self._tone_phase = [0.0, 0.0, 0.0]
        self._noise_phase = 0.0
        self._noise_lfsr = 0x8000
        self._noise_output = 1.0

    def reset(self) -> None:
        self.__init__(self.clock_hz)

    def write(self, value: int) -> None:
        if value < 0 or value > 0xFF:
            raise ValueError("PSG write must fit u8")
        if value & 0x80:
            channel = (value >> 5) & 0x03
            is_volume = bool(value & 0x10)
            data = value & 0x0F
            self.latched_channel = channel
            self.latched_volume = is_volume
            if is_volume:
                self.volume[channel] = data
            elif channel == 3:
                self.noise_control = data & 0x07
                self._noise_lfsr = 0x8000
                self._noise_output = 1.0
            else:
                self.tone_period[channel] = (self.tone_period[channel] & 0x3F0) | data
        else:
            channel = self.latched_channel
            data = value & 0x3F
            if self.latched_volume:
                self.volume[channel] = data & 0x0F
            elif channel == 3:
                self.noise_control = data & 0x07
                self._noise_lfsr = 0x8000
                self._noise_output = 1.0
            else:
                self.tone_period[channel] = (
                    self.tone_period[channel] & 0x00F
                ) | (data << 4)

    @staticmethod
    def attenuation(level: int) -> float:
        if level >= 15:
            return 0.0
        return 10.0 ** (-(2.0 * level) / 20.0)

    def tone_frequency(self, channel: int) -> float:
        period = self.tone_period[channel] & 0x3FF
        if period <= 1:
            return 0.0
        return self.clock_hz / (32.0 * period)

    def noise_frequency(self) -> float:
        rate = self.noise_control & 0x03
        if rate == 3:
            return self.tone_frequency(2)
        return self.clock_hz / float(512 << rate)

    def sample(self, sample_rate: int) -> float:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        mixed = 0.0
        for channel in range(3):
            frequency = self.tone_frequency(channel)
            if frequency > 0:
                self._tone_phase[channel] = (
                    self._tone_phase[channel] + frequency / sample_rate
                ) % 1.0
                wave_value = 1.0 if self._tone_phase[channel] < 0.5 else -1.0
                mixed += wave_value * self.attenuation(self.volume[channel])
        frequency = self.noise_frequency()
        if frequency > 0:
            self._noise_phase += frequency / sample_rate
            while self._noise_phase >= 1.0:
                self._noise_phase -= 1.0
                white = bool(self.noise_control & 0x04)
                bit0 = self._noise_lfsr & 1
                feedback = bit0 ^ ((self._noise_lfsr >> 3) & 1) if white else bit0
                self._noise_lfsr = (self._noise_lfsr >> 1) | (feedback << 15)
                self._noise_output = 1.0 if (self._noise_lfsr & 1) else -1.0
            mixed += self._noise_output * self.attenuation(self.volume[3])
        return max(-1.0, min(1.0, mixed / 4.0))

    def state(self) -> dict[str, object]:
        return {
            "clock_hz": self.clock_hz,
            "tone_period": list(self.tone_period),
            "tone_frequency": [self.tone_frequency(i) for i in range(3)],
            "volume": list(self.volume),
            "noise_control": self.noise_control,
            "noise_frequency": self.noise_frequency(),
            "latched_channel": self.latched_channel,
            "latched_volume": self.latched_volume,
        }


def render_sn76489(
    writes: Iterable[ChipWrite],
    *,
    duration: float,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    clock_hz: int = GENESIS_PSG_CLOCK,
    gain: float = 0.85,
) -> bytes:
    if duration <= 0 or not math.isfinite(duration):
        raise AudioTraceError("duration must be finite and positive")
    if sample_rate < 8_000 or sample_rate > 384_000:
        raise AudioTraceError("sample rate is outside 8000..384000")
    if gain <= 0 or not math.isfinite(gain):
        raise AudioTraceError("gain must be finite and positive")
    ordered = list(writes)
    for write in ordered:
        if write.chip != "sn76489":
            raise AudioTraceError(
                f"SN76489 renderer cannot synthesize {write.chip} writes"
            )
        if write.at > duration:
            raise AudioTraceError(
                f"write at {write.at:.6f}s lies after requested duration {duration:.6f}s"
            )
    total_samples = int(round(duration * sample_rate))
    psg = SN76489(clock_hz)
    output = bytearray(total_samples * 2)
    write_index = 0
    for sample_index in range(total_samples):
        now = sample_index / sample_rate
        while write_index < len(ordered) and ordered[write_index].at <= now + 1e-12:
            psg.write(ordered[write_index].value)
            write_index += 1
        value = int(round(psg.sample(sample_rate) * gain * 32767.0))
        value = max(-32768, min(32767, value))
        struct.pack_into("<h", output, sample_index * 2, value)
    return bytes(output)


def write_wav(path: Path, pcm: bytes, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    if len(pcm) % 2:
        raise AudioTraceError("16-bit mono PCM byte count must be even")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)


def _tone_writes(channel: int, frequency: float, volume: int, at: float) -> list[ChipWrite]:
    if channel not in (0, 1, 2):
        raise ValueError("tone channel must be 0..2")
    period = max(2, min(0x3FF, int(round(GENESIS_PSG_CLOCK / (32 * frequency)))))
    latch_tone = 0x80 | (channel << 5) | (period & 0x0F)
    data_tone = (period >> 4) & 0x3F
    latch_volume = 0x90 | (channel << 5) | (volume & 0x0F)
    return [
        ChipWrite(at=at, chip="sn76489", value=latch_tone),
        ChipWrite(at=at, chip="sn76489", value=data_tone),
        ChipWrite(at=at, chip="sn76489", value=latch_volume),
    ]


def demo_trace() -> list[ChipWrite]:
    """A short deterministic three-voice arpeggio plus noise click."""

    writes: list[ChipWrite] = []
    notes = [261.6256, 329.6276, 391.9954, 523.2511]
    for index, frequency in enumerate(notes):
        at = index * 0.25
        writes.extend(_tone_writes(0, frequency, 2, at))
        writes.extend(_tone_writes(1, frequency / 2.0, 5, at))
    # Noise channel: white noise at the fastest fixed rate, briefly audible.
    writes.append(ChipWrite(at=0.0, chip="sn76489", value=0xE4))
    writes.append(ChipWrite(at=0.0, chip="sn76489", value=0xF8))
    writes.append(ChipWrite(at=0.08, chip="sn76489", value=0xFF))
    # Silence tones at the end.
    for channel in range(3):
        writes.append(
            ChipWrite(at=1.0, chip="sn76489", value=0x90 | (channel << 5) | 0x0F)
        )
    return sorted(writes, key=lambda write: write.at)


class YM2612TraceState:
    """Register-retention model for integration work; not an FM synthesizer."""

    def __init__(self) -> None:
        self.address_latch = [0, 0]
        self.registers = [bytearray(256), bytearray(256)]
        self.key_on_events: list[dict[str, int]] = []

    def write_port(self, port: int, value: int, *, data: bool) -> None:
        if port not in (0, 1):
            raise ValueError("YM2612 port must be 0 or 1")
        value &= 0xFF
        if not data:
            self.address_latch[port] = value
            return
        address = self.address_latch[port]
        self.registers[port][address] = value
        if port == 0 and address == 0x28:
            self.key_on_events.append(
                {
                    "channel": (value & 0x03) + (3 if value & 0x04 else 0),
                    "operators": (value >> 4) & 0x0F,
                }
            )

    def apply(self, write: ChipWrite) -> None:
        if write.chip != "ym2612":
            raise AudioTraceError("YM2612 state can only apply YM2612 records")
        if write.address is not None:
            self.address_latch[write.port] = write.address
            self.write_port(write.port, write.value, data=True)
        else:
            # Trace convention: port 0/1 are address writes; 2/3 are not representable
            # in ChipWrite, so an explicit address is required for data records.
            raise AudioTraceError("YM2612 trace record requires an address")

    def summary(self) -> dict[str, object]:
        nonzero = []
        for port in range(2):
            for address, value in enumerate(self.registers[port]):
                if value:
                    nonzero.append(
                        {"port": port, "address": address, "value": int(value)}
                    )
        return {"nonzero_registers": nonzero, "key_on_events": self.key_on_events}
