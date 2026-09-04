# SAME audio

## Score intent versus rendition

S4 introduces `same_score_v1`, a small backend-neutral score resource. It keeps
timed note/control events, stable voice identities, duration, and loop points.
The SCUMM adapter saves these logical playheads and reconstructs playback after
load; it never saves opaque SPC state.

This deliberately separates composition from SNES arrangement. The manually
reviewed Monkey Island MML/TAD projects remain valuable curated renditions and
may be selected by a profile. They are not the only route: a backend may instead
allocate the score's voices live on SPC/TAD or stream a rendered MSU track. All
three paths must preserve the same engine-visible timing and resource identity.

The next reusable layer is now implemented under `same.music`; its complete
contract is in [MUSIC_ARCHITECTURE.md](MUSIC_ARCHITECTURE.md). `SequenceIR`
keeps part, note, and physical voice identity separate. Source-device models
preserve authored response, while fingerprinted reviewed banks make the proven
low/main/high octave-zone method available to every importer and backend.

C40/C41 add the corresponding generic path for raw v5 game data. A strict
`SOU ` adapter chooses `ROL `, `ADL `, or `SPK ` by negotiated preference and
decodes every MIDI track. The stateful iMUSE player implements the Fate command
set: setup/start, hook jumps, part gates, and markers, with exact branch-state
restore. SCUMM sees sound identity, running state, hook controls, and a saveable
playhead.

The SNES backend now boots Terrific Audio Driver protocol v20, transfers common
audio and song data through the official loader, queues normalized SAME audio
commands without silent loss, and plays the first reviewed Fate rendition
(sound 172). A fresh Nexen capture proves real S-SMP/DSP output above a blank
baseline while the video and SAME frame counters advance by exactly 120. This
closes the backend/delivery unknown.

C42 starts the reviewable instrument-bank workflow. It reuses user-authorized,
manually reviewed Monkey Island samples and maps explicit low/main/high zones so
the SNES does not have to pitch one source across an audibly strained range.
Six dry TAD songs isolate organ, marimba, flute, atmospheric pad, soft bass, and
percussion. Scale runs, held notes, repeated boundary notes, a deliberately
strained bass octave, velocity steps, and a simple beat make the important
failure modes audible in isolation. The capture harness records real Nexen
S-SMP/DSP output, rejects silence and clipped tails, and emits a listener review
sheet. Passing that mechanical gate does not approve the timbres: listener
verdicts determine the final zone map. After the subsequent sound-17 and
sound-154, sound-83, sound-18, sound-185, sound-190, sound-192, sound-141,
sound-201, sound-202, sound-207, sound-183, sound-91, sound-117, sound-78, and
sound-81 and sound-153 conversions, 9 readable Fate sounds still
need production renditions.

Round-one listening accepted bass and percussion. It rejected audible organ
gaps, the floaty low marimba, an unusable high-flute loop/tail, and the grating
low pad. Round two preserves the keepers, applies the exact MI organ/flute zone
boundaries, removes both rejected low sources, substitutes a reviewed generic
MT-32 organ main zone, and auditions a compact Phantasia high flute. These four
repairs are again delivered as isolated real-DSP captures; they are candidates,
not approvals.

Round-two listening accepts marimba, rejects the residual organ seam and both
flute upper sources, and accepts the pad only below its highest notes. Round
three removes the organ seam entirely. Its flute mid/high zones are high-quality
offline 2x/4x resamples of the accepted p74-low source; its pad-high zone is a 2x
resample of the accepted p88 source. This keeps timbre provenance constant while
reducing the S-SMP pitch multiplier. Derived loops are waveform-closed and
16-sample aligned before BRR encoding.

Round three hard-rejects those repairs: the single-source organ still exposes
its long-loop period, while accelerated flute/pad loops become grating or click.
Round four discards the long loops. A reproducible builder phase-averages their
steady-state cycles into one exact BRR-aligned period per octave zone and uses
TAD's duplicated-block loop mode. This removes uncontrolled chorus/modulation;
such movement may return only after a clean periodic foundation passes listening.

The listener's round-four interval concern triggered an objective audit. An
initial octave-error diagnosis was itself an analysis error: TAD defines C4 as
middle C. With the canonical note map, all notes were at the intended octave;
their common ~2.2-cent offset was Nexen's configured 32,040 Hz SPC clock versus
TAD's nominal 32 kHz reference. Round five adds a clock-corrected ±3-cent gate
and measures all 16 sustained notes within 0.65 cents. It also replaces the
duplicated-block hack with TAD's filter-reset loop mode, removing predictor-state
drift before the next timbre/seam review. The listener accepted all three as
usable sounds while noting their limited texture, closing isolated-bank review.

C43 begins production coverage beyond the one-note proof. A reusable bounded
ROL-to-MML converter pairs note events, retains source velocity/channel volume,
allocates up to eight S-DSP voices, quantizes canonical event times at 125 Hz,
and selects reviewed instruments at exact note-zone boundaries. It fails closed
on unreviewed programs, excessive polyphony, unterminated notes, and multi-track
iMUSE resources requiring explicit branches. Fate sound 17 is its first complete
cue: 23 notes over 13.38 seconds, with a four-note pad bed and a zoned flute line.
Logical sound IDs now map independently to compiled TAD song IDs.

C44 extends that converter with cue-specific program/range policies. They make
register-dependent arrangement substitutions visible and fail closed outside
their reviewed bounds. Fate sound 154 converts all 28 notes over 12.317 seconds
at the source's exact eight-voice peak: programs 32/36 use the accepted bass
through B3 and pad above it, programs 50/92 use pad, and program 97 uses zoned
flute. A real-DSP capture pins its audible entrance and tail.

The corrected canonical-AdLib sound-154 path is also the first consumer of the
shared music-device layer. It resolves complete 30-byte AdLib patch fingerprints
through seven reviewed zones and uses the shared SCUMM nonlinear operator-volume
model. Its normalized iMUSE path retains 26 post-jump attacks and regenerates
the accepted MML byte-for-byte, rather than embedding new cue-specific dynamics
or octave math.

M2 moves the selected iMUSE timeline importer and sampled-AdLib realization out
of the sound-154 tool entirely. A copyright-free second SCUMM cue proves the
same path with active-note CC7 automation. A separate strict QTMA importer now
decodes a 232-byte, two-part raw fixture to the same `SequenceIR` and committed
golden trace; the backend trace contains no SCUMM or QuickTime fields. No other
Fate cue is promoted into the sound-154 bank because its complete patch/range
set has not passed listener review.

M3 adds a source-neutral playback session beneath both importers. Absolute
rational tick mapping prevents cumulative sample drift; lowest-free voice
handles, part-local sustain, completion cleanup, explicit stop, and bounded
voice failure are deterministic. An integer-only triangle/noise reference synth
renders the QTMA fixture to exactly 24,000 mono frames with canonical WAV
SHA-256
`5555b38dc9c89f9cd6572003ad1cfef3b39d81b0037cb5c5cbb91d77a9fad811`.
It is test instrumentation, not a production timbre decision.

M4 proves that architecture against a second real v5 title. The supplied
Monkey archive is mounted in memory, all 138 sounds are hash-inventoried, and
the room-78 church cue traverses the shared AdLib importer, patch model,
reviewed-zone resolver, playback scheduler, and reference backend. Its 197
attacks use the exact manually reviewed MI organ samples split below/above MIDI
58, peak at eight voices, preserve pan and the whole-cue loop, and render
459,072 unclipped 8 kHz frames. The local report retains complete traces; no
commercial game bytes or score trace is committed.

M5 adds the first generic compiled sampled backend. It turns source-neutral
resolved notes into TAD MML with bounded lowest-free voice allocation, exact
instrument/volume changes, explicit stereo or mono pan policy, and whole-song
loop markers. Unsupported controls, more than eight voices, partial/crossing
loops, and missing zones fail with source/tick evidence. TAD's two-tick minimum
is visible in the result: Monkey church receives a one-tick leading bias and
two one-tick-early releases, while retaining all 197 attacks.

The generated MML/TAD identities are repeatable across build directories. A
special ROM plays appended song 26 through real S-SMP/DSP execution for 3,900
video frames. The capture is unclipped and its repeated entrance correlates
0.998933 after clock correction. The compiler contains no SCUMM or title code;
the archive-to-bank adapter and ephemeral commercial-derived MML remain outside
it.

M6 makes selection data-driven. The profile-owned compiled-music catalog binds
each logical request to exact source bytes and one compiler-confirmed TAD song,
plus its logical duration and loop. The generic SNES backend consumes a
generated bounded pair table; its former 19-way Fate switch is gone. A changed
source, duplicate identity, absent/renumbered song, malformed catalog, or stale
save identity fails closed. Fate and Monkey use the same catalog decoder,
generator, normalized play/stop packets, and saved logical-playhead contract.

M7 makes compilation data-driven too. A profile-owned build graph binds each
selected rendition to a source hash, importer, source-device model, reviewed
bank, target policy, expected MML, and compiled catalog identity. The generic
runner verifies all dependencies and the compiler binary, stages the complete
MML/project/catalog/TAD/report set, and publishes it atomically. The SCUMM v5
adapter regenerates two Fate cues and Monkey church through this seam; both
produced ROMs remain byte-identical to their accepted M6 versions.

M8 expands the Fate graph from two proof nodes to all 19 production songs.
Exact converter auditing is part of the policy: five cues are reproducibly
generated, while fourteen older listener-approved arrangements are immutable
hash-pinned graph dependencies. All 19 raw source identities and output hashes
are checked before the complete local project is compiled. This preserves the
accepted DSP image while eliminating the project's production-time dependency
on MML files outside the graph transaction.

M9 closes the build handoff. A profile-bound graph compilation carries the
profile hash in its manifest, and a bundle verifier checks the graph, compiler,
catalog, TAD enums/binary, and artifact hashes as one unit. The SNES builder is
invoked only after that check. Users no longer select a TAD directory and music
catalog independently; one profile-oriented command builds either supplied v5
archive, while `--reuse` safely consumes an already verified cache.

M10 removes the final SCUMM-specific selection from that command. Adapter
registration is keyed by engine and graph source family. The repository-owned
QTMA conformance profile proves a second family can decode a symbolic sequence,
realize it to sampled TAD MML, generate a pinned bank, compile a catalog, reuse
the verified bundle, and assemble a ROM through the same path. Its generated
triangle/noise instruments are intentionally small functional test assets;
reviewed production timbres remain bank policy rather than importer policy.

M11 proves that the non-SCUMM artifact is a runtime score, not merely bytes in a
ROM. The opt-in QTMA personality addresses logical catalog entry 1 through the
normal audio packet ABI and later issues the normal stop operation. It never
touches TAD state or SPC registers. Emulator evidence pins the two-packet trace,
WAITING/PLAYING/COMPLETE transitions, catalog mapping, final blank state, frame
pacing, audible interval, energy, and unclipped peak.

M12 moves the synthetic score deadline into a generic, opt-in compiled-music
lifecycle coordinator. A separately generated table supplies bounded duration
and loop metadata without changing the stable catalog mapping. Engines receive
READY, STOPPED, or FAILED over the normal engine-service seam; the coordinator
uses only normalized audio packets and does not inspect TAD or S-SMP state.

M13 adds the missing QuickTime container boundary. A strict host-side adapter
extracts self-contained `musi` descriptions and samples through checked
`stsd/stts/stsc/stsz/stco|co64` tables, then hands the reconstructed event bytes
to the unchanged QTMA importer. The fixture’s TAD and runtime ROM equal M12,
proving MOV parsing adds no instrument, scheduling, or backend policy.

M14 adds explicit source-neutral time conversion. Absolute rational mapping
avoids accumulated delta-rounding drift; exact mode rejects fractional target
ticks, while bounded-nearest mode reports its rational error and fails if a
note or loop would collapse. The 600 Hz QTMA fixture reaches the 125-tick TAD
clock with exact total duration and at most half a target tick of displacement.

M19 proves the first compiled SCUMM cue through the normal SNES engine path.
Monkey sound 154 is started, stopped, status-queried, and restarted by actual
SCUMM opcodes; the resulting engine-to-SPC packet trace maps through the existing
catalog to song 26. The validator never writes the debugger logical-request
byte. Its post-restart DSP capture crosses the previously accepted church loop
at 57.303875 seconds with 0.998934 correlation.

C45 adds opt-in, deterministic voice reduction for cues that exceed the eight
physical S-DSP voices. The converter preserves stronger notes and breaks exact
ties toward the lower register, while writing every omission into the generated
MML. Sound 83's sole nine-voice collision omits only a velocity-1/CC7-47 G6
double of its retained G5 layer; the other 29 source notes remain intact.

C46 adds interval-based voice virtualization. Sound 18 retains all 25 source
notes despite an eleven-voice peak: overlapping identical pad pitches collapse
into their stronger foreground equivalents, and the quiet program-50 chord is
ducked only for the exact intervals that exceed eight physical voices. Its
notes resume when capacity returns, and every merge/duck interval is audited in
the generated MML. The listener accepted the resulting real-DSP capture as
sounding alright.

C47 introduces the accepted marimba as an explicit program-0 attack role for
sound 185. Its seven-note D2–A4 chord retains every source note and dynamic on
seven physical voices, without reduction or virtualization.

C48 adds a shared split-register program-0 impact policy. Sounds 190 and 192
use accepted bass for C1..B1 and accepted marimba for C2..B5, retaining all
three and four source notes respectively without reduction.

C49 corrects the numeric marimba ceiling to match its reviewed/project-declared
C2..B5 range and adds four compact program-0 cues. Sounds 141, 201, 202, and
207 each retain both source notes; the overlapping second attacks in 201/202
remain independent voices.

C50 adds chord-aware same-instrument virtualization for sound 183. All 110
source attacks remain represented despite a twelve-voice peak: outer pitches
and new attacks are protected, then the strongest interior tones fill the
remaining slots. Fourteen bounded duck decisions identify ten restores and
four sustains that yield through note end. A cue-specific two-tick timing grid
models TAD's minimum key-off duration without hidden compiler repair.

C51 adds the shared sound-91/117 E2..G7 ascending effect. Accepted bass covers
E2..B2 and the existing production Fate tone covers C3..G7. The two-tick grid
retains every rapid attack; sound 117 also retains all three sustained harmony
notes. The cues represent 34/34 and 37/37 source attacks without reduction.

C52 adds long-form sound 78. Its high program-73 lead uses the zoned flute,
while programs 82/91 use the accepted pad. All 91 notes survive across the
84.000-second timeline with a six-voice peak. The production gate now supports
bounded captures up to 6,000 frames and proves this entire cue over 5,280
frames instead of sampling only its opening.

C53 adds capacity-triggered identical-pitch sharing for sound 81. Its only
over-capacity region is resolved by sharing the quiet program-92 G4 with the
stronger simultaneous program-90 G4 for 56 milliseconds. All other duplicate
layers remain independent, all 113 source attacks are represented, and no
unrelated pitch is reduced.

C54 adds attack-preserving orchestral virtualization for sound 153. When more
than eight notes are active, only sustained identical pitches are mergeable;
new attacks and both register edges are protected before strength selects the
remaining interiors. All 55 attacks survive its twelve-voice peak. The cue uses
a two-tick minimum grid and audits 31 merges, eight restores, and three sustains
that yield through note end.

C55 remains under listener review: its first mechanically passing sound-150
conversion discarded in-note CC7 automation and turned a terminal interactive
hold into an 84-second static drone. The converter now records every CC7 change
that occurs while a note is active, preserves that envelope while quantizing and
virtualizing voices, and emits 0..255 TAD fine-volume changes around `w` waits so
the held sample is not retriggered. Sound 150 retains source/engine timing but
slurs its terminal voices into a fade ending at 18.680 seconds; audible DSP now
ends at 22.197 seconds.

The resulting all-production-cue audit found active-note CC7 only in sounds 18,
83, 150, 154, and 192. Those five have been regenerated; the other fourteen
production cues contain no such automation. The new MML retains 123, 101, 73,
50, and 2 quantized fine-volume changes respectively. Every corrected cue
compiles and passes a fresh real-S-SMP/DSP timing capture from ROM
`0d7c7641dc54478e6e7dad01e82bec1df202c38f76255e70d4fa697202b58805`.
Focused listener review remains the musical acceptance gate.

Fate's `ADL` child is now an additional independent oracle. The embedded-audio
decoder retains complete 30-byte iMUSE `$10` instruments, including extended
modulation envelopes, and a pinned ScummVM SCUMM-iMUSE build renders them with
Nuked OPL. Sound 154 also proves why raw SMF playback is insufficient: an
unconditional iMUSE jump at 148,806 microseconds skips its setup silence. See
`audio/fate_s6/ADLIB_ORACLE.md` for identities, harness, timing, and WAV hash.
The same oracle now has an isolated five-octave capture for each of sound 154's
six patches. Those listener files are the acceptance input for selecting
octave-local BRR sources; no patch is promoted merely from a whole-mix match.
The accepted production candidate uses seven multi-cycle zones from five active
patches and now follows the canonical iMUSE jump rather than linear SMF time.
Its converter also mirrors SCUMM AdLib's patch-dependent nonlinear operator
attenuation. This preserves velocity-insensitive texture notes—including sound
154's velocity-1 G5/G6 finale—that a linear MIDI-volume conversion loses.
This is also the intended reusable boundary: SCUMM emits a score/patch graph;
the SNES asset lane performs zoning, BRR compilation, ARAM budgeting, and DSP
validation.

S4 proves selection and state convergence with synthetic data. C41 subsequently
proves live TAD compilation and production SPC delivery for one Fate sound;
C42 proves the repeatable isolated-instrument review path.

M15 adds source-neutral segmented provenance before audio realization. QTMA
parts and events now retain their exact movie track, sample description, media
sample, physical file byte, and logical event word through M14 normalization.
This changes no playback bytes: M13/M14, Fate, and Monkey retain their accepted
ROM identities and pass real-S-DSP regression gates.

M16 persists that sequencer state in a canonical, graph-hashed audit artifact.
The document records resolved sampled-note zone identities but does not alter or
reimplement the audio backend. M13 and M14 retain exact MML, TAD, catalog, ROM,
and real-S-DSP behavior.

M17 strictly decodes and replays that normalized IR to identical MML with the
source importer disabled. This establishes a genuine sequencer/backend boundary;
it adds no QuickTime playback subsystem and changes no accepted audio bytes.

M18 checkpoints that sequencer boundary. Warm restore is command-silent while
the live backend voices remain preserved. Cold restore is transactionally bound
to IR, realized sample catalog, engine/profile, schema, and timing identities,
but restores logical voice ownership only. It does not claim continuous samples
without backend sample/envelope/oscillator state and pending-command proof.

M20 connects a narrower policy to real SNES SRAM and SCUMM load. A validated
running record emits semantic stop then play packets; the TAD backend retains
one deferred compiled-song request while its blank-song transfer completes.
This orders an ordinary restart without TAD seeking or SPC-state serialization.
The saved logical position remains advisory and is intentionally ignored.

M21 and M22 add two deliberately bounded compiled-route mechanisms driven by
synthetic SCUMM command fixtures, not authentic room-entry traces. M21 resolves
an immediate hook before a song reaches audible ownership. M22 keeps hook 8
pending while the already playing hook-14 arrangement continues, then lets a
source-authored compiled bytecode boundary choose one of two precompiled
continuations without a song reload. The SPC exposes only a stable boundary
token; it does not expose or serialize its instruction pointer, voices, sample
cursors, or DSP state. Cold load therefore still means deterministic restart
from the cue beginning with the saved route plan, not musical-position or
sample-continuous restoration.

M23B does not add another audio mechanism. It replaces the room-49 proof's
synthetic command origin with the complete authentic ENCD executed from PC zero
through normal resource and room lifecycle. The source queues start 80 and
hook 14 before one flush; the existing M21 catalog route then owns TAD song 27.
The default song never becomes audible, and a sound-81-running source-state
control skips the block without emitting an audio packet.

M23C likewise adds no music mechanism or instrument realization. Authentic
room 63 supplies the delayed hook through normal ENCD execution: hook 8 is
queued, global script 151 starts and yields, sound 82 is queried, `0x0110`
clears the iMUSE deferred/trigger queue, and the later authentic flush arms the
existing M22 selector. Song 27 keeps playing across the room and section
transition with no reload or false stopped interval. Cold load remains
deterministic cue restart, not musical-position or DSP-continuous restoration.

M24R-A is an isolated backend feasibility patch, not a public audio ABI. One
S-CPU command is observed at a TAD tick before channel countdown processing;
one outgoing physical-voice mask receives a gain ramp, and a fixed table steals
specified voices into precompiled incoming subroutines. It neither mixes two
TAD songs nor schedules notes dynamically. See `M24RA_REPORT.md`.

## Two source levels

SAME accepts:

1. **semantic commands** — play music, stop music, play SFX, start PCM stream;
2. **chip writes** — SN76489, YM2612, YM2610, AY/YM variants.

A target can start with chip writes for fidelity, then replace known driver paths
with semantic commands when measurement proves the substitution.

## Implemented host lab

`src/same/audio.py` implements:

- SN76489 latch/data register behavior;
- three tone channels and one noise channel;
- attenuation and a deterministic 16-bit mono WAV renderer;
- JSONL trace input;
- a YM2612 register/key-on retention model.

Generate the demonstration:

```bash
same audio demo \
  --trace examples/audio/sn76489-demo.jsonl \
  --wav out/sn76489-demo.wav \
  --duration 1.25
```

The WAV is proof of the CPU-independent source side. It is not proof that a TAD or
SPC translation is correct.

## SNES backend gate

The first backend consumes normalized `MUSIC_PLAY`, `MUSIC_STOP`, and `SFX_PLAY`
packets and drives TAD. Its acceptance evidence now includes:

- one packet produces one expected TAD command;
- queue full/driver not-ready is reported, not dropped;
- an emulator audio capture contains nonzero sample energy;
- target and backend status agree;
- no video DMA or NMI budget regression.

## YM2612 boundary

No FM synthesizer is claimed in 0.2.0. The next useful step is not writing a full
FM core on the SNES. It is collecting real register traces, classifying how a
selected game's driver uses channels/operators, and deciding per game whether to:

- translate semantic music/SFX events;
- author TAD equivalents;
- stream rendered music through MSU-1;
- preserve only sound effects on SPC;
- or implement a bounded subset of YM2612 behavior.
