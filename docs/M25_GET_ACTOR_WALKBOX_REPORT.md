# M25 canonical `$7B getActorWalkBox`

Status: **implemented and fresh-emulator proven**. Exactly one authentic
semantic blocker was implemented. M24R-B remains paused.

## Canonical semantic

The local authoritative v5 implementation in
`/home/chad/scummvm/engines/scumm/script_v5.cpp` performs exactly:

```text
getResultPos()
actor = getVarOrDirectByte(PARAM_1)
setResult(actor._walkbox)
```

The SAME host and production SNES implementations now follow that contract for
`$7B/$FB`. They read the actor's existing stored walkbox. They do not consult
room geometry, adjust coordinates, construct a route, move the actor, or mutate
any actor field.

The authentic instruction is source-bound as:

```text
resource             room.49/LSCR.216
script SHA-256        588c3a457f799681c616bce088d980847ffb77823e6a65b29511a67bb06b0f60
normalized offset     +$0000
original file offset  $05D3DD
original ROOM offset  $0138FE
original chunk offset $0009
bytes                 7B BA 01 01
decode                getActorWalkBox(Var[442], actor 1)
PC                    +$0000 -> +$0004
```

## Copyright-free conformance

Host tests cover direct and variable actor operands, result replacement,
multiple destinations, stored boxes zero/two/three, unrelated-variable
isolation, malformed/truncated operands, invalid actors, and exact PC
advancement.

Three dedicated fresh-power-on SNES ROMs exercise the production cooked-room
lookup and interpreter. The valid fixture deliberately places actor 3 at
`(4,1)`, geometrically inside box 1, while its stored field is box 3. `$7B`
returns 3. Four queries return `[0,2,3,3]`; direct and variable forms advance
`43->47`, `47->51`, `51->55`, and `55->60`. The complete bounded actor-state
snapshot has the same SHA-256 before and after:

```text
57b04ce6053b258489dee6a1f6a324c5b7c69f0906e0e1d56d5c8fa86457642d
```

Invalid actor 32 fails with `SCUMM_ERR_ARGUMENTS`; the truncated `$FB` variable
operand fails with `SCUMM_ERR_PC_RANGE`. Neither executes the query handler.

Evidence: `build/m25-get-actor-walkbox/conformance.json`.

## Authentic Fate proof

The integrated ROM starts from fresh power with zero debugger writes and uses
the accepted complete room resources, room lifecycle, nested scheduler, and
headless semantic lane. Authentic LSCR 200 first executes
`putActor(1,399,116)` at `+$019C`; canonical placement stores walkbox 11 and
destination box 11. LSCR 216 later queries that field.

Immediately before `$7B`, actor 1 is:

```text
room                 49
position             (399,116)
stored walkbox       11
facing               0
movement             0 / stationary
walk destination     (-1,0), destination box 11
visible              true
scale                (255,255), box scale $8001
costume              0
frame                 $FF
```

The authentic query records:

```text
result target         Var[442] (runtime result offset $2374)
actor operand mode    direct
actor                 1
Var[442] before       0
stored walkbox        11
Var[442] after        11
PC                    +$0000 -> +$0004
```

The complete relevant SNES actor storage hash is identical before and after:

```text
13ac5902a25dee51e0abf260638c14d5d7b1ef90e4d133a50c360ca3463dd48b
```

LSCR 216 then executes its authentic comparisons, `setBoxFlags(21,$80)`,
`breakHere`, and loop normally. Thus `$7B` does not merely decode; its result is
observed by subsequent authentic bytecode and the child remains scheduler-owned.

Evidence: `build/m25-get-actor-walkbox/authentic-report.json`.

## Next authentic blocker

No later room-49 opcode fails. The existing deterministic lifecycle eventually
enters authentic room 63. Its ENCD reaches:

```text
resource             room.63/ENCD
script SHA-256        c40ef1e4b47d122e81ecf34df09c6dd83283d9ab8eb296410a0ee5c1433e3002
normalized offset     +$00DE
original file offset  $07AF7D
original ROOM offset  $00A7D6
original chunk offset $00E6
cooked-record offset  $00AA9E
surrounding bytes     01 01 52 00 01 00 00 01 78 00 FF 1C 50 0A 97 FF
                      2A CA FF 00
decode                startScript(202), no arguments
```

Canonical `$2A` decoding succeeds and consumes `CA FF`. The failure is
`SCUMM_ERR_SCRIPT`: authentic room-63 LSCR 202 exists in the complete cooked
record, but the current integrated profile only makes room 63's entry script
executable. LSCR 202 is therefore absent from its generated executable-local
lookup. This is a room-local resource-delivery/registration boundary, not a
new opcode implementation gap. M25 does not enable or execute LSCR 202.

## Presentation limitations

Costume presentation remains blocked because authentic costume.45 is absent
from the supplied Fate demo and the SNES costume renderer does not yet exist.

Text glyph rendering remains unavailable. The accepted headless talk/message
semantics are preserved; no costume or text pixels are claimed.

## Validation and identity

```text
unit tests:             PASS, 343/343 (341 accepted plus 2 host `$7B` tests)
repository validation: PASS with established validator/demo-registration diagnostics
Poppy/source traps:     PASS, 29 files / 2321 global labels
assembly/LoROM audit:   PASS, 524288 bytes, reset=$8000, NMI=$8062, IRQ=$8084
integrated ROM SHA-256: 3feccac7895943ae98452072003bda3062d1c74d715c6641385a48a0c6c41887
```

Accepted historical ROM artifacts were not rewritten. No music, iMUSE, TAD,
instrument, actor presentation, movement, pathfinding, or subsequent script
semantic was added.
