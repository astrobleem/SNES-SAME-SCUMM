# Phase 6L-A1 producer-chain preflight

Phase 6L-A1 stops in mandatory preflight with classification **G — an
unsupported production prerequisite occurs before the authentic script-204
start**.  No production code or generated artifact is changed by this
adjudication.

## Source identities

- Fate demo archive SHA-256:
  `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`
- `PLAYFATE.000` SHA-256:
  `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9`
- `PLAYFATE.001` SHA-256:
  `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240`
- cooked room-49 record SHA-256:
  `7f87742246295b430ead21b50872f046d005620d5f5b1f3a24126b8b22881328`

## The reported `$007D` boundary

The owner is room-49 ENCD.  Its final sequence is:

```
0075  1A A4 00 CC 00  move Var[164], 204
007A  0A C8 FF        startScript(200, [])
007D  00              stopObjectCode
```

Thus `$007D` is not the script-204 call.  It is the continuation after
`startScript(200, [])` and the address of ENCD's terminating opcode.  A current
natural host run executes `$007A -> $007D`, starts LSCR 200, terminates ENCD,
and does not raise `SCUMM_ERR_SCRIPT`.  The old `$0B` report was produced before
the accepted generic outer/local `startScript` repairs and is not reproducible
in the current tree.  At this checkpoint dense `Var[164]` changes from zero to
204; its target byte offset is `$0148` and its physical address is `$7E0948`.

## Exact source-owned producer chain

An exhaustive scan of all 200 authoritative global scripts and all room-49
local scripts finds no direct call to LSCR 204 in ENCD or LSCR 200.  The only
consumer of `Var[164]` as a script number is global script 4:

```
global script 4 +0222  8A A4 00 FF
                           startScript(Var[164], [])
```

At that instruction `Var[164] == 204`, so the generic resolver classifies the
result as room-local index 4.  Global script 4 is itself started by global
script 1:

```
global script 1 +15A2  6A 04 35 00 ... FF
                           startScript(4, <word varargs>)
```

Global scripts 1 and 4 are authoritative source resources but are absent from
the current profile-selected generated global-script directory.  The selected
directory contains 2, 14, 83, 144, 145, and 151.  Delivering and executing
global scripts 1 and 4 is outside Phase 6L-A1's authorization to add LSCR 204;
directly allocating LSCR 204 would bypass the source-owned producer.

Source provenance for the missing prerequisite resources:

| Script | DSCR room/offset | decoded chunk/payload | payload bytes | SHA-256 |
|---:|---:|---:|---:|---|
| 1 | 68 / 19384 | 525542 / 525550 | 13176 | `fb89246b501a4d9a32cb81331d4b4d43258e4cf1b72b3ffe538d389c55cdd7c7` |
| 4 | 68 / 34166 | 540324 / 540332 | 975 | `e51c4db1639857e919e7f71cac612be4c2b2ed2265d60ac3f86f200e3447f765` |

## Room-49 LSCR inventory

All entries below already exist in the cooked sparse room-local directory and
resolve by exact source ID.  Registration does not allocate or schedule them.

| ID | local index | decoded file offset | ROOM-relative offset | bytes | payload SHA-256 |
|---:|---:|---:|---:|---:|---|
| 200 | 0 | 362375 | 60584 | 460 | `dc34f2d549455fbd6ee30eb057470b39e97e4544ff3cbe49d94424158e3cbc6c` |
| 201 | 1 | 362844 | 61053 | 252 | `920a5a11a61c1eac8f06ad13ddf35698f7e8fa8863052d8f77a49b3ce429e85d` |
| 202 | 2 | 363105 | 61314 | 208 | `a2708bc44847af25775b5684781b83ccb3cf8e059872e34453984af4bedee043` |
| 203 | 3 | 363322 | 61531 | 167 | `6d39e0c9d5a2a313532fb2054f4057482f7d9554ca860d24f91feed337d39f4e` |
| 204 | 4 | 363498 | 61707 | 40 | `cedb2ca89b86400d2340bd8f6f40ee718bf1af00019456acd0eebdcca9937666` |
| 205 | 5 | 363547 | 61756 | 4393 | `5de222466ebf493f86e74577e27ffc096c8db843d80f05868f84c42b7dac670d` |
| 206 | 6 | 367949 | 66158 | 2894 | `c8c0819915db47ad35e9aa06ec8d0dd05f62a5e3f25b3c6b4b0c7b2f544bd59a` |
| 207 | 7 | 370852 | 69061 | 1196 | `05cdf24ef121d6ce34bc60b2f60a5819cfc4489cc856a7ea8a556219c64489e2` |
| 208 | 8 | 372057 | 70266 | 7441 | `2c84fa24e6e6c37c353cc08cfb2d94b78cc2a27be39cdc161b1131f480cd7876` |
| 209 | 9 | 379507 | 77716 | 147 | `48f4b658cd612927cca8e22759d4811cd29345eb51525c05810f0a423e3e5735` |
| 210 | 10 | 379663 | 77872 | 252 | `c7ef5ea54153beaeb1bbb831ff667e8b3b87a76b30b877f1a14be32ad1df8134` |
| 211 | 11 | 379924 | 78133 | 761 | `56fcd3dcd49f671ac7f86fbea741bb6f5a187604ac64fa382b1576bf70cd1d23` |
| 212 | 12 | 380694 | 78903 | 385 | `e49b26e3e4be3213d32830ddf346b7307781ddb7a2a48b4e2c9a02f1552bc171` |
| 213 | 13 | 381088 | 79297 | 698 | `7ff9b40debde133cf461ef55f965e2a1e5dc74456aacd94bfaf7088930854b7c` |
| 214 | 14 | 381795 | 80004 | 29 | `a8fb780d4ecdcca2b7651cb61d05514ccd6e63505614995808955898fbd9abed` |
| 215 | 15 | 381833 | 80042 | 75 | `2035abc8b8d67229a60f77dfc11b03a87979d93d1ad108cfdfbaf079e519d227` |
| 216 | 16 | 381917 | 80126 | 41 | `588c3a457f799681c616bce088d980847ffb77823e6a65b29511a67bb06b0f60` |
| 217 | 17 | 381967 | 80176 | 175 | `cfbeef8866ff3b45b7ff0cc89a18ced95539693d61218d493a6e57a60ccdc769` |

## Complete LSCR 204 disassembly

LSCR 204 is WIO_LOCAL, local index 4, and has a complete 40-byte payload.

```
0000  48 B0 00 02 00 06 00  ifEqual(Var[176], 2), relative branch
0007  0A CE FF              startScript(206, [])
000A  18 1A 00              jumpRelative +$001A
000D  48 B0 00 0A 00 06 00  ifEqual(Var[176], 10), relative branch
0014  0A CD FF              startScript(205, [])
0017  18 0D 00              jumpRelative +$000D
001A  48 B0 00 0B 00 06 00  ifEqual(Var[176], 11), relative branch
0021  0A D0 FF              startScript(208, [])
0024  18 00 00              jumpRelative +$0000
0027  A0                    stopObjectCode
```

The direct LSCR-208 call is therefore source-proven at `+$0021`; its decoded
parent continuation is `+$0024`, it is nonrecursive and non-freeze-resistant,
and its word-vararg list is empty.  It is not reached in an authentic run
because the global-script 1/4 producer prerequisites are not delivered.

## Stop disposition

- Classification: **G**.
- No LSCR 204 or LSCR 208 slot was directly allocated.
- No sound-82 ownership, command, trigger, or queue state was fabricated.
- No load-room opcode or room-63 path was enabled.
- The preliminary transition patch remains parked at
  `docs/attachments/PHASE6L_PRELIMINARY_LOAD_ROOM_WITH_EGO.patch`, SHA-256
  `941bd2c490968afc7b557456e51ead0472ff9e2f274ac0fe147f28a56038a28c`.
- No new ROMs were produced because the focused gate cannot pass without a
  separately authorized global-script 1/4 delivery milestone.
