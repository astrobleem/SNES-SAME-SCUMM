# M23A — authentic Fate room delivery and generic room lifecycle

Status: passed on 2026-08-26. At this report's acceptance boundary M23B and M24
had not begun; M23B is now reported separately in `docs/M23B_REPORT.md`.

## Corrected provenance boundary

M21 and M22 used bounded synthetic SCUMM command fixtures. They remain valid
opcode, route, timing, TAD, DSP, lifetime, and SRAM evidence, but they are not
authentic room-entry traces. The authentic scripts batch commands differently:

- room 49 ENCD queues `soundKludge [8,80]` and
  `soundKludge [0x010C,80,0,14]`, then performs one `soundKludge [-1]` flush;
- room 63 ENCD queues `soundKludge [0x010C,80,0,8]`, executes
  `startScript 151`, `isSoundRunning 82`, a conditional, and on the applicable
  path queues command `0x0110`, then reaches the later flush.

M23A inspects those bytes but deliberately does not dispatch either authentic
ENCD. It emits no music command and makes no sound-80 or hook execution claim.

## Source and generated identities

| Identity | SHA-256 |
|---|---|
| `/home/chad/fatedemo-box.zip` | `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798` |
| `FATEDEMO/PLAYFATE.000` | `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9` |
| `FATEDEMO/PLAYFATE.001` | `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240` |
| Fate profile | `d824c9b7aa06db8acbd383c07227d52aad16af23eaba6b1687686066b2551561` |
| game/profile identity | `37bc71eb005f72fbad00dd4fea9a0ab0245df4e9af50a3ffce04167c99156c2b` |
| room 49 complete ROOM | `fbf234f2ffe3530ba365980abfae556636d83e5cada9bdc649c43d4cce7242f6` |
| room 49 cooked record | `67595f8c4f6db3ee144d433662390037f90a080cd816f652a8cb703124c329e9` |
| room 63 complete ROOM | `94896a976d35531ab2ab5180a1a9f90387f34f4b12b0a8034bf1b3bbc901d390` |
| room 63 cooked record | `d3c6a495fdf0c1dac3fdd7b8a62c32c73e5e8b53c76a9eb52c39846bfa0da9db` |
| cooked manifest | `77d509bd20c867ef7c539c5387d2cd6ad37d8416148470c595927218ac61f92d` |
| copyright-free lifecycle manifest | `89a29f3c351cf2620d2c8e11d7cc93ba89045f8ec6c12fcae1684b6e45a6be47` |
| final M23A ROM | `6a622d0ac0fef4faa52808311ff08b73a9125aa50ecc737740de3b1c5167e640` |

Two clean temporary output directories reproduced the same manifest and both
cooked-record hashes byte for byte. No authentic ROOM payload is repository
source; it is generated locally from the user-supplied archive into ignored
build output.

Room 49's original ROOM payload begins at `PLAYFATE.001` file offset 301791,
has length 80351, and becomes an 82535-byte cooked record. Its ENCD payload is
at original file offset 362230, ROOM-relative offset 60439, chunk-relative
offset 8, and cooked-record offset 62591. Room 63's corresponding values are
460711, 43536, 44280, 503455, 42744, 8, and 43456. The generated manifest lists
the same mapping and SHA-256 for every EXCD, ENCD, and LSCR (20 descriptors in
room 49; five in room 63).

For an instruction at script offset `n`, the report keeps these coordinates
distinct:

```text
original file       = ENCD original_file_offset + n
original ROOM       = ENCD original_room_offset + n
original chunk      = ENCD original_chunk_offset + n
cooked record       = ENCD cooked_record_offset + n
normalized script   = n
runtime instruction = n
```

The complete machine-readable mapping is in
`build/m23a-rooms/authentic/manifest.json`; the asserted command report is
`build/m23a-rooms/inspection.json`.

## Cooked record and entry points

`src/same/engines/scumm_v5/cooked_room.py` owns the strict version-1 binary
record. It binds profile, game, archive, index, data, complete ROOM, script
table, payload CRC32, compact checksum, lengths, non-overlapping bounds, source
coordinates, per-script identities/SHA-256, and whole-record SHA-256.
`tools/cook_scumm_v5_rooms.py` extracts complete ROOM chunks through
`LucasartsScummV5ResourceProvider`; `tools/generate_snes_cooked_rooms.py`
generates profile-owned lookup and ROM data. `tools/build_snes.sh` performs all
three M23A generation steps only for the M23A personality.

Host entry points are `ScummV5Engine._prepare_room`, `_load_room`, and
`inspect_room_lifecycle` in `src/same/engines/scumm_v5/engine.py`, plus the raw
ROOM decoder in `room.py`. The SNES entry points are
`ScummV5_M23A_RequestRoom`, `ScummV5_M23A_ResourceReady`,
`ScummV5_M23A_CommitRoom`, and the slot-zero ENCD/EXCD frame in
`runtime/snes/engines/scumm_v5.pasm`. `runtime/snes/services/storage.pasm`
receives the normal engine-originated Storage READ and validates the generated
record before setting the resource-ready phase. Game/resource identities live
in generated profile tables, not the generic dispatcher or storage service.

## Lifecycle contract

Local ScummVM source establishes the semantic commit order in
`engines/scumm/room.cpp`: `startScene` requests the change, runs EXCD at line
78, calls `killScriptsAndResources` at line 80, sets the new current room at
line 154, acquires it at line 175, discovers its subblocks, and calls ENCD at
line 254. `script.cpp` registers EXCD/ENCD as nested scripts; LSCR is
discoverable and is run only when requested.

SAME adds a transaction-safe staging step demanded by the cooked-record gate:

```text
request -> acquire and validate complete new record without mutation
-> run old EXCD -> retire old room-owned scripts
-> transfer resource ownership -> activate new room
-> register EXCD and LSCR -> schedule ENCD -> first ENCD instruction
```

Validation failure stops before EXCD, retirement, room activation, registry
change, or audio change. Host and SNES use this same contract. Registration-only
authentic records stop after ENCD scheduling with PC zero. The copyright-free
fixture executes the whole contract: room-1 ENCD starts LSCR 200, that local
executes and yields, room-1 EXCD executes during transition, the local is
retired exactly once, and room-2 ENCD executes. No stale slot remains.

## Authentic command inspection

Room 49:

| ENCD offset | Meaning |
|---|---|
| `+0x004F` | queue `soundKludge [8,80]` |
| `+0x0057` | queue `soundKludge [0x010C,80,0,14]` |
| `+0x0065` | one `soundKludge [-1]` flush for both commands |

Room 63:

| ENCD offset | Meaning |
|---|---|
| `+0x00A7` | queue `soundKludge [0x010C,80,0,8]` |
| `+0x00B5` | `startScript 151`, no arguments |
| `+0x00B8` | `var[0] = isSoundRunning(82)` |
| `+0x00BC` | `notEqualZero var[0]` conditional; the false branch skips `+0x001D` to `+0x00DE` |
| `+0x00C1` | queue `soundKludge [0x0110]` on the sound-82-running path |
| `+0x00C6` | eventual `soundKludge [-1]` flush on that path |

This corrects the earlier immediate-flush assumption. The inspection artifact
SHA-256 is `4b3c31818b1e58bfa75a2ead330a5a04a563d082c5f322da59a63b2149a08765`.

## Acceptance evidence

- 310 unit tests pass after adding three cooked-room tests: strict identity,
  integrity, length, schema, bounds/overlap rejection; host transactionality;
  and full copyright-free lifecycle order.
- Host authentic registration report:
  `build/m23a-rooms/host-report.json`, SHA-256
  `2ebcb4f71fc8312842c9f0de2ee247e00d266d1041b49905ad200690b7589771`.
- Three independent fresh-power-on Nexen processes prove authentic room 49,
  authentic room 63, and the executable lifecycle fixture:
  `build/scumm-m23a-rooms-6a622d0ac0fef4fa/report.json`, SHA-256
  `e30d1b27ccaa32d1e2644ce1253abc2c74c501ba4329d9afc4608b9c56210e8b`.
- Authentic cases observe one engine-to-profile Storage READ, one successful
  complete-record validation, correct descriptor/checksum tables, active room,
  pending ENCD at runtime PC zero, zero audio packets, and zero active music.
- Poppy lint and SNES audit pass. The M23A ROM is a 512 KiB LoROM because it
  contains the two locally generated complete ROOM records.
- M19-M22 code and accepted ROMs are not rebuilt into M23A identities; their
  accepted files/hashes remain unchanged.

No new timbre approval required.

## Exact dependency cone to the authentic music offsets

### Room 49, normal ENCD entry to `+0x004F`

The exact prefix is:

- `+0x0000`: `$7A verbOps` defines verb 53's inline name as `Demo`;
- `+0x0009`: `$13 actorOps` resets actor 7, assigns costume 234, sets initial
  animation frame 18, and sets X/Y scale to 255/255;
- `+0x0014`: `$1A move` writes global `var[27]=214`;
- `+0x0019`: `$0A startScript 144` with arguments 88 and 2;
- `+0x0022`: `$48 isEqual` reads indexed bit variable
  `0xA1A1 + 1 = 0x81A2`, i.e. bit 418, and compares it with 1. A false
  result takes relative `+3` to `+0x002E`; a true result reaches
  `$42 chainScript 213` at `+0x002B`, replacing the ENCD and making
  `+0x004F` unreachable in that execution;
- `+0x002E`: `$28 equalZero` tests bit 425 (`0x81A9`). If it is nonzero,
  the false condition takes relative `+0x000A` to `+0x003D`. If it is zero,
  `+0x0033` sets bit 425, `+0x0038` starts sound 80 through ordinary `$1C`,
  and `+0x003A` jumps past the iMUSE block;
- `+0x003D`: `$7C` stores `isSoundRunning(81)` in global `var[0]`;
  `+0x0041` skips the block by relative `+0x0027` when that value is nonzero;
- `+0x0046`: `$7C` stores `isSoundRunning(80)` in global `var[0]`;
  `+0x004A` skips the block by relative `+0x001E` when that value is nonzero.

Therefore normal entry reaches `+0x004F` only after script 144 has had its
canonical scheduling opportunity, with bit 418 not equal to 1, bit 425 set,
sound 81 stopped, and sound 80 stopped. The dependency classification is:

- already implemented but requiring authentic initialization: variables and
  bit variables, relative comparisons, `startScript`, `startSound`,
  `isSoundRunning`, actor records, and sound-status ownership;
- missing opcode/semantic closure on SNES: any verb-53 inline-name and actor-7
  suboperations not already covered by the bounded verb/actor implementations;
  the branch-only `$42 chainScript 213` is implemented generically but its
  authentic target resource is not registered;
- missing subsystem/data: authentic global script 144 registration and every
  opcode/state dependency it executes before returning or yielding; authentic
  script 213 is additionally required for the bit-418-equals-1 branch;
- missing earlier-gameplay state: bit 418, bit 425, actor 7 and costume 234,
  and sound-80/81 ownership/status;
- no prefix branch is declared dead for the supplied demo state without a
  controlled authoritative run, so M23A does not force any of them.

### Room 63, normal ENCD entry to `+0x00A7`

The first two operations are canonical `$1D ifClassOfIs` tests on object 595:
class selectors 146 and 148 (bit 7 means required-present classes 18 and 20).
Failure of either test jumps directly to
`+0x004F`. If both classes are present, `+0x0012..+0x004E` queues command
`0x0110` and flushes it, queues command `0x0101` for sound 80 and two `0x010D`
commands for sounds 80 and 153, stops script 151, starts sound 46, flushes,
and starts script 200 before converging at `+0x004F`.
Exact `$1D` semantics are those in local ScummVM `script_v5.cpp`: read a
word object, read class selectors until `0xFF`, require bit-7 selectors to be
present and unflagged selectors to be absent, then take the relative jump when
the combined condition is false.

From `+0x004F`, the exact remaining path is:

- `$48` compares `var[224]` with 49. A mismatch jumps directly to `+0x0072`.
  A match places actor `var[1]` in room `var[4]` at object 851, requests animation
  248, follows that actor with the camera, yields once, walks the actor to
  `(360,130)`, and then converges at `+0x0072`;
- `$28` at `+0x0072` tests `var[414]`. A nonzero value jumps to `+0x0095`.
  Zero executes two `$AC` expressions: first `var[444]=855-853`; then
  `var[444]=random(0..var[444])+853`; `$9A` copies the selected object number
  into `var[414]` before converging at `+0x0095`;
- `var[0]=isSoundRunning(80)` at `+0x0095`; sound 80 must be running so the
  not-equal-zero test does not skip the hook block;
- `var[0]=isScriptRunning(151)` at `+0x009E`; script 151 must be stopped so the
  equal-zero test does not skip the hook block.

Classification:

- already implemented but requiring authentic state: variables, expressions,
  deterministic RNG state, actor placement/animation/camera intent, walk
  intent, yields, sound/script status, comparisons, and relative flow;
- missing SCUMM opcode: canonical `$1D ifClassOfIs` on SNES (including its
  multi-class terminator, high-bit negative-class rule, object lookup, and
  false-condition relative jump); any unimplemented encoded variants in the
  actor/expression prefix must also be closed rather than skipped;
- missing engine subsystem: authoritative object 595 class ownership and the
  actor/camera/walk lifecycle needed if `var[224] != 49`;
- missing earlier-gameplay state: object 595's class-146/class-148 ownership,
  `var[224]`, `var[414]`, actor `var[1]`, deterministic RNG state, sound 80
  running, and script 151 stopped; the both-classes branch additionally depends
  on sound-command state and authentic script 200;
- subordinate-script dependency: authentic script 151 must be registered for
  the post-hook operation at `+0x00B5`; it is not needed merely to arrive at
  `+0x00A7` but is required for the authentic batching/flush path.

Nothing in this analysis labels a branch dead merely to reach the target.

## M23B decision

1. **Smallest correct semantic dependency closure.** This is the eventual
   gameplay-quality route. It requires canonical `$1D`, object-class state,
   actor/result variants, authentic script 144 (and later 151), and an
   authoritative initialized demo state. Its advantage is genuine normal ENCD
   execution. Its risk is that the closure is not narrow: it crosses class,
   actor, object, subordinate-script, and earlier-progression boundaries that
   M23A intentionally excluded.

2. **Hash-bound source-extracted basic blocks.** Extract the complete command
   blocks from the already bound ENCD identities at build time, retain original
   offsets and predecessor-state assertions, and execute them as an explicitly
   limited integration fixture through the real dispatcher/resource catalog.
   This does not claim room-entry reachability or gameplay semantics. It is
   narrow and would replace the hand-authored M21/M22 command fixtures with
   authentic bytes while preserving their accepted music behavior.

Recommended M23B gate: approach 2. Bind room 49 `+0x004F..+0x0069` and room 63
`+0x00A7..+0x00CA` to the complete ROOM/ENCD hashes, preserve authentic batching
and intervening operations, execute from generated source extracts through the
real dispatcher, and label the result “source-extracted block integration,”
not authentic room-entry gameplay. Approach 1 should become a later gameplay
milestone only when its full dependency cone is in scope.
