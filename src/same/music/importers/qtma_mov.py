"""Strict self-contained QuickTime ``musi`` track extraction."""

from __future__ import annotations

from dataclasses import dataclass

from ..model import Provenance
from ..segmented import ByteSourceSegment, SegmentedByteSource


class QtmaMovieError(ValueError):
    def __init__(self, code: str, source: str, byte_offset: int, path: str, detail: str) -> None:
        self.code = code
        self.source = source
        self.byte_offset = byte_offset
        self.path = path
        super().__init__(f"QTMA movie {source!r} {code} at byte {byte_offset} ({path}): {detail}")


@dataclass(frozen=True, slots=True)
class QtmaMovieSample:
    index: int
    offset: int
    size: int
    duration: int
    description_index: int
    payload: bytes


@dataclass(frozen=True, slots=True)
class QtmaMovieDescription:
    index: int
    offset: int
    size: int
    event_offset: int
    events: bytes


@dataclass(frozen=True, slots=True)
class QtmaMusicTrack:
    track_index: int
    time_scale: int
    duration: int
    description: QtmaMovieDescription
    samples: tuple[QtmaMovieSample, ...]
    event_source: SegmentedByteSource

    @property
    def description_events(self) -> bytes:
        return self.description.events

    @property
    def event_data(self) -> bytes:
        return self.event_source.data


@dataclass(frozen=True, slots=True)
class _Atom:
    kind: bytes
    offset: int
    payload_offset: int
    end: int
    path: str

    @property
    def payload_size(self) -> int:
        return self.end - self.payload_offset


def _u32(raw: bytes, offset: int) -> int:
    return int.from_bytes(raw[offset : offset + 4], "big")


def _u64(raw: bytes, offset: int) -> int:
    return int.from_bytes(raw[offset : offset + 8], "big")


def _label(kind: bytes) -> str:
    return kind.decode("latin-1")


def _error(code: str, source: str, offset: int, path: str, detail: str) -> QtmaMovieError:
    return QtmaMovieError(code, source, offset, path, detail)


def _atoms(raw: bytes, start: int, end: int, source: str, parent: str) -> tuple[_Atom, ...]:
    output: list[_Atom] = []
    offset = start
    while offset < end:
        if end - offset < 8:
            raise _error("truncated_atom_header", source, offset, parent, f"{end - offset} trailing bytes cannot hold an atom header")
        size32 = _u32(raw, offset)
        kind = raw[offset + 4 : offset + 8]
        header = 8
        if size32 == 1:
            if end - offset < 16:
                raise _error("truncated_atom_header", source, offset, parent, "extended-size atom has no 64-bit size")
            size = _u64(raw, offset + 8)
            header = 16
        elif size32 == 0:
            size = end - offset
        else:
            size = size32
        path = f"{parent}/{_label(kind)}"
        if size < header:
            raise _error("invalid_atom_size", source, offset, path, f"declared size {size} is below its {header}-byte header")
        atom_end = offset + size
        if atom_end > end:
            raise _error("atom_out_of_bounds", source, offset, path, f"declared end {atom_end} exceeds parent end {end}")
        output.append(_Atom(kind, offset, offset + header, atom_end, path))
        offset = atom_end
    return tuple(output)


def _children(raw: bytes, atom: _Atom, source: str) -> tuple[_Atom, ...]:
    return _atoms(raw, atom.payload_offset, atom.end, source, atom.path)


def _one(atoms: tuple[_Atom, ...], kind: bytes, source: str, owner: _Atom) -> _Atom:
    found = tuple(atom for atom in atoms if atom.kind == kind)
    if len(found) != 1:
        raise _error("required_atom_count", source, owner.offset, owner.path, f"expected one {_label(kind)!r} child, found {len(found)}")
    return found[0]


def _fullbox(raw: bytes, atom: _Atom, source: str, minimum: int = 4) -> bytes:
    payload = raw[atom.payload_offset : atom.end]
    if len(payload) < minimum:
        raise _error("truncated_table", source, atom.offset, atom.path, f"requires at least {minimum} payload bytes, got {len(payload)}")
    if payload[0:4] != bytes(4):
        raise _error("unsupported_fullbox", source, atom.payload_offset, atom.path, f"version/flags {payload[0:4].hex()} are unsupported")
    return payload


def _mdhd(raw: bytes, atom: _Atom, source: str) -> tuple[int, int]:
    payload = raw[atom.payload_offset : atom.end]
    if len(payload) < 4:
        raise _error("truncated_mdhd", source, atom.offset, atom.path, "header is absent")
    version = payload[0]
    if payload[1:4] != bytes(3):
        raise _error("unsupported_fullbox", source, atom.payload_offset, atom.path, "flags are nonzero")
    if version == 0:
        if len(payload) < 20:
            raise _error("truncated_mdhd", source, atom.offset, atom.path, "version 0 fields are truncated")
        time_scale, duration = _u32(payload, 12), _u32(payload, 16)
    elif version == 1:
        if len(payload) < 32:
            raise _error("truncated_mdhd", source, atom.offset, atom.path, "version 1 fields are truncated")
        time_scale, duration = _u32(payload, 20), _u64(payload, 24)
    else:
        raise _error("unsupported_mdhd", source, atom.payload_offset, atom.path, f"version {version} is unsupported")
    if time_scale == 0:
        raise _error("invalid_time_scale", source, atom.payload_offset, atom.path, "time scale is zero")
    return time_scale, duration


def _sample_descriptions(
    raw: bytes, atom: _Atom, source: str,
) -> tuple[QtmaMovieDescription, ...]:
    payload = _fullbox(raw, atom, source, 8)
    count = _u32(payload, 4)
    offset = 8
    descriptions: list[QtmaMovieDescription] = []
    for index in range(count):
        if len(payload) - offset < 16:
            raise _error("truncated_stsd", source, atom.payload_offset + offset, atom.path, f"description {index + 1} header is truncated")
        size = _u32(payload, offset)
        if size < 20 or offset + size > len(payload):
            raise _error("invalid_sample_description", source, atom.payload_offset + offset, atom.path, f"description {index + 1} size {size} is invalid")
        entry = payload[offset : offset + size]
        if entry[4:8] != b"musi":
            raise _error("unsupported_sample_description", source, atom.payload_offset + offset, atom.path, f"description {index + 1} format is {_label(entry[4:8])!r}")
        if entry[8:14] != bytes(6) or int.from_bytes(entry[14:16], "big") != 1:
            raise _error("unsupported_data_reference", source, atom.payload_offset + offset, atom.path, "only self-contained data reference 1 is supported")
        if entry[16:20] != bytes(4):
            raise _error("unsupported_music_flags", source, atom.payload_offset + offset + 16, atom.path, f"music flags are {entry[16:20].hex()}, not zero")
        events = entry[20:]
        if len(events) % 4:
            raise _error("unaligned_qtma_data", source, atom.payload_offset + offset + 20, atom.path, "description events are not 32-bit aligned")
        entry_offset = atom.payload_offset + offset
        descriptions.append(QtmaMovieDescription(
            index + 1, entry_offset, size, entry_offset + 20, events,
        ))
        offset += size
    if count == 0 or offset != len(payload):
        raise _error("invalid_stsd", source, atom.offset, atom.path, f"description count {count} leaves {len(payload) - offset} bytes")
    return tuple(descriptions)


def _counted_u32(raw: bytes, atom: _Atom, source: str, width: int) -> tuple[tuple[int, ...], ...]:
    payload = _fullbox(raw, atom, source, 8)
    count = _u32(payload, 4)
    required = 8 + count * width * 4
    if required != len(payload):
        raise _error("invalid_table_size", source, atom.offset, atom.path, f"count {count} requires {required} payload bytes, got {len(payload)}")
    return tuple(tuple(_u32(payload, 8 + (row * width + column) * 4) for column in range(width)) for row in range(count))


def _sample_sizes(raw: bytes, atom: _Atom, source: str) -> tuple[int, ...]:
    payload = _fullbox(raw, atom, source, 12)
    common, count = _u32(payload, 4), _u32(payload, 8)
    required = 12 if common else 12 + count * 4
    if required != len(payload):
        raise _error("invalid_table_size", source, atom.offset, atom.path, f"sample count {count} requires {required} payload bytes, got {len(payload)}")
    return (common,) * count if common else tuple(_u32(payload, 12 + index * 4) for index in range(count))


def _chunk_offsets(raw: bytes, atom: _Atom, source: str) -> tuple[int, ...]:
    payload = _fullbox(raw, atom, source, 8)
    count = _u32(payload, 4)
    width = 8 if atom.kind == b"co64" else 4
    required = 8 + count * width
    if required != len(payload):
        raise _error("invalid_table_size", source, atom.offset, atom.path, f"chunk count {count} requires {required} payload bytes, got {len(payload)}")
    read = _u64 if width == 8 else _u32
    return tuple(read(payload, 8 + index * width) for index in range(count))


def _durations(raw: bytes, atom: _Atom, source: str, count: int) -> tuple[int, ...]:
    rows = _counted_u32(raw, atom, source, 2)
    output: list[int] = []
    for sample_count, duration in rows:
        if sample_count == 0 or duration == 0 or sample_count > count - len(output):
            raise _error("invalid_stts", source, atom.offset, atom.path, f"run ({sample_count}, {duration}) exceeds {count} samples")
        output.extend((duration,) * sample_count)
    if len(output) != count:
        raise _error("invalid_stts", source, atom.offset, atom.path, f"table describes {len(output)} of {count} samples")
    return tuple(output)


def _in_mdat(start: int, size: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(first <= start and start + size <= last for first, last in ranges)


def _extract_track(raw: bytes, track: _Atom, track_index: int, source: str, mdat_ranges: tuple[tuple[int, int], ...]) -> QtmaMusicTrack:
    mdia = _one(_children(raw, track, source), b"mdia", source, track)
    mdia_children = _children(raw, mdia, source)
    time_scale, media_duration = _mdhd(raw, _one(mdia_children, b"mdhd", source, mdia), source)
    minf = _one(mdia_children, b"minf", source, mdia)
    stbl = _one(_children(raw, minf, source), b"stbl", source, minf)
    tables = _children(raw, stbl, source)
    descriptions = _sample_descriptions(raw, _one(tables, b"stsd", source, stbl), source)
    sizes = _sample_sizes(raw, _one(tables, b"stsz", source, stbl), source)
    if not sizes or any(size == 0 or size % 4 for size in sizes):
        raise _error("unaligned_qtma_data", source, stbl.offset, stbl.path, "music samples must be nonempty and 32-bit aligned")
    durations = _durations(raw, _one(tables, b"stts", source, stbl), source, len(sizes))
    mappings = _counted_u32(raw, _one(tables, b"stsc", source, stbl), source, 3)
    if not mappings or mappings[0][0] != 1:
        raise _error("invalid_stsc", source, stbl.offset, stbl.path, "first chunk mapping must begin at chunk 1")
    for index, (first, per_chunk, description) in enumerate(mappings):
        if per_chunk == 0 or not 1 <= description <= len(descriptions):
            raise _error("invalid_stsc", source, stbl.offset, stbl.path, f"mapping {index} has invalid count or description")
        if index and first <= mappings[index - 1][0]:
            raise _error("invalid_stsc", source, stbl.offset, stbl.path, "first-chunk values are not strictly increasing")
    offset_atoms = tuple(atom for atom in tables if atom.kind in (b"stco", b"co64"))
    if len(offset_atoms) != 1:
        raise _error("required_atom_count", source, stbl.offset, stbl.path, f"expected one stco/co64 child, found {len(offset_atoms)}")
    chunks = _chunk_offsets(raw, offset_atoms[0], source)
    samples: list[QtmaMovieSample] = []
    sample_index = 0
    for chunk_index, chunk_offset in enumerate(chunks, 1):
        mapping = mappings[0]
        for candidate in mappings[1:]:
            if candidate[0] > chunk_index:
                break
            mapping = candidate
        cursor = chunk_offset
        for _within in range(mapping[1]):
            if sample_index >= len(sizes):
                raise _error("invalid_stsc", source, stbl.offset, stbl.path, "chunk table describes more samples than stsz")
            size = sizes[sample_index]
            if not _in_mdat(cursor, size, mdat_ranges):
                raise _error("sample_out_of_bounds", source, cursor, stbl.path, f"sample {sample_index} is outside self-contained mdat payloads")
            samples.append(QtmaMovieSample(sample_index, cursor, size, durations[sample_index], mapping[2], raw[cursor : cursor + size]))
            cursor += size
            sample_index += 1
    if sample_index != len(sizes):
        raise _error("invalid_stsc", source, stbl.offset, stbl.path, f"chunk table describes {sample_index} of {len(sizes)} samples")
    used = {sample.description_index for sample in samples}
    if len(used) != 1:
        raise _error("description_change", source, stbl.offset, stbl.path, "music description changes within one extracted track")
    description = descriptions[next(iter(used)) - 1]
    event_data = description.events + b"".join(sample.payload for sample in samples)
    segments: list[ByteSourceSegment] = [ByteSourceSegment(
        0, len(description.events), Provenance(
            source, track=track_index,
            sample_description=description.index,
            byte_offset=description.event_offset,
        ),
    )]
    logical_offset = len(description.events)
    for sample in samples:
        segments.append(ByteSourceSegment(
            logical_offset, sample.size, Provenance(
                source, track=track_index,
                sample_description=sample.description_index,
                sample=sample.index, byte_offset=sample.offset,
            ),
        ))
        logical_offset += sample.size
    event_source = SegmentedByteSource(
        event_data, Provenance(source, track=track_index), tuple(segments),
    )
    if sum(durations) != media_duration:
        raise _error("duration_mismatch", source, stbl.offset, stbl.path, f"stts duration {sum(durations)} differs from mdhd {media_duration}")
    return QtmaMusicTrack(
        track_index, time_scale, media_duration, description, tuple(samples),
        event_source,
    )


def extract_qtma_movie(raw: bytes, *, source: str = "qtma.mov", music_track: int = 0) -> QtmaMusicTrack:
    """Extract one self-contained ``musi`` track without decoding QTMA words."""
    if music_track < 0:
        raise ValueError("music track index must be nonnegative")
    top = _atoms(raw, 0, len(raw), source, "root")
    moov_atoms = tuple(atom for atom in top if atom.kind == b"moov")
    if len(moov_atoms) != 1:
        raise _error("required_atom_count", source, 0, "root", f"expected one 'moov' atom, found {len(moov_atoms)}")
    mdat_ranges = tuple((atom.payload_offset, atom.end) for atom in top if atom.kind == b"mdat")
    if not mdat_ranges:
        raise _error("missing_mdat", source, 0, "root", "no self-contained media data atom exists")
    tracks = tuple(atom for atom in _children(raw, moov_atoms[0], source) if atom.kind == b"trak")
    music: list[tuple[int, _Atom]] = []
    for track_index, track in enumerate(tracks):
        track_children = _children(raw, track, source)
        mdia_atoms = tuple(atom for atom in track_children if atom.kind == b"mdia")
        if len(mdia_atoms) != 1:
            continue
        mdia_children = _children(raw, mdia_atoms[0], source)
        handlers = tuple(atom for atom in mdia_children if atom.kind == b"hdlr")
        if len(handlers) != 1 or handlers[0].payload_size < 12:
            continue
        payload = raw[handlers[0].payload_offset : handlers[0].end]
        if payload[8:12] == b"musi":
            music.append((track_index, track))
    if music_track >= len(music):
        raise _error("missing_music_track", source, moov_atoms[0].offset, moov_atoms[0].path, f"requested music track {music_track}, found {len(music)}")
    track_index, track = music[music_track]
    return _extract_track(raw, track, track_index, source, mdat_ranges)
