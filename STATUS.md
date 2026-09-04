# SAME 0.2.0 status

## Verified in the packaging environment

- **304/304 tests pass.**
- Both bundled engine profiles validate and negotiate capabilities.
- SCUMM v5 runs 120 ticks, increments variable 20 to 120, keeps music track 1
  active, produces a deterministic indexed framebuffer, and loses no packets.
- AGI v2 runs 120 logic cycles, increments variable 20 to 120, sets flag 40,
  produces a deterministic 16-color framebuffer, and loses no packets.
- Both engines save and restore through the same CRC-protected envelope.
- The profile can bind resources to raw files, memory, composite providers, or a
  verified section in a SAME package.
- Indexed fill/blit/transparency, palette, dirty rectangles, cursor composition,
  frame hashing, and PNG output pass.
- Engine lifecycle misuse and missing capabilities fail closed.
- Unknown SCUMM and AGI opcodes fail with script offset evidence.
- AGI decoded logic resources and message offsets parse correctly.
- The 16-byte service packet remains byte-compatible with 0.1 and now includes
  engine/save/job service numbers.
- The SNES include closure passes the Poppy hazard checker: 20 files and 1,500
  global labels for the demo selection (1,494 for SCUMM v5).
- The adventure package contains four aligned, per-section-CRC resources.
- The legacy machine-host tests, Genesis scheduler simulation, SN76489 renderer,
  package tests, oracle tests, and four SAME-VDP golden cases still pass.

Generated demonstration artifacts under `out/` include:

```text
adventure-demo.samepkg
adventure-demo.inc.pasm
scumm-v5-report.json
scumm-v5-frame.png
scumm-v5-slot0.same-save
agi-v2-report.json
agi-v2-frame.png
agi-v2-slot0.same-save
genesis-simulation.json
sn76489-demo.wav
```

The 120-frame host results are:

| Engine | State proof | Packets | Rejected/dropped | Queue high-water |
|---|---|---:|---:|---:|
| SCUMM v5 | `var[20] = 120`, room 0, music 1 | 252 | 0 / 0 | 6 |
| AGI v2 | `var[20] = 120`, flag 40 | 248 | 0 / 0 | 5 |

## SNES host assembled and observed on the configured workstation

- Engine lifecycle host and active demo engine.
- SCUMM v5 and AGI adapter entry seams.
- Engine/save/job packet routing.
- Input edge state, fixed WRAM ownership, and NMI-owned backdrop commit.
- SAME 0.1 target compatibility labels.

On 2026-08-23, the configured Linux workstation assembled and audited:

```text
build/same-engine-host.sfc
32768 bytes
SHA-256 966caf1de4e38fddda4c156fb5b30491f4e322d147821fd4663b933a71189fb7
reset=$8000 nmi=$8051 irq=$8073
```

The build pins `astrobleem/poppy` commit `ec005c196eedabf7d0c25ff6336398c427dd43ac`
and DLL SHA-256 `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`.
The LoROM audit verifies the
header, vectors, inverse checksum pair, and actual ROM byte-sum checksum.

H0 then passed from a fresh power-on in the MCP-enabled Nexen build on 2026-08-23:

- lifecycle reached RUNNING with engine `$01` and READY `$0A`;
- the frame and operation counters advanced once per subsequent video frame;
- two heartbeat packets crossed the queue by video frame 180;
- the queue remained drained with zero dropped/rejected packets through the
  complete gate;
- Left/Right/B/A produced exact one-frame press/release edges and NMI-committed
  blue/green/red/white screens;
- a 240-frame Left hold produced no repeated press edge or packet loss;
- Start reached the audio service as `MUSIC_PLAY`, track 1.

Latest evidence is in `build/h0-nexen-966caf1de4e38fdd/`; `report.json`
SHA-256 is `2b57d814fcc20d85a228a5231049bce6455194b656769c0bb7dd2663b8dda367`.
No physical-hardware claim is made.

K1 then passed from a fresh power-on for the rebuilt ROM:

```text
build/same-engine-host.sfc
32768 bytes
SHA-256 966caf1de4e38fddda4c156fb5b30491f4e322d147821fd4663b933a71189fb7
reset=$8000 nmi=$8051 irq=$8073
```

- Monkey donor HEAD: `640e48359c5a17a9edd3a0c2208d62180757a2c1` with its
  pre-existing dirty paths recorded in `docs/DONOR_MAP.md`.
- BOR donor HEAD: clean `b80edcbb8020373b9652cece24fb01d6d64cfb7c`.
- Kernel DMA queue: eight slots, 2 KiB per-NMI budget, complete-descriptor
  publication, and channel 7 owned only by the kernel commit backend.
- Exact hardware reads matched 16 VRAM, 8 CGRAM, and 8 OAM fixture bytes.
- Four blank-time requests committed with zero rejects/budget deferrals,
  including a zero sentinel at the protected VRAM target. A fifth
  forced-blank-only request stayed pending and left that sentinel exact through 120 active
  display frames while the blank-deferral counter advanced from 3 to 123.
- Held Left produced one exact press edge, no edge on the next/final sampled
  frame, and one frame-counter increment per video frame.
- The complete H0 gate passed again on the same ROM, including its 240-frame
  held-input proof and exact video/audio/event behavior.

K1 evidence is in `build/k1-nexen-966caf1de4e38fdd/report.json`; report SHA-256
is `af41803f3e4f0bf004045a6e9517f6a30c53973d11f23e715c14613a5256a827`.
The final C32 demo ROM `966caf1de4e38fddda4c156fb5b30491f4e322d147821fd4663b933a71189fb7`
retained H0 and K1. Latest report SHA-256 values are
`2b57d814fcc20d85a228a5231049bce6455194b656769c0bb7dd2663b8dda367`
and `af41803f3e4f0bf004045a6e9517f6a30c53973d11f23e715c14613a5256a827`.
No physical-hardware claim is made.

## Archived Monkey binary observation (not a gate)

An earlier investigation characterized the supplied, known-incomplete Super
Monkey Island bundle in Nexen without modifying either Monkey checkout:

- exact ROM SHA-256
  `89090a712861492b2573812c220e2dd77d241c9e1b55c87e1e126207132fe803`;
- frame-exact START cadence reaches title, campfire intro, Part One, and room 33;
- final frame 13,220 remains in room 33 with the CPU running and no engine
  exception-hook hit;
- the ROM demonstrably reads the `.msu` pack header/index and issues playback
  for silent placeholder track 1086;
- the full intro capture contains 222.964 seconds of nonzero stereo audio, but
  this is not talkie-speech proof;
- the dock save restores captured memory exactly, and two 180-frame replay
  branches converge to identical memory and pixels;
- the immediate post-load framebuffer retains a documented 337-pixel sprite
  history difference.

Exact identities, procedure, hashes, caveats, and evidence paths are archived in
`docs/S0A_MONKEY_BASELINE.md`. This is historical inventory, not a baseline,
oracle, regression target, or pending gate. No additional long Monkey run or
source-build comparison is scheduled.

## Current SCUMM v5 semantic boundary

The SNES runtime now includes an independent SCUMM v5 semantic nucleus driven by
a copyright-free 61-byte fixture. C1 passed from fresh power-on in Nexen in six
video frames for ROM SHA-256
`0c4067cdd9177ae4d97c5eed7f071e4b0bfbc04d0ccd3a52db61fa85ebef53b5`.
Five exact WRAM checkpoints cover direct/variable move, add, subtract,
increment, true/false equality flow, relative jump, yield, delay, and stop. It
uses no donor ROM, screenshots, audio, or game assets. Evidence is in
`build/scumm-core-nexen-0c4067cdd9177ae4/report.json`.

C2 expands that nucleus with generated selectable fixtures. On 2026-08-22 the
final ROM SHA-256
`8ade4f762b5e58e6a1bd9dd3c76c962455f548861175c4b9868e72377f51ecac`
passed eight cases in 12 video frames: a four-tick signed arithmetic,
comparison, and variable-delay trace plus seven exact fail-closed terminals.
Evidence is in `build/scumm-c2-nexen-8ade4f762b5e58e6/report.json`. No donor ROM,
screenshots, audio, or game assets participated.

C3 adds indexed result references, variable forms for every implemented
arithmetic/comparison family, exact 16-bit wraparound, and deterministic
two-slot scheduling. On 2026-08-22 ROM SHA-256
`1afca069a497b31c47c4472e59914772ff9976055cb14fbc004f23313a7fe738`
passed three cases in 10 video frames. The five-frame scheduler trace proves a
delayed slot does not starve its runnable peer; unsupported bit-variable results
fail explicitly. Evidence is in
`build/scumm-c3-nexen-1afca069a497b31c/report.json`. The same ROM retained C2 in
12 frames at `build/scumm-c2-nexen-1afca069a497b31c/report.json`. No game ROM,
screenshots, audio, or donor assets participated.

C4 adds synthetic start/stop-script lifecycle, nested execution, 32 local
variables per slot, deterministic first-dead-slot reuse, and an exact 25-slot
limit. On 2026-08-22 ROM SHA-256
`5055b69c377615409b3ad5dd3dc38f30d8e869d2f83743cfea1bc8b8e640a19d`
passed two C4 cases in five video frames. Evidence is in
`build/scumm-c4-nexen-5055b69c37761540/report.json`. The same ROM passed the
complete C3 matrix in 10 frames and C2 matrix in 12 frames. No game ROM,
screenshots, audio, or donor assets participated.

C5 gives recursive and freeze-resistant flags exact scheduler behavior and adds
freeze/unfreeze plus script-running queries. On 2026-08-22 ROM SHA-256
`de56a0b3c163e470e823f19133a925c5064b5f54dcc30efcedc723b12ee7c507`
passed its five-tick scheduler trace in six video frames. Evidence is in
`build/scumm-c5-nexen-de56a0b3c163e470/report.json`. The same ROM retained C4
in five frames, C3 in 10, and C2 in 12. No game ROM, screenshots, audio, or
donor assets participated.

C6 implements direct and variable `chainScript` handoff with caller retirement,
inherited recursive/freeze-resistant flags, reinitialized locals, and reserved
slot-zero capacity behavior. On 2026-08-22 ROM SHA-256
`9c59520d659c5e285a44f8b7a96aead95be5b40ab403d4ac77c4fde2cff81ff4`
passed three C6 cases in six video frames. Evidence is in
`build/scumm-c6-nexen-9c59520d659c5e28/report.json`; report SHA-256 is
`f154fa35a2a8c8cf1ba1b44630ebaa5982af14c23a444347686e177b244a966d`.
The same ROM retained C5 in six frames, C4 in five, C3 in 10, and C2 in 12.
No game ROM, screenshots, audio, or donor assets participated.

S1 adds a validated, non-runnable-until-supplied Monkey 1 Ultimate Talkie
profile template. It names raw index/data resources, sound and speech maps,
absolute VCTL-offset speech indexing with track base 1000, logical 320x200
coordinates inside a host-owned viewport, original-engine cursor behavior,
the copy-protection bypass choice, and an optional script-patch manifest. All
quirks are narrowly namespaced; none enter the opcode core. Missing
`game.index` fails profile loading exactly, while a supplied dummy resource
layout validates without changing policy. Evidence is in
`build/scumm-s1-profile/report.json`, SHA-256
`821a2f65bfebaf1965ece0a36465cbac3e7f83d25410a85125f095a1f15d443f`.
No commercial data was read and no Monkey ROM was run. The SNES build remained
byte-identical to the C6 ROM.

S2 adds a host-side raw LucasArts SCUMM v5 resource provider and logical input
adapter. A generated, copyright-free encrypted index/data pair proves exact
room, script, sound, costume, and charset lookup through stable SAME keys;
truncated chunk bounds fail closed, and absent full-game entries retained by a
sparse demo index are not advertised. Pointer motion, physical and logical pointer
buttons, joypad commands, text, releases, and per-frame transient clearing are
exact across three host frames. Logical 320x200 cursor coordinates remain
engine-owned while the 256x224 video backend owns physical clamping.

Evidence is in `build/scumm-s2-adapters/report.json`, SHA-256
`99ea6b5b744b85c95b703fc0114589eba211739614528063d30637222be15117`.
No commercial data was read and no Monkey ROM was run. The SNES ROM remained
byte-identical to C6 at
`9c59520d659c5e285a44f8b7a96aead95be5b40ab403d4ac77c4fde2cff81ff4`;
the short H0, K1, and C2-C6 regressions all passed on that ROM.

S3 adds a host-side SCUMM logical-video adapter with an exact 320x200 indexed
scene, host-owned 256x224 viewport projection, priority-tested actors, z-mask
occlusion, cursor projection, and resource-backed v5 CHAR-style bitmap fonts.
The copyright-free fixture renders `SAME S3` and `FONT!`; corrupt scene and font
bounds fail closed. Baseline and negotiated tile/OAM/z-mask/SA-1 plans converge
to the same logical SHA-256
`6d4451b55770536cde22b8b01338d5dbda06cdf0d6198d1d1066d86faf53b086`
and physical SHA-256
`54ddea1f2a877e6a88fad3ea2a94987688e29705e78e8fb21fd1fb9f29e2afaf`.

Evidence and PNGs are in `build/scumm-s3-video/`; `report.json` SHA-256 is
`23dc2bd7b8faef09770df554cd339dc300e3f01dd582c7202267837473a9aef4`.
No commercial data was read and no Monkey ROM was run. The SNES ROM remained
byte-identical to C6, and the short H0, K1, and C2-C6 regressions all passed.

S4 adds a backend-neutral score-intent decoder and SCUMM audio adapter. A strict
copyright-free score retains timed note/control events and loop points while a
profile-negotiated plan selects a score interpreter, a curated TAD rendition,
or MSU streaming without changing the logical playhead. Exact synthetic music,
SFX, and speech requests pass. Save schema 2 restores variables, bit state,
script slots, room, camera, cursor, counters, and music/SFX/speech playheads
across a room transition; wrong game, schema, and CRC fail before engine load.

Evidence is in `build/scumm-s4-audio-save/report.json`, SHA-256
`715ffdbdd0b77480d3713f0d99668b6e8a0b31d065b54e472e5856f5b18c1765`.
No commercial data or Monkey audio was used. The SNES ROM remained byte-identical
to C6 at `9c59520d659c5e285a44f8b7a96aead95be5b40ab403d4ac77c4fde2cff81ff4`;
H0, K1, and C2-C6 passed in bounded fresh runs.

S5 replaces the private parallel SCUMM lane with generated active-engine
selection. A SCUMM build now binds `ScummV5_Engine_*` to the stable
`Same_ActiveEngine_*` lifecycle; the kernel boots and ticks only that selected
engine. A two-tick copyright-free fixture agrees exactly between host and SNES
on PC, status, error, operations, variable state, and four normalized audio
packets including both arguments and endpoints. No packet was dropped or
rejected. The SCUMM ROM SHA-256 is
`59e39dc6b97ed98d617298ba3aaf26afa9c76dec0b2b18908bf8561a6b9f629f`.

Evidence is in `build/scumm-s5-binding-59e39dc6b97ed98d/report.json`, SHA-256
`601affa6bde5274f967a3d1f0803c4ed16df4b4d7b5ed32c7e52289f90f81478`. The
demo-selected ROM SHA-256
`b22b11461de0f19d96afacc1a5fbcbcc989e1149b9d8e30003012bcc2c7ac5f7`
retained H0 and K1; the SCUMM-selected ROM retained C1-C6 in bounded runs. No
commercial or donor game data participated.

C8 implements all five generic v5 `$27 stringOps` subcommands in the host and
SNES engines: load, copy, set character, get character, and create empty. Raw
`$FF` control sequences and their argument bytes remain intact while a typed
glyph/control view feeds the existing font boundary. All 256 byte-sized IDs
have independent 255-byte capacity in a deterministic 64 KiB WRAM table; no ID
clamping or aliasing is allowed. Host string state round-trips through saves.
The exact copyright-free host/SNES case also covers variable operands, missing
source nuke semantics, bounds behavior, malformed streams, and a scheduler
yield. SCUMM ROM SHA-256 is
`2486bb6cc549e87cf7d2ffb05911d891f7ab0b820f6ac04eab957f8e9d861074`;
evidence is `build/scumm-c8-nexen-2486bb6cc549e87c/report.json`, SHA-256
`7518bbc69522d28c2da6b797ef0144490cb8908bcff87dc9b2882dd87663914e`.

C9 implements canonical v5 `$26/$A6 setVarRange` in the host and SNES engines.
The resolved starting reference advances across indexed globals, locals, or
packed bits while byte and signed-word payloads retain their exact width. The
copyright-free matrix covers zero-count 256-entry behavior, packed-bit wrap,
truncation, and global/local boundaries. SCUMM ROM SHA-256 is
`19bff51435685c9ce26ee413ba708760d67c6e83c95c9a67096c8b61822b241f`;
evidence is `build/scumm-c9-nexen-19bff51435685c9c/report.json`, SHA-256
`a2bf862be179fd38cd074f6eef1c0520a23930bbfae9f13b8ea25ded53061e57`.
The same ROM retained C1-C8 and S5. Demo ROM SHA-256
`147344e4b9d8aafc724f35324722207f7f7423d9552bcb024d4e73d43e78dba3`
retained H0 and K1.

C10 implements the complete full-header v5 `$33/$73/$B3/$F3 roomOps` family in
both semantic engines. It records deterministic room intent for camera limits,
screen bounds, shake, scaling, intensity/shadow/transform ranges, fade, palette
overrides, temporary slot-99 save requests, color-cycle timing, and named
auxiliary-string save/load. The host applies palette overrides through the SAME
video surface and persists the complete intent and auxiliary data in save schema
2. The v3-only room-color sub-op and malformed ranges, slots, filenames, and
streams fail closed. The 111-byte copyright-free matrix executes all 19
operations in bounded Nexen time. SCUMM ROM SHA-256 is
`f4926d569b8bc2844b5b054c826b97310c755c251eec8a90f7067805dfa03a7e`;
evidence is `build/scumm-c10-nexen-f4926d569b8bc284/report.json`, SHA-256
`e46d2cbe3d7f14d2b76cc205020a2a8862d4e33cc48dd86fad98a1c5b8852911`.
The same ROM retained C1-C9 and S5. Demo ROM SHA-256
`11fa8ba30df1ded394f588ee9a0c9b504db4cff448a824ed4b6c289ae875cd27`
retained H0 and K1.

C11 implements canonical v5 `$16/$96 getRandomNr` in both semantic engines.
The engine owns a deterministic nonzero 16-bit PRNG state, advances it exactly
once per opcode, and maps its high-byte sample into the inclusive range
`0..maximum`. Direct and variable maximum operands share the same path; the
state is inspected, validated, saved, and restored so replay continues exactly.
The copyright-free matrix covers maximums 0, 9, 10, and 255 plus save/load
continuation. SCUMM ROM SHA-256 is
`847b318ea1716ce59af47b6036bf33e6d6b54d807e8c37ce19ab756179950652`;
evidence is `build/scumm-c11-nexen-847b318ea1716ce5/report.json`, SHA-256
`98ae6678b066b74c07b3397c5eb85901a0f76bb993d90d5840dd8b6b01482aaa`.
The same ROM retained C1-C10 and S5. Demo ROM SHA-256
`628c2ee7f4a4829acf30d383b6705200c704bfa724bed77a15e273c60c234ca1`
retained H0 and K1.

C12 implements canonical v5 `$CC pseudoRoom` in both semantic engines. The
engine owns all 128 high-bit room mappings, ignores list entries without bit 7,
supports deterministic overwrite, resolves mapped room loads, and preserves the
table through host save/load. The 14-byte copyright-free fixture spans two
ticks and proves mapping persistence. SCUMM ROM SHA-256 is
`aadbf933825a881c0c8763b9df36b144ed8c01ce04575793bdcaa6f24bcbff3a`;
evidence is `build/scumm-c12-nexen-aadbf933825a881c/report.json`, SHA-256
`b3234bd590b54202da74a3db7c6652e583fe3c58f56e265cf5a9beb5e933fb95`.
The same ROM retained C1-C11 and S5. Demo ROM SHA-256
`535598e91e8313084f592f849e27cbf910cb1f3694cbd073ab25b19d6781e4e5`
retained H0 and K1.

C13 implements generic v5 `$0C/$8C resourceRoutines` in both semantic engines.
The engine owns cache and lock intent for scripts, sounds, costumes, rooms, and
charsets; nuke requests evict intent without deleting source resources. Room
operations normalize through C12, clear-heap remains the canonical no-op, and
object loads retain mapped room plus 16-bit object identity. The 76-byte
copyright-free fixture proves all 20 operations, direct and variable operands,
malformed-input failure, and save/load replay. SCUMM ROM SHA-256 is
`44bb9e4eca6d7287a77262e56809015ff4cbda5a2934805da2e8512fd3456f3c`;
evidence is `build/scumm-c13-nexen-44bb9e4eca6d7287/report.json`, SHA-256
`586df1fe2caf5906953bd2be9cb93f1da022b761e32147fbffbfa851d1e2125e`.
The same ROM retained C1-C12 and S5. Demo ROM SHA-256
`b6bfdb38e811f511523702d97ae9291ebe8add88ad51d3f18d8876a5095752e0`
retained H0 and K1.

C14 implements canonical full-header v5 `$13/$53/$93/$D3 actorOps` in both
semantic engines. The engine owns 32 actor configuration records with costume,
walk speed, sound, animation frames, signed elevation, palette, talk color,
encoded name, width, scale, box scale, clipping/box policy, animation speed, and
shadow. `SO_DEFAULT` mirrors `Actor::initActor(0)` while retaining costume,
palette, and name. Actor state is inspected, validated, and persisted in host save
schema 2. The 115-byte copyright-free matrix covers every valid v5 sub-operation,
direct and variable operands, both scheduler ticks, malformed streams, and
save/load replay. SCUMM ROM SHA-256 is
`172d9a439f5d5310da008f1516bb570ebe3d61c7235b5555036f170dd7b70125`;
evidence is `build/scumm-c14-nexen-172d9a439f5d5310/report.json`, SHA-256
`ab21b1b886be8bccf7027ed521e05d73cd9a4ddf71de516ab5516c48d56ad867`.
The same ROM retained C1-C13 and S5. Demo ROM SHA-256
`3840408eee47fe495e265f144a551520ba541df41a923f99c2f5e93e9e085cda`
retained H0 and K1. The SNES implementation avoids Poppy's current one-byte
location-counter defect for `JMP (abs,X)` by using an explicit bounded dispatch
chain.

C15 implements canonical v5 `$52/$D2 actorFollowCamera` in both semantic
engines. The opcode stores bounded camera-follow intent independently from actor
configuration and presentation policy, supports direct and variable actors, and
round-trips through host save schema 2. The 12-byte copyright-free fixture spans
two scheduler ticks and proves both forms plus malformed-state failure. SCUMM ROM
SHA-256 is
`f12914c423a97617b847e6ed8854eee25b606338a681efbbe31ab17bbc3a5865`;
evidence is `build/scumm-c15-nexen-f12914c423a97617/report.json`, SHA-256
`066648bd65cb0194bca2f790820bdc361586ba3337cd2d95b15f0ebb0d0218e3`.
The same ROM retained C1-C14 and S5. Demo ROM SHA-256
`05d3eb83a86d848965e06b6291b41a23564b41cd8b5a9c4c535812bc40a2bf56`
retained H0 and K1.

C16 implements canonical v5 `$5D/$DD setClass` in both semantic engines. Full
16-bit object identity maps to a 32-bit class mask through a reusable, bounded
512-record sparse table; direct and variable selectors support set, remove, and
raw-zero clear-all behavior. Host save schema 2 validates canonical object keys
and sorted unique class IDs. The 52-byte copyright-free fixture spans two ticks,
proves direct/variable objects and class operands, recovers cleared capacity,
and fails closed on malformed streams and invalid classes. SCUMM ROM SHA-256 is
`fe1fb1421077648c9584eefcbb0a5eaf3e1f821e7727cba6a4816d52173ffbff`;
evidence is `build/scumm-c16-nexen-fe1fb1421077648c/report.json`, SHA-256
`282be45a82c5fc81f71df4c557523fc8f88d8a86bb2895f5ca2cea7c8d253529`.
The same ROM retained C1-C15 and S5. Demo ROM SHA-256
`b8496790687a0fdfe4ca64455ac80c48dbc1c02978164c436df19a12be347dde`
retained H0 and K1.

C17 implements canonical v5 `$7A/$FA verbOps` in both semantic engines. The
engine owns a bounded 256-entry verb table while drawing and hit-testing remain
adapter concerns. All valid v5 selectors support their canonical direct/variable
operands, encoded inline/resource names, image sources, modes, `NEW` defaults,
and deletion. Host save schema 2 validates and round-trips the verb table. The
98-byte copyright-free fixture spans two ticks and covers the complete selector
surface plus malformed streams and bounded-name failures. SCUMM ROM SHA-256 is
`c4ec37cdce22fa48f6123122c1e733393d9a94aea9048eacb2944347a4a26b26`;
evidence is `build/scumm-c17-nexen-c4ec37cdce22fa48/report.json`, SHA-256
`5363624900dceebc7f9b4b580d4e893ceabcb05685d5ac8602a3c15f18006e29`.
The same ROM retained C1-C16 and S5. Demo ROM SHA-256
`9f0483ae507726b529ba7b6988dd7a05c856e3fd9093bf32fc5a65a62363ea06`
retained H0 and K1.

C18 implements canonical v5 `$AC expression` in both semantic engines. Its
shared bounded stack holds 256 signed 32-bit values, supports direct/variable
pushes, add/subtract/multiply/divide, canonical reserved-token behavior, nested
ordinary opcode dispatch, and v5 narrowing only at the final result write. The
93-byte copyright-free fixture spans two ticks and proves 32-bit intermediates,
truncation-toward-zero division, indexed/local/bit destinations, nesting,
malformed-input failure, and save/load replay. The canonical comparison operand
order was corrected in both engines when the real Fate sequence exposed the
older reversal. SCUMM ROM SHA-256 is
`17c3d40202e4e80509a00ea7cf227c9b518af9e15498ceacc99ac106d1e254c6`;
evidence is `build/scumm-c18-nexen-17c3d40202e4e805/report.json`, SHA-256
`52953b0eba95034b8908565d8aabff21ec3451fc5a01fddadabff1bdf607db07`.
The same ROM retained C1-C17 and S5. Demo ROM SHA-256
`6710633952df3ba1047e527781a5af7099133afdf7a8894a6b786f68c3b76afc`
retained H0 and K1.

C19 implements canonical v5 `$40 cutscene`, `$C0 endCutscene`, and `$58
beginOverride/endOverride`. The host engine owns the bounded nested stack,
signed word-varargs, callback variables 35/36, per-script override depth,
recorded override PC/slot, logical skip abort, and complete save/load state. The
SNES conformance path proves the same bounded opcode state and exact unwind;
callback execution remains a host-side proof until raw script resources are
available to the SNES adapter. The 31-byte copyright-free fixture spans two
ticks and covers direct/variable arguments, nesting, override markers, and
scheduler persistence. Malformed stack/override/save state fails closed. SCUMM
ROM SHA-256 is
`b4ad8bb60153535e9b4079009d72f068fb8aa2323b537d85f0fa047ef156178a`;
evidence is `build/scumm-c19-nexen-b4ad8bb60153535e/report.json`, SHA-256
`8267c9d9b00e05d1437c6ed8aab3c72fc750b56e92b29be1f972f6bd9fe6fd70`.
The same ROM retained C1-C18 and S5. Demo ROM SHA-256
`b31ef5588a6a59bf0753158247f5187b4f43906afbfd5d66e9c4c36916cff6eb`
retained H0 and K1.

C20 implements canonical v5 `$19/$39/$59/$79/$99/$B9/$D9/$F9 doSentence`
in both semantic engines. The engine owns a bounded six-record LIFO queue with
u8 verbs, full u16 object identities, derived preposition state, and nested
freeze counts. The host launches variable 33's sentence script after ordinary
frame scripts, suppresses identical nonzero object pairs, and persists and
validates the queue. Canonical verb `$FE` consumes no object operands, clears
the queue, stops the sentence script, and clears transient input without
releasing held buttons. The 77-byte copyright-free fixture spans two ticks and
proves all eight operand flag combinations, cancellation, freeze/unfreeze, and
exact queue replacement. Malformed operands, overflow, and noncanonical save
state fail closed. SCUMM ROM SHA-256 is
`da9e832a2a7b2d7c3b41050ed3a6926a89482ae7369987d9b97f20a5070c479a`;
evidence is `build/scumm-c20-nexen-da9e832a2a7b2d7c/report.json`, SHA-256
`be2dc963a9e87df758a3496f26d652be00aefc696383709b3e1bf20e527a8055`.
The same ROM retained C1-C19 and S5. Demo ROM SHA-256
`bf283f285cf154c020cc931dcfbcdcb17d323eb2e5854076da3b41739293421e`
retained H0 and K1.

C21 implements canonical v5 `$05/$85 drawObject` in both semantic engines.
Direct/variable object identity and full-header position/state/neither selectors
share one parser; position uses canonical eight-pixel units and relocates the
walk target, exact rectangle overlap clears old states, missing local objects
are no-ops, and draw intent is bounded. Raw `OBCD/CDHD` metadata now supplies
room-local identity, geometry, flags, parent, walk target, and actor direction;
mutable object state and queue intent round-trip through host save schema 2. The
46-byte copyright-free fixture proves both opcode forms, variable/direct
coordinates and state, relocation, overlap clearing, exact queue order, missing
lookup, malformed/capacity failure, and replay. SCUMM ROM SHA-256 is
`f0626c8194eb2ff30c51528480c009ea583b0cceb6ff0028024d3a047325c9d0`;
evidence is `build/scumm-c21-nexen-f0626c8194eb2ff3/report.json`, SHA-256
`e3237a6b0189f31628d0d700e17cbce1e6af73979cc8b6bf239c5b5bb534731a`.
The same ROM retained C1-C20 and S5; the S5 report SHA-256 is
`b254ae1712b02f3632c220652f6a1de3e276b2c05df53d5a34200a73446edf71`.
Demo ROM SHA-256
`e2ce9fa4cc5a25930920ec113e0d58c8769ca5502e7bb4b53d54e04ba03a382c`
retained H0 and K1.

C22 implements canonical v5 `$72/$F2 loadRoom` transition intent and the
resource-less room-zero scene in both semantic engines. Direct and variable
room operands resolve through the existing pseudo-room mapper. Every successful
transition clears room-local objects and pending draw intent; room zero commits
current room 0, retains global object state, needs no ROOM resource, detaches
the room adapter, and produces a deterministic black presentation. Explicit
synthetic `room.0` and initial-scene fixtures remain usable without weakening
opcode semantics. The 14-byte copyright-free fixture spans four ticks and
proves variable/direct transitions, local clearing, room-zero persistence, and
the terminal state; host tests add missing-nonzero failure and save/load replay.
SCUMM ROM SHA-256 is
`f93789ee016d4c061d8833bf9e0d90ed3e35a8798f595872c94ef653c750ec8d`;
evidence is `build/scumm-c22-nexen-f93789ee016d4c06/report.json`, SHA-256
`e4d460bf72cba2860144e0958351b395df8adcd8e0b15f2dee5eea06bdcf7e46`.
The same ROM retained C1-C21 and S5; the S5 report SHA-256 is
`0d66780550e0b537d98567e3b2f89259c9090a6a2d49860d482ebe4a888ec4ed`.
Demo ROM SHA-256
`22a96a90366183260642d489c8c31e79d75163914daca88121e1494fc68b0698`
retained H0 and K1.

C23 implements canonical v5 `$14/$94 print` and `$D8 printEgo` in both semantic
engines. Four actor-routed print slots retain defaults independently; AT, COLOR,
CLIPPED, CENTER, LEFT, and OVERHEAD use canonical selector flags, `$FF` saves
defaults without emitting text, and low-nibble-15 emits a bounded encoded
message from transient style. Unsupported v5 erase/voice selectors fail closed.
Host state, message tokens, and presentation survive save/load. The CHAR adapter
now accepts both SAME's cooked fixture and canonical LucasArts v5 wrappers with
relative glyph offsets. The exact SNES fixture proves variable/direct operands,
actor slots 0/2/3, printEgo, default isolation, and `$FF 03` encoded control.
SCUMM ROM SHA-256 is
`6c9a2b2421a728b434532eb3cc3c0419d94b71c060a600f61b5b5120c033bfd5`;
evidence is `build/scumm-c23-nexen-6c9a2b2421a728b4/report.json`, SHA-256
`44df272262b4c29dac88c3f4379e9ad4325333c34833735c08e30380e469fea9`.
The same ROM retained C1-C22 and S5; the S5 report SHA-256 is
`d6cd9d29aef9dc8a7c34dc8d726ed07b2ca0b2a46c7887d68ae06fd7dab1556f`.

C24 corrects canonical v5 `$58 beginOverride/endOverride` at cutscene depth
zero. Record zero is a real sentinel, not underflow: beginOverride records the
current script PC/slot and skips the following jump, skip-abort can resume it,
and endOverride clears it without changing cutscene depth. The sentinel is
inspectable and persists in save schema 2 with backward-compatible loading.
The 20-byte copyright-free fixture proves record-zero arming across a yield,
standalone clearing, continued execution, and exact halt in both semantic
engines. SCUMM ROM SHA-256 is
`8f2f1a22e71a5c68238af5e58bc6623d30fa9d79665e95e96b17530d9d7387c3`;
evidence is `build/scumm-c24-nexen-8f2f1a22e71a5c68/report.json`, SHA-256
`1dd70280d6f5c4d2e7f92b2caed32c5f9f5ab9da4e45b8e61bde51439f7a0e44`.
The same ROM retained C1-C23 and S5; the S5 report SHA-256 is
`00ef0f92102bbc64cc435a41f700b71dcac3bde8691b3a18360c7d75c2e3782b`.

C25 implements canonical v5 `$4C soundKludge` word-varargs and the iMUSE
queue/flush boundary in both semantic engines. Commands persist until a list
beginning with `-1` drains them in order; the portable command subset maps
master volume, start/stop sound, and stop-all to normalized audio packets and
then emits an explicit FLUSH. Host save state retains the bounded 16-command,
32-word queue plus bounded history and rejects malformed streams, unsupported
commands, and capacity overflow. The 13-byte copyright-free SNES fixture proves
command 11 persistence across a yield and exact music-stop, all-SFX-stop,
speech-stop, and flush packets. SCUMM ROM SHA-256 is
`b0e38b77bbd470289572ce0b7da7da3820fbac9271a8973244d8577a5fbe9c89`;
evidence is `build/scumm-c25-nexen-b0e38b77bbd47028/report.json`, SHA-256
`d9b2755b4e9412f7a29ca1306b644cec19b59a1b1ec61bfc4bba3f4173050b22`.
The same ROM retained C1-C24 and S5; the S5 report SHA-256 is
`7bde2e7ac9e93f0503aa34c9c83160c0d43b8c6683e998836ae69e82d52a0dea`.

C26 implements canonical v5 `$AB saveRestoreVerbs` in both semantic engines.
Inclusive u8 ranges save active verb records into an independent bounded
64-slot namespace, allowing a new active verb to reuse the same identity;
restore deletes that replacement and moves the original back to bank zero,
while delete targets the requested namespace. Host save state persists and
validates active and saved records. The 42-byte copyright-free fixture proves
two-record bank save, same-ID replacement, destructive restore, saved deletion,
reversed-range no-op, and exact halt. SCUMM ROM SHA-256 is
`49cf161cc05cd27a668d9d6beff354cf52a64e06386f60efcd484c1ae653194c`;
evidence is `build/scumm-c26-nexen-49cf161cc05cd27a/report.json`, SHA-256
`8d011ee0871dc7d4040bf9bc7a982f51a556c722b7e53ef123787de72dfdf4bf`.
The same ROM retained C1-C25 and S5; the S5 report SHA-256 is
`481c22b18b4b53f3d931dbda66df42cc752a372381d7e9a8dfffdbc541ac705e`.

C27 extends the generic raw-v5 room adapter with canonical `ENCD`, `EXCD`, and
v5 `LSCR` decoding. Local script identities and bodies remain owned by their
room; `$0A startScript` resolves a missing global from only the current room,
local slots are retired on room transition, and save/load reconstructs and
validates the `(room, script)` identity. Synthetic tests cover resolution,
nested execution, yield persistence, transition cleanup, duplicate/truncated
chunks, and malformed save identity. The SNES ROM remains byte-identical to
C26 because raw package/resource delivery is still the separate K2 boundary.

C28 implements canonical v5 `$11/$51/$91/$D1 animateActor` in both semantic
engines. The live animation request is deliberately separate from C14's actor
frame and speed configuration, accepts independent direct/variable actor and
animation operands, and persists as a validated u8 in host save state. The
21-byte copyright-free fixture proves animation 250 followed by fully-variable
animation 6 across a yield and exact halt. SCUMM ROM SHA-256 is
`8c692e621bbe787321074dd7cdaa3f04db7d5847b96a1e24b2b416dcf9642776`;
evidence is `build/scumm-c28-nexen-8c692e621bbe7873/report.json`, SHA-256
`ff33aa0b99818f0c436df6e3c413454bd8f9f00ef3eac976c2d16242efc50ada`.
The same ROM retained C26 and S5; their report SHA-256 values are
`ede142686911e45bec037e0dd05746dc4fff770b1f54ed258d5fe62bcbce8946`
and `b95d7d537391007f932259372963c5e9b18f8f2b9e4293c567cf5c0cb89f337a`.
Fate room 75 independently executes exact animations 250 and 6 from local
script 200 at `$0837/$083B`.

C29 implements canonical v5 `$15/$55/$95/$D5 getActorFromPos` in both semantic
engines. It reads independent direct/variable word coordinates, searches actor
IDs 1 through 31 in ascending order, and returns the first visible actor in the
current room whose inclusive renderer-published bounds contain the point and
whose object-class mask does not include class 32 (untouchable). Neutral spatial
state persists with strict save validation. The 34-byte copyright-free fixture
proves first-match ordering, untouchable rejection, direct and fully-variable
forms, no-match zero, exact halt, and debugger-injected actor state. SCUMM ROM
SHA-256 is
`095ada6faf3113a9b233342b57e0b4760e9ae6d31e723e88973bfff4f37cfd02`;
evidence is `build/scumm-c29-nexen-095ada6faf3113a9/report.json`, SHA-256
`2421543e2c10277b53556e691cde52aa73371f08ccedaca1ac25d0d18b203403`.
The same ROM retained C28, C26, and S5; their report SHA-256 values are
`b31a6eb70615a212cb201e5d2a0d5ac72b2f7b161a2bdb5a33c785868a721c04`,
`adca354db6f298126ca7750a62bb2e1b3349651c501317a40fedc6c324692d26`,
and `a4423b58041ab423b2fdf166df1d8f99c6bd22db795e14aaf5ab05922c8a5189`.
Fate room 75 independently executes the exact `$D5` in local script 205 at
`$0004` and stores zero for its empty actor-picking scene.

C30 implements canonical v5 `$35/$75/$B5/$F5 findObject` in both semantic
engines. It reads independently direct-byte or full-variable coordinates,
searches room objects in local resource order, rejects class 32, walks the
canonical parent-state hierarchy, and applies half-open right/bottom bounds.
Raw CDHD flags map to the parent state by low nibble, with `$80` canonically
mapping to 1; local indexes and hierarchy persist with strict save validation.
The 30-byte fixture proves first-match ordering, untouchable rejection, visible
and hidden parent chains, a variable coordinate above 255, boundary/no-match
zero, exact halt, and debugger-injected room state. SCUMM ROM SHA-256 is
`b1883a97bb8fbc742a62c1159b8d3e7a4304c57086e02020dec8e9270cb78d55`;
evidence is `build/scumm-c30-nexen-b1883a97bb8fbc74/report.json`, SHA-256
`731e025c51ece913dccdc80484d65a5649188971bc14004367f09687ecfe3447`.
The same ROM retained C29, C28, C26, and S5; their report SHA-256 values are
`4afb7389971df694de5c0b880aca4a7bbbc67f5655fe653ee733595ffec5fd04`,
`972416c52f6cfcd088d9b7842f1d8d6819904e9b691355d09b190b5197dc0cd8`,
`c0dfb01b22167d966cf97b4bcf12801c1c641401922a0e02717b8a0688ba54f5`,
and `0a4bd02678077830038934edc140ee9fe463e8809350392ba8f9b529f4f34fca`.
Fate room 75 independently executes the exact `$F5` in local script 205 at
`$0018`, stores zero in local 0 and variable 108, and yields at PC `$0025`.

C31 implements canonical v5 `$2D/$6D/$AD/$ED putActorInRoom` in both semantic
engines. Actor and room are independent direct/variable byte operands. A
nonzero room assignment preserves placement, movement, and visibility; room
zero performs the canonical removal placement at `(0,0)`, stops movement, and
hides the actor. Logical position and movement flags now persist with strict
host save validation and occupy a bounded supplemental SNES actor-state block.
The 25-byte fixture proves both operand forms, variable byte truncation,
nonzero preservation, room-zero removal, exact yields/halt, save/load,
malformed-state rejection, and debugger-injected spatial state. SCUMM ROM
SHA-256 is
`037756487486b48f54eef64cae52aa7270ad42e081cd168e7a322282bdf2c62a`;
evidence is `build/scumm-c31-nexen-037756487486b48f/report.json`, SHA-256
`2a8c22ba55c3f7b2bd5d6031be1ff180c657cc258155e381127de64f2e5452dc`.
The same ROM retained C30, C29, C28, C26, and S5; their report SHA-256 values
are `7d4b53d68d041c4de4a1a140b838c05b92b030f29716c6745bfcca77156cd113`,
`f6411aea3423e1bd0b444aba6a9f47f504aca6f520102eb555d3e939ddbee274`,
`0a43c63e13637aa396ea1bbc895b598f696ab57e6597d63befa6ee440c9d896f`,
`674d645b27fbf2a9c2d57ad006192b4a95bd18a5d0d0383acf4953edf6eb656a`,
and `5d4c98567c55a5fedca6a3b2cdd99afd0fa11f8446bb1cd4f5a13446221d5363`.
Fate room 75 independently executes exact `$2D 0A 4B` in local script 200 at
`$082D`: actor 10 joins room 75 but remains hidden at `(0,0)` pending the next
canonical `$0E putActorAtObject` at `$0830`.

C32 implements canonical v5 `$0E/$4E/$8E/$CE putActorAtObject` in both
semantic engines. It resolves the selected room object's decoded walk point,
uses the canonical `(240,120)` fallback when that object is unavailable, and
applies `putActor` visibility/movement lifecycle: actors in the current nonzero
room are shown and stopped, visible actors elsewhere are hidden and stopped,
and already-hidden actors elsewhere retain movement state. Raw-room walkbox
snapping is explicitly deferred. The 27-byte fixture proves direct and
variable operand forms, two walk points, fallback placement, all three
lifecycle branches, exact yields/halt, save/load, invalid actors, and truncated
operands. SCUMM ROM SHA-256 is
`9600d1e035cd86e0aeecac5a75dd2a1595a9a1ac22cedc27ef90338d8f3687da`;
evidence is `build/scumm-c32-nexen-9600d1e035cd86e0/report.json`, SHA-256
`47ec45e5fdd2aed1425614a1adee6f96f101ca7bb8511788f678191086e7963a`.
Fate room 75 independently executes exact `$0E 0A 07 04` in local script 200
at `$0830`, placing actor 10 at object 1031's decoded walk point `(1164,46)`,
showing it, and leaving movement stopped.

C33 adds a generic classic v5 costume decoder and raw-room actor compositor in
the host presentation adapter. It strictly decodes stripped format `$58/$59`
headers, 16/32-color palettes, animation/data/frame offset tables, initial limb
sequences, signed cel geometry, and BYLE RLE. Visible current-room actors are
drawn in vertical order with costume palette overrides; their exact rendered
bounds become the hitbox consumed by C29. Copyright-free `$58/$59` resources
prove decoding, composition, palette mapping, hitbox publication, absent poses,
and corrupt format/table/RLE rejection. Fate costume 58 independently decodes
its initial 180-degree frame to one 7x7 cel: 37 opaque pixels at
`(1161,43)..(1167,49)` around C32's actor-10 placement, producing logical room
SHA-256 `7b1c33673fd48f822bbaca4d25a2877e63596bce3dfaa42d4275cae66bf91ee5`.
Evidence remains in `build/scumm-s6-fate-preflight/report.json`, SHA-256
`6c6a69620e5fab6020491ca2733b2a4223da970d3c5a70bc62033c7e0a7eacb6`.
SNES-side raw costume delivery remains owned by K2, so the C32 ROMs are
byte-identical.

C34 makes classic costume chores persistent in the host oracle. Each actor now
owns a cardinal facing, active frame, step cursor, and speed progress which all
round-trip through strict save validation under the bumped schema 3. The
decoder advances all limb sequences with loop/one-shot behavior and canonical
`$7C/$78` skip handling;
the engine draws before advancing and only recomposes when visible commands
change. Synthetic two-cel resources prove looping, one-shot holding, speed
gating, draw order, save/load, and corrupt cursor rejection. Fate costume 58
independently advances frame 1 from command 0 to command 1: its second logical
pose retains 37 opaque pixels and the exact hitbox but changes the room SHA-256
to `0e1972cf93f4fdce4d62abe54f4f2164417b50dfd971eee4be24c6aca041f104`.

C35 implements the classic 256-phase costume scale table in the raw-room actor
compositor. It scales signed cel offsets around the actor's foot anchor, applies
independent x/y actor scales, retains the original draw-direction phase, and
uses canonical column-major BYLE traversal. Copyright-free asymmetric 4x4 cels
prove horizontal overwrite, vertical suppression, nonuniform `(128,192)`
scaling, exact anchors, mirrored phase behavior, hitboxes, and final pixel
counts. Fate costume 58 at `(128,192)` scales from 37 to 26 opaque pixels with
bounds `(1162,43)..(1166,48)` and exact logical-room SHA-256
`62db861295d986afacf38eb97e24ce29b99bdc2cb2e4eea3c0a79e29d94d33f2`.

C36 decodes classic raw-room `ZP01..ZP04` occlusion planes declared by `RMIH`.
It validates each little-endian strip-offset table, accepts canonical zero
offsets as blank strips, expands literal/repeat mask RLE (including zero count
as 256), and retains one MSB-first mask byte per eight-pixel strip row. The
actor compositor applies the explicit v5 `forceClip` plane, clamps it to the
room's available planes, counts occluded writes, and derives hitboxes only from
visible pixels. Synthetic rooms prove plane layout, blank strips, both RLE
forms, exact pixel occlusion, and malformed-data rejection. Fate room 42
independently exposes three planes; plane 1 hides all 37 opaque pixels of real
costume 58 at `(10,55)`, producing no hitbox and exact base-room logical
SHA-256 `9d451e87313acc1a834ed29dbfbc23c1bd3596de0c9de348e3ecf95117a7cc55`.
Automatic walkbox-driven plane selection remains coupled to the future walkbox
adapter; explicit `forceClip` occlusion is complete.

C37 decodes canonical v5 `BOXD` walkboxes as a little-endian count followed by
20-byte records containing four signed corners, z-mask selector, flags, and
scale. Point containment follows the classic oriented-edge test, including the
v5 near-line case, and selects overlapping usable boxes from highest index
down. With no explicit `forceClip`, actor feet now inherit their walkbox mask;
ignore-box actors and class 20 bypass clipping, while positive `forceClip`
retains precedence. Synthetic trapezoids prove geometry, record validation,
automatic occlusion, class bypass, and explicit override. All ten Fate rooms
decode their exact walkbox counts. In room 42, actor position `(193,100)` lands
in walkbox 10, whose mask 1 automatically hides all 37 costume-58 pixels and
leaves an empty hitbox. `BOXM` route decoding and actor motion remain separate.

C38 strictly decodes `BOXM` into one `$FF`-terminated route row per walkbox.
Each ordered three-byte range maps destination boxes to the next itinerary box;
invalid, overlapping, out-of-range, truncated, or trailing records fail closed,
with the canonical single alignment byte accepted. The generic room exposes
bounded next-box queries. Canonical `$7B/$FB getActorWalkBox` now resolves the
actor's current raw-room foot box for direct or variable actor operands and
returns `$FF` outside the current room. Actor walkbox state persists under the
bumped save schema 4. Synthetic routes prove compressed ranges, opcode forms,
and save/load. Fate room 42 independently pins routes `1->10` via 2 and `10->1`
via 7 across its real 11-row matrix. `$1E walkActorTo` gate traversal remains
the next movement slice.

C39 implements canonical v5 actor movement in the host oracle. All eight `$1E`
operand forms snap destinations into usable boxes, select decoded `BOXM` routes,
cross exact shared-edge gates, and step scaled 16.16 deltas while updating
walkboxes, cardinal facing, and walk/stand chores. `$56/$D6 getActorMoving` and
`$3B/$BB waitForActor` observe the live flags. Save schema 5 strictly persists
the complete route and fractional leg state. The synthetic proof resumes a
three-box walk mid-leg; Fate room 42 independently crosses boxes `5→6→8→7→10`
from `(44,80)` to `(200,110)` in 27 frames.

C40 adds generic embedded audio playback to the S6 second-profile work.
The adapter validates `SOU ` containers, selects `ROL `/`ADL `/`SPK ` by tag,
parses `MDhd` plus the initial Standard MIDI track, and synthesizes deterministic
signed-16 PCM into SAME's host streaming service. `$7C/$FC isSoundRunning`
reports the live adapter state, and save schema 6 restores embedded playheads.
All 27 readable Fate sound resources decode; stale full-game directory entries
are no longer advertised. Real sound 172 renders 12,210 frames at 22.05 kHz with PCM
SHA-256 `e328daeefaedacf1316e284286e56fbe177d94a19d2959898dc5f61b06573749`.
Its frame-1 save resumes to byte-identical output and stops at the decoded end.

The S6 raw-room slice adds a generic v5 decoder and presentation adapter behind
the engine/resource boundary. It strictly parses `RMHD`, `TRNS`, `CLUT`,
`RMIM/IM00/SMAP`, and `OBCD/CDHD`, retains a logical indexed surface and local
object metadata, and projects the surface into the
host viewport. The supported canonical strip families are raw 256-color,
horizontal/vertical zig-zag (including transparent variants), and the
major/minor families. Synthetic raw, vertical, and major/minor strips, viewport
presentation, corrupt chunks/offsets, and unsupported codecs are covered by
four new tests. All ten rooms exposed by the Fate demo decode; room 68 produces
logical SHA-256
`2f633aec02b1b7f5e22adc70e18aa15fff9a668b3b15d5c829ae1b1907e57490`
and projected SHA-256
`31539e278fb6a3485bd02859a4c6363b633814a6316fd7c61050f8ecb0e90581`.

S6 preflight now uses the user-supplied Fate of Atlantis interactive demo. Its
included `READ.ME` explicitly permits free copying/distribution when copyright
and trademark notices remain intact. The exact archive SHA-256 is
`558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`.
The new profile models embedded audio, costumes, three accessible CHAR resources,
320x200 logical coordinates, preserved copy-protection behavior, and the demo's
disabled game save menu. The generic adapter exposes only bytes actually present:
10 rooms, 74 scripts, 27 readable sounds, 20 costumes, and three charsets.
Logical pointer input reaches the engine and SAME save schema 6 round-trips the
boot state.

This remains a deliberately incomplete S6 gate. The exact real
boot now crosses the C8 string workload, both C9 range initializations, and its
first C10 `loadString(31, "iq-points")` without altering the destination when
the auxiliary file is absent. C11 then executes the real script-75 random call:
maximum 255 produces 226, persists PRNG state `$E270`, and supplies the exact
delay used by the child slot. C12 then consumes all 31 pseudo-room records and
constructs the exact 128-entry mapper, with 100 populated entries. C13 executes
the real `$0C 11` clear-heap resource routine with empty intent. C14 configures
Indy (costume 2, talk color 15), Sophia (costume 28, talk color 13), and actor 4
(talk color 14), preserving encoded names. C15 then selects actor 1 as the
camera-follow target. C16 then sets class 13 on object 2. C17 constructs 35 exact
verb records (IDs 1-12, 50-55, 100-112, and 129-132). C18 completes the two
canonical `$AC` expressions in script 132. C19 enters the real `$40` cutscene
and stores its exact stack record. C20 crosses `$19 FE`, empties the sentence
queue, clears the transient pointer edge while retaining the held pointer, and
completes callback script 20 plus child initializer scripts 13 and 14. Script 74
then crosses `$72 loadRoom(68)`: the raw 19,376-byte `RMHD` room decodes as a
320x200 logical image of forty codec-18 strips and presents through the 256x224
host viewport. C21 then crosses the real `$05` at script 74 offset `$0033`,
drawing object 939 with default state 1 and decoded geometry 24,32 / 272x144.
After pointer release, C22 crosses `$72 loadRoom(0)` without requesting a
resource, clears room-local object/draw state while preserving global state 1
for object 939, and presents the deterministic null scene. C23 consumes the
setup-only `$14` at `$007A`, saving slot-0 `(160,8)`, centered and overhead,
without emitting text. The real raw `charset.1` also decodes its exact 6x8
digit-three glyph. C24 identifies `$58 00` in callback script 21 at offset
`$0004` as a legal zero-depth sentinel clear. Script 74 then retires at PC 140,
the main boot script retires at PC 13168 on frame 524, and the engine enters raw
room 75 with deterministic projected SHA-256
`03c2fbb7571a6848f81d73fe70b06bb0451de2969327a6bd722e7b7f0e37c46c`.
The room-75 `ENCD` frontier then supplies exact bytes `4c010b00ff` at `$00E7`
and `4c01ffffff` at `$00EC`: command 11 queues without an audio packet and
command -1 flushes the exact four normalized packets proven by C25.
The exact four `$AB` records in script 19 at `$0117` also save verb ranges
`1..12`, `101..112`, `100`, and `52..55` into banks 1/5 through C26, removing
all 29 records from the active namespace.
The C27 adapter then decodes room 75's nine local scripts `200..208`; its exact
entry code resolves `LSCR.200`. C28 executes that script's exact `$11`
actor-10 animation requests 250 and 6 at local offsets `$0837/$083B`. C29 then
executes the exact `$D5` in `LSCR.205` at `$0004`, stores the no-hit result zero
in local 0, and takes the canonical branch. C30 executes the exact `$F5` at
`$0018`, stores zero in local 0 and variable 108, and reaches its yield at PC
`$0025`. C31 executes exact `$2D 0A 4B` in `LSCR.200` at `$082D`, assigning
actor 10 to room 75 without prematurely showing it. C32 executes exact
`$0E 0A 07 04` at `$0830`, placing and showing actor 10 at object 1031's
decoded walk point `(1164,46)`. C33 decodes costume 58's initial 7x7 cel,
draws 37 opaque pixels, and publishes hitbox `(1161,43)..(1167,49)`.
C34 then advances costume 58 from step 0 to step 1 with exact second-pose SHA-256
`0e1972cf93f4fdce4d62abe54f4f2164417b50dfd971eee4be24c6aca041f104`.
C35 scales its initial pose to `(128,192)`, producing 26 pixels, bounds
`(1162,43)..(1166,48)`, and logical SHA-256
`62db861295d986afacf38eb97e24ce29b99bdc2cb2e4eea3c0a79e29d94d33f2`.
C36 decodes room 42's three raw z-planes. C37 then selects plane 1 automatically
from walkbox 10 at `(193,100)`: all 37 costume-58 pixels are hidden and its
hitbox is empty. C38 decodes the complete `BOXM` routing matrix and pins real
Fate route probes. C39 implements canonical `$1E` movement, `$56` queries, and
`$3B` waits, with complete route persistence. C40 decodes every readable Fate
sound, streams deterministic PCM, implements `$7C/$FC`, and resumes active
audio under save schema 6. C41 decodes every MIDI track and the complete
observed Fate iMUSE SysEx surface: 104 setup, 27 start, 189 hook-jump, 28
part-gate, and 12 marker commands. Real sound 80 consumes hook 15 by jumping
from track 0 tick 90 to track 2 tick 1920, and its branch state resumes
byte-identically after save/load.

C41 also adds the first production SNES audio path. The 64 KiB SCUMM ROM boots
Terrific Audio Driver protocol v20 through its loader, transfers common/song
data, and maps normalized SAME play/stop requests. A reviewed sound-172 MML uses
a repository-generated additive waveform. Fresh Nexen evidence captures real
S-SMP/DSP output above the blank-song baseline for exactly 120 video frames,
with zero queue rejections and an equal SAME frame-counter delta. The same ROM
retains C1 through an atomic engine-frame inspection guard. S6 remains in
progress: after C54 sound 153, production arrangements for 9 readable sounds
remain.
Evidence is
`build/scumm-s6-fate-preflight/report.json`, SHA-256
`8334ae6cc371d9f9e23b51b8bdb3bf2a247744d22668f2cac3a0c3c92335f95b`.
No Fate-specific branch was added to the opcode core.

C42 adds the first listener-reviewable Fate instrument bank. The authorized MI
library supplies low/main sample pairs for organ, marimba, flute, atmospheric
pad, and a soft-bass source plus kick/snare percussion. Six short TAD audition
songs expose sustained tone, scale range, exact zone seams, a deliberately
strained bass octave, velocity steps, and a simple beat in isolation. The TAD
layout is now generated from compiler output and can span two LoROM banks; the
current 128 KiB ROM is
`f8d06bd49fe6a81581c1bd27a1f19fcc91deb3ab28ea7045746a41470c53d9c4`.
Its Nexen capture suite passes nonzero DSP output, exact 2,400-frame advancement,
and unclipped-tail checks for all six songs. Report SHA-256 is
`3946eaa6809b198be533bb07c9f8697d85719c1f99377937cc3ed3df9a583587`.
Timbre and octave transitions are intentionally pending listener verdicts; a
mechanically valid capture is not treated as an approved instrument.

The first listener pass accepts and locks soft bass and kick/snare percussion.
It rejects the organ main loop/seam, low marimba, high flute, and low pad. That
verdict is preserved in `audio/fate_s6/auditions/REVIEW_ROUND1.md`. Round two
removes the rejected zones, uses exact reviewed MI boundaries, and captures four
focused repairs from ROM
`f9c1dd17c051c5c1afcf7d2b24a7a1b7bc8d6b8fc2c89199e1423f7779666c02`.
Its report SHA-256 is
`15341d532925ca1259c2f7837fe861769f43359e04d802aab6b9c2362f2be0d7`;
the second listening pass remains open.

Round two accepts and locks marimba, rejects the remaining organ seam and flute
upper sources, and accepts the pad only below its highest notes. Round three
uses a single organ source and derives flute 2x/4x and pad 2x zones offline from
their accepted low PCM, closing each derived loop on its own waveform at a BRR
boundary. Current ROM SHA-256 is
`018b78b08fdcf27b4bf44ea5bb8e31c2f7278df0cdd89e6806cb1913bbf14430`;
three-capture report SHA-256 is
`6c7ff5cad1e505af60fce81da475a38512eec2bf0b083fd5e7e0fc6742943caf`.
The third listening pass remains open.

Round three instead hard-rejects all three repairs: organ exposes its underlying
long-loop period, flute becomes grating at the 2x zone, and pad progresses from
an audible seam to severe clicking. Round four discards those long-loop sources
and builds exact-period phase-averaged wavetables in TAD's loop-safe mode. Current
ROM SHA-256 is
`5d097a9489ae83bc91bba8c9b6cff3b4db50d59918aee058149113b5bc7f4eae`;
three-capture report SHA-256 is
`8a2e9b325b03e79fdca554a04670082e85c4bc35748df5e1a1552a7a5a2695e4`.
The fourth pass's perceived interval concern triggered objective measurement.
The first octave-low conclusion was invalid because the analysis mapped TAD
octaves incorrectly; TAD uses C4 as middle C. Round five uses the canonical map,
accounts for Nexen's configured 32,040 Hz SPC clock, and gates every sustain to
±3 cents. All 16 notes pass within 0.65 cents. It also replaces duplicated-block
loops with filter-reset loops. Current ROM SHA-256 is
`01a9d2c5da64286298e9ddde8aa1b48c19f7ea34f2b9a21e538e4bd8df3d03a0`;
three-capture report SHA-256 is
`4c3510572edc65e918d091002fc99ab0f9600457b7585a6eac331452d228dd68`.
Round five passes as usable sounds. The listener explicitly notes that the
periodic organ, flute, and pad have little texture; this is accepted as a clean
foundation, with expression deferred to complete arrangements. The verdict is
preserved in `audio/fate_s6/auditions/REVIEW_ROUND5.md`.

C43 adds the first complete production cue after sound 172. A bounded reusable
ROL-to-zoned-MML converter pairs note lifetimes, retains dynamics, allocates
polyphony across at most eight voices, and selects reviewed pad/flute zones by
MIDI note. Unsupported programs and interactive multi-track resources fail
closed. Fate sound 17 converts all 23 notes and its complete 13.380-second
timeline. The SNES mapper now separates logical sound IDs from compiled TAD song
IDs (`172→1`, `17→8`). Fresh Nexen evidence advances exactly 900 video/SAME
frames, enters at 4.742 seconds, ends at 13.658 seconds, and records zero rejected
requests. Production ROM SHA-256 is
`e18efcb6b9cf019fbc8d47c0074d858f6a9bc0a99215bfe47b74b83984b3f107`;
sound-17 report SHA-256 is
`9f60623d3bf6c077de0cc7b5ddcefbca86d48c0f071ff9842d6ee3c352097139`.
Sound 172 and C1 independently remain green.

C44 adds the first cue-specific register policy and the third production cue.
Fate sound 154 converts all 28 source notes across the exact eight-voice peak.
Programs 32/36 retain the accepted bass through B3 and explicitly cross to pad
above its reviewed range; programs 50/92 use pad and program 97 uses zoned
flute. Out-of-policy notes fail closed. Logical sound 154 maps to compiled TAD
song 9. Fresh real-DSP evidence advances exactly 840 video/SAME frames, enters
at 3.163 seconds, ends at 12.614 seconds, and reports no rejected requests.
Production ROM SHA-256 is
`6b5ee39f2e38d0bb19f99fcf47634e0961a094d63e2a5537e9d676443d322ec5`;
sound-154 report SHA-256 is
`7b4c78744812b107b1ca6b5975fc3348ad1db02d8a8dcbf5d74feede522c7488`.
Sounds 17/172 and C1 independently remain green.

C45 adds opt-in deterministic reduction for source cues above eight voices.
The policy preserves stronger notes, breaks exact-strength ties toward the lower
register, and audits every omission in generated MML. Sound 83 accounts for all
30 notes: 29 remain, while its sole 9-voice collision omits only a
velocity-1/CC7-47 G6 double of the retained G5 layer. Logical sound 83 maps to
TAD song 10. Fresh real-DSP evidence advances exactly 840 frames, enters at
3.140 seconds, ends at 12.534 seconds, and reports no rejected requests.
Production ROM SHA-256 is
`264f68839b56a9486a9e2557842c994f619fbfadd7b6ec849baebcb391fcfcaf`;
sound-83 report SHA-256 is
`6436c96170ac8effe8486d0a21d841783eb843a29905fc4661f33f822d43ccc7`.
Sounds 17/154/172 and C1 independently remain green.

C46 adds interval-based voice virtualization for dense cues. Sound 18 retains
all 25 source notes despite an eleven-voice peak: identical mapped pad pitches
merge into the stronger foreground note, while the quiet program-50 chord ducks
only during over-capacity intervals and resumes afterward. All nine merge/duck
decisions are audited in generated MML. Logical sound 18 maps to TAD song 11.
Fresh real-DSP evidence advances exactly 780 frames, enters at 2.493 seconds,
ends at 11.425 seconds, and reports no rejected requests. The listener accepted
the capture as sounding alright. Production ROM SHA-256 is
`e6718d46726bdb2d2193767d1138b553f0b01cb90a78bdd12acc7658d2c764e4`;
sound-18 report SHA-256 is
`6bd551ab280850d8387582c406b35a04070f7b08b09520d8febffa6a3a51537f`.
Sounds 17/83/154/172 and C1 independently remain green.

C47 adds the accepted marimba as an explicit program-0 attack role. Fate sound
185 retains all seven notes of its D2–A4 chord on seven physical voices with no
reduction. Logical sound 185 maps to TAD song 12. Fresh real-DSP evidence
advances exactly 120 frames, enters at 0.512 seconds, ends at 1.599 seconds, and
reports no rejected requests. Production ROM SHA-256 is
`50bb3b2d7be8407103f6685512b01c9c04234b8763c6ec4a484e145b50b27730`;
sound-185 report SHA-256 is
`2b99221a25dc72ac12238d557edbe70b686e14b4f8f14d5004ae6f9a371ee4a5`.
Sounds 17/18/83/154/172 and C1 independently remain green.

C48 adds a shared split-register program-0 impact policy. Sounds 190 and 192
retain all three and four source notes respectively: C1..B1 uses accepted bass,
while C2..B5 uses the accepted marimba attack. Logical sounds 190/192 map to TAD
songs 13/14. Fresh real-DSP evidence advances exactly 90 frames per cue. Sound
190 enters at 0.328 seconds and ends at 1.192 seconds; sound 192 enters at 0.393
seconds and ends at 1.050 seconds. Both report zero rejected requests. Production
ROM SHA-256 is
`f1fab4cb1b5f6dd080a2a918edcac12f9f66b1368df792127fc658c868fb3038`;
report SHA-256 values are
`839704a7ee7aa7c5fa8a45e24960a3c02ea72d0b13015f60d7058930b296bd61`
and `d269901f68701ccea9568a894350f5be18cab648cdf2df51761d3ed03e4e311c`.
Sounds 17/18/83/154/172/185 and C1 independently remain green.

C49 corrects the marimba policy ceiling from the accidental B4 numeric bound to
the reviewed/project-declared B5 bound. Sounds 141, 201, 202, and 207 each retain
both source notes without reduction; the overlapping attacks in 201/202 remain
independent. Logical sounds map to TAD songs 15–18. Fresh real-DSP evidence pins
audible windows `2.963–7.134`, `0.319–5.576`, `0.318–5.576`, and
`0.319–1.788` seconds respectively, with exact frame pacing and zero rejection.
Production ROM SHA-256 is
`88c0264e7ea2a05b38a03c1dc4b5754376efda4134063ad4ea770a16c304af3d`;
report SHA-256 values are
`d2d681cfc9527f1563a170e3db58902b45807c924e55e5f19405111bacf4cea2`,
`5ef5816cab45976a6efc9677c0fb94736f7c9947a5c5aeb09617b28a65f058f0`,
`0fc600f4b3d7c44faa068de0f959631bbc711625144a02a6c8e78ca9ae0bfff7`,
and `d5acf98e07d2d932e313406f64454a32493a759ba71a5896173246f51c95ac3f`.
All eight earlier production cues and C1 independently remain green.

C50 adds chord-aware same-instrument virtualization. Sound 183 represents all
110 source attacks despite a twelve-voice peak by protecting outer pitches and
new attacks, then selecting the strongest interior tones. Its 14 audited duck
intervals include 10 restores and four already-attacked sustains that yield
through note end. A cue-specific two-tick grid encodes TAD's minimum key-off
duration; excessive simultaneous protected attacks fail closed. Logical sound
183 maps to TAD song 19. Fresh real-DSP evidence advances exactly 1,140 frames,
enters at 0.365 seconds, ends at 17.822 seconds, and reports no rejection.
Production ROM SHA-256 is
`39e7bcc4957ea241057dda10433c01686fe7bbdc838f34b9e374347af8dedf2e`;
sound-183 report SHA-256 is
`41e40471c943070ad4cbce716266c08cf1ef5474881397ea7023402cf299780f`.
All twelve earlier production cues and C1 independently remain green.

C51 adds a reviewed wide-register effect family for the shared sound-91/117
ascending gesture. Both cues use accepted bass for E2..B2 and the existing
production Fate tone for C3..G7 on a two-tick timing grid. Sound 91 represents
all 34 source attacks on one voice; sound 117 represents all 37 attacks on four
voices, including its sustained harmony. Neither cue needs omission, merging,
or voice reduction. Logical sounds 91/117 map to TAD songs 20/21. Fresh
real-DSP captures advance exactly 240/360 frames and pin audible windows of
2.294–3.011 and 2.295–3.974 seconds with no rejection. Production ROM SHA-256
is `787c8bf5da4674e98304c6376c98ec1923da1b7273927edbdf415bce077fa544`;
report SHA-256 values are
`8a49bb0b1bbd13fc57f78cf04dc2a025272609b7696874c834f1463a217a5df1`
and `125108f998790bba08804027633b8c3aef4821f2fd6a5273cec4b1dedfe3426c`.
All thirteen earlier production cues and C1 independently remain green.

C52 adds the first complete long-form production arrangement. Sound 78 maps
program 73's C5..G7 lead to the reviewed zoned flute and programs 82/91's
C2..G4 layers to the accepted pad. All 91 source notes and their dynamics remain
represented across the exact 84.000-second timeline; its six-voice peak needs no
reduction or virtualization. Logical sound 78 maps to TAD song 22. The extended
real-DSP harness advances exactly 5,280 video and SAME frames and pins audible
output from 6.333 through 82.957 seconds with no rejected request. Production
ROM SHA-256 is
`0c2f732bca9345130503788cb3ba4d43c30e189232fdd57bb494ce81fefcebaa`;
sound-78 report SHA-256 is
`c0cea87666cf1ea3429b174e41046a6e04af28b46e754c26380326f2455d5a9f`.
All fifteen earlier production cues and C1 independently remain green.

C53 adds capacity-triggered identical-pitch sharing and complete sound 81. Its
113 source notes use marimba for program 0, split bass/pad registers for program
32, and pad for programs 82/90/92. Only the exact 7.968–8.024-second nine-voice
interval requires sharing: a velocity-1 program-92 G4 temporarily merges into
the stronger program-90 G4. All 113 source attacks remain represented; no
unrelated pitch is reduced or ducked. Logical sound 81 maps to TAD song 23.
Fresh real-DSP evidence advances exactly 1,500 frames, remains audible from
2.777 through 22.320 seconds, and records no rejection. Production ROM SHA-256
is `6dd844df83205f2e2501c93c109bbbef4cdeed90249b6c9fddf29e7753855e5a`;
sound-81 report SHA-256 is
`4d551f72664a029d57d896ae26fee3ea9b12c1f6ba34d41e58dce861c051da0b`.
All sixteen earlier production cues and C1 independently remain green.

C54 adds attack-preserving orchestral virtualization and complete sound 153.
Its 55 source notes use existing marimba, split bass/pad, pad, zoned flute, and
Fate-tone roles across a twelve-voice peak. At capacity, only already-sounding
identical pitches may merge; all new attacks and the outer register remain
protected before the strongest interiors are selected. All 55 attacks survive.
The 42 audited decisions comprise 31 merges, eight duck/restores, and three
sustains yielding through note end. A two-tick grid explicitly satisfies TAD's
minimum key-off duration. Logical sound 153 maps to song 24. Fresh real-DSP
evidence advances exactly 1,920 frames, remains audible from 3.156 through
28.388 seconds, and records no rejection. Production ROM SHA-256 is
`fa4a10c07121757e8dc717814ccee46434f17edc7345128de7471b5d236a73a6`;
sound-153 report SHA-256 is
`5f5f7909bfbbb0a8f61a931ae822ce16fa8157e8a0b7ecf800d26e02baf43429`.
All seventeen earlier production cues and C1 independently remain green.

C55 remains under listener review after its original rejection. The converter
now carries CC7 changes through held source notes, timing quantization, and
voice virtualization, then emits TAD fine-volume changes with `w` waits so the
sample is not retriggered. Sound 150 retains its logical 94.963-second lifecycle
and all 23 attacks, while its terminal static loops slur into a 256-tick fade
ending at 18.680 seconds; audible DSP ends at 22.197 seconds. Re-auditing all 19
production cues found active-note automation only in sounds 18, 83, 150, 154,
and 192. All five have been regenerated; the other 14 require no envelope
change. Candidate ROM SHA-256 is
`0d7c7641dc54478e6e7dad01e82bec1df202c38f76255e70d4fa697202b58805`.
Fresh exact-ROM S6-TAD reports for sounds 18/83/150/154/192 have SHA-256 values
`84e4f3afa199e4c84be30f421178d914eb16b902464e49009da67f61b8233a33`,
`9ae7601e28b2e41478c4e0b859fa8d9d67c3e3b6b6bf7abe568e3c2e659c592f`,
`6dcd613ace471406525e21fef965027df7755fea0c0dc996cfb97ac47adf42aa`,
`884629edb14d7d6dc64a9fc30b07e3463da38978bac5eb2506d14cb17ac0e8db`,
and `0f8a11a54d6ba67177fa6378fd8e0064a6c1d0308ef7ad2964ed7c5ac195cdb6`.

The generic embedded-audio decoder now also preserves complete iMUSE `$10`
AdLib instruments: channel plus all 30 decoded bytes, including both optional
modulation envelopes. Fate sound 154 contains six such definitions. An isolated
ScummVM iMUSE/Nuked-OPL capture additionally proves that its unconditional
`$30` jump at 148,806 microseconds skips the apparent linear-SMF setup silence.
The 10.643696-second reference WAV SHA-256 is
`b35f72d3153ce5fef282d62cc1204346f71079a143cb6dd9fcf23c289b0e44f3`;
exact inputs and the oracle harness are recorded in
`audio/fate_s6/ADLIB_ORACLE.md`.
All mechanical gates pass; focused listener acceptance remains required before
the affected cues regain production-audio status.

The next sound-154 timbre gate is now concrete. A local extractor emits all six
commercial-demo `$10` definitions without committing them, and an audition-only
ScummVM harness plays C2 through C6 through Nuked OPL. The deterministic capture
has raw PCM-container SHA-256
`9c63b135ce9d3e0a26c3db1cd894024950427bd357ed578b98b702f8d64822fb`;
six isolated listener WAVs, exact PCM hashes, and a checklist are under
`build/fate-sound154-adlib-auditions/`. Channels 1/2/4/5/6 are active score
layers; channel 9 is retained as the sixth source definition. BRR zoning and
production TAD replacement remain intentionally gated on this isolated review.
The first verdict correctly identifies channel 9 as an unused percussion/noise
definition rather than a melodic candidate. It also caught a listener-file
defect: channel 6 had been cut directly into its first attack. That WAV is now
recut with 255 ms of near-silent pre-roll; its low octave remains pending
re-listening before any BRR zone is selected.

The corrected sound-154 candidate is now integrated. Five independently reset
Nuked captures produce seven BRR-aligned multi-cycle octave zones; channel 9 is
not promoted. A dedicated canonical-ADL converter follows the unconditional
`$30` jump, retains all 26 post-jump attacks, five melodic timbres, active-note
CC7, and an exact eight-voice peak. The old 2.857-second linear setup delay is
gone. Its volume path now reproduces the SCUMM AdLib driver's patch-dependent
nonlinear operator attenuation instead of multiplying velocity by CC7. That
restores channel 5's intentional velocity-1 G5/G6 finale, formerly reduced to
TAD `V1`. ROM SHA-256 is
`67daeb570fefb30b6db540ef0618fdf7daf35ebe74939e94ce93c57ed8a63514`;
the passing 840-frame real-DSP report SHA-256 is
`5572df06217405668033297e5d1fe4a363f07c1087cc9322f4109eeb1afeeb20`.

The cue now proves the first QuickTime-inspired reusable SAME music-device
slice. A backend-neutral `SequenceIR` separates parts, stable note lifetimes,
controllers, source timing, and provenance from physical voices. A shared
SCUMM-v5 AdLib device implements the original nonlinear, patch-dependent
operator response, while a schema-validated bank resolves complete patch
fingerprints and pitches to SHA-pinned, listener-approved octave zones. Sound
154 consumes all three layers and regenerates the accepted MML with unchanged
SHA-256
`45110f50f2b4d4ff31a922f8eb2c43d886dbba5940dea8dae5ea0b3f035a5a18`.
The rebuilt SCUMM ROM remains byte-identical at
`67daeb570fefb30b6db540ef0618fdf7daf35ebe74939e94ce93c57ed8a63514`;
its fresh 840-frame real-DSP gate passes. This is the reusable semantic and bank
foundation, not yet a QTMA decoder or runtime OPL synthesizer.
Audio begins at 0.496 seconds, ends at 9.939 seconds, and records no rejection.
Its 12,324 PCM peak closely matches the 12,055 Nuked oracle peak, with zero
clipped samples.
Focused A/B listening against the Nuked oracle is the remaining acceptance gate.
The first candidate failed that gate with repeated hard attack clipping. Adding
a 256-sample phase-correct fade-in and retaining BRR predictor history reduced
its worst adjacent PCM jump from 2,260 to 846 at the final oracle-matched level,
versus 657 in the reference;
the corrected candidate remains pending listener acceptance.

M2 removes cue identity from the shared conversion path. A generic linear
SCUMM/iMUSE importer owns selected-path timing and provenance; a generic AdLib
realizer verifies part/patch identity, applies the source-device response, and
resolves fingerprinted octave zones. An independently authored two-note SCUMM
AdLib cue proves a second consumer including active-note CC7. No other Fate cue
is treated as covered: the demo-wide fingerprint/range survey found none whose
complete patch set lies inside the seven approved sound-154 zones.

A strict raw QTMA importer now targets the same `SequenceIR`. Its copyright-free
232-byte fixture contains two Note Requests, melodic and percussion parts,
Volume/Pan/Sustain, a chord, crossing-rest percussion, a melody note, and End at
tick 600. It peaks at three notes and emits a committed exact 13-record trace.
Fixture SHA-256 is
`1a595217e6ef5e05e3f15c193a92d364243db7c308c179ff48109e1456e2b0c0`.
Malformed General framing, truncation, unknown parts, unsupported event types,
and trailing data fail with typed source word/byte offsets. Fate sound 154 still
regenerates byte-identically at MML SHA-256
`45110f50f2b4d4ff31a922f8eb2c43d886dbba5940dea8dae5ea0b3f035a5a18`.
MOV `musi` extraction remains a later, separate adapter gate.

M3 adds a source-neutral deterministic playback session. It uses absolute
rational tick-to-sample mapping, lowest-free stable voice handles, part-local
sustain deferral, and explicit completion/stop cleanup. Bounded allocation
failure reports the exact tick, requested note, and active-note set. The
integer-only reference synthesizer renders the copyright-free QTMA fixture to
exactly 24,000 mono signed-16 frames at 24 kHz with zero clipped samples. PCM
SHA-256 is
`0b5d2002c7a3f72069ddc373f6000ef90c29ff8b71de37909bb57eafd7a933a7`;
canonical WAV SHA-256 is
`5555b38dc9c89f9cd6572003ad1cfef3b39d81b0037cb5c5cbb91d77a9fad811`.
MOV parsing and TAD policy remain outside the scheduler/backend contract. The
next music target is a real cue from the user-supplied Monkey Island v5 data,
with commercial bytes kept outside the repository and uncovered timbres still
failing closed.

M4 completes that real cross-title proof. The validator mounts the supplied
Ultimate Talkie ZIP in memory and accounts for all 138 sound resources as 97
decodable AdLib cues, 35 silent stubs, and six SBL-only effects, with no game
bytes committed. Room-78 church sound 154 traverses the generic decoder,
importer, AdLib device model, fingerprinted bank, realizer, scheduler, and
integer backend: 197 attacks, MIDI 36..91, an explicit whole-cue loop, and an
eight-voice peak. Its one patch maps only to the exact reviewed MI p13 low/main
samples at the established MIDI-58 boundary. IR/action/resolved-note SHA-256
values are `ae9efce8ebe913269a0f8d9878a7db20aac855c43ce9456a6fc0e65edc1030eb`,
`65d97b64607cddb0e9e72bf33e20d75d3738587b6473e5f5295599265256ef63`,
and `401ca8eafd2c85d18d91f51fefdb2c4d558afba3ae124cc816bdaea7b18e0b51`.
The exact 459,072-frame reference WAV SHA-256 is
`0f41ec1d04eb7dd0cbd7b867b81c2ec1aa8438db91504b91384ad96bbfce3361`
with zero clipped samples. Existing Fate MML and both SNES ROM identities are
unchanged. M5 is the generic resolved-note-to-TAD compiler.

M5 now completes that compiler. `same.music.backends.tad_mml` is source-neutral
and has independent copyright-free coverage for loops, stereo/mono pan,
automation, zones, provenance, and bounded voice failure. Monkey church
compiles all 197 attacks to eight voices with generated MML SHA-256
`3781ebf57a3cacb4a8f9ffaa835642213b364f240d1595453f03fb75eda410de`
and TAD binary SHA-256
`ee4a65af794b92850a4ac79ef6a101674c217faacbd451751eb174938c0e7a8d`.
The explicit TAD minimum-duration policy adds one leading tick and shortens two
releases by one tick; no attack is removed or shifted relative to the loop.

Special validation ROM
`aa5524ce8b3d04eeaa9e4931ebfdd7af221f8112c25ee830bb3c223300c8e673`
passes a fresh 3,900-frame real-DSP capture. Peak is 12,710 with no clipping;
the in-capture loop repeats at 57.303875 seconds with 0.998933 correlation,
matching the configured 32,040 Hz SPC clock. Generated commercial-derived MML
stays under `build/`. The next music gate is M6's profile-driven compiled-song
catalog, replacing the backend's hard-coded Fate mapping.

M6 replaces that mapping with the profile-owned `same_compiled_music_catalog_v1`
resource. Each entry binds one logical ID to an exact source resource/SHA-256,
compiled song name/ID, time scale, duration, and optional loop. Schema damage,
duplicate logical/source/compiled identities, stale source bytes, missing songs,
and compiler renumbering all fail closed. Compiled play, stop, loop progress,
and save/load retain the catalog and source identity without changing the audio
packet ABI or engine core.

The Fate catalog contains all 19 reviewed production mappings and has SHA-256
`809a3346c1db8113033119315f5bc1beebb7cad9fafebd3be3760f6d70ab23fc`;
the Monkey catalog contains the church cue and has SHA-256
`0859072807c14312901d6b4e60733ffb8e6f15fec57a6b046b9f05be3b0e8792`.
Both supplied archives validate against those identities and their exact TAD
enum files. The M6 report SHA-256 is
`1756320cb2ac4f428a451d07eb1f38d4fe3e0e18ad647cc4db5db17544c0495a`.
The generated-table Fate ROM is
`147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`;
C32 and sounds 172/154 pass. The Monkey ROM is
`b6d39664487f700a93a6e13ceace0a37be7c8895cf52e15760f51c8d61cc1c43`.
Its fresh 3,900-frame request uses logical sound 154, resolves song 26 through
the generated one-entry catalog, remains unclipped, and repeats at 57.303875
seconds with 0.998932 correlation. Report SHA-256 is
`b039a969288a7281409a5bdc201f426bd86f88c3aa18b811700c42787997d55e`.

M7 replaces the remaining per-cue assembly step with
`same_music_build_graph_v1`. Each profile now owns a graph resource selecting
the importer, source-device model, reviewed bank, target policy, output MML,
compiled identity, and catalog entry. The source-neutral runner verifies source,
bank, policy, expected MML, compiler, and every emitted artifact identity; it
publishes MML, project, catalog, dependency manifest, TAD outputs, and report as
one directory transaction. A failed render or compiler run leaves the prior
complete output untouched.

The Fate proof regenerates reviewed sounds 83 and 154 byte-for-byte; Monkey
church regenerates all 197 attacks through the M5 generic sampled backend.
Graph SHA-256 values are
`8c5ba6bb3a81ea49f17bbe43b3426e7849180abea583c251fb81e40c5743609e`
and `b216275ef992600f51b188fe69a584fc85f5e8431e0ee849f04abb4e7f969076`.
The generated TAD binaries are
`895dbaafb3479dac66d68a8125f7d57778333d7398439694993c36e9760bf44c`
and `ee4a65af794b92850a4ac79ef6a101674c217faacbd451751eb174938c0e7a8d`.
All commercial-derived MML and projects stay under `build/`.

Both resulting ROMs are exactly the accepted M6 images: Fate
`147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`
and Monkey
`b6d39664487f700a93a6e13ceace0a37be7c8895cf52e15760f51c8d61cc1c43`.
Fresh DSP reports pass Fate sounds 83/154 and Monkey's full loop with SHA-256
`84aabd1980d77ec0b8a7ee4f064cfdc9fc3ec086f0a0ab67c7e5bb783a66c025`,
`508517c781a5668b5f2d12cb042913af736d55db46d47c22a7564aed83869c34`,
and `592034cbc941167d7470154b1dc2a29c3d7df13e0d0f53ec49aa8ebe46effd01`.

M8 moves the complete 19-entry Fate production catalog under the declarative
graph. A byte audit found five arrangements that today's converters reproduce
exactly: ROL sounds 18, 83, 150, and 192 plus canonical AdLib sound 154. The
other fourteen—including the hand-authored short sound 172 and legacy-dynamics
sound 17—are explicit immutable reviewed inputs. Each is still bound to its
exact raw source, bank, policy, output, and compiled identity; the graph will not
silently replace listener-reviewed bytes with a newer mechanical conversion.

Graph SHA-256 is
`9843346be7ede3bdd0328ac955f58dbbdd00def7a0d9fd1b7578b18e54637fbe`.
One transaction emits all 19 MML files and a complete local project. Repeated
project, catalog, dependency-manifest, TAD-binary, and report SHA-256 values are
`a9709545b166868c5250fe0e0d86c94027510b5af2d41794f46c2ab190d004f0`,
`ea5c62c099c8289743b55aaf1eb5861c5b92f93e2b3eabd8e46c892c37e71094`,
`e12a474f671bc6c03275ba07d65a27a239610ac31b323b9d8e10b51bea7d0e00`,
`895dbaafb3479dac66d68a8125f7d57778333d7398439694993c36e9760bf44c`,
and `d730cdd9ae396d02964c13d50474aebe021d2ff92fe9bccdf5667b1f54742862`.
The M8 ROM remains exact M6/M7 ROM
`147c150c08468807e7acefb4c72f0164f2fd907e8adefdae5c6647b82a0ad04a`.
Fresh short/virtualized/dense/CC7 DSP report hashes for sounds 172, 18, 153,
and 150 are
`1ef3a1be1fe0672d1235ecd8c6f37b22ffe467e74449e0e4d9afd80ef25dd412`,
`d41373084aff07111f9824a4e115796f53e7a44cf55304b19a39b924291376c8`,
`e3cc49e63aced9f403bc1f0afd70750eb79f903808a9c30d729816e0a5d5e489`,
and `d73d42f490e82ca9087f030c3c0c5e66e4a22278c641213cb12dda8c2f6b8a6e`.

M9 makes the profile the single ROM-build authority. The profile resolves its
`MBGR` resource; the handoff verifies that the graph names the same game ID,
records the exact profile bytes into the music transaction, validates the
catalog against the emitted TAD enums, and verifies every artifact before the
SNES builder runs. The caller supplies a profile and external source archive,
not a manually coordinated TAD directory/catalog pair. Verified cached bundles
can be reused without reopening the commercial archive.

Fate and Monkey profile/graph SHA-256 pairs are
`d824c9b7aa06db8acbd383c07227d52aad16af23eaba6b1687686066b2551561` /
`4eb320c36ef44e1eb1737405876845287422d4eb72a72d824a67e3c276a323a8`
and
`7cd28cc851b70cd25077561e21b7c6e19a674ab4a2632f2a6ae8957440fa563a` /
`9bf3a52d952c3e4e1631697d7d18ea95a1055a1dfd2e651de2659cc1371470b8`.
Their handoff-report SHA-256 values are
`94e120d8d005dea40c476b7f864df6430b9b71c343b6c359d839951c6432e2f0`
and `e3cbc75c2c9b98c1f950fa4905b81d063ae9de1287181a50c4eeb5bf1a22580c`.
A deliberately crossed Fate-catalog/Monkey-TAD bundle fails before assembly and
produces no ROM. Both ROMs remain exactly M8/M6, and fresh Fate-154 and Monkey
DSP report SHA-256 values are
`6c0c90f59d7776d78fe90d8838817349802120050df497a7eb8795385e445f0c`
and `6b0d8b6ab0f5f34575fcdb8c4471d0352d118b9862d764ae997fda86e71e9d7d`.

M10 passes the second-engine-family graph gate. The profile orchestrator now
selects music adapters only through an engine/source-family registry; it has no
direct SCUMM adapter import. An invalid `MusicBuildGraph.adapter` or mismatched
engine/family pair is rejected before compilation output. The copyright-free
QTMA conformance profile uses the checked-in M2 event fixture plus two generated
integer waveform instruments to produce a one-song verified TAD bundle and demo
ROM through the same command as the commercial-data adapters.

The QTMA profile/graph/TAD/ROM SHA-256 values are
`3bf3cc7b28c8d653c60188ce449ff6adeabd3e04f36a9a8a7211ff01e6367fc7`,
`b622d815191cd2039d22b0f5fa3f9de1d43222c7f95ce30858f5b84be4ce9be9`,
`8abae1aef2f32568e17f5ddbdb420b4566b980b9d68b74dfe3e5e8d1ede49a77`,
and `c12f028ee17c81c4e81c46fc9209a78972bf6619341af727a8a579a9c7335f92`.
Fresh and `--reuse` ROMs are byte-identical. Explicit adapter identity changes
the Fate and Monkey graph hashes to
`efbe8c2ff9c27899a459962a426a52841b7cd3d4ac6a933efcc12ec69c298487`
and `7b529f7d1f6c374b1c7ad0ac63c0a5787d09a99728790a0d9b8214f7f39e85a3`,
while their accepted ROMs remain `147c150c...ad04a` and `b6d39664...1cc43`.
Fresh Fate-154 and Monkey-loop real-DSP report SHA-256 values are
`fe21816ec12440078d82db95ece4443bc9f65077710d0b47f89d613b8aa7fa4b`
and `0ecb6fd520db29d250c5b68322a9faf6b25251490b6a1c169fc7b9d69ab472ec`.

M11 passes the non-SCUMM runtime-consumer gate. A dedicated profile selects the
`qtma_conformance` SNES personality while retaining the `demo` engine-family
adapter. The runtime module knows only logical catalog entry 1 and normalized
audio operations. It contains no SCUMM policy, TAD symbol, or S-SMP/DSP port
access. Its retained state changes WAITING→PLAYING at semantic frame 120 and
PLAYING→COMPLETE at frame 423 while the backend records exactly one required
play packet and one required stop packet.

The M11 profile/graph/TAD/ROM SHA-256 values are
`b38f5ff5f6565f13430bd529a90bbac43e30d367d709cf0f55268b2fdbb563ae`,
`b622d815191cd2039d22b0f5fa3f9de1d43222c7f95ce30858f5b84be4ce9be9`,
`8abae1aef2f32568e17f5ddbdb420b4566b980b9d68b74dfe3e5e8d1ede49a77`,
and `22cf9b2fd5cee700d98b1f50729a5728ac72a3f1661e5c24a607628b5f1d3c17`.
The final real-DSP capture is audible from 2.373 through 5.017 seconds with peak
16283 and no clipping. Gate-report SHA-256 is
`d77cab98c127ab31da56788b59cd0f6972f834ce7da2be56291230802af00404`.
Rebuilt M10 demo, Fate, and Monkey ROM identities remain exact.
Fresh Fate-154 and Monkey-loop DSP report SHA-256 values are
`96deae99d780514de41ee78ef6d1c0040dc00ad736618a0a993c6a36e0f04fec`
and `f779f8d1d3222fb980111dd6204067a6da78256d6609a40f768e33f00d36ca4e`.

M12 moves duration and completion policy out of the QTMA consumer into an
opt-in generic compiled-music lifecycle coordinator. A separate generated table
preserves the stable catalog bytes while supplying bounded duration/loop policy.
The consumer requests logical entry 1 at frame 120, reacts to READY at 136 and
natural STOPPED at 424, and contains no hardcoded completion frame. The generic
coordinator transitions PENDING at 120, PLAYING at 135, and COMPLETED at 423;
host tests independently prove explicit stop, invalid identity, and looping
no-auto-complete behavior.

The M12 ROM SHA-256 is
`e19cd796323df3d85862fb4fa5f6610bb6754be1e9596c5a53608c79a2ec7b50`.
Real-Nexen evidence retains the exact one-play/one-stop service trace, final TAD
blank state, and audible unclipped DSP output. Gate-report SHA-256 is
`03ad5edceb90d18f0dcf776095e0c209832b283817213fa3a81cb381ec6e9b3b`.
Fresh Fate-154 and Monkey-loop DSP report SHA-256 values are
`7acaeef9a8e3e176a2049d4a01239d14319d7ab0d7a0568a1e04cbd84a314792`
and `f19e441379fb62a1a5c2210a239d444845be4893d5935c22bb3767b99e9f7da5`.
The next ordered music gate is M13, a strict QuickTime MOV `musi` extraction
adapter feeding the existing QTMA importer.

M13 passes that container-adapter gate. The strict self-contained QuickTime
reader traverses normal and extended-size atoms, selects `musi` media, validates
the zero-flag music sample description, expands `stts/stsc/stsz`, resolves
`stco` or `co64` offsets only inside `mdat`, and rejects malformed counts,
sizes, descriptions, timing, alignment, and offsets with source byte paths. It
does not decode QTMA words.

The 536-byte copyright-free movie stores both NoteRequests in its description
and splits one phrase across two samples. Extraction reconstructs the exact M2
232-byte event stream before the unchanged importer runs. Raw movie, graph,
profile, TAD, and ROM SHA-256 values are
`feb16d388acb55624f53b2dec2e8d76393ce1b5381b1f3d8880e23c74fe78ae1`,
`5e7d934680fc5abb34871371bfc4b5e9acac93c37ea1ae2393f8dd4bf3ce6571`,
`14fe551dfed95486f42d1c5c61c9c46ad615de2d927cbf9838794c1d36e834e9`,
`8abae1aef2f32568e17f5ddbdb420b4566b980b9d68b74dfe3e5e8d1ede49a77`,
and `e19cd796323df3d85862fb4fa5f6610bb6754be1e9596c5a53608c79a2ec7b50`.
Fresh and reused outputs are identical; the TAD and ROM also equal M12 exactly.
The current real-DSP runtime report SHA-256 is
`78722cc703d9b56d82cb86017a7274b167de0bbbcb76cc3e87508aa0c1286d26`.
Fresh Fate-154 and Monkey-loop M14 regression report SHA-256 values are
`99d9c2e7ddc4e311a9158183a566eca84ea6d85d6206434689b0f4fc4fc69818`
and `34de15b387c1baa963740c654b4e2601af86d2bdd021efff95a9ac123adb586d`.
The next ordered music gate is M14, explicit rational source-time normalization
for ordinary movie time scales without accumulated drift.

M14 passes. `same.music.timing` maps absolute timestamps by integer rational
arithmetic under explicit `exact` or `nearest_absolute` policy. Exact mode
rejects the first fractional target tick. Nearest mode uses half-up rounding,
reports an exact rational maximum error, preserves simultaneous order, records
the original tick/time scale in each event's provenance, and rejects any note or
loop collapsed by quantization.

The 600 Hz movie maps to backend ticks `0,31,52,63,94,125`; its duration is
exactly 125 ticks and maximum error is `300/600`, one-half target tick. Graph,
profile, TAD, catalog, ROM, and real-DSP report SHA-256 values are
`8729f155b9313c3b0226a39ab867a9813156ee9f1588ddc346a77aae85907587`,
`f987c3745d5e6c3feafa135afd2449cd980a9e8aace48d0262156b7386a245aa`,
`b9552071d7124d738f11b2b3a7ef1823a7eb0442c2915fa43971cfcbf2ced939`,
`581127076eb0f8dac9be0a3dbd4415158e6fed33d083eda0c9903440df52afcb`,
`c1ed252514aeacd9863963477407f01f9676c662f6aa05bec00f6ba195474c59`,
and `73a8ef7a68dc942f2c3c1e38e8e9b8f605b5d51519e26a7e937d4d15601ba198`.
Fresh/reuse outputs match. The lifecycle starts at 135, completes at 195, and
the engine retains COMPLETE at 196; DSP is audible from 2.389 through 3.140
seconds without clipping. M13 remains byte-exact.

The next ordered music gate is M15, segmented QTMA provenance across movie
sample descriptions, media samples, and original file-byte locations.

M15 passes. The generic `SegmentedByteSource` requires a complete, ordered,
nonoverlapping coverage map and resolves each complete importer frame back to
one physical source segment. A frame crossing a segment boundary fails before
semantic decoding. The QTMA importer knows only this generic resolver; MOV atom
and sample-table knowledge remains confined to the container adapter.

In the M13/M14 movie, the two NoteRequests retain sample-description 1 and
absolute file bytes 232 and 324. The logical boundaries at bytes 184 and 212
resolve independently to media sample 0/file byte 44 and sample 1/file byte 72;
the first emitted event in sample 1 retains logical word 54 and file byte 76.
After 600→125 normalization that event also retains source tick 300 and source
scale 600. Fresh/reused M13 and M14 ROMs remain exactly
`e19cd796323df3d85862fb4fa5f6610bb6754be1e9596c5a53608c79a2ec7b50`
and `c1ed252514aeacd9863963477407f01f9676c662f6aa05bec00f6ba195474c59`.
Their M15 real-DSP report SHA-256 values are
`0f9a6501a012157f6e5a87fd683074580986695b02d82bd0c39c496a8682aba6`
and `e54f458a23e0e253d921d4dc2fd7e9c078596ccbd822be05dc5b849f0da2aa07`.
Fate and Monkey retain their accepted ROM identities and pass fresh DSP gates.

The next ordered music gate is M16, a canonical conversion-audit manifest that
serializes and hash-binds source provenance, normalized timing, and realization
identity into each graph build.

M16 passes without adding another QuickTime feature. The source-neutral
`same_music_sequence_audit_v1` document records the complete imported and
normalized `SequenceIR`: parts and instrument requests, note/control/marker
events, lifetimes, source order, loops, diagnostics, and every provenance field.
It separately records exact rational timing evidence and the sampled-note zone
identities presented to the TAD compiler.

M13 and M14 audit SHA-256 values are
`d5515a65442e7c70d8137546b401a0ac187df59dc0b45ab920dbf765340bd37e`
and `146b6e9e8548e5d40a5a74df321ef339beeb045a1377e5f8b2da0d48ad97435b`.
Each graph declares the audit path and expected hash; the transactional builder
and reuse verifier reject missing, corrupt, or unexpected audit bytes. MML, TAD,
catalog, and ROM bytes remain exact. M16 real-DSP report SHA-256 values are
`05bb8227c7e5b6a1cb3fde7b82e8c4a3c65593c4f5d2b122de686dff2d1f9faa`
and `ec384acc596dd92ec7a4368f72a21681ce167030fceeb2be23e54abdb006c5b6`.

The next ordered music gate is M17, canonical IR interchange and replay: decode
the normalized audit IR as a strict build input and prove it realizes to the
same MML without invoking its original importer.

M17 passes. `decode_canonical_sequence_ir` reconstructs every typed part, event,
instrument request, provenance record, diagnostic, loop, and ordering key under
an exact-field schema, then lets `SequenceIR` reapply its note-lifetime and
structural invariants. `decode_sequence_audit` independently recomputes M14's
rational normalization from the imported IR and rejects any disagreement with
the recorded normalized IR or error evidence.

A fresh adapter replays both audits to their accepted MML hashes while MOV
extraction and QTMA event decoding are patched to raise if entered. Realization
zones are regenerated from normalized IR and must equal the recorded identities
before the backend runs. M13/M14 audit, MML, TAD, catalog, and ROM bytes remain
exact. M17 real-DSP report SHA-256 values are
`f9bf20d5077d826d3fe02a24962aefd962db004559beda0904a76d5bd8a371c4`
and `4e0c99a589669001461219ef3ee777db2d7d79b611f300ebc24159f55d04ef50`.

The next ordered music gate is M18, deterministic sequencer checkpoints: save
and restore the IR playback cursor, rational clock position, controllers,
sustain/deferred releases, and active voice ownership without retriggering.

M18 passes with explicit warm and cold contracts. Warm restore belongs to the
originating live backend and emits no command while restoring the exact
next-unconsumed cursor, rational remainder, allocator generations, sustain, and
deferred ordering. Cold restore uses a SHA-256-protected canonical document
bound to the IR, realized sample-zone catalog, schema, engine/profile, rational
timing, voice policy, and loop configuration; validation is transactional and
requires a fresh sequencer instance.

The destructive fork oracle compares every subsequent tick after destroying
the original B instance. It covers same-timestamp group splits, nonzero clock
remainders, loops, deferred sustain, deterministic voice stealing, overlapping
same-pitch notes, note-off/pause/stop/end boundaries, and repeat restore. MOV
and QTMA importers are forced unreachable. Cold state preserves logical voice
ownership only, not backend sample/envelope/oscillator continuity. M18 real-DSP
report SHA-256 values are
`7fc1113e13ed8e1b45de6524c60a8828f29f81aa51fca135d70a468a3ae9dc9f`
and `1aeaaa3e135569ce35a2021679a8920745ac42d13b252b6d14dc893ffac6f8ff`.

M19 returns the completed music work to the real SNES SCUMM dispatcher. A
copyright-free 32-byte script executes `$02 startMusic(154)`, `$7C`
`isSoundRunning`, `$20 stopMusic`, a stopped-status query, and a restart. The
normal event/audio-service trace is exactly play 154, stop, play 154 from the
engine endpoint; the debugger logical-request byte remains zero. SCUMM logical
status is `1,0,1`, TAD reaches blank song zero after stop, and the profile-owned
catalog maps the restart to existing Monkey church song 26.

The fresh-power-on M19 ROM SHA-256 is
`78a71ee35f2658da62a25958ad76ff6ed6036024793193ff04ab9ed27d91fc05`.
Its 3,900-frame restarted real-DSP capture is audible and unclipped, retains
exact video/NMI pacing, and repeats at 57.303875 seconds with 0.998934
correlation. Gate-report SHA-256 is
`8c54e88c5cfd0058a0ad739754f268193de65bf4d361ba46022230ac61d7f8ee`.
M19 adds no cue conversion, source-format behavior, iMUSE transition, or
save-state work.

M20 adds the first real SNES cartridge-SRAM save path, narrowly scoped to one
SCUMM compiled-music slot. The fixed record uses the existing `SAMESAV`
version/engine/game/schema/length/CRC32 envelope and a versioned subrecord bound
to the Monkey catalog and sound-154 source identities. Its declared policy is
deterministic cue restart: a running load emits exactly stop then play 154
through the normal SAME event/audio service, waits through the backend blank
transfer, and restarts TAD song 26 from its compiled beginning. The stored
logical frame position is advisory and is not honored.

Midpoint and pre-loop records each survive destruction and a fresh Nexen
process with SRAM retained; stopped state emits no play. Corrupt, wrong-engine,
wrong-game, wrong-schema, and wrong-catalog records reject before any audio
mutation. Eleven-process gate evidence is
`build/scumm-m20-save-9349a24ca2df99bd/report.json`, SHA-256
`afc7fbdc9efa6884d1db8e8c07fcac3523f4dedfe95cf4dfba2062edc90a8f0b`.
The M20 ROM is
`9349a24ca2df99bd374edf5cd7ef1d312b6d0b729ff3321a45f0ef6320015445`;
M19 remains exactly
`78a71ee35f2658da62a25958ad76ff6ed6036024793193ff04ab9ed27d91fc05`.

M21 reconnects one Fate iMUSE hook to that compiled backend without claiming a
live branch sequencer. A bounded synthetic command fixture runs encoded start
80, flush, hook 14, flush through the normal SNES SCUMM `$4C` dispatcher; it is
not an authentic room-entry trace. Profile-owned route
keys select distinct precompiled TAD songs: default 26 consumes branch
`(0,100)->(0,1920)`, while hook 14 selects song 27 and consumes
`(0,90)->(3,1920)`. Same-frame deferral prevents the pending default route from
ever reaching ready/playing ownership in the hooked run. Stop clears the
one-shot selection; start alone returns to default; replaying the room pair
selects hook 14 again.

The version-2 compiled-music SRAM subrecord binds the selected route identity
and cold load deterministically restarts that arrangement from its beginning.
The stored position remains advisory and ignored. A CRC-valid mismatched route
identity rejects before logical or audio mutation. Fresh-process mechanical
evidence is `build/scumm-m21-fate-route-b16fcb68583506d0/report.json`; the M21
ROM is `b16fcb68583506d0aa2bd97b8af2e0339136a57b5a7cb8ab0dc5c2be8fea0807`.
Programs 32, 33, 50, 57, 77, and 82 have isolated, unclipped S-DSP auditions
under `build/fate-m21-auditions-b16fcb68583506d0/`. Their mechanical gate
passes, and Chad accepted the M21 timbre gate.

M22 adds one genuinely live, bounded iMUSE decision. After a bounded synthetic
fixture selects the sound-80 hook-14 route, its encoded `$4C` hook-8 command
remains pending
while TAD song 27 continues. A source-audited custom bytecode boundary at track
3 tick 68160 (69,152,026 microseconds; normalized TAD tick 8644, -26
microseconds error) selects either the no-hook continuation or the precompiled
track-3 tick-1920 destination. The SPC reports boundary token 1; SCUMM consumes
it once on the following engine frame without loading or restarting a song.

Fresh hooked/control captures are equivalent before the boundary (median
correlation 0.9999999 after at most 32 samples of recorder-clock alignment) and
diverge afterward by over 3,400 times the pre-boundary differential. Both are
audible and unclipped; `$7C` remains running, TAD remains on song 27, and packet
loss/rejection remains zero. The final ROM is
`de6e257897a8e150a85f78b0dcf1ea49ef80b0a49d9f359263e843f819f9b332`.
Runtime evidence is `build/scumm-m22-fate-hook8-de6e257897a8e150/report.json`.

The version-3 SRAM record preserves route history, section plan, pending or
consumed hook choice, and catalog/source/route/bank identities while retaining
M20's honest deterministic-restart policy. Armed, consumed, and default saves
survive fresh emulator processes; CRC-valid wrong-route, wrong-section,
wrong-catalog, and wrong-bank records reject transactionally. No APURAM, DSP,
voice, BRR cursor, envelope, echo, TAD pointer, or pending SPC command is
serialized, and the saved position remains advisory and ignored. Save evidence
is `build/scumm-m22-save-de6e257897a8e150/report.json`.

Newly reached program/range auditions for 50-low, 97, and 107 mechanically
pass under `build/fate-m22-auditions-de6e257897a8e150/`; Chad accepted their
human timbre gate. M23A raises the suite to 310 tests. M19, M20, and M21
emulator regressions pass against their unchanged accepted ROM identities.

M23A adds authentic Fate room-resource delivery and the generic SCUMM room
lifecycle without executing unsupported authentic gameplay semantics. Complete
room 49 and 63 ROOM records are cooked locally from the user-supplied archive,
bound to source/profile/game identities, and delivered through normal host and
SNES resource providers. ENCD, EXCD, and LSCR descriptors retain all source,
cooked, normalized, and runtime coordinates. Authentic registration runs stop
with ENCD pending at PC zero and emit no music; a copyright-free fixture proves
EXCD, retirement, activation, registration, ENCD, and LSCR execution order.
The M23A ROM is
`6a622d0ac0fef4faa52808311ff08b73a9125aa50ecc737740de3b1c5167e640`.
Full identities and corrected authentic command batching are in
`docs/M23A_REPORT.md`.

M23B executes the complete authentic room-49 ENCD from PC zero through that
resource/lifecycle path. A hash-bound named pre-Thera state supplies only bit
425 and the authentic boot-script string shapes. Authentic global scripts 144
and 145 execute nested; the room then evaluates indexed bit 418 and sound 81/80
ownership before reaching ENCD `+0x004F`, `+0x0057`, and `+0x0065`. The queue is
exactly start 80 plus class-0 hook 14 and one flush selects TAD song 27 without
letting song 26 reach audible ownership. A negative state changing only sound
81 ownership takes the authentic skip to `+0x006D` and emits no audio packet.

Fresh emulator evidence is
`build/scumm-m23b-d0d3452e62c51801/report.json`; the positive ROM is
`d0d3452e62c51801efd3e475b3005432446d7b0516d93ee209c84d09ea932951`
and the negative ROM is
`3efc7e1e66a7b48fd5e4d94d7ab4573a6274b4505422ba90dbd0eb8657d79300`.
The suite is 311 tests. Full source mappings, dependency evidence, host trace,
and the room-63/M23C cone are in `docs/M23B_REPORT.md`.

M23C executes the authentic room-49-to-room-63 path through the normal room
lifecycle. Room 63 begins at ENCD PC zero; canonical `$1D ifClassOfIs`, the
authentic delayed global script 151, sound-80/82 status, hook-8 queueing,
`0x0110`, and the later source flush all execute normally. The final flush is
exactly hook 8 followed by command `0x0110`; hook 8 remains pending until the
accepted M22 boundary and consumes once without a song reload, false stopped
state, gap, clipping, packet loss, or rejected packet. Three fresh-power-on
processes prove the positive, class-state, and sound-82 controls. The positive
ROM is
`ca5ae06865ebca737bc1fd5bb7f2cadbc2c6bdc829f7b449431d91939ca3bbef`.
The suite is 315 tests; full evidence is in `docs/M23C_REPORT.md`.

M24R-A proves the smallest backend mechanism that the rejected M24 composite
needed but TAD did not expose: a generation-safe transition request observed at
the next driver tick even while all eight channels are inside long notes, an
independent outgoing-group fade, deterministic voice steals, and admission of
five precompiled incoming lanes without a song reload. The synthetic ROM is
`e68f1b513076cb34039aee47c1ae1724d87ce87c438496fca061abd00478d8b6`;
the suite is now 318 tests. This does not implement Fate sound 82 or create a
general mixer/sequencer. Evidence and exact costs are in `docs/M24RA_REPORT.md`.

M22 deterministic cold restart passes unchanged. Complete room/class/script
game-save restoration is still outside the current save envelope.

No new timbre approval required.

No new timbre approval required.

Implemented in the executable host oracle:

- stop, yield, relative jump;
- direct/variable result operands;
- increment/decrement;
- add/subtract/multiply/divide/and/or;
- zero/nonzero and six relational tests;
- fixed and variable delays;
- start/stop scripts, nested execution, per-slot locals, and 25-slot capacity;
- recursive/freeze-resistant scheduling, nested freeze counts, and running queries;
- direct/variable chain-script handoff with inherited flags and fresh locals;
- packed bit variables, cursor commands, all five string operations,
  byte/signed-word variable-range initialization, full-header roomOps intent
  with palette and auxiliary-string persistence, deterministic saved random,
  persistent pseudo-room resource mapping, resource cache/lock intent, and
  full-header actor configuration with encoded names, canonical live animation
  requests, actor-follow camera intent, canonical point-to-actor lookup over
  visible current-room actor bounds with untouchable-class rejection,
  canonical actor room assignment and room-zero removal lifecycle, plus
  canonical object-walk-point actor placement and missing-object fallback,
  classic `$58/$59` costume initial-pose decoding, BYLE-RLE composition, and
  rendered actor hitbox publication,
  canonical point-to-object lookup over ordered raw-room geometry, class and
  parent-state visibility,
  sparse 32-class object masks, bounded v5 verb configuration, and the canonical
  saved-verb bank namespace, plus the canonical signed 32-bit v5 expression
  stack with nested opcode dispatch, plus nested
  cutscene callbacks, override markers, skip abort, and persistence, and the
  bounded v5 sentence queue/callback/cancellation lifecycle;
- room load and camera position;
- start/stop music and sound request translation, plus bounded canonical
  soundKludge queue/flush, normalized iMUSE command 6/8/9/10/11 mapping, and
  the observed four-word class-0 hook command 0x010C compiled-route selection;
- script slot persistence and save/load.

Not yet implemented in the extracted SAME module:

- full 105-opcode surface;
- verb drawing/input and dialog;
- direct loading of raw LucasArts data in the SNES runtime;
- direct raw-resource delivery in the SNES runtime; production TAD delivery is
  proven for Fate sounds 172, 17, 154, 83, 18, 185, 190, 192, 141, 201, 202,
  207, 183, 91, 117, 78, 81, and 153, while production coverage of the other 9
  sounds is still open.

## Current AGI v2 semantic boundary

Implemented:

- decoded logic-resource and message parsing;
- increment/decrement, assign/add/subtract direct and variable forms;
- left/right indirect variables;
- set/reset/toggle direct and variable flags;
- direct/variable `new.room`;
- sound/stop-sound request seam;
- player/program control;
- simple ego directional state;
- cooked 16-color picture presentation;
- save/load.

Not yet implemented:

- IF/NOT/OR test expressions and GOTO;
- original AGI vector-picture decoder and priority screen;
- views, loops, cels, animation, motion and collision;
- vocabulary/parser, `said`, text windows, inventory and menus;
- native AGI sound interpretation;
- raw VOL/DIR game-resource discovery;
- a complete King’s Quest play path.

## Explicitly still outside 0.2

- An unchanged upstream ScummVM C++ binary on 65816.
- A ScummVM launcher or dynamic plugin loader.
- Physical-hardware-observed SNES engine host.
- listener-approved Fate instrument zones and reviewed TAD arrangements beyond
  the initial sound-172 production proof.
- SNES-side resource/package reader and a general multi-slot/full-engine save
  backend beyond M20's one-slot compiled-music SRAM proof.
- SA-1 job execution behind the job capability.
- Migrated MC68000/Z80 targets.

See `docs/NEXT_GATES.md` for the ordered gates.

## M25 authentic object-script execution

Canonical v5 `$37/$77/$B7/$F7 startObject` and complete room-owned OBCD
delivery are emulator-proven.  The authentic semantic Walk To action now runs
global script 2, completes the 91-tick walk, executes object 596 verb 10 from
OBCD `+$0029`, decodes `42 D3 FF` as `chainScript(211)`, retires the object
slot, and enters room-49 LSCR 211 at PC zero through the generated local-script
directory.  The next unsupported semantic is LSCR 211 `+$026E`, canonical
`$B2 setCameraAt(Var[2])`. This historical frontier was cleared by Phase 6L;
see `docs/M25_START_OBJECT_REPORT.md`.

## M25 authentic stored-walkbox query

Canonical SCUMM v5 `$7B/$FB getActorWalkBox` is implemented as a pure read of
the actor's stored walkbox field. Copyright-free host/SNES tests prove direct
and variable actor forms, exact PC consumption, result isolation, fail-closed
input, and no actor mutation, including a position deliberately lying in a
different geometric box. Fresh-power-on authentic Fate execution writes
actor 1's naturally established box 11 to Var[442] at room-49 LSCR 216
`+$0000`, then runs that local script's condition/box-flag/yield loop normally.

The next authentic failure is no longer in room 49: room-63 ENCD `+$00DE`
canonically decodes `2A CA FF` (`startScript 202`) but fails closed because
the complete cooked LSCR 202 descriptor is not yet enabled in room 63's
generated executable-local lookup. No LSCR 202, movement, walkbox routing, or
audio work was added. See `docs/M25_GET_ACTOR_WALKBOX_REPORT.md`.
M25 complete room-local LSCR lookup is emulator-proven. Authentic room-63
`startScript(202)` resolves through the generated active-room directory,
executes LSCR 202 from PC zero, yields at `+$0005`, and restores ENCD exactly.
The integrated scheduler resumption was subsequently cleared by Phase 6L. See
`docs/M25_ROOM_LOCAL_LOOKUP_REPORT.md` for the historical evidence.

## Phase 6L — accepted Fate room transition

**Status: Accepted and closed.** The authored M25 path is emulator-proven from
room 49 through global script 2, object 596 / LSCR 211, the sound-82 fallback,
`$02D9`, `$02DE`, generic `$24/$64/$A4/$E4 loadRoomWithEgo`, and room 63.
Room-63 ENCD completes and global script 151 runs its authored periodic
delay/movement/message loop. The stable observation is actor 1 at `(430,140)`
on walkbox 5, stationary, with the camera lifecycle active; sound 80 owned and
sounds 81/82 inactive. The retained `$010C` command is canonical because the
sound-82-false branch intentionally skips the later `$0110`/flush sequence.

The accepted ROM ran 10,000 emulator frames with `error=0`:

`fddea1f7b877bbdb5f0bc9d9ca9bf8a13df4d4cc319a708410df178014b3a555`

See `docs/PHASE6L_ACCEPTANCE.md`. The legacy `make m23c` failure is retained as
layout-compatibility debt from the relocated M25 build; the accepted
relocation is not rolled back. The next boundary is normal player sentence
dispatch after the global-151 loop; no player action is fabricated by Phase 6L.
