# Phase 6H-A — global script 14 and outer `startScript`

## Source and generated resource

The source archive is `/home/chad/fatedemo-box.zip`, SHA-256
`558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`.
Its encrypted members are:

- `FATEDEMO/PLAYFATE.000`: 12,030 bytes,
  `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9`.
- `FATEDEMO/PLAYFATE.001`: 929,852 bytes,
  `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240`.

The authoritative DSCR directory contains 200 global scripts.  Entry 14
selects room/LFLF 68 and LFLF-relative offset 36,094 (`$8CFE`).  The LFLF
header is at decoded data offset 506,150; the `SCRP` header is at decoded and
encrypted physical offset 542,252 (`$8462C`), and its payload begins at
542,260 (`$84634`).  The chunk is 266 bytes; its complete bytecode payload is
258 bytes and hashes to
`ee6b379d25e4ace9772673b05bb40d2f428dd2c0bd9142a8f53d85005fb4e371`.
Script 14 is therefore `WIO_GLOBAL`, not an LSCR/object/fixture program.

Payload bytes:

```text
486c00a50311002701206f72696368616c63756d00180800270120ff066c0000
486d00a50311002701216f72696368616c63756d00180800270121ff066d0000
a86c0045009d6c00018d00ff1e007a6402ff056b0020ff066c0020ff056e0020
ff066d0000837600ff181b007a6402ff056b0020ff07200020ff056e0020ff07
210000837600ff187700c86b006f005a000804004f003e00a81f822400380400
e2001d00040400e70016007a64021000ff7a6402466c6f617400837600ff1840
007a64021000ff7a640257616c6b00837600ff1812007a64021000ff7a64024c
6f6f6b00837600ff1816007a6402ff056b0020ff056e0020ff07210000837600
ffa0
```

The profile-owned `phase6ha` closure is `[2,14,144,145,151]`.  The generic
cooker emits all five complete resources; the generic generated directory
assigns script 14 program identity `$ED`.  No authentic payload is committed.
The generated execution gate identifies the generated program, not script 14
inside the interpreter, and holds after that child returns so the acceptance
ROM remains immediately before Var[120].

## Complete disassembly

```text
0000  48 6C00 A503 1100     unless Var[108] == 933 goto 0018
0007  27 01 20 ... 00       stringOps load string 32, "orichalcum"
0015  18 0800               goto 0020
0018  27 01 20 FF066C0000   stringOps load string 32, name(Var[108])
0020  48 6D00 A503 1100     unless Var[109] == 933 goto 0038
0027  27 01 21 ... 00       stringOps load string 33, "orichalcum"
0035  18 0800               goto 0040
0038  27 01 21 FF066D0000   stringOps load string 33, name(Var[109])
0040  A8 6C00 4500          unless Var[108] != 0 goto 008A
0045  9D 6C00 01 8D00 FF 1E00  ifClassOfIs Var[108], class 141; goto 006C
004E  7A 6402 ... 00        verbOps verb 100: composed object names, color Var[118]
0069  18 1B00               goto 0087
006C  7A 6402 ... 00        verbOps verb 100: composed string slots, color Var[118]
0087  18 7700               goto 0101
008A  C8 6B00 6F00 5A00    unless Var[107] == Var[111] goto 00EB
0091  08 0400 4F00 3E00    unless Var[4] != 79 goto 00D6
0098  A8 1F82 2400          unless Bit[543] != 0 goto 00C1
009D  38 0400 E200 1D00    unless Var[4] <= 226 goto 00C1
00A4  04 0400 E700 1600    unless Var[4] >= 231 goto 00C1
00AB  7A 6402 1000 FF       verbOps verb 100, name control 10
00B1  7A 6402 "Float" ...  verbOps verb 100, name "Float", color Var[118]
00BE  18 4000               goto 0101
00C1  7A 6402 1000 FF       verbOps verb 100, name control 10
00C7  7A 6402 "Walk" ...   verbOps verb 100, name "Walk", color Var[118]
00D3  18 1200               goto 00E8
00D6  7A 6402 1000 FF       verbOps verb 100, name control 10
00DC  7A 6402 "Look" ...   verbOps verb 100, name "Look", color Var[118]
00E8  18 1600               goto 0101
00EB  7A 6402 ... 00        verbOps verb 100: verb/name composition, color Var[118]
0101  A0                    stopObjectCode
```

There are no yields, delays, starts, chains, local/bit writes, or unsupported
instructions on the authentic path.  All paths terminate at `$0101`; the
retired slot records terminal PC `$0102`.

## Lifecycle evidence

Before `$0A`, parent slot 2 is global script 2, program `$EC`, PC `$0468`.
`0A 0E FF` decodes a direct script byte 14, no arguments, nonrecursive and
non-freeze-resistant, advancing the saved parent PC to `$046B`.  The ordinary
allocator chooses slot 1, clears all 32 locals, assigns global program `$ED`,
sets PC `$0000`, marks `didexec`, and enters it immediately through the shared
nested-context stack.  Script 14 reaches `$A0` and retires at PC `$0102`.
The parent identity check restores slot 2/program `$EC`/PC `$046B`; the
profile-generated milestone gate then yields and sets the existing lifecycle
hold.  At the final gate Var[120] is `$0000`.

The former rejection had two ordered causes: an outer invocation with return
mode zero was rejected by a false room-lifecycle precondition (`$A0` site);
after bypassing that check in the accepted M25 context, lookup failed at `$A1`
because script 14 was not in the generated directory.  `startScript` now uses
the scheduler-owned parent slot as its context and the generated global lookup
provides the resource.  No room phase is fabricated.

## Artifacts

- LoROM + legacy: `05869578eeb495915cfa97ca94bd3200e5d5d02161c6703d59f2fd4315329a9b`
- SA-1 + legacy: `d764e5f839adcd48ea32124b3b3f539739892dbd351e515482195c4868b87ea1`
- SA-1 + Mode 3 + BG2: `cfb222a794498a613d2ab1c57458729fcfb128b28a38dc77563f1dbd4c3d4f84`

Each was built twice byte-identically.  Fresh-emulator evidence for all three
records identical parent/child PCs, programs, status, Var[120], and no VM
error.  Both SA-1 variants preserve K:PC `00:0000` and all architectural
registers; no SA-1 IRQ, DMA, mailbox, or character conversion is used.

The deferred dense-table design remains in
`docs/PHASE6H_GLOBAL_VARIABLE_PREFLIGHT.md`.

## Validation status

- Focused profile/resource/source traps: 3/3 pass.
- Three fresh-emulator Phase 6H-A gates: pass, sequentially.
- All three artifacts rebuilt twice: byte-identical.
- Phase 6G-B regression: exact 76-pixel/six-cell and
  15-pixel/one-cell masks; hidden layer has zero pixels; SA-1 unchanged.
- Full Python/unit suite: 448 tests pass.
- `make validate`, `make demo`, S3, Poppy lint, and `git diff --check`: pass.
- The aggregate `make m25a-validator` target does not complete in this
  worktree: its normal build expects the M24RB far room-validator symbol while
  the M25A generator configuration emits the local validator; attempting to
  emit both then makes the depth fixture overflow bank 0.  This is recorded as
  an existing regression-infrastructure/generated-bank issue, not repaired in
  Phase 6H-A.  Consequently, the requested *entire* historical Nexen matrix is
  not claimed green here even though the focused outer-context gate passes.
