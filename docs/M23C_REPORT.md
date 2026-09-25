# M23C — authentic Fate room-63 ENCD and delayed hook 8

M23C is complete. The positive path executes authentic room 49 from PC zero,
establishes audible sound 80 on the hook-14 route, performs the normal room
lifecycle into authentic room 63, executes its complete reached ENCD prefix
from PC zero, and lets the already accepted M22 backend consume hook 8 at the
source-bound musical boundary. M24 was not started.

## Bound identities

| Artifact | SHA-256 |
|---|---|
| supplied `fatedemo-box.zip` | `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798` |
| `PLAYFATE.000` | `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9` |
| `PLAYFATE.001` | `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240` |
| original room 49 | `fbf234f2ffe3530ba365980abfae556636d83e5cada9bdc649c43d4cce7242f6` |
| executable cooked room 49 | `2904015371af15b616711013298b8e95874e55c5e9c45216fe09bf9a544a025f` |
| original room 63 | `94896a976d35531ab2ab5180a1a9f90387f34f4b12b0a8034bf1b3bbc901d390` |
| room-63 ENCD | `c40ef1e4b47d122e81ecf34df09c6dd83283d9ab8eb296410a0ee5c1433e3002` |
| executable cooked room 63 | `0eea0fac7d4feb7a9dd5060c731d96ccaf8c8c97e6803e01d01ebf63c9c55117` |
| global script 151 | `1c9518ce222115f2936acc40344317cd426d04100c71a1d71e33a9eac9e41b56` |
| named M23C state | `33fb74472d2baf3c0a8f838ed7eddef10871383984b751132b46342af652590d` |
| compiled music catalog | `38834324a87b59854da6f2c4ba635ebfaa3a03cb99d83e860fc27d45bd5acde2` |
| positive M23C ROM | `ca5ae06865ebca737bc1fd5bb7f2cadbc2c6bdc829f7b449431d91939ca3bbef` |
| class-control ROM | `da5b7a83ee063e82c4cf71e81e52821dfaa584ae36274dd566e5c8446069073f` |
| sound-82-control ROM | `210f2dad5733e20216b3a25619f19999d278b1f6386ed9692adfcd071015aaa9` |
| copyright-free `$1D` conformance ROM | `42a66f96678dbe57d823040cb7deee2e77fd32d94c96ad08be5ee2b96ebfa9ae` |

The selected profile file SHA-256 is
`d824c9b7aa06db8acbd383c07227d52aad16af23eaba6b1687686066b2551561`;
its game identity is
`37bc71eb005f72fbad00dd4fea9a0ab0245df4e9af50a3ffce04167c99156c2b`.

## Phase-A dependency closure

This is the exact positive room-63 parent-script path through the authentic
flush. The authoritative semantic references are the local accepted host
interpreter and `/home/chad/scummvm/engines/scumm/script_v5.cpp`; iMUSE command
16 is independently identified by local ScummVM
`engines/scumm/imuse/imuse.cpp` as `clear_queue()`.

| ENCD offset | Opcode | Semantic meaning and branch | State read | State written | Prior status / required change |
|---|---:|---|---|---|---|
| `+0x0000` | `$1D` | object 595 must have class 18; false jumps to `+0x004F` | object 595 classes | condition/PC | missing; canonical class-list opcode implemented |
| `+0x004F` | `$48` | `var[224] == 49`; false jumps to `+0x0072` | var 224 = 0 | PC | implemented |
| `+0x0072` | `$28` | `var[414] == 0`; true continues | var 414 = 0 | PC | implemented |
| `+0x0077` | `$AC` | `var[444] = 855 - 853` | constants | var 444 = 2 | implemented |
| `+0x0082` | `$AC` | select `random(0..var[444]) + 853` | var 444, saved RNG | result var 0 = 854 in this deterministic run | implemented |
| `+0x0090` | `$9A` | copy expression result to object selector | var 0 | var 414 = 854 | implemented |
| `+0x0095` | `$7C` | query sound 80 | authentic room-49 ownership | var 0 = 1 | implemented |
| `+0x0099` | `$A8` | nonzero test; sound 80 running continues | var 0 | PC | implemented |
| `+0x009E` | `$68` | query script 151 before starting it | scheduler | var 0 = 0 | bounded authentic query connection repaired |
| `+0x00A2` | `$28` | zero test; stopped script 151 continues | var 0 | PC | implemented |
| `+0x00A7` | `$4C` | queue `[0x010C,80,0,8]` | cue generation | soundKludge queue | existing hook semantic; authentic source now reaches it |
| `+0x00B5` | `$0A` | start global script 151 normally | script resource/slots | active slot for 151 | authentic resource registered and scheduler-connected |
| script 151 `+0x0000` | `$2E` | delay 7200 and yield at PC 4 | immediate delay | slot PC/delay/status | implemented; script remains active across flush |
| `+0x00B8` | `$7C` | query sound 82 | legitimate logical SFX ownership | var 0 = 1 | generic logical-SFX status connected on SNES |
| `+0x00BC` | `$A8` | nonzero test; running sound 82 falls through | var 0 | PC | implemented |
| `+0x00C1` | `$4C` | queue `[0x0110]`; iMUSE class 1 command 16 clears its deferred/trigger queue | command | soundKludge queue; clear count on flush | exact one-word form implemented; malformed forms reject |
| `+0x00C6` | `$4C` | authentic flush of hook 8 then `0x0110` | two queued commands | pending hook 8, empty SCUMM queue | existing ordered flush connected to authentic path |

The class-control path adds only class 18. It therefore executes the second
authentic `$1D` at `+0x0009`, where missing class 20 takes the source jump to
`+0x004F`; it then converges with the positive path. The sound-82 control
changes only ordinary sound ownership. Its query returns zero and the `$A8`
branch lands at `+0x00DE`, so `0x0110` and the `+0x00C6` flush are not reached.

The room-49 EXCD also exposed `$03 getActorRoom`. The implemented canonical
bounded behavior reads a direct or variable actor ID from normal actor state,
returns room zero for an invalid/nonexistent actor, and fails closed on a
malformed operand. It does not add actor rendering or gameplay behavior.

Phase A remained bounded: no inventory, class UI, actor renderer, movement,
walkbox, or earlier-gameplay subsystem was required to reach the acceptance
flush.

## Canonical `$1D ifClassOfIs`

The opcode reads a direct/variable object word followed by one or more
direct/variable class words terminated by `0xFF`. Class IDs are the low seven
bits and must be in 1..32. Bit 7 means the class must be present; without bit 7
the class must be absent. Every selector must match. A false combined result
takes the normal signed relative branch.

Both host and SNES use the ordinary sparse object-class mask. Copyright-free
tests cover true, false, multiple required classes, an unflagged required-
absent class, the authentic object-595/class-18 operand form, class IDs 0/33,
and truncated lists. Unsupported or malformed forms fail closed with error
`$1F`; no Fate, room, object, or branch-result special case exists.

## Named pre-Thera state

`examples/resources/scumm_v5/fate_m23c_pre_thera.json` extends the accepted
M23B state only with source-bound ordinary state needed by room 63:

- object 595 owns classes 2, 7, and 14, exactly matching its supplied DOBJ mask
  `0x00002042`; classes 18 and 20 are absent;
- logical sound 82 is running, representing legitimate preceding-gameplay SFX
  ownership;
- global script 151 is initially inactive and is supplied as its authentic,
  hash-bound resource.

Bit 425 and strings 30/31 remain the accepted M23B room-49 inputs. Sound 80 is
not initialized by this fixture: the positive run obtains it only by executing
authentic room 49. No PC, branch answer, hook, command, or script-completion
state is injected after execution starts.

## Source mapping and authentic batching

Room 63 begins at `PLAYFATE.001` file offset 460711. Its ENCD program begins at
file offset 503455, ROOM-relative offset 42744, chunk-relative offset 8, and
cooked-record offset 43456. Normalized offset equals runtime PC for this
descriptor. Therefore the key instructions map as follows:

| Instruction | Original file | ROOM-relative | Chunk-relative | Cooked | Normalized/runtime |
|---|---:|---:|---:|---:|---:|
| first class test | `503455` | `42744` | `8` | `43456` | `+0x0000` |
| queue hook 8 | `503622` | `42911` | `175` | `43623` | `+0x00A7` |
| start script 151 | `503636` | `42925` | `189` | `43637` | `+0x00B5` |
| query sound 82 | `503639` | `42928` | `192` | `43640` | `+0x00B8` |
| conditional | `503643` | `42932` | `196` | `43644` | `+0x00BC` |
| queue `0x0110` | `503648` | `42937` | `201` | `43649` | `+0x00C1` |
| flush | `503653` | `42942` | `206` | `43654` | `+0x00C6` |

The positive final pre-flush queue is exactly
`[[0x010C,80,0,8],[0x0110]]`. Hook 8 remains queued while script 151 starts and
yields, sound 82 is queried, and its conditional executes. One authentic flush
processes the commands in order. This is not the immediate-flush shape used by
the older bounded synthetic M21/M22 command fixtures.

## Host, SNES, and DSP evidence

The host validator runs positive, class-control, and sound-82-control cases.
The positive and class-control histories end with hook 8 then `0x0110`, one
iMUSE clear-queue operation, active script 151 at PC 4 with delay 7200, and
pending hook 8. The sound control reaches the authentic `+0x00DE` branch with
hook 8 still in the unflushed SCUMM queue and no clear operation.

The SNES validator launches three fresh emulator processes and makes zero
debugger audio writes, PC writes, post-start state writes, opcode skips, or
branch-result overrides. Positive evidence includes:

- authentic room 49 reaches hook-14 song 27 ready/playing and audible before
  the normal room-change request;
- room lifecycle requests/validations/entries are 2/2/2, room-49 EXCD runs,
  two old room-local owners retire, and room 63 registers five descriptors;
- the exact 17-operation room-63/global-151 trace above begins at ENCD PC zero;
- sound 80 and sound 82 queries both return 1, while script 151 first returns 0;
- hook 8 arms only at the `+0x00C6` flush, remains pending, and is consumed once
  one frame after boundary token 1;
- `$7C` remains running, song 27 is not reloaded, and packet rejection/loss are
  both zero;
- normalized TAD boundary is tick 8644 at 125 Hz, with -26 microseconds source
  conversion error and zero additional authentic-SCUMM latency;
- transition latency is one frame, silent gap is 0 microseconds, and no
  clipping, duplicated notes, or truncated notes were observed;
- the 48 kHz stereo DSP capture peaks at 10438, SHA-256
  `71cdce7169372b6b4f530a339de497915e9bd19b3a8c7e0bb1c5872e15fc2316`,
  and correlates 0.924486 with the accepted M22 hook-8 capture over the aligned
  five-second comparison window.

Evidence files:

- `build/m23c-host-report.json` (SHA-256
  `18437585cf95438858da9b8cfceb5501c725775f076f14b5e4b04b7ef0371ba1`);
- `build/scumm-m23c-ca5ae06865ebca73/report.json` (SHA-256
  `db318775a361e2a17140d4359073557d888fe454fe8a2adab86b827a13e90cca`);
- `build/scumm-m23c-ca5ae06865ebca73/authentic-room63-hook8.wav`;
- `build/m23c-if-class-42a66f96678dbe57/report.json`.

## Save/load and regression

M22's policy is unchanged: a cold load transactionally restores logical route
history and restarts the compiled cue from its beginning. It does not restore
the musical position or any SPC/DSP-continuous state. Armed, consumed, and
default-route SRAM cases and identity/corruption rejections pass against the
unchanged M22 ROM
`de6e257897a8e150a85f78b0dcf1ea49ef80b0a49d9f359263e843f819f9b332`.
Complete room, class, actor, and live script state is still not connected to a
complete game-save format; M23C does not claim otherwise.

- 315 unit tests pass.
- Repository validation and Poppy lint pass.
- All four M23C builds pass Poppy lint, SNES assembly, and ROM audit.
- M19 through M23B accepted ROM files retain their recorded identities.
- The M22 cold-SRAM report is
  `build/scumm-m22-save-de6e257897a8e150/report.json`.

No new timbre approval required.

## Evidence-based next blocker and M24 recommendation

Immediately after the accepted flush, authentic room 63 queues an `0x010D`
duration/fader command for sound 82, starts sound 80 again, starts script 151
again, and chains to room-local script 202. The present named state can answer
the sound-82 status query, but it does not supply or run authentic sound 82 as a
real resource; advancing the host audio lifecycle beyond the M23C barrier fails
closed on missing sound 82. Local script 202 then reaches actor movement,
delay/wait, and walkbox-dependent state.

The narrowest M24 should therefore not assume another music feature. It should
be **authentic room-63 post-entry sound-82 lifecycle and local-script-202
preflight**, first identifying sound 82's source type, `0x010D` semantics and
duration ownership, and the exact reached script-202 dependency cone. Its gate
should cook and execute sound 82 only if that is bounded and should stop before
adding actor/walkbox gameplay if script 202 proves materially larger. Acceptance
would require authentic execution from the M23C state through the first honest
yield/blocked boundary, matched host/SNES command and ownership traces, and no
new music semantics unless the source path actually demands them.
