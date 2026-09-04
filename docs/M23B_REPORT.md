# M23B — authentic Fate room-49 ENCD execution

M23B is complete. It executes the complete authentic room-49 ENCD from PC zero
through the normal resource provider, room lifecycle, scheduler, and SCUMM v5
dispatcher. It does not use a source-extracted basic block or an interior entry
point. M23C and M24 were not started.

## Bound identities

| Artifact | SHA-256 |
|---|---|
| supplied `fatedemo-box.zip` | `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798` |
| `PLAYFATE.000` | `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9` |
| `PLAYFATE.001` | `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240` |
| original room 49 | `fbf234f2ffe3530ba365980abfae556636d83e5cada9bdc649c43d4cce7242f6` |
| authentic room-49 ENCD | `205ccdf64c470ff47a08be391ab3606267c57141f1ca3bc556ec50e24e8920da` |
| cooked room 49 | `2904015371af15b616711013298b8e95874e55c5e9c45216fe09bf9a544a025f` |
| global script 144 | `15df9d2f8ea96729aff1816ccb96b3365b69b7b0af7f029f9850d1218d28c594` |
| global script 145 | `c2a5ef1468895155cae658dd75f955396e1f8dc3ed44350816905e4785eb7543` |
| named positive state | `ae4329468113b2083b4fa852f6454f1373ecf626abd8044278dc50d1b5ae54e7` |
| named negative state | `46b524c83d5d090da6d6fdd4b067f8a3426a64e4411a82766bae9d47a283babc` |
| positive M23B ROM | `d0d3452e62c51801efd3e475b3005432446d7b0516d93ee209c84d09ea932951` |
| negative-control ROM | `3efc7e1e66a7b48fd5e4d94d7ab4573a6274b4505422ba90dbd0eb8657d79300` |

The profile identity is
`37bc71eb005f72fbad00dd4fea9a0ab0245df4e9af50a3ffce04167c99156c2b`.
The compiled catalog SHA-256 observed by the host is
`38834324a87b59854da6f2c4ba635ebfaa3a03cb99d83e860fc27d45bd5acde2`.

## Phase-A dependency closure

The table records the complete parent-ENCD path to the music block. Opcodes in
global scripts 144 and 145 are also executed normally; their important newly
exposed terminator is included below.

| ENCD offset | Opcode | Semantic requirement | Prior status | State read/written | Required M23B change and evidence |
|---|---:|---|---|---|---|
| `+0x0000` | `$7A` | configure verb 53 and decode inline `Demo` | implemented | verb record 53 | none; host and SNES trace advance to `+0x0009` |
| `+0x0009` | `$13` | actor 7 reset, costume 234, init frame 18, scale 255/255 | implemented | actor 7 | none; canonical suboperations already covered by C14 |
| `+0x0014` | `$1A` | assign `var[27]=214` | implemented | global 27 | expanded SNES profile variable backing; both traces record 214 |
| `+0x0019` | `$0A` | start global 144 with locals 88 and 2; 144 starts 145 nested | resource/outer-call connection missing | slots, locals, strings 30/31, globals 450/451 | register hash-bound scripts 144/145; preserve four bounded caller frames and outer-vs-nested return mode; local ScummVM `engines/scumm/script.cpp::runScriptNested` is the semantic source |
| global-script end | `$A0` | canonical stop-object-code alias | host implemented, SNES missing | current script slot | dispatch `$A0` to the same stop semantics as `$00`; local host maps both and local ScummVM v5 opcode table confirms the form |
| `+0x0022` | `$48` | compare indexed bit ref `0xA1A1 + 1`, i.e. bit 418, with 1 | indexed read missing | bit 418 | add generic indexed variable-reference resolution; unit test `test_m23b_indexed_bit_reference_is_consumed_by_comparisons` |
| `+0x002B` | `$42` | chain to local script 213 when bit 418 equals 1 | implemented; irrelevant required path | slot ownership | no change; positive fixture leaves bit 418 clear and trace takes `+0x002E` |
| `+0x002E` | `$28` | test bit 425 | implemented | bit 425 | named state sets it from ordinary SCUMM bit state |
| `+0x0033..0x003A` | `$1A,$1C,$18` | set bit/start ordinary sound/jump when bit 425 is clear | implemented; irrelevant required path | bit 425, SFX 80 | not executed in either M23B state |
| `+0x003D` | `$7C` | query sound 81 | implemented | sound ownership, `var[0]` | positive reads stopped; negative reads running |
| `+0x0041` | `$28` | skip the music block when sound 81 is running | implemented | `var[0]` | negative observation barrier proves the real relative branch reaches `+0x006D` |
| `+0x0046` | `$7C` | query sound 80 | implemented | sound ownership, `var[0]` | positive reads stopped |
| `+0x004A` | `$28` | skip when sound 80 is running | implemented | `var[0]` | positive falls through to `+0x004F` |
| `+0x004F` | `$4C` | queue `[8,80]` | implemented by C25/M21 | soundKludge queue | authentic source descriptor, not fixture bytes |
| `+0x0057` | `$4C` | queue `[0x010C,80,0,14]` | implemented by M21 | same queue | authentic source descriptor, not fixture bytes |
| `+0x0065` | `$4C` | flush the two queued commands once and resolve hook route | implemented by M21 | logical cue/route and SAME packets | observation barrier captures pending count 2 before queue scratch is reused |

The 65816 stop path also now normalizes an 8-bit slot ID before using a 16-bit
X register. This prevents a stale accumulator high byte from addressing a
false cutscene-depth entry. These are generic interpreter repairs; no room,
sound, hook, or ENCD offset is embedded in opcode semantics.

## Named pre-Thera state

`examples/resources/scumm_v5/fate_m23b_pre_thera.json` contains only state that
affects the prefix:

- bit 425 is set; bit 418 is clear;
- strings 30 and 31 are the authentic boot-script shape: 153 bytes each,
  filled with the IQ bias value 100;
- sounds 80 and 81 are stopped;
- the bounded room-request driver occupies the test initialization boundary,
  while boot script slot 1 is inactive.

The negative state changes one relevant ordinary engine value: sound 81 is
running. It retains bit 425 and the same strings, room, scripts, and resources.
Neither state stores a branch answer, opcode result, or PC.

Host execution of scripts 144/145 mutates `var[450]` to 2 and `var[451]` to
-98 before returning to ENCD. The positive and negative host cases each execute
1,254 operations. A controlled ScummVM gameplay run could not be made
authoritative from the supplied demo installation because its bootable
preceding-game state is unavailable locally; semantic comparison therefore
uses the checked-out ScummVM opcode implementation plus the accepted local host
implementation's complete instruction/branch trace. No ScummVM runtime trace
is claimed.

## Offset mapping and authentic batching

Room 49 begins at `PLAYFATE.001` offset `301791`. The complete ENCD descriptor
begins at original file offset `362230`, original ROOM-relative offset `60439`,
original chunk-relative offset `8`, and cooked-record offset `62591`.
For this descriptor, normalized script offset equals runtime PC. Thus:

| Instruction | Original file | ROOM-relative | Chunk-relative | Cooked | Normalized/runtime |
|---|---:|---:|---:|---:|---:|
| queue start 80 | `362309` | `60518` | `87` | `62670` | `+0x004F` |
| queue hook 14 | `362317` | `60526` | `95` | `62678` | `+0x0057` |
| single flush | `362331` | `60540` | `109` | `62692` | `+0x0065` |

The host's final pre-flush queue is exactly
`[[8,80],[0x010C,80,0,14]]`; one flush consumes both in that order. This
corrects the authentic acceptance model without changing the older M21/M22
bounded synthetic fixtures, which remain accurately labeled synthetic.

## SNES and DSP evidence

`tools/validate_scumm_m23b_nexen.py` launches separate fresh-power-on positive
and negative emulator processes. It makes zero debugger audio writes, PC
writes, opcode skips, branch-result writes, or post-start state writes.

Positive final evidence:

- normal resource request/validation/entry counts are 1/1/1, active room is 49;
- ENCD runtime PC is `0x006A`, last opcode is `$4C`, and total operations are
  1,268 including the lifecycle driver;
- authentic flush count is 1 and captured pending command count is 2;
- logical music is 80; route is `(hook,14)`; compiled TAD song is 27;
- route history is start/default-resolution/hook/hook-resolution, with song 26
  never reaching ready or audible ownership;
- TAD reaches state `$82`, ready 1, song 27, with zero TAD rejection, packet
  rejection, or packet loss;
- the normal SAME packet trace is default play 80, hook-route replacement 80,
  then flush; no debugger-facing injection seam is used;
- the stereo 48 kHz DSP capture is non-silent and unclipped (peak 2693).

The accepted M21 hook-14 excerpt is used with its accepted default-route
control. The final run correlates 0.92764 with hook 14 and 0.03617 with the
default route, giving an unambiguous route discriminator while allowing normal
capture/DSP phase variation.

Negative evidence:

- ENCD executes from PC zero with identical resources and scripts;
- sound 81 running makes the authentic `+0x0041` branch land at `+0x006D`;
- flush count is zero, music-route history is empty, and no audio packet is
  emitted;
- the final interpreter state has no error and no packet loss/rejection.

Evidence files:

- `build/m23b-host-report.json` (SHA-256
  `bcd015983f40c3550fba46c23e6e752ba8fa34dbbcf3388499dc164741bb5ec1`);
- `build/scumm-m23b-d0d3452e62c51801/report.json` (SHA-256
  `24b839920615de56e81d0dead988d5690d70bd814d2c68dbdddc5a9532b415ea`);
- `build/scumm-m23b-d0d3452e62c51801/m23b-positive.wav`.

## Regression

- 311 unit tests pass.
- Repository validation and Poppy lint pass.
- Both M23B builds pass Poppy lint, SNES assembly, and ROM audit.
- The unchanged accepted M23A, M19, M20, M21, and M22 ROMs retain their recorded
  SHA-256 identities and pass their fresh-power-on emulator gates.
- M22 live hook-8, hook-lifetime, and cold-save matrices all pass unchanged.

No new timbre approval required.

## Remaining room-63 dependency cone and M23C recommendation

Authentic room 63 still requires these semantics/state before ENCD `+0x00A7`:

- `+0x0000` and the following class test: canonical `$1D ifClassOfIs` on object
  595, including the `0xFF` list terminator, bit-7 required-present selectors
  146/148 (classes 18/20), object lookup, and false relative branch.
  This remains a missing SNES opcode.
- Object 595 class ownership is missing authoritative initialized state. The
  both-classes branch additionally performs the already decoded soundKludge
  command batches, stops script 151, starts sound 46, and starts authentic
  script 200.
- From `+0x004F`, `var[224]`, actor `var[1]`, room `var[4]`, object 851,
  animation 248, camera follow, yield, and walk-to `(360,130)` select whether
  the actor/camera path runs. The individual bounded operations exist, but the
  authentic actor/object state does not.
- At `+0x0072`, `var[414]` selects whether two `$AC` expressions and
  deterministic RNG choose object 853..855. Expressions and RNG exist; the
  authentic variable/RNG state is missing.
- Sound 80 must remain running at `+0x0095`; script 151 must be stopped at
  `+0x009E` to reach hook 8.
- After `+0x00A7`, the authentic script starts global script 151, queries sound
  82, branches at `+0x00BC`, and only the sound-82-running path queues `0x0110`
  at `+0x00C1` and performs the eventual flush at `+0x00C6`. Global script 151
  and every semantic dependency it reaches must be cooked, registered, and
  executed; the hook must not be described as immediately flushed.

The narrowest honest M23C is **authentic Fate room-63 ENCD execution and
batching through the real interpreter**, using a second named, hash-bound
ordinary SCUMM state derived from the M23B hook-14-running state. Its gate
should implement canonical `$1D`, cook/register only the required authentic
global script 151 (and script 200 only if the chosen authoritative class path
executes it), enter room 63 at PC zero through normal room change, and prove the
complete branch trace through `+0x00C6`. It should include one relevant state
negative control and then reuse the already accepted M22 delayed-boundary
backend. It must not begin at `+0x00A7`, force class/sound results, or describe
the registration trace as gameplay reachability.
