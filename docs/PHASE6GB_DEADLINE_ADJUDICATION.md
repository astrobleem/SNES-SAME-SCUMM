# Phase 6G-B deadline adjudication

## Decision

Classification **B — NMI 299 is physically unavailable for the complete
authentic six-cell preparation**.

The instrumented diagnostic carrier measured 6,729 S-CPU cycles from the S5
`SET_LAYER` acceptance store to the NMI 299 entry.  The complete generic S6-S9
path consumed 22,424 S-CPU cycles after subtracting the 148-cycle intervening
NMI:

| Work | S-CPU cycles |
|---|---:|
| S5 to NMI 299 | 6,729 available |
| screen-cell enumeration and six 4bpp characters | 20,868 |
| tilemap preparation | 598 |
| two descriptor publications | 636 |
| complete S6-S9 preparation | 22,424 |

The descriptor-only diagnostic lower bound fits in the remaining interval,
but that is not a valid production path: its character and tilemap sources are
preprepared.  The source-neutral production path cannot reach NMI 299.

Machine-readable evidence is emitted at
`build/phase6gb-deadline-final2/deadline.json`.  Nexen exposes an S-CPU cycle
counter and scanline, but not a reliable dot/master-cycle field; the report
therefore records exact S-CPU hook-cycle timestamps and states that limitation.

## Certified timing contract

Storage/functional capacity remains 80x8 pixels and at most 22 touched cells.
The real-time class certified by the authentic gate is six active cells, 204
DMA bytes, and two descriptors:

* S0-S5 and S6/S7 entry occur at NMI counter 298.
* NMI 299 interrupts the same `Same_Frame_Run`; no overlay descriptor is active
  and no partial subtitle is visible.
* S6-S9 resume and finish in that invocation at counter 299.
* NMI 300 commits both complete descriptors and exposes all six cells.
* No second `ScummV5_Engine_Frame`, scheduler pass, message update, cursor
  advance, or talk-delay decrement occurs before visibility.  Delay remains
  120, cursor remains 17, `VAR_HAVE_MSG` remains `$FF`, and actor 2 retains the
  message.

This is one dropped video opportunity caused by bounded S-CPU preparation and
zero lost SCUMM subtitle lifetime.  It is deliberately not described as
first-NMI visibility.

Segment 2 and final hide retain their stronger next-NMI contract:

| Transition | semantic / S0-S9 | commit / visible |
|---|---:|---:|
| segment 1 show | 298 / preparation ends 299 | 300 |
| segment 2 replace | 410 | 411 |
| final hide | 464 | 465 |

## Interrupt safety

Character and tilemap staging complete before descriptor publication.  Queue
descriptors retain active-last publication.  NMI 299 therefore sees no partial
segment-1 transfer.  NMI preserves and restores the interrupted mainline CPU
state; preparation resumes with balanced stack and restored M/X and DBR state.
Font rasterization, sparse scanning, and 4bpp conversion remain outside NMI.

## Visual and semantic identities

* Segment 1: 76 pixels, six cells,
  `2237a3ae1c7c292e61908c9b65b0867620bea331bc4b751a79810b1ed2a8db74`.
* Segment 2: 15 pixels, one cell,
  `27bfa2acbc93bdd6e84aab3e6a9ddc395bd9e5c237a9a0d9fdfc1c7d701c1984`.
* Final hide: zero visible BG2 pixels.
* Final deterministic Mode-3/BG2 ROM:
  `e192a1919ec5b24572bafe46852e45e928f4faf460b0fc95b1c28cc3724e0ed3`.

The message remains 24 bytes, advances `$027B -> $0296`, resumes after `FF 03`
at cursor 17 exactly once, uses delays 120 and 84, clears `VAR_HAVE_MSG` at the
accepted L52 publication boundary, and requests one actor-2 talk-start and one
talk-stop transition.

## Remaining blocker

Execution stops at global script 2 `+$046B`:

`1A 78 00 FF FF` — `move Var[120], $FFFF`.

The current contiguous WRAM variable allocation physically reserves only 16
u16 slots at `$7E2320`; subsequent addresses own other VM/scheduler state.
Although the M23B profile count admits the wider logical index, Var[120] has no
non-overlapping physical backing.  Variable storage was not enlarged and the
instruction was not implemented in this phase.

