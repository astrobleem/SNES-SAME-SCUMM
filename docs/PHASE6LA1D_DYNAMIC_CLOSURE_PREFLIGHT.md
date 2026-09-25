# Phase 6L-A1D dynamic-closure preflight

## Classification

Phase A classifies the requested boot-to-LSCR208 run as **C — additional room
or input dependency** and stops before production resource changes.

Canonical boot does not lead directly to the accepted room-49 object-596
interaction.  With no additional input, the authoritative engine initializes
the title/global control scripts, changes from room 0 to room 68, and settles
there.  The accepted M25 semantic action is only defined after a synthetic
room-49 installation and pre-Thera state fixture.  Reaching that checkpoint
from canonical boot requires at least a title/game-start input and a room
transition.  Both are excluded by Phase 6L-A1D.

Consequently there is no valid deterministic trace, using the authorized input
schedule, from boot script 1 to LSCR 208.  A closure manifest with terminal
`room.49/LSCR.208:$0000` cannot honestly be frozen.

## Canonical trace start

- profile: `indy4-fate-demo`, `dos-vga-en-1992-07-09`
- boot contract: global script 1
- initial slot: slot 0, WIO_GLOBAL script 1, PC `$0000`, active
- initial room: 0
- initial previous-room value: 0
- initial RNG state: 44257 / `$ACE1`
- initial ordinary-variable backing: 2048 zero host words; SHA-256 of its
  little-endian bytes:
  `ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7`
- initial 4096 bit-variable bytes SHA-256:
  `ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7`
- initial sentence queue: empty
- initial logical music/SFX ownership: none

The host's larger internal zero list does not change the Fate profile's target
contract of 800 ordinary globals.

## Executed boot closure prefix

The following global resources are actually requested during canonical logical
tick 1 before the engine reaches its title/control wait.  They are chronological
execution evidence, not a Phase-B manifest:

| order | caller and PC | callee | args | flags | immediate outcome |
|---:|---|---:|---|---|---|
| 1 | boot lifecycle | 1 | boot locals | profile boot | begins at `$0000` |
| 2 | script 1 `$050A` | 75 | `[]` | nonrecursive, not freeze-resistant | enters at `$0000`; delays at `$0007` |
| 3 | script 1 `$060D` | 18 | `[]` | nonrecursive, not freeze-resistant | enters at `$0000` |
| 4 | script 18 `$0167` | 132 | `[]` | nonrecursive, not freeze-resistant | enters and terminates normally |
| 5 | script 1 `$3352` | 74 | `[]` | nonrecursive, not freeze-resistant | enters at `$0000` |
| 6 | script 74 `$0000` cutscene lifecycle | 20 | `[]` | ordinary global child | enters at `$0000` |
| 7 | script 20 `$0079` | 13 | `[]` | nonrecursive, not freeze-resistant | enters and terminates normally |
| 8 | script 20 `$007C` | 14 | `[]` | nonrecursive, not freeze-resistant | enters and terminates normally |

All calls occur in room 0 during scheduler pass/logical tick 1.  The complete
source identities for the executed prefix are:

| ID | payload bytes | SHA-256 |
|---:|---:|---|
| 1 | 13176 | `fb89246b501a4d9a32cb81331d4b4d43258e4cf1b72b3ffe538d389c55cdd7c7` |
| 75 | 46 | `0f304d268977db1ad8e94df7dc10fe01a866c1b8a70d7f015b7cd16ebad48455` |
| 18 | 484 | `f4f200aaf3e67445e4dbe6b643862b74d4395158ac7833c39f8713b9d7362767` |
| 132 | 138 | `1440b1832cb2541512e7073b4e95d4c79d0b3b16bd3c37df6bbbea52d897aadf` |
| 74 | 140 | `4362aa0993d9e4a1218f1d13ca06c1802c09ebdaa89c5727cd85b8353cfdb745` |
| 20 | 146 | `926e6b5a69cc6b7dcf8f07b648d9d864d96b9e616d832006d1e444a9fda0c0c3` |
| 13 | 56 | `434e7ae6a6cd10d2a4c6178372ede2bc273d2880348868abfcb8cbab91e8d812` |
| 14 | 258 | `ee6b379d25e4ace9772673b05bb40d2f428dd2c0bd9142a8f53d85005fb4e371` |

This is a dynamic prefix only.  Script 4 is not requested before the input
boundary, and LSCR 204/208 are not requested.

## RNG and delay/freeze evidence

Script 75 executes the previously proven sequence:

```
0000  16 BA 01 FF  getRandomNumber(255) -> Var[442] = 226
0004  2B BA 01     delayVariable(Var[442])
0007               saved continuation
```

Script 1 resumes at `$050D` in the same scheduler pass.  Script 75 is later
frozen during logical tick 1.  At the settled boundary it remains active at
PC `$0007`, delay 226, freeze count 1; no decrement or resume occurs.

## Script 18 provenance and active outcome

Script 18 is DSCR room 68, directory offset 36648, decoded chunk 542806,
decoded payload 542814, chunk length 492, payload length 484, SHA-256
`f4f200aaf3e67445e4dbe6b643862b74d4395158ac7833c39f8713b9d7362767`.

Its executed path performs cursor/verb initialization, bounded variable loops,
starts global script 132 at `$0167`, installs the remaining verb/string state,
sets its final variables, executes cursor command at `$01E0`, and terminates at
`$01E3 -> $01E4`.  Script 132 completes immediately before script 18 resumes.
No unsupported opcode occurs on this executed path.

A complete static disassembly is not used as closure input because Phase A
classifies at the interaction-schedule boundary; the dynamic trace includes
only executed instructions as required by the closure definition.

## Interaction incompatibility

After 300 input-free logical ticks the authoritative state is:

- current room: 68;
- script 1: active at PC 13142 / `$3356`, frozen, yielded;
- script 75: active at `$0007`, delay 226, freeze count 1;
- script 74: active at `$006F`, delayed;
- no queued sentence for object 596;
- no room-49 local-script ownership.

The accepted M25 producer injects exactly one semantic sentence only after all
of these fixture conditions hold:

- active room 49 and active room record 0;
- frame/lifecycle ready;
- actor 1 idle at `(399,116)`, walkbox 11;
- sentence queue empty;
- verb 10, object A 596, object B 0.

Those conditions do not arise from the input-free canonical boot trace.  The
existing M25 harness obtains them by directly installing room 49 and applying a
named pre-Thera state fixture after disabling boot slot 0.  Issuing the same
sentence in room 68 would not be the accepted interaction.  Moving from the
canonical title state to room 49 requires an additional title/game-start input
and its resulting room transition, so Phase-A classification C is mandatory.

## Capacity and stop disposition

No program-ID or ROM-capacity assignment is made because classification C
prevents freezing a terminal closure and entering Phase B.  Capacity is not the
blocking mechanism.

- no global resource set changed;
- no closure manifest was emitted for production consumption;
- no ROM was assembled;
- no direct slot allocation, PC forcing, or debugger write was used;
- no sound-82 state or opcode was implemented;
- no loadRoomWithEgo or room-63 path was enabled;
- the Phase 6K `$4C` repair remains intact;
- the preliminary transition patch remains parked with SHA-256
  `941bd2c490968afc7b557456e51ead0472ff9e2f274ac0fe147f28a56038a28c`.
