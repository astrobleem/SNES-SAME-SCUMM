"""Backend-neutral symbolic music, device models, and instrument assets."""

from .instruments import InstrumentBank, InstrumentZone
from .model import (
    ControllerEvent,
    InstrumentRequest,
    MarkerEvent,
    NoteOffEvent,
    NoteOnEvent,
    PartSpec,
    Provenance,
    ScheduledEvent,
    SequenceIR,
)
from .realize import ResolvedAdlibNote, realize_scumm_adlib_notes, sequence_trace
from .playback import (
    ActiveVoiceState, CheckpointError, PlaybackAction, PlaybackBackend,
    PlaybackCheckpoint, PlaybackSession, VoiceBudgetError, sequence_ir_sha256,
)
from .reference import ReferenceRender, ReferenceSynth, pcm_wav, render_reference
from .backends import (
    SampledNote, TadCompileError, TadInstrument, TadMmlSong, TadPanPolicy,
    compile_tad_mml,
)
from .catalog import CompiledMusicCatalog, CompiledMusicEntry
from .build_graph import (
    MusicBuildAdapter, MusicBuildDependency, MusicBuildGraph, MusicBuildNode,
    compile_music_graph, verify_music_build,
)
from .profile_build import (
    ProfileMusicBundle, load_profile_music_graph, profile_music_owner,
    verify_profile_music_bundle,
)
from .lifecycle import (
    CompiledMusicLifecycle, MusicLifecycleAction, MusicLifecycleStatus,
)
from .timing import (
    TimeScaleError, TimeScaleNormalization, TimeScalePolicy,
    normalize_sequence_time_scale,
)
from .segmented import (
    ByteSourceSegment, SegmentedByteSource, SegmentedSourceError,
)
from .audit import (
    SequenceAudit, SequenceAuditError, canonical_sequence_ir,
    decode_canonical_sequence_ir, decode_sequence_audit, encode_sequence_audit,
)

__all__ = (
    "CompiledMusicCatalog", "CompiledMusicEntry", "ControllerEvent",
    "InstrumentBank", "InstrumentRequest", "InstrumentZone",
    "MarkerEvent", "NoteOffEvent", "NoteOnEvent", "PartSpec", "PlaybackAction",
    "PlaybackBackend", "PlaybackCheckpoint", "PlaybackSession", "Provenance",
    "ActiveVoiceState", "CheckpointError", "ReferenceRender",
    "ReferenceSynth", "ResolvedAdlibNote", "ScheduledEvent", "SequenceIR",
    "SampledNote", "TadCompileError", "TadInstrument", "TadMmlSong",
    "MusicBuildAdapter", "MusicBuildDependency", "MusicBuildGraph",
    "MusicBuildNode", "TadPanPolicy", "VoiceBudgetError",
    "ProfileMusicBundle",
    "CompiledMusicLifecycle", "MusicLifecycleAction", "MusicLifecycleStatus",
    "TimeScaleError", "TimeScaleNormalization", "TimeScalePolicy",
    "ByteSourceSegment", "SegmentedByteSource", "SegmentedSourceError",
    "canonical_sequence_ir", "encode_sequence_audit",
    "SequenceAudit", "SequenceAuditError", "decode_canonical_sequence_ir",
    "decode_sequence_audit", "sequence_ir_sha256",
    "compile_music_graph", "compile_tad_mml", "pcm_wav",
    "realize_scumm_adlib_notes", "render_reference", "sequence_trace",
    "normalize_sequence_time_scale",
    "load_profile_music_graph", "profile_music_owner",
    "verify_music_build", "verify_profile_music_bundle",
)
