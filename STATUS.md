# SAME 0.2.0 status

## Verified in the packaging environment

- **172/172 tests pass.**
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
- The SNES include closure passes the Poppy hazard checker: 18 files and 1,339
  global labels for the demo selection (1,333 for SCUMM v5).
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
SHA-256 026ef519d6ae1af761f76f5b902a5b1ab8e102b2ecc74e41207120bc7bb42f5c
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

Latest evidence is in `build/h0-nexen-026ef519d6ae1af7/`; `report.json`
SHA-256 is `6f838423a53840356e54e5511f4e6f71a7b4bbb1c43afd7999c85492601081b8`.
No physical-hardware claim is made.

K1 then passed from a fresh power-on for the rebuilt ROM:

```text
build/same-engine-host.sfc
32768 bytes
SHA-256 5f4182758e6e9649e2de6b067d4cf156ac69d58290f70cec2b7917039f72cade
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

K1 evidence is in `build/k1-nexen-5f4182758e6e9649/report.json`; report SHA-256
is `e81b20190625842899f463b709dfbb395f16a820e92cf0d595c533a916629b88`.
The final C26 demo ROM `026ef519d6ae1af761f76f5b902a5b1ab8e102b2ecc74e41207120bc7bb42f5c`
retained H0 and K1. Latest report SHA-256 values are
`6f838423a53840356e54e5511f4e6f71a7b4bbb1c43afd7999c85492601081b8`
and `815afc27cad4e3af14780bff1b4ea64fe51742d866f3cf8bf94c4fccf07ae87e`.
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
script 200 at `$0837/$083B`; `$D5 getActorFromPos` in local script 205 at
`$0004` is the next pinned frontier.

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
The new profile models embedded audio, costumes, four accessible CHAR resources,
320x200 logical coordinates, preserved copy-protection behavior, and the demo's
disabled game save menu. The generic adapter exposes only bytes actually present:
10 rooms, 74 scripts, 28 sounds, 25 costumes, and four charsets. Logical pointer
input reaches the engine and SAME save schema 2 round-trips the boot state.

This is deliberately recorded as incomplete, not a gate pass. The exact real
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
actor-10 animation requests 250 and 6 at local offsets `$0837/$083B`. The next
canonical frontier is `$D5 getActorFromPos` in `LSCR.205` at `$0004`.
Actor behavior and embedded-audio playback remain. Evidence is
`build/scumm-s6-fate-preflight/report.json`, SHA-256
`ee1c5d7cb50c9db308f6c21e16b5d33865846ea49ae2f76516b2732f1bddefe5`.
No Fate-specific branch was added to the opcode core.

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
  requests, actor-follow camera intent,
  sparse 32-class object masks, bounded v5 verb configuration, and the canonical
  saved-verb bank namespace, plus the canonical signed 32-bit v5 expression
  stack with nested opcode dispatch, plus nested
  cutscene callbacks, override markers, skip abort, and persistence, and the
  bounded v5 sentence queue/callback/cancellation lifecycle;
- room load and camera position;
- start/stop music and sound request translation, plus bounded canonical
  soundKludge queue/flush and normalized iMUSE command 6/8/9/10/11 mapping;
- script slot persistence and save/load.

Not yet implemented in the extracted SAME module:

- full 105-opcode surface;
- actor movement/render behavior, object, walkbox, verb drawing/input, dialog,
  costume, and iMUSE behavior from SNES-SuperMonkeyIsland;
- direct loading of raw LucasArts data in the SNES runtime;
- completed Fate demo actor/audio proof for the second SCUMM v5 profile; its
  resource/input/save/boot/room preflight is complete, but S6 is not.

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
- TAD/SPC delivery behind the new audio service.
- SNES-side resource/package reader and save backend.
- SA-1 job execution behind the job capability.
- Migrated MC68000/Z80 targets.

See `docs/NEXT_GATES.md` for the ordered gates.
