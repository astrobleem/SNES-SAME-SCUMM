"""Generic contiguous byte sources with exact physical provenance."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .model import Provenance


class SegmentedSourceError(ValueError):
    def __init__(self, code: str, byte_offset: int, detail: str) -> None:
        self.code = code
        self.byte_offset = byte_offset
        super().__init__(
            f"segmented music source {code} at logical byte {byte_offset}: {detail}"
        )


@dataclass(frozen=True, slots=True)
class ByteSourceSegment:
    """One logical span and the provenance of its first physical byte."""

    logical_offset: int
    length: int
    provenance: Provenance

    def __post_init__(self) -> None:
        if (
            isinstance(self.logical_offset, bool)
            or not isinstance(self.logical_offset, int)
            or self.logical_offset < 0
        ):
            raise ValueError("segment logical offset must be a nonnegative integer")
        if (
            isinstance(self.length, bool)
            or not isinstance(self.length, int)
            or self.length <= 0
        ):
            raise ValueError("segment length must be a positive integer")
        physical = self.provenance.byte_offset
        if (
            isinstance(physical, bool)
            or not isinstance(physical, int)
        ):
            raise ValueError("segment provenance requires a physical byte offset")

    @property
    def end(self) -> int:
        return self.logical_offset + self.length


@dataclass(frozen=True, slots=True)
class SegmentedByteSource:
    """Bytes plus a gap-free map back to independently owned source spans."""

    data: bytes
    provenance: Provenance
    segments: tuple[ByteSourceSegment, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.data, bytes):
            raise TypeError("segmented source data must be bytes")
        expected = 0
        for segment in self.segments:
            if not isinstance(segment, ByteSourceSegment):
                raise TypeError("segmented source entries must be byte source segments")
            if segment.provenance.source != self.provenance.source:
                raise SegmentedSourceError(
                    "source_mismatch", segment.logical_offset,
                    f"segment source {segment.provenance.source!r} differs from "
                    f"{self.provenance.source!r}",
                )
            if segment.logical_offset > expected:
                raise SegmentedSourceError(
                    "coverage_gap", expected,
                    f"next segment begins at {segment.logical_offset}",
                )
            if segment.logical_offset < expected:
                raise SegmentedSourceError(
                    "coverage_overlap", segment.logical_offset,
                    f"previous coverage ends at {expected}",
                )
            if segment.end > len(self.data):
                raise SegmentedSourceError(
                    "coverage_out_of_bounds", segment.logical_offset,
                    f"segment ends at {segment.end}, data ends at {len(self.data)}",
                )
            expected = segment.end
        if expected != len(self.data):
            raise SegmentedSourceError(
                "coverage_gap", expected,
                f"data ends at {len(self.data)}",
            )

    def resolve(
        self, byte_offset: int, byte_length: int, *, word_offset: int | None = None,
    ) -> Provenance:
        """Resolve a complete framed item; crossing a segment fails closed."""
        if (
            isinstance(byte_offset, bool) or not isinstance(byte_offset, int)
            or isinstance(byte_length, bool) or not isinstance(byte_length, int)
            or byte_offset < 0 or byte_length <= 0
        ):
            raise SegmentedSourceError(
                "invalid_span", byte_offset,
                f"length {byte_length} is not a positive in-range span",
            )
        end = byte_offset + byte_length
        if end > len(self.data):
            raise SegmentedSourceError(
                "span_out_of_bounds", byte_offset,
                f"span ends at {end}, data ends at {len(self.data)}",
            )
        for segment in self.segments:
            if segment.logical_offset <= byte_offset < segment.end:
                if end > segment.end:
                    raise SegmentedSourceError(
                        "framing_crosses_segment", byte_offset,
                        f"span {byte_offset}..{end} crosses boundary {segment.end}",
                    )
                physical = int(segment.provenance.byte_offset) + (
                    byte_offset - segment.logical_offset
                )
                return replace(
                    segment.provenance, byte_offset=physical,
                    word_offset=word_offset,
                )
        raise SegmentedSourceError(
            "uncovered_span", byte_offset, "no segment owns the span",
        )
