# Phase 6K — `$4C` far dispatch and empty-flush conformance (corrected)

> **Phase 6L-A correction.** The original report overstated its authentic
> provenance.  Phase 6K proves that the far/local `$4C` dispatch reaches the
> common C25 parser and that an empty `soundKludge([-1])` emits the normalized
> FLUSH packet.  It does **not** prove that authentic LSCR 211 reached `$02D9`
> with an empty queue, nor that room 63 was reached through LSCR 211.  The old
> validator hardcoded `queue_before = 0` and accepted a room-63 snapshot made
> possible by the synthetic M23C transition driver.

## Result and failure classification

Phase 6K is classification **A — opcode dispatch integration gap**.  The single
production C25 implementation already parsed v5 word varargs, retained commands
in the engine-wide FIFO, dispatched its accepted iMUSE subset, and emitted the
normalized final FLUSH packet.  Authentic LSCR 211 executes from the far/cold
program path, whose dispatcher omitted `$4C`; it therefore reported opcode
error 25 before entering C25.

The repair adds `$4C` to that generic cold dispatcher and jumps to the existing
`ScummV5_Op_SoundKludge`.  No queue, parser, command mapping, audio backend, or
room/script special case was added.

## Authentic stream

The complete relevant LSCR 211 bytes decode as follows:

| PC | Bytes | Decode | Next PC | Status before Phase 6K |
|---:|---|---|---:|---|
| `$02AB` | `C0` | `endCutscene` | `$02AC` | supported |
| `$02AC` | `7C 00 00 52` | `isSoundRunning`, result `Var[0]`, sound `$52` | `$02B0` | supported |
| `$02B0` | `A8 00 00 29 00` | `ifNotEqualZero(Var[0])`, branch over conditional audio changes | `$02B5`/`$02D9` | supported; authentic branch reaches `$02D9` |
| `$02B5` | `4C 01 06 01 01 52 00 01 00 00 FF` | `soundKludge([$0106,$0052,$0000])` | `$02C0` | not reached authentically |
| `$02C0` | `4C 01 01 01 01 52 00 01 00 00 FF` | `soundKludge([$0101,$0052,$0000])` | `$02CB` | not reached authentically |
| `$02CB` | `4C 01 0D 01 01 52 00 01 32 00 01 78 00 FF` | `soundKludge([$010D,$0052,$0032,$0078])` | `$02D9` | not reached authentically |
| `$02D9` | `4C 01 FF FF FF` | `soundKludge([-1])` | `$02DE` | fixed by generic far dispatch |
| `$02DE` | `24 53 03 3F FF FF FF FF` | `loadRoomWithEgo(851,63,-1,-1)` | `$02E6` | next excluded visual/lifecycle boundary |

Selector `$01` consumes the complete direct word `$FFFF`; the following `$FF`
is the vararg terminator.  The low byte of the direct word is not mistaken for
the terminator, and the PC advances naturally from `$02D9` to `$02DE`.

## Queue and audio oracle

The Phase 6K validator did not observe the engine-wide queue immediately before
`$02D9`; its `queue_before` field was a constant.  The empty queue below is
therefore only the isolated C25 conformance case:

```text
count:    0
capacity: 16 records
commands: []
```

No claim about the authentic LSCR 211 queue follows from this isolated case.
Phase 6L-A owns reconstruction of sound 82 and the real branch outcome.

The accepted empty-queue behavior is zero command-dispatch packets followed by
one normalized `SAME_AUDIO_OP_FLUSH` packet (opcode 8).  The processed queue is
empty afterward and the flush counter increments.  Event occupancy drains to
zero with zero required-event rejection.  The flush neither queues command
65535 nor emits stop/start operations.

In the isolated empty-flush diagnostic, logical and backend ownership remains:

- active logical music: 80
- route kind/value/song: hook / 14 / 27
- pending hook: none
- no TAD reload or restart
- final audio packet: FLUSH with arguments 0/0

The S-CPU continues immediately; playback is not awaited.  LoROM can execute
the already-supported following logical room transition in the same host frame,
so later LoROM snapshots may contain room-63 queue records.  Those records are
not part of the empty `$02D9` batch.

## Next boundary

The instruction at `$02DE` is verified from the complete source payload as
`loadRoomWithEgo(851,63,-1,-1)`: direct object 851, direct room 63, direct
signed X/Y `-1`.  Its logical machinery already exists in the older M23C lane,
but Phase 6K makes no room-63 visual or transition claim and adds no support for
the instruction.  It is the next excluded presentation/lifecycle boundary.

## Artifacts

Two builds of each artifact are byte-identical:

| Variant | SHA-256 |
|---|---|
| LoROM + legacy | `79229fccdd9035edfa33954e09a734cc17d224bf59b4b5e3b5467012827032e6` |
| SA-1 + legacy | `67306c49f8d1f16a42fd3dd0639b3078bbeb389f43a72cdd98af3e8c7ed60549` |
| SA-1 + Mode-3/BG2 | `1448ec1b518e355529687801cb4a3166699420a36a7743a19b62eaa29bbb45c3` |

All carriers decode the same words in the conformance path, emit the same final
FLUSH, retain music ownership, and report no event rejection.  Historical ROM
hashes remain evidence for that dispatcher repair, not an authentic LSCR-211
sound-82 lifecycle proof.
Both SA-1 variants retain reset architectural state with K:PC `00:0000`, no
IRQ, mailbox, DMA, or character conversion.

Validation completed with 460 unit tests passing, along with `make validate`,
`make demo`, all four SAME-VDP goldens, Poppy production lint, and
`git diff --check`.  M19 and M20 pass their fresh-emulator playback/restart
gates; M21 retains its accepted mechanical-pass/human-timbre-pending result;
M22 passes its live hook-8 transition gate.  The Phase 6J historical artifact
still produces its exact four-tick movement and `$02D9` blocker evidence.  The
Phase 6G-B mask hashes remain
`2237a3ae1c7c292e61908c9b65b0867620bea331bc4b751a79810b1ed2a8db74`
and `27bfa2acbc93bdd6e84aab3e6a9ddc395bd9e5c237a9a0d9fdfc1c7d701c1984`.
The M25A umbrella retains its exact missing-far-entry failure, while its
normal/depth/missing/outer validators pass directly.
