# M25 canonical headless message/talk lifecycle

Status: **implemented and emulator-proven**. M24R-B remains paused. No
subsequent authentic semantic blocker was implemented.

## Canonical v5 oracle

The local ScummVM execution model establishes this ordering for the authentic
Fate line:

```text
slot-0 SO_TEXTSTRING -> actorTalk
base talk delay       = 60 jiffies
VAR_CHARINC           = 4 in the validated Fate state
encoded glyph count   = 25 (the $10 Fate charset glyph counts once)
initial delay         = 60 + 25 * 4 = 160 jiffies
engine delta          = 4 jiffies per logical loop
```

The message starts after that loop's frame-begin decrement. The fortieth
subsequent loop decrements 4 to 0; scripts in that loop still observe the
previously published `VAR_HAVE_MSG=1`. The post-script dialog phase emits the
logical stop request and clears internal ownership. The forty-first subsequent
loop publishes `VAR_HAVE_MSG=0`, which is the first loop in which
`waitForMessage` may proceed.

Actor 1's logical talk-start and talk-stop requests are chore/frame 4 and 5.
They are recorded without changing its visible frame. Starting another slot-0
actor message first emits the old owner's stop request, then establishes a new
generation and start request. Canonical wait suboperation `$AE/$02` rewinds to
its opcode, yields while `VAR_HAVE_MSG` is nonzero, and resumes only on the
published-clear loop.

## Implemented boundary

The host and production SNES interpreter now provide:

- bounded 32-byte encoded slot-0 talk storage, the smallest power-of-two bound
  covering the authentic 26-byte terminated message;
- exact NUL retention and bounds/EOF rejection, with `$10` preserved as an
  encoded Fate glyph;
- actor ownership, generation, talk delay, internal message state, and
  script-visible `VAR_HAVE_MSG`/`VAR_TALK_ACTOR` publication;
- logical, exactly-once talk-start and talk-stop events;
- engine-clock countdown and canonical `$AE/$02 waitForMessage` retry/yield;
- headless presentation mode, which leaves glyph and costume rasterization out
  without suppressing semantic talk events.

The representation survives across frames because it is engine-owned WRAM.
This milestone does not extend cold-save serialization.

Malformed/truncated input is transactional with respect to talk ownership:
partial bytes may occupy decoder scratch, but no active owner, generation,
event, or `VAR_HAVE_MSG` claim is created.

## Copyright-free conformance

Host tests cover the exact 160-jiffy lifecycle, replacement, independent
actors, exactly-once events, malformed/truncated/over-capacity input, and
wait blocking/resumption.

Dedicated fresh-power-on SNES validators use production cooked-room lookup,
the production scheduler, and production interpreter:

- `message`: actor 1 says `A`, giving `60 + 1*4 = 64` jiffies; immediate child
  LSCR 201 blocks in `$AE/$02`, remains blocked for 16 loops, and executes its
  next instruction only on loop 17 when zero is published.
- `message-malformed`: a descriptor-ending unterminated SO_TEXTSTRING reports
  canonical EOF at `$14`, with zero talk ownership and zero lifecycle events.

Evidence:

```text
build/m25-message-talk/wait-report.json
build/m25-message-talk/malformed-report.json
```

## Authentic Fate proof

The fresh-power-on integrated run uses complete authentic room 49 and LSCR 200
through the normal resource provider, room lifecycle, nested scheduler, and
interpreter, with zero debugger writes. At LSCR 200 `+$01A8` it consumes:

```text
14 01 0F 57 65 6C 6C 2C 20 68 65 72 65 20 49 20
61 6D 20 6F 6E 10 54 68 65 72 61 2E 00
```

This is actor 1 saying `Well, here I am on\x10Thera.`. The canonical encoded
message is retained byte-for-byte, PC advances `+$01A8 -> +$01C5`, the initial
delay is 160, and LSCR 200 continues while the message remains active. The
trace records start, every distinct countdown state, the exact completion
loop, stop, and next-loop publication of zero.

Observed authentic state at start:

```text
emulator frame             295
logical frame              2
speaker                    actor 1
speaker position/room      (399,116), room 49
speaker facing/walkbox     0, box 11
speaker visible/moving     true, false
PC                         $01A8 -> $01C5
initial delay              160
completion logical frame   42 (40 subsequent loops)
VAR_HAVE_MSG at completion 1
VAR_HAVE_MSG next loop     0
```

Evidence:

```text
build/m25-message-talk/authentic-report.json
```

## Next authentic semantic blocker

LSCR 200 continues through its already-supported tail, follows the camera with
actor 1, and starts authentic room-local LSCR 216. That child resolves through
the generated room-local descriptor table and fails closed at its first
instruction:

```text
resource             room.49/LSCR.216
script SHA-256        588c3a457f799681c616bce088d980847ffb77823e6a65b29511a67bb06b0f60
normalized offset     +$0000
original file offset  $05D3DD
original ROOM offset  $0138FE
original chunk offset $0009
cooked-record offset  $014166
bytes                 7B BA 01 01 48 BA 01 07 00 07 00 30 01 15 00 18
decode                getActorWalkBox(result Var[$01BA], actor 1)
next PC if supported  +$0004
classification        opcode plus actor/walkbox-state query gap
```

`$7B getActorWalkBox` is not implemented by this milestone.

## Presentation limitations

Costume presentation remains blocked because authentic costume.45
is absent from the supplied Fate demo and the SNES costume renderer
does not yet exist.

Text glyph rendering is not implemented by this milestone.

Talk-start and talk-stop are logical SCUMM actor events only; no visible
mouth animation is claimed.

The generic host costume direction oracle was separately corrected to use
canonical `newDirToOldDir` (`0->3`, `90->1`, `180->2`, `270->0`, including the
accepted boundary order). This does not unblock costume presentation.

## Validation

Final identities and validation results are filled from the immutable final
build and machine-readable emulator reports below; historical accepted ROM
identities are not rewritten.

```text
unit tests:             PASS, 341/341 (338 accepted + 3 lifecycle tests)
repository validation: PASS with established validator/demo-registration diagnostics
Poppy/source traps:     PASS, 29 files / 2304 global labels
assembly/LoROM audit:   PASS, 524288 bytes, reset=$8000, NMI=$8062, IRQ=$8084
integrated ROM SHA-256: 2530ccccd236361946890e29e78e8c47fe469fb36698f8259071d64f85547a4e
```
