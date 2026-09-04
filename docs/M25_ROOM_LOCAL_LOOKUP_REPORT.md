# M25 complete room-local LSCR executable lookup

Status: **implemented and fresh-emulator proven**. Exactly one authentic
blocker was cleared. M24R-B remains paused.

## Canonical namespace and generator correction

The supplied Fate index has 200 DSCR entries. The authoritative global/local
boundary is therefore source-bound as:

```text
numGlobalScripts = 200
script < 200      -> global resource
script >= 200     -> active-room LSCR, local index = script - 200
```

The raw resource provider exposes this count; authentic cooked manifests carry
it as `num_global_scripts`; the SNES generator emits
`SCUMM_V5_NUM_GLOBAL_SCRIPTS = $00C8`. Host and SNES `startScript` now select
one namespace before lookup. They no longer try global lookup and then fall
back to a room-local script with the same number.

The generator previously used one `executable` flag for two different ideas:
lifecycle scheduling and later script resolution. An `entry-only` room thus
omitted all LSCR program bytes. These are now separate:

- ENCD/EXCD lifecycle scheduling is unchanged;
- every LSCR descriptor in a validated, non-registration-only complete room is
  included in its executable-local directory;
- no LSCR is automatically scheduled by that inclusion;
- lookup is selected by active record/room ownership;
- room replacement invalidates the previous directory through the accepted
  room-generation retirement lifecycle.

Generated directories retain logical number, 16-bit local index, program ID,
complete cooked descriptor/source mapping, length, identity, and SHA-256.
Duplicate IDs, IDs below the boundary, inconsistent manifest boundaries,
malformed records, and ambiguous cooked ranges reject before output/runtime
activation.

## Authentic room-63 inventory

All executable LSCRs from the complete authentic room-63 record are:

| Script | Local index | Original file offset | ROOM offset | Payload | SHA-256 |
|---:|---:|---:|---:|---:|---|
| 200 | 0 | `$07AF94` | `$00A7ED` | 190 | `80b6c093ea63204817617202c3f54644c3b1e8ca006a0af3ba10b9dceba6c485` |
| 201 | 1 | `$07B05B` | `$00A8B4` | 131 | `9b4fd6d782bb96a0b67dece770f5faa57bfe409173a5c26e5396f3e134cf18dd` |
| 202 | 2 | `$07B0E7` | `$00A940` | 208 | `90e13f2440380e9f77fae78204e2cc0d8122124c73f1d06556cdfa1166049671` |

LSCR 202 begins at cooked offset `$00AC08`; its complete identity comes from
the authentic ROOM record and not a copied block or direct ROM label.

## Copyright-free conformance

A generated room contains ENCD plus LSCR 200, 201, 202, and 208 and global
script 10. At the first ENCD `breakHere`, all five result variables remain
zero: directory inclusion did not auto-run any local script. Explicit
`startScript` operations then select distinct generated programs `$D2`, `$D3`,
`$D4`, `$D5`, and global `$D6`, producing unique values for every script.
The generated local indices are `[0,1,2,8]`, directly guarding the historical
201/208 8-bit-to-16-bit alias class.

Missing LSCR 203 produces `SCUMM_ERR_SCRIPT`, leaks no child slot or nested
context, and never executes an arbitrary address. Host coverage additionally
proves a room change invalidates old ownership and a same-number LSCR resolves
to the new room, while global scripts remain on the global resource path.

Evidence: `build/m25-room-local/conformance/report.json`.

## Authentic Fate proof

From fresh power with zero debugger writes, the accepted room-49 path and
normal room transition reach authentic room-63 ENCD. The decisive trace is:

```text
room.63/ENCD +$00DE  program $E7  $2A startScript(202)
room.63/LSCR.202 +0 program $EA  $1A move(Local[0], -1)
room.63/LSCR.202 +5 program $EA  $80 breakHere
room.63/ENCD +$00E1 program $E7  $00 stopObjectCode
```

Captured resolution state:

```text
active room/record       63 / 1
numGlobalScripts         200
requested script         202
classification           current-room local
computed local index     2
generated program        $EA
allocated slot           2
parent PC before         $00DE
child entry PC           $0000
child post-yield PC       $0006
parent resume PC          $00E1
nested depth after return 0
```

The yielded child remains independently owned in slot 2 at PC `$0006`; slot 0
is retired after the parent resumes and executes its authentic stop. This
proves normal generated lookup, immediate nested execution, canonical yield,
and exact parent restoration.

Evidence: `build/m25-room-local/authentic-report.json`.

## Next authentic blocker

The next blocker is an **integrated scheduler/lifecycle gap**, not an opcode or
resource lookup failure. Authentic LSCR 202 is legitimately yielded/runnable
at PC `$0006`, but after room-63 ENCD completes the integrated room/audio driver
does not invoke the accepted general script scheduler. Even after another 300
frames, the child remains at PC `$0006`; the already implemented next opcode
is never dispatched.

Surrounding authentic bytes are:

```text
LSCR.202 +$0000:
1A 00 40 FF FF 80 7B 01 40 01 88 01 40 00 40 BB 00 48 01 40 02

+$0000  move(Local[0], -1)
+$0005  breakHere
+$0006  getActorWalkBox(Local[1], actor 1)
```

The next milestone should connect the integrated room driver to the existing
canonical scheduler so yielded room-local/global scripts receive later passes.
That work was not started here.

## Validation and identity

```text
unit tests:             PASS, 345/345 (343 accepted plus 2 lookup tests)
repository validation: PASS with established demo/profile diagnostics
Poppy/source traps:     PASS, 29 files / 2339 global labels
assembly/LoROM audit:   PASS, 524288 bytes, reset=$8000, NMI=$8062, IRQ=$8084
integrated ROM SHA-256: 720f1e46ab65f642ffb758e0235ee1c2054f6568d345eac67bf9b5eb097a84d9
```

Accepted cooked ROOM hashes remain unchanged. Costume 45 remains absent, the
SNES costume renderer and text glyph rendering remain unavailable, and no
presentation claim is made. No audio, iMUSE, TAD, instrument, actor movement,
pathfinding, or subsequent LSCR-202 semantic was implemented.
