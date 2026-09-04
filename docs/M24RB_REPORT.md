# M24R-B report — authentic Fate sound-82 composite application

Status: **hard stop before full milestone acceptance**.  The real-content composite,
host interpreter path, and cold-emulator backend gates pass.  The required single-process
authentic SNES SCUMM run does not yet assemble because the additional interpreter/lifecycle
closure crosses bank 0's fixed internal-header boundary.  This report does not combine the
split proofs or call them an end-to-end pass.

M24R-B1 subsequently removed the ROM-layout blocker without changing audio semantics, but
the first combined authentic run exposed the frozen SNES command-dispatch defect documented
in `M24RB1_REPORT.md`. M24R-B therefore remains incomplete.

## Frozen backend and content

M24R-A remains the only asynchronous physical mechanism.  M24R-B applies its command 22,
generation binding, 256-tick outgoing gain ramp, and fixed admissions at transition ticks
`19,38,63,94,125` to real Fate content.  The only TAD content addition is the reserved-bytecode
marker decoder (`audio/m24rb/terrific_audio_driver_m24rb_content.patch`): 15 driver bytes, no
new driver state, allocator, interpreter, seek operation, or transition type.

The composite builder is `tools/build_fate_m24rb_composite.py`.  Its source identities are:

* sound 80: `3692a73673d619461b6215bae731832752610c99c166bbbf5978beb30afd5ed0`
* sound 82: `e665931c3440486624afde85035d4f1cd895a1ac097c9d915e115511b82dcb25`
* linked TAD image: `e6be3456d9d28d89f13173d4089f81d92a9ffab27130f6a4e79773a187730e59`
* composite audit: `eec8bd3ebd250765055167055202e6cc2f7a6a48363ade90b762cbdfe87ef275`

The compiled route is exactly the bounded hook14/hook7 lead-in, marker 7/8 handoff,
sound-82 initial section and loop, and five-lane accepted hook8 continuation.  The runtime
marker is a compiled boundary notification; it does not claim to execute a source tick.

## Voice reduction and instruments

Sound 82 contains 558 source note instances and peaks at 14 logical voices.  The compiled
policy represents 554 instances.  It first merges identical same-pitch timbral doublings,
then protects melody (programs 35/82), bass/fundamental notes, outer structural chord tones,
velocity/duration, and stable source order.  Four sub-two-TAD-tick fragments are omitted;
every interval decision is in `build/m24rb-content/composite-audit.json`.  Room-63 admissions
take physical voices 7,6,5,4,3 only when their incoming lanes need them; five voices are not
permanently reserved.

The bounded ranges use reviewed pad, bass, flute, and marimba zones.  Program 112's short
struck role uses the reviewed marimba envelope rather than silently inheriting a sustained
GM mapping.  Program 82's low fundamental uses the bass zone; its upper range remains the
reviewed pad.  No unresolved mechanically plausible timbre fork remained, so no new human
approval gate was created.

## Host authentic-script proof

`tools/validate_scumm_m24rb_host.py` loads the complete authentic room-49 record, executes
the accepted PC-zero ENCD path, schedules authentic LSCR 208 at PC zero, and observes its
source-mapped commands:

1. hook 7; trigger marker 7; deferred 600-step sound-80 fade; trigger-group terminator;
2. trigger marker 8; deferred priority 0, speed 0, 60-step fade, and start sound 82;
3. trigger-group terminator and canonical frame-end processing.

The host state changes `82: absent -> deferred -> active -> fading -> stopped`; `$7C` ownership
is true for deferred/active/fading and false only after fade completion.  Marker 8 consumes
its four commands once.  The report is `build/m24rb-host-report.json` (SHA-256
`c1b4fdff85b0174ec4a64a523f8b438f325d86201f3f065782260bba69cf568b`).

## Cold-emulator real-content backend proof

Four fresh Nexen processes use the real composite.  The three transition ROMs are:

* low-density phase: `991e152258459d06fd52d7cfd90175e56839024628ee47999dd92cf179f324e3`
* high-density phase: `b2980a96c74538f4982d9da74ce9234e26f4ed3d577845b94dbc6912aacc9c03`
* sustained-note phase: `1decc173ed13cadf13065b1da6bb82da3da4caf3a08fef7313be0b79bb495f9f`
* no-transition full-loop control: `1816ccb5191c05d8f5c4c7cbd3885d09c95cce781af206e50c30647938af64a7`

All phase runs emitted `90,A7,A6,A5,A4,A3,BF` with transition-relative ticks
`0,19,38,63,94,125,0`.  Song 1 remained ready/playing: no blank, load, or full-song reload;
packet loss/rejection was zero.  Captured peaks were 15,322, 15,207, and 15,322, below hard
clipping.  The aligned room-63 excerpts have no zero 20-ms windows.  The 256-tick fade is
2.048 seconds at 125 Hz.

The sound-82 source loop `97920 -> 1920` compiles to 12,931 TAD ticks = 103.448 seconds,
0.377 ms above the accepted 103.447623-second oracle.  The 141.431-second cold control crossed
the loop with no transition/completion token, no ownership loss, no zero 20-ms seam window,
and a peak of 15,322.  Evidence is in `build/m24rb-nexen-3/report.json` (SHA-256
`d01c185b5230130addb10226f3d377da7f7854f9c638ed5dd02286acf4e4f1c2`).

Reference excerpts are in `build/m24rb-reference/`: marker 8, representative body, loop seam,
all three arbitrary phases, and post-fade sound 80.  Marker 8 retains the source-authored
silent transfer interval; the room-63 async transitions introduce no additional silent window.

## APURAM and cost

* driver upload: 3,558 bytes (M24R-A plus 15-byte content marker handler)
* low/driver/common base through `$11E8`: 4,584 bytes
* common audio item: 4,369 bytes = 128-byte overhead + 4,241 sample bytes
* composite song/transition data: 6,115 bytes
* echo: 256 bytes
* deterministic free APURAM: 50,212 bytes
* peak physical voices: 8
* peak logical source voices: 14
* transition CPU bound: unchanged from M24R-A, at most 420 extra SPC cycles/tick (5.13%)
* new driver state: 0 beyond M24R-A; S-CPU logical evidence state: 8 bytes

## Regression and save scope

All 320 unit tests pass (318 inherited + 2 M24R-B).  Repository validation and default Poppy
lint pass.  The four backend ROMs assemble and pass ROM audit.  M19-M24R-A artifacts were not
rewritten.  The known unchanged-M19 long-capture video/NMI pacing assertion and the unrelated
generic Fate catalog/base-TAD mismatch remain separate existing harness issues.

Save semantics remain deterministic cue restart.  No arbitrary-phase composite, APURAM, DSP,
voice, BRR cursor, envelope, echo, or TAD instruction state is serialized or claimed restored.

## Hard-stop evidence

The guarded authentic SNES connection now includes profile-selected LSCR 208 registration,
canonical deferred command forms, independent logical ownership, room-63 frame-end fade queue,
and a stop barrier before script 202.  With the authentic cooked rooms and composite linked,
Poppy reports bank-0 emitted code ending at `$103DF`, overlapping the fixed SNES header at
`$FFC0-$FFFF`.  The existing bank-0 code budget is therefore exceeded by 1,056 bytes.

Finishing the single-process gate requires a far-code-bank layout for SCUMM helper routines
(or an equivalent deliberate bank-layout refactor).  That is outside M24R-B's instruction to
apply the accepted backend without widening architecture.  No source block, debugger injection,
interior-PC entry, fake sound-82 ownership, or split-proof acceptance claim was substituted.

The next authentic execution blocker after audio remains local script 202's actor movement,
`$7B getActorWalkBox`, walkbox/pathfinding, and associated scheduler yields—but M24R-B must first
receive an explicit decision on the code-bank relocation needed to finish its integrated SNES gate.
