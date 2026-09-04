# SAME music-device architecture

SAME treats a music device as a reusable semantic adapter, not as a collection
of cue-number exceptions. The design borrows the useful separation from
QuickTime Music Architecture: an importer describes musical intent, a source
device model preserves the behavior of the device for which that intent was
authored, and a backend decides how to realize it on the available hardware.

```text
SCUMM iMUSE / QTMA / MIDI / native score importer
                         |
                         v
                 canonical SequenceIR
             parts, notes, controls, timing,
             loops, identities, provenance
                         |
                         v
                source-device response
           OPL patch semantics, controller law,
              bend/range and percussion rules
                         |
                         v
             instrument and voice realization
        fingerprinted zones, allocation, expression
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          TAD/BRR      OPL chip     rendered/MSU
```

The normalized SAME audio service packet remains the engine/backend boundary.
The symbolic model lives above that packet ABI and can feed a compiled song,
live chip commands, or a rendered stream without making SCUMM semantics part of
the generic audio service.

## Identities that must remain separate

- A **part** is a logical musical role and instrument request.
- A **note** is a stable lifetime within a part. Overlapping equal pitches are
  still different notes.
- A **voice** is a temporary physical playback allocation.
- A source **channel** is importer provenance or source-device state, not a
  promise that a backend owns a permanent voice.

Conflating these was the root of many cue-specific compromises. `SequenceIR`
therefore gives every note a stable ID, records ordered source ticks, preserves
controller events, and validates note lifetimes before a backend sees them.

## Instrument identity and octave zones

An instrument request may carry portable, named, numbered, GM-fallback, and
device-specific identities. SCUMM AdLib patches use SHA-256 of the complete
30-byte decoded definition. A compiled bank resolves that fingerprint and pitch
to exactly one listener-approved sample zone. Each zone pins:

- source-device and patch identity;
- sample-resource SHA-256;
- root and permitted pitch range;
- loop geometry;
- listener-review status; and
- the velocity/CC7 calibration at which it was captured.

This makes the successful Monkey Island/Fate octave-splitting technique a bank
facility instead of hidden MML knowledge. Resolution fails closed for an
unreviewed patch, an uncovered octave, an ambiguous zone, or altered sample
bytes.

## First implemented source device

`same.music.devices.scumm_adlib.ScummV5AdlibDevice` implements the SCUMM v5
AdLib driver's nonlinear volume table and patch-dependent operator attenuation.
It is a performance-response model, not an OPL waveform synthesizer. Nuked OPL
remains the exact waveform oracle. A sample backend compares the requested
velocity and CC7 response with the recorded capture calibration and derives a
bounded backend volume. FM patches use the carrier response; additive patches
use a deterministic combined-power approximation for both audible operators.

Fate sound 154 is the first end-to-end consumer. Its taken iMUSE jump path is
normalized into `SequenceIR`, instrument zones resolve by patch fingerprint and
pitch, and the shared device supplies dynamics before the existing eight-voice
TAD realization. The new path regenerates the accepted MML byte-for-byte:

```text
sound_154.mml SHA-256
45110f50f2b4d4ff31a922f8eb2c43d886dbba5940dea8dae5ea0b3f035a5a18
```

That invariant is important: this slice extracts reusable semantics without
silently retuning the cue that passed listener review.

## M2 importer and realization seam

M2 removes the remaining sound-154 knowledge from the reusable path. The
generic SCUMM iMUSE importer accepts an explicit timeline selection/rebase and
produces `SequenceIR`; the generic AdLib realizer verifies each part's patch
identity, applies the shared device response, resolves the reviewed bank, and
returns source-neutral zoned notes. Sound 154 now retains only its actual
branch coordinates, compiled instrument order, and eight-voice MML policy.

An independently authored SCUMM AdLib conformance cue is the second consumer.
It carries two notes and an active-note CC7 change through the same importer,
device, bank resolver, and realizer. The conformance cue is intentional: none
of the other real Fate cues is completely covered by the seven listener-approved
sound-154 patch/range zones. M2 records that as a fail-closed bank boundary
rather than silently granting approval to another timbre or octave.

The first raw QTMA importer is also implemented. Its event words follow the
QuickTime 7.6.6 `QuickTimeMusic.h` layouts and decode:

- standard Note and Rest events;
- signed 8.8 Controller values normalized to signed Q16.16;
- End and informational Marker events; and
- framed General Note Request events, including tone names, GM fallback,
  percussion identity, requested polyphony, and typical polyphony.

The copyright-free 232-byte fixture has two parts, a chord, percussion crossing
a rest, a melody note, Volume/Pan/Sustain controls, a 600-tick end, and a
three-note peak. Its raw SHA-256 is
`1a595217e6ef5e05e3f15c193a92d364243db7c308c179ff48109e1456e2b0c0`.
The committed golden trace is source-neutral and byte-stable. Truncation,
invalid/mismatched General framing, unknown parts, unsupported event families,
and data after End report structured source byte/word offsets.

## M3 deterministic playback and reference synthesis

`PlaybackSession` is the first live consumer of `SequenceIR`. It maps every
source tick to an absolute sample position with integer rational arithmetic;
there is no per-event rounding accumulator to drift. Logical notes receive the
lowest available bounded voice handle. A budget failure identifies the exact
tick, requested note, and complete active-note set rather than stealing a voice
silently.

Controller 64 sustain state is part-local. Note-off events under an active pedal
remain allocated and are released in stable voice order when that part's pedal
clears. Other parts remain unaffected. Natural completion and explicit stop
both release every surviving voice and call the backend's stop boundary.

The deliberately plain reference backend uses only integer phase, triangle,
noise, volume, and mixing operations. It is an audible conformance oracle, not
an attempt to imitate a source synthesizer or a production SNES arrangement.
The M2 fixture renders exactly 24,000 mono signed-16 frames at 24 kHz. It has no
clipped samples, PCM SHA-256
`0b5d2002c7a3f72069ddc373f6000ef90c29ff8b71de37909bb57eafd7a933a7`,
and canonical WAV SHA-256
`5555b38dc9c89f9cd6572003ad1cfef3b39d81b0037cb5c5cbb91d77a9fad811`.
The committed JSON oracle binds those results to the M2 source hash.

## M4 real Monkey v5 cross-title proof

M4 mounts the supplied Ultimate Talkie index/data directly from its ZIP and
does not extract or commit game bytes. A complete inventory accounts for all
138 advertised sounds: 97 decode as AdLib, 35 are the title's 24-byte silent
stubs, and six are SBL-only effects. This exposed two valid early-v5 container
forms: repeated unselected SBL children and a zero-padded iMUSE jump. The
decoder accepts only those bounded forms; duplicate selected renditions and
nonzero jump padding still fail closed.

The room-78 church cue is the first real cross-title consumer. It carries one
AdLib patch, one pan control, 197 attacks from MIDI 36 through 91, an explicit
whole-cue loop, and peak/requested polyphony 8. The generic importer now
preserves standard pan and derives requested polyphony from the selected path.
Patch extraction also requires one immutable complete definition per channel.

Its patch fingerprint resolves to two exact, manually reviewed Monkey Island
organ samples already authorized for this repository: `mt32_p13_low` below
MIDI 58 and `mt32_p13` at 58 and above. This is an approved arrangement mapping
between the AdLib identity and the reviewed MI rendition, not a claim that the
MT-32 waveform equals OPL. The mapping is isolated in a bank manifest; another
patch or uncovered pitch cannot inherit it.

`tools/validate_monkey_v5_music.py` emits the complete local inventory, IR,
playback actions, resolved notes, and audible reference WAV. The commercial
score-derived traces stay under `build/`; documentation records only identities
and digests. The deterministic WAV SHA-256 is
`0f41ec1d04eb7dd0cbd7b867b81c2ec1aa8438db91504b91384ad96bbfce3361`.

## Present boundary and next proof

This foundation does not yet provide MOV `musi` extraction, runtime OPL
synthesis on SNES, or automatic conversion of every SCUMM title. Those belong
above or below the stable playback contract rather than in an importer.

M5 now provides the generic sampled-backend compiler. It consumes only the
canonical sequence, resolved sampled notes, and named backend instruments. It
preserves stereo pan, volume automation, whole-song loops, and eight bounded
voices. TAD's two-tick duration floor is handled as visible target adaptation:
one leading tick of bias and two isolated one-tick release adjustments for the
Monkey church cue. The 197 attacks are otherwise unchanged. A copyright-free
fixture independently proves the compiler has no importer or game dependency.

The resulting Monkey MML and TAD binary are repeatable, and a real-DSP capture
crosses the complete loop. Its measured 57.303875-second repeat matches the
32,040 Hz clock-corrected prediction and correlates 0.998933 with the first
traversal window. The special build uses an opt-in precompiled-TAD input; normal
Fate assets and ROM identities are restored and independently checked.

M6 adds the profile-driven compiled music catalog. It binds logical identity,
source resource/SHA-256, compiled song name/ID, duration, time scale, and loop.
Both real v5 archives validate against their catalogs and TAD enums. The SNES
backend now performs a generated bounded lookup and contains no Fate, Monkey,
or cue-number mapping. Catalog/source identity also survives semantic compiled
playhead save/load without changing the normalized audio packet ABI.

M7 implements the declarative multi-song build graph. Profiles select importers,
device models, reviewed banks, target policies, expected MML, and catalog
identities. The generic runner has no SCUMM, title, or cue knowledge: a title
adapter supplies source bytes, renders a declared node, and finalizes the target
project. Source, bank, policy, compiler, and output hashes are recorded and
verified. Publication is one directory transaction, so an incomplete render or
compiler failure cannot replace the prior complete build.

The first real graphs regenerate Fate sounds 83 and 154 and Monkey church.
Their graph SHA-256 values are
`8c5ba6bb3a81ea49f17bbe43b3426e7849180abea583c251fb81e40c5743609e`
and `b216275ef992600f51b188fe69a584fc85f5e8431e0ee849f04abb4e7f969076`.
Repeated builds emit byte-identical MML, project, catalog, dependency manifest,
TAD binary, and report. The resulting Fate and Monkey ROMs are byte-identical to
M6, and fresh DSP captures pass both regenerated Fate cues plus Monkey's loop.
Commercial-derived intermediates remain under `build/`. MOV `musi` extraction
remains a separate adapter gate.

## M8 complete Fate graph

M8 accounts for every one of Fate's 19 compiled production entries. An exact
audit separates five reproducible conversions from fourteen immutable reviewed
arrangements. Sounds 18, 83, 150, and 192 regenerate through the current ROL
converter; sound 154 regenerates through the canonical AdLib branch and reviewed
Nuked-OPL zones. The remaining cues are declared with
`reviewed_immutable_mml_v1`, an exact dependency hash, and their raw source
identity. This is deliberate preservation, not an importer fallback.

The generated project references all 19 transaction-local MML outputs, so TAD
compilation no longer reaches back to per-cue production paths. Repeated builds
produce identical project, catalog, manifest, TAD, and report bytes. The TAD
binary and ROM remain exactly the accepted M7 identities, and fresh DSP gates
cover a short immutable cue, active virtualization, twelve-voice source density,
and CC7 automation with terminal fade.

## M9 profile-to-ROM ownership

The profile now owns the complete compiled-music handoff. Its
`music_build_graph` option must resolve to an `MBGR` resource whose graph profile
identity exactly equals the game ID. Compilation records the profile SHA-256 in
the transaction manifest. Before ROM assembly, the bundle verifier checks that
profile owner, graph, dependencies, compiler, every artifact, catalog schema,
and every catalog song name/ID against the emitted TAD enum file.

`tools/build_profile_music_rom.py` accepts the profile and external source
archive, builds the graph, verifies the inseparable bundle, and gives its own
catalog/TAD pair to the unchanged SNES backend. `--reuse` accepts only a valid
cached bundle and therefore needs no commercial archive. A crossed catalog is
rejected before ROM creation. Fate and Monkey both reproduce their accepted ROM
hashes and pass fresh representative DSP captures.

## M10 adapter registry and QTMA consumer

The profile orchestrator no longer imports or selects a SCUMM adapter. A small
registry resolves the exact `(engine_id, graph.adapter)` pair and records whether
that source family requires an external archive. Adapter mismatch is therefore a
pre-output error while graph compilation, bundle verification, catalog checking,
and ROM assembly remain engine-neutral.

The second registration is the `demo` engine with the repository-owned
`qtma_fixture_v1` family. It runs the strict QTMA importer, consumes source
sustain according to an explicit encoded-lifetime policy, passes CC7 and CC10
intent into the sampled backend, and creates deterministic copyright-free
marimba/noise samples. Those are conformance instruments, not claims of General
MIDI timbre fidelity. The resulting one-song bundle uses the identical
profile-to-ROM transaction and verified-cache path as Fate and Monkey.

## M11 non-SCUMM runtime consumer

M11 gives the QTMA profile an opt-in SNES personality that consumes the compiled
catalog at runtime. The personality emits only normalized `MUSIC_PLAY` and
`MUSIC_STOP` packets using logical identity 1; it has no TAD, SPC-port, importer,
or SCUMM dependency. Its compact WAITING/PLAYING/COMPLETE state makes the
synthetic score window observable without putting test policy in the backend.

Real-S-DSP evidence records exactly two audio-service packets, a nonzero and
unclipped QTMA capture, exact semantic transitions at frames 120 and 423, no
rejections, and final blank-song state. Keeping the personality separate from
the ordinary demo include preserves the M10 demo and both SCUMM ROM identities.

## M12 generic lifecycle coordinator

Duration and completion policy no longer lives in the synthetic QTMA engine.
Catalog generation emits a separate opt-in lifecycle table so the stable logical
to compiled-song mapping remains unchanged. The coordinator owns IDLE, PENDING,
PLAYING, COMPLETED, STOPPED, and FAILED states; it emits only normalized audio
packets and engine-service responses, and never reads TAD or hardware ports.

The QTMA personality now requests logical entry 1 and reacts to READY, STOPPED,
or FAILED. Real-emulator evidence fixes the request/start/completion response
schedule at semantic frames 120/135/423, with engine reactions one frame later,
and retains the exact one-play/one-stop backend trace. Host-side conformance
covers explicit stop, invalid identity, and looping tracks that never
auto-complete. MOV `musi` extraction remains the next independent adapter gate.

## M13 QuickTime `musi` container adapter

The MOV layer now ends exactly where the existing QTMA event importer begins.
It inventories a self-contained music track, validates its media time scale and
sample description, expands the bounded sample tables, and returns description
events plus ordered sample payloads. It knows nothing about parts, notes,
controllers, instruments, TAD, or engine lifecycle.

The repository-owned 536-byte movie deliberately uses an extended-size unknown
atom, places two NoteRequests in the `musi` sample description, and splits the
phrase across two samples. Normal and 64-bit chunk offsets are covered. The
reassembled bytes equal the prior raw QTMA fixture, so the produced TAD binary
and M12 runtime ROM are byte-identical despite the independent graph adapter and
profile. The next boundary is explicit rational normalization for movie time
scales that do not directly match a target clock.

## M14 rational time normalization

Time conversion is now a source-neutral transformation between import and
realization. It maps every absolute event, end, and loop position with integer
rational arithmetic. `exact` and `nearest_absolute` are graph-visible policies;
there is no implicit backend rounding. Original ticks and source scale remain in
event provenance, and collapsed notes/loops fail before realization.

The 600 Hz MOV fixture converts to the TAD backend's 125-tick scale with exact
one-second duration and a measured half-tick maximum positional error. Its
runtime lifecycle duration is 60 frames, independently proving that generated
catalog metadata follows the normalized score rather than the source word count.
M13's exact 125→125 policy returns the original sequence and preserves its TAD
and ROM bytes.

## M15 segmented importer provenance

Container concatenation no longer erases physical identity. The source-neutral
`SegmentedByteSource` binds a logical byte stream to contiguous physical spans;
each span carries the ordinary music `Provenance` record. Construction rejects
gaps, overlaps, source mismatches, and out-of-range coverage. Importers resolve
one complete framed item at a time, so a format event may never silently cross
a source-segment boundary.

The MOV adapter supplies three spans for the conformance track: one `stsd`
sample-description event area and two `mdat` media samples. The QTMA decoder is
still unaware of atoms and sample tables. It simply receives exact track,
sample-description, media-sample, absolute byte, and logical event-word identity
from the resolver. NoteRequest provenance now lives on `PartSpec`; scheduled
event provenance survives M14 time normalization unchanged except for the added
original source tick and scale.

This proves the in-memory audit trail. M16 will make that trail a canonical,
hash-bound graph artifact rather than losing it after MML realization.

## M16 canonical sequence audit

The build now emits a canonical sequencer-owned document containing the complete
imported and normalized IR, exact rational timing evidence, and resolved sampled
note identities. It contains no MOV atom model and no historical QuickTime
runtime behavior. QTMA is merely one producer of the same part, event, clock,
instrument-request, and provenance structures available to other importers.

Audit paths and hashes are graph declarations. Compilation rejects unexpected
bytes transactionally, and reuse verifies the audit alongside every other build
artifact. The artifact is currently deliberately one-way. M17 will add strict
IR decoding and replay so realization can consume the intermediate form without
loading the original source adapter.

## M17 canonical IR replay

Canonical audit IR is now a strict input, not merely output. Decoding rebuilds
typed model objects under exact-field rules and reapplies all `SequenceIR`
invariants. It also recomputes the imported-to-normalized rational transform and
requires complete structural equality with the recorded result and error
evidence.

The replay path consumes normalized IR and recorded sampled-note identities,
regenerates those identities for comparison, and invokes the existing MML
realizer. Tests disable both MOV and QTMA importer entry points; M13 and M14
still reproduce their exact MML. The next sequencer boundary is checkpointable
playback state, not additional source-format emulation.

## M18 sequencer save-state boundary

`PlaybackSession` now exposes two intentionally different save-state contracts.
A warm checkpoint belongs to one live in-process backend and restores the next
unconsumed event cursor, rational remainder, controller/sustain state, deferred
release order, and stable allocator ownership without issuing any backend
command. A cold checkpoint is a canonical, checksummed logical state document
accepted only by a fresh sequencer with matching IR, realization catalog,
engine/profile, timing, voice-policy, and loop identities. Validation is
transactional and source importers are outside the restore dependency graph.

Stable note IDs and monotonically assigned voice-generation IDs are serialized;
Python object identities and backend pointers are not. Cold active voices mean
only deterministic logical ownership. M18 does not serialize a synth voice's
sample cursor, envelope or oscillator phase, backend generation, or pending
commands, so it makes no sample-continuity claim. Exact cold audio continuation
requires a separately proven backend snapshot containing those fields.

## M19 normal SCUMM runtime integration

Monkey church sound 154 is no longer proven only from a debugger-injected
logical request. A copyright-free SCUMM v5 script now executes the real SNES
`$02` dispatcher path, yields across the asynchronous SAME service drain,
checks `$7C` running status, executes `$20`, checks stopped status, and restarts
the cue. The generated catalog performs the unchanged logical-154 to TAD-song-26
mapping.

The engine retains only the logical active sound needed by synchronous SCUMM
status semantics. Catalog entries, TAD song ids, loader state, and S-SMP/DSP
state stay below the audio-service boundary. The exact packet trace is
play/stop/play, and the debugger request byte remains zero. A fresh emulator
lifecycle proves the blank stop, restart readiness, and the accepted
57.303875-second loop at 0.998934 correlation. M19 deliberately adds no new
music source behavior or sequencer/save-state policy.
