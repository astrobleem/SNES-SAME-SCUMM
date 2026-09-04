# Phase 6I — Authentic global script 83

## Result

Phase 6I delivers the complete authentic global script 83 through the existing
profile-selected global-script directory.  The fresh target trace resolves and
starts it from room 49 LSCR 211 at `$0298`, executes its authentic path
immediately, retires the child normally, restores LSCR 211 at `$029B`, and
continues to the next unsupported opcode at `$02A0`.  No dense-variable or video
code changed.

## Provenance

| Item | Value |
|---|---|
| Fate demo archive SHA-256 | `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798` |
| `PLAYFATE.000` SHA-256 | `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9` |
| `PLAYFATE.001` SHA-256 | `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240` |
| `numGlobalScripts` | 200 |
| Script | 83 (`83 < 200`, therefore `WIO_GLOBAL`) |
| DSCR directory entry | room 68, offset `$9FF4` (40948) |
| Owning member | `FATEDEMO/PLAYFATE.001` |
| Encrypted/decoded chunk offset | `$085922` (547106) |
| Decoded payload offset | `$08592A` (547114) |
| Chunk / payload length | 53 / 45 bytes |
| Payload SHA-256 | `598a8bed2a2870fba2dfe1622572608f2877fb1a9e1c172f2dd0ecd3f6f2e538` |
| Generated program identity | `$EE` |

The generated entry also records the `DSCR` tag, namespace, source member,
directory coordinates, both source offsets, chunk length, payload length and
payload hash.  Bounds and mapped-ROM placement are validated before the generic
resolver can allocate a slot.

## Complete payload and disassembly

Payload:

```text
A8 14 80 27 00 1A 14 80 00 00 9A B1 00 B0 00
1A B0 00 00 00 7A 32 07 FF 9A 20 00 C0 01 28
00 40 06 00 0A 13 01 02 00 FF 2C 01 2C 03 A0
```

| PC | Bytes | Canonical decode | Production status |
|---:|---|---|---|
| `$0000` | `A8 14 80 27 00` | `ifNotEqualZero(Bit[20])`, false branch to `$002C` | supported; authentic branch |
| `$0005` | `1A 14 80 00 00` | `move Bit[20], $0000` | supported; not reached authentically |
| `$000A` | `9A B1 00 B0 00` | `move Var[177], Var[176]` | supported; not reached |
| `$000F` | `1A B0 00 00 00` | `move Var[176], $0000` | supported; not reached |
| `$0014` | `7A 32 07 FF` | `verbOps(50): SO_VERB_OFF; end` | supported; not reached |
| `$0018` | `9A 20 00 C0 01` | `move Var[32], Var[448]` | supported; not reached |
| `$001D` | `28 00 40 06 00` | `ifEqualZero(Local[0])`, false branch to `$0028` | supported; not reached |
| `$0022` | `0A 13 01 02 00 FF` | `startScript(19, [$0002])` | resource deliberately not added; unreachable in authentic state |
| `$0028` | `2C 01` | `cursorCommand(SO_CURSOR_ON)` | supported; not reached |
| `$002A` | `2C 03` | `cursorCommand(SO_USERPUT_ON)` | supported; not reached |
| `$002C` | `A0` | `stopObjectCode` | supported; authentic termination |

The only reachable authentic path is `$0000 -> $002C -> $002D`; consequently
script 19 is not part of the Phase 6I profile closure.

## Authentic nested execution

LSCR 211 executes `0A 53 FF` at `$0298`: direct global script 83, zero
word arguments, nonrecursive, non-freeze-resistant.  Decoding naturally saves
the parent continuation `$029B`.

The target trace records `(requested script, parent slot, allocated slot,
parent status) = (83, 3, 1, 2)`.  Slot 1 is initialized as `WIO_GLOBAL`, program
`$EE`, PC `$0000`, canonical default cycle, and all 32 local words zero.  The
same scheduler pass records program `$EE` at PC `$0000` with opcode `$A8`, then
PC `$002C` with opcode `$A0`.  The child finishes with stopped status and the
parent program `$DD` resumes at `$029B`; no lifecycle special case or direct
program selector is involved.

After restoration, LSCR 211 executes the supported instruction beginning at
`$029B` and stops at the next genuine blocker:

```text
029B: 40 01 02 00 FF
02A0: 9E 01 00 1C 00 26 00
02A7: AE 81 01 00 C0 7C 00 00 52 A8 00 00 29 00 4C ...
```

The blocker is opcode `$9E` at `$02A0`, the variable-actor form of the v5
`walkActorTo` family (`actor = Var[1]`, direct X `$001C`, direct Y `$0026`).
The target reports `SCUMM_ERR_OPCODE`; Phase 6I does not implement it.

## Artifacts and regressions

Two clean builds of each artifact were byte-identical:

| Variant | SHA-256 |
|---|---|
| LoROM + legacy | `f453462933fef6b7278627b9c8c7a49b997c4b27d53ab118f2e0d050256c7dcc` |
| SA-1 + legacy | `5e229e6903cab44d6ab2ca3e7b2b44d076c75ecefeaaec84da240702c553eff2` |
| SA-1 + Mode-3/BG2 | `f598f6b5d20b4a480151fbef39e31e5298f08fc86654c69fddb49d780d8d0cb6` |

All three fresh-emulator runs agree on script identity, global namespace,
zero locals, normal retirement, Var[119/120/121] = `$0000/$FFFF/$0000`, and
the `$02A0` blocker.  Both SA-1 runs retain architectural state with K:PC
`00:0000`, no IRQ, mailbox, DMA, or character-conversion activity.

The Phase 6G-B regression retained mask hashes
`2237a3ae1c7c292e61908c9b65b0867620bea331bc4b751a79810b1ed2a8db74`
and `27bfa2acbc93bdd6e84aab3e6a9ddc395bd9e5c237a9a0d9fdfc1c7d701c1984`.
The segmented lifecycle retained one continuation, cleared `VAR_HAVE_MSG`, and
committed the hidden overlay generation.

The full Python suite passes 452 tests; `make test`, `make validate`, `make
demo`, SAME-VDP (four golden cases), Poppy lint, and `git diff --check` pass.
The historical `make m25a-validator` umbrella still fails at
`runtime/snes/services/storage.pasm:36:9` with undefined symbol
`ScummV5_M23A_ValidateRecord_FarEntry`, exactly the accepted infrastructure
signature.  Its fixture-level nested-script tests (normal, depth-24, missing,
outer, scheduler, and startObject coverage) pass in the full unit suite.
