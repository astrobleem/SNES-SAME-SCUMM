# M25 canonical `$F7 startObject` and executable OBCD report

## Result

The canonical SCUMM v5 `$37/$77/$B7/$F7` family now executes complete,
room-owned OBCD resources through the production interpreter.  The authentic
room-49 path reaches object 596 / verb 10, executes its source bytecode
`42 D3 FF`, retires that object-script through canonical `chainScript(211)`,
and enters authentic LSCR 211 at PC `$0000`.

The milestone stops at the next unsupported semantic, LSCR 211 `+$026E`
`$B2 setCameraAt(Var[2])`.  Camera semantics were not implemented.

## Source binding

| Identity | Value |
|---|---|
| game/profile | `scumm_v5 / indy4-fate-demo / dos-vga-en-1992-07-09` |
| profile identity | `37bc71eb005f72fbad00dd4fea9a0ab0245df4e9af50a3ffce04167c99156c2b` |
| archive | `/home/chad/fatedemo-box.zip` |
| archive SHA-256 | `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798` |
| index SHA-256 | `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9` |
| data SHA-256 | `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240` |
| room 49 source offset/length | `PLAYFATE.001 +301791`, 80,351 bytes |
| room 49 SHA-256 | `fbf234f2ffe3530ba365980abfae556636d83e5cada9bdc649c43d4cce7242f6` |
| cooked room SHA-256 | `2904015371af15b616711013298b8e95874e55c5e9c45216fe09bf9a544a025f` |

Object 596 is local object index 5.  Its complete 73-byte OBCD begins at
`PLAYFATE.001 +361408`, room-relative `+59617`, and cooked-record `+61769`.
Its SHA-256 is
`5cceb69e9f9276a8ba0504aff16ddd24b38968eaa7cbfd54ea617468f702bc4e`.
CDHD is OBCD `+$0008`; VERB is OBCD `+$001D` and occupies 16 bytes.  Entry 10
resolves canonically to OBCD `+$0029`.

LSCR 211 is 761 bytes with SHA-256
`56fcd3dcd49f671ac7f86fbea741bb6f5a187604ac64fa382b1576bf70cd1d23`.
It begins at `PLAYFATE.001 +379924`, room-relative `+78133`, and cooked-record
`+80285`.

## Authentic `$F7` decode

Global script 2 `+$0458` contains:

```text
F7 01 40 00 40 81 02 40 81 00 40 FF
```

The instruction decodes as:

```text
object:       variable-word $4001 = Local[1] = 596
entry:        variable-byte $4000 = Local[0] = 10
argument 0:   variable-word $4002 = Local[2] = 0
argument 1:   variable-word $4000 = Local[0] = 10
terminator:   $FF
PC:           $0458 -> $0464
```

The sentence-script locals immediately before the instruction were
`[10, 596, 0, 1, 596, 0]`.  The new object-script locals were initialized as
`[0, 10, 0, ...]`; they did not alias the parent locals.

One decoder defect found by the shortened gate was corrected before
acceptance: the vararg selector had initially used generic fetch-byte scratch,
which the following word fetch overwrote.  A dedicated selector byte now
preserves the mode until variable resolution; the gate guards the exact
`[0, 10]` result.

## Resource and execution model

The room cooker now records every complete OBCD, its source/cooked identity,
CDHD and VERB bounds, and canonical verb entries.  The SNES generator promotes
each OBCD to a room-owned executable program.  `getVerbEntrypoint` and
`startObject` consult the same canonical VERB directory; the latter does not
use a second object-to-program map.

The production runtime performs this sequence:

```text
resolve current-room object and VERB entry
stop an existing same-object non-recursive slot
allocate a normal object-script slot
bind room generation + WIO_ROOM + u16 object identity + complete OBCD program
zero locals and copy decoded word varargs
run immediately through the existing nested interpreter
```

The u16 object identity is kept separately from the legacy u8 normal-script
number field.  When `chainScript(211)` replaces the object program, the reused
slot is retyped to `WIO_LOCAL`, its object identity is cleared, and LSCR 211 is
resolved through the current room's generated local directory.

## Emulator evidence

The fresh-power authentic trace records:

```text
global script 2: program 236, $0458 -> $0464
object 596 OBCD: program 232, PC $0029, opcode $42
chain target: 211
object retired: once
LSCR 211: program 221, PC $0000, first opcode $62
```

The chained slot ends as local script 211 with `where=WIO_LOCAL`, object number
zero, and the authentic room-local program identity.  There were no debugger
writes or direct PC/program selection.

The copyright-free SNES room separately exercises two objects, exact entries
10 and 8, `$FF` fallback, an absent entry, distinct same-number verbs, immediate
nested execution, `chainScript`, and independent locals.  Its four expected
programs execute, the absent entry allocates no object slot, and nested depth
returns to zero.

Machine-readable evidence:

- `build/m25-start-object.json`
- `build/m25-start-object-conformance.json`

The final integrated ROM is 524,288 bytes with SHA-256
`a48c0db782b6d1df304d164527f2123a0fd99e0f56617e4404a64aeb35765a8c`.
A clean second assembly produced the same hash.  The copyright-free validator
ROM SHA-256 is
`a14b56f0cf8307a5ff2ccb604769ccf82daf499751eaff303c51546014f12778`.

Validation completed with 356 unit tests, repository/profile validation,
Poppy source traps (29 files and 2,800 global labels), SNES assembly and
LoROM audit, the copyright-free fresh-power emulator gate, and the authentic
fresh-power emulator gate.

## Next blocker

Authentic LSCR 211 reaches `+$026E` with these surrounding bytes from `+$025E`:

```text
1A 00 40 00 00 48 00 40 00 00 81 00 62 D7 62 56
B2 02 00 28 90 A1 02 00 23 00 11 02 01 14 02 0F
49 27 6C 6C 20 77 61 69 74 20 68 65 72 65 2E FF
```

Canonical decode is `$B2 setCameraAt(Var[2])`.  The reached value of Var[2]
is zero.  This is an opcode/engine camera-state semantic gap, not an OBCD,
scheduler, or room-generation failure.  It remains unimplemented.

Costume 45 and text glyph presentation remain unavailable as previously
documented.  M24R-B remains paused.  No new timbre approval is required.
