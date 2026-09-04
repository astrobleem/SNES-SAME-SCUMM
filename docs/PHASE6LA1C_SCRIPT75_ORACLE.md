# Phase 6L-A1C script-75 oracle and chronological stop

Phase 6L-A1C stops during the focused gate before production modification.
The first newly encountered missing dependency is **global script 18**, called
by global script 1 at `+$060D`, after script 75 enters its authentic delay but
before script 1 reaches the desired `+$15A2` call to script 4.

The phase authorizes generated globals 1, 4, and 75 only and explicitly
requires an immediate stop when another missing global is encountered.

## Provenance

- Fate archive SHA-256:
  `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`
- `PLAYFATE.000` SHA-256:
  `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9`
- `PLAYFATE.001` SHA-256:
  `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240`

Global script 75 is DSCR entry 75, directory room 68, directory offset
40277.  Its decoded chunk begins at 546435, its decoded payload begins at
546443, its chunk length is 54 bytes, and its complete payload is 46 bytes.
Its payload SHA-256 is
`0f304d268977db1ad8e94df7dc10fe01a866c1b8a70d7f015b7cd16ebad48455`.
Because 75 is below the source-owned `numGlobalScripts == 200`, it is
WIO_GLOBAL.

## Complete script-75 disassembly

All 46 payload bytes are accounted for below.  Every opcode shown is already
implemented by the current host/target interpreter.

```
0000  16 BA 01 FF        getRandomNumber -> Var[442], maximum 255
0004  2B BA 01           delayVariable(Var[442])
0007  16 00 40 01        getRandomNumber -> Local[0], maximum 1
000B  28 00 40 1A 00     if Local[0] == 0 fall through; else branch $002A
0010  80                 breakHere
0011  F8 42 01 41 01
      12 00              if Var[321] > Var[322] fall through; else -> $002A
0018  80                 breakHere
0019  5A 42 01 1E 00     add Var[322], 30
001E  C4 42 01 41 01
      05 00              if Var[321] < Var[322] fall through; else -> $002A
0025  9A 42 01 41 01     move Var[322], Var[321]
002A  18 D3 FF           jumpRelative -45 -> $0000
002D  A0                 stopObjectCode
```

The two comparison forms use the existing v5 false-branch convention.  The
script is a randomized delayed loop; `$002D` is its bounded normal termination
path when reached by the branch structure.

Variables used:

- global Var[442]: randomized delay value;
- global Var[322] and Var[321]: loop comparison/update state;
- Local[0]: randomized binary branch selector.

The script starts no scripts and accesses no room-local resources.

## Exact delay lifecycle

The formerly ambiguous `$0007` description is resolved as follows:

- delay opcode PC: `$0004`;
- delay bytes: `2B BA 01`;
- operand: variable reference `$01BA`, global Var[442];
- value in the authoritative deterministic boot run: 226;
- decoded/post-opcode PC: `$0007`;
- saved slot PC: `$0007`;
- child state after the opcode: active, yielded, delay 226;
- script-1 parent continuation: `$050D` in the same scheduler pass.

The value 226 is not encoded as a literal.  The preceding instruction at
`$0000` deterministically produces it from `getRandomNumber(255)` and stores it
in Var[442].

The current scheduler's delay unit is one SCUMM logical scheduler update.  A
delayed, unfrozen slot decrements once when visited in a later scheduler pass;
the pass which creates the delay does not decrement it.  A pass that changes
delay 1 to zero does not also execute the script; execution resumes on its next
eligible pass.

In this exact canonical boot trace there is no first decrement or resume tick
yet: later operations in global script 1 freeze script 75 during logical tick
1.  At the tick boundary script 75 is at PC `$0007`, delay 226, freeze count 1.
Subsequent observed ticks retain delay 226 because frozen scripts are neither
executed nor delay-decremented.  Claiming a tick-228 resume for this authentic
state would therefore be incorrect.

## Canonical boot and immediate child trace

The profile already owns `boot_script_number: 1`.  Generic host boot creates
one WIO_GLOBAL script-1 slot at PC `$0000` with zeroed locals.  During logical
tick 1 it naturally reaches:

```
script 1 +050A  0A 4B FF  startScript(75, [])
script 1 saved continuation: $050D
script 75 entry: $0000
script 75 $0000 -> $0004: Var[442] = 226
script 75 $0004 -> $0007: delayed/yielded, delay = 226
script 1 restored at $050D during the same pass
```

The child is not executed twice in that scheduler pass.  It remains an
independent global slot rather than blocking the script-1 parent.

The historical M23C/M25 room checkpoint deliberately disables this boot slot
with `engine.state.scripts[0].active = False`; it remains a synthetic
post-initialization harness and is not used as producer-lifecycle proof.

## Chronologically first new dependency

After restoration at `$050D`, script 1 continues naturally and reaches:

```
script 1 +060D  0A 12 FF  startScript(18, [])
script 1 continuation:     $0610
```

Decode:

- direct global script ID: 18;
- recursive flag: false (canonical nonrecursive start);
- freeze-resistant: false;
- word-vararg list: empty;
- immediate child entry required at script 18 PC `$0000`.

Global script 18 is source-valid but absent from the profile-selected generated
global directory.  It is encountered before script 1 `+$15A2`.  Adding it is
not authorized by Phase 6L-A1C.

For provenance, script 18 is DSCR room 68 / directory offset 36648, decoded
chunk 542806, decoded payload 542814, chunk length 492, and payload length 484.
Its payload SHA-256 is
`f4f200aaf3e67445e4dbe6b643862b74d4395158ac7833c39f8713b9d7362767`.
The call is an active-path instruction in logical tick 1, not an unreachable
static reference.

## Stop disposition

- No global scripts were added to generated profile data.
- No boot/runtime code changed.
- No validator directly allocated scripts 1, 4, 75, 204, or 208.
- No forced PC or extracted basic block was used.
- LSCR 204 and LSCR 208 remain registered but unscheduled.
- No sound-82 ownership or soundKludge behavior was introduced.
- The Phase 6K `$4C` far dispatch remains unchanged.
- The loadRoomWithEgo implementation remains parked and disabled.
- No ROMs or full regression matrix were produced because the focused gate
  stopped at the required first missing dependency.
