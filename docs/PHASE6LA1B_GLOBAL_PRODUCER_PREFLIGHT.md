# Phase 6L-A1B global-producer preflight

Phase 6L-A1B stops before production modification with mandatory
classification **C — missing global-script dependency before the producer
call**.

The authoritative boot trace reaches `startScript(75, [])` in global script 1
at `+$050A`, long before the requested script-4 producer at `+$15A2`.  Global
script 75 is not in the profile-selected generated directory, and this phase
explicitly forbids adding another discovered global dependency automatically.

## Source identities

- archive SHA-256:
  `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`
- `PLAYFATE.000` SHA-256:
  `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9`
- `PLAYFATE.001` SHA-256:
  `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240`

All three scripts below are entries in the authoritative DSCR directory and
are WIO_GLOBAL because their IDs are below `numGlobalScripts == 200`.

| script | DSCR room/offset | decoded chunk | decoded payload | chunk bytes | payload bytes | payload SHA-256 |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 68 / 19384 | 525542 | 525550 | 13184 | 13176 | `fb89246b501a4d9a32cb81331d4b4d43258e4cf1b72b3ffe538d389c55cdd7c7` |
| 4 | 68 / 34166 | 540324 | 540332 | 983 | 975 | `e51c4db1639857e919e7f71cac612be4c2b2ed2265d60ac3f86f200e3447f765` |
| 75 | 68 / 40277 | 546435 | 546443 | 54 | 46 | `0f304d268977db1ad8e94df7dc10fe01a866c1b8a70d7f015b7cd16ebad48455` |

Scripts 1, 4, and 75 are source-readable today.  None has a current generated
program identity or ROM placement in the selected target directory.  The
selected generated globals remain 2, 14, 83, 144, 145, and 151.

## Canonical boot producer and harness audit

The Fate profile already declares `boot_script_number: 1`.  The generic host
boot implementation resolves `script.1`, creates one ordinary global slot,
zero-initializes its locals, and begins at PC `$0000`.  A fresh authoritative
host run therefore starts with exactly:

```
slot 0: script.1, WIO_GLOBAL, PC $0000, active
```

The first tick executes script 1 from PC zero through ordinary scheduler and
nested-script machinery.  Script 1 is not restarted on room installation.

The current M23C/M25-derived room harness deliberately disables this canonical
slot with:

```python
engine.state.scripts[0].active = False
```

It then installs a pre-Thera/room checkpoint.  Consequently that harness begins
after—and intentionally bypasses—the title-wide global-main lifecycle.  It
cannot be converted into proof of the producer chain by starting script 1 late
inside room 49.

## First active-path dependency

During canonical frame 1, after boot initialization, global script 1 naturally
reaches:

```
050A  0A 4B FF   startScript(75, [])
050D              parent continuation
```

Decode:

- opcode family: canonical `startScript`
- script operand: direct byte `$4B` = 75
- freeze-resistant: false
- recursive: false
- word-varargs: empty, terminated by `$FF`
- parent continuation: `$050D`

The host resolves global script 75, enters it immediately at PC `$0000`, and
the child reaches a canonical delayed/yielded state at PC `$0007` with delay
226.  Only after the immediate child returns does script 1 continue from
`$050D`.  Thus script 75 is an executed lifecycle dependency, not an
unreachable static reference.

The profile-selected target has no generated entry for script 75.  If scripts
1 and 4 alone were added, target execution would fail closed at `$050A` before
the requested producer call.  Adding script 75 is outside this gate.

## Requested later producer evidence

The source bytes remain verified but are not reached by an acceptance run:

```
global script 1 +15A2:
    6A 04 35 00 1A EE 00 03 00 25 14 00 01 25 A6 03 ...
    startScript(4, <non-empty authentic word-varargs>)

global script 4 +0222:
    8A A4 00 FF
    startScript(Var[164], [])
```

At the second call, dense `Var[164]` would be read from byte offset `$0148`,
physical address `$7E0948`; room-49 ENCD has established value 204.  The
generic namespace rule would therefore resolve room-local index 4.  No target
execution claim is made because script 75 prevents reaching this boundary with
the authorized generated closure.

## Stop disposition

- Classification: **C**.
- First missing dependency: global script 75 at script 1 `+$050A`.
- No generated resources, program IDs, boot scheduling, or runtime code were
  changed.
- No script 1, 4, 204, or 208 slot was directly allocated by a validator.
- LSCR 204 and LSCR 208 remain registered but unscheduled.
- No sound-82 state or command was fabricated.
- The Phase 6K far `$4C` route remains unchanged.
- The preliminary load-room patch remains parked at
  `docs/attachments/PHASE6L_PRELIMINARY_LOAD_ROOM_WITH_EGO.patch` with SHA-256
  `941bd2c490968afc7b557456e51ead0472ff9e2f274ac0fe147f28a56038a28c`.
- No ROM artifacts or regression matrix were run because the focused gate
  cannot pass under the explicitly required classification-C stop rule.
