# Barnett exploration — Milestone E in progress

Milestone D remains accepted at `0740cbca`. This successor work does not
requalify the taxi/map trip or claim the office is playable yet.

## Source-selected route

The original room-2 office door is object34. Open (verb3, OBCD PC65) sets
state1 and clears walkbox16's flags before rebuilding the movement matrix.
Walk-to (verb10, PC50) loads room1 at PC62 only when the door is open.
An isolated original-body host control verifies the open operation.

The candidate persistent action in room1 is Pick up coat (object25, verb11,
PC53): ordinary pickup, global10, state0, classes26/32. The isolated host
control yields owner15→1 and preserves newspaper141 ownership. This is a
semantic oracle, **not evidence of native reachability or a host playthrough**.
The exact eventual input/state must come from the installed original room.

## Observed exit failure and correction

Normal input on the matching D ROM opened the door, retired its object script,
and entered `RoomExitProgram(2)`. Its `soundKludge(13,64)` and flush raised
SCUMM error25. Class-zero iMUSE command13 is a sound-status query; it does not
request a new music conversion. Reference: pinned ScummVM
`10a54c2696126a81ee2b2f7f10b1a8be90ed7711`,
`engines/scumm/imuse/imuse.cpp` and `engines/scumm/sound.cpp`.

The host and native command dispatch now publish the logical result through
v5 VAR_SOUNDRESULT (56). The native query shares the existing logical music
and 256-bit SFX ownership used by isSoundRunning. SFX ownership was previously
compiled only in the M23C fixture; normal M19 runtime now initializes and
maintains it after accepted service requests. The same 32-byte allocation is
included explicitly in the ownership audit. No additional audio buffer,
executable-cache lease or title-specific sound branch is introduced.

Native support is bounded to IDs0..255 and explicit logical start/stop
ownership. First-player (`-1`) and wider native IDs fail explicitly. This does
not certify natural completion of every converted sound, a general iMUSE
player allocator, deferred-trigger playback, or acoustic output. The host's
existing deferred adapter distinguishes queued starts (2) from active (1) and
absent (0), and does not report a cleared deferred entry as queued.

`actor_scene_fixture --sound-status-probe` produces original copyright-free
SCUMM bytecode for start/query/stop, queued start/stop-all and result lifetime.
`validate_scumm_sound_status_nexen.py` observes it under `run_visual_once.py`;
there are no guest memory writes. Process success is separate from semantic
acceptance. The initial native control failed because the ownership table was
not enabled; the corrected initial control observed `[0,1,0,0,0x1357]` at
frame24 with error0. The extended control observes `[0,1,0,0,0x1357,1,0,0]` at frame24,
error0. Supervisor completion: 5.582 seconds, normal exit,
cleanup complete and no owned survivors. This control precedes the additional guard preventing a wider SFX service ID
from aliasing the 256-bit ownership table. The final guarded build also passes at frame24, error0, in 5.576 seconds,
with complete cleanup. Its ROM is `b88edd64c35760c836fe11914477fa66af6f7246afc3c83f809e3f5a0686d286`,
map `4dbaa3b85d55a3ffdacd2b151876e4b1cde5c57fd5b7155a9951b79be90ce140`,
and build identity `eb2e4581da89d4a33b72cac09329f28d560f3465cec179256427e476a61d0405`.
Package identity is unchanged. This is synthetic logical-query acceptance.

- Native fixture ROM: `7a0d2150a5d8cb60c5ba775ad482afdf1d3fc8944c55201365fb961794833fe5`
- Map: `0a93ec461e262183a88407a8de04b247e8fd09a0739bf95eacd53926a3aacbc3`
- Package: `fb29d19dde30fedc721c68d78c4bdac8bd3bb96b8e9773bf51fce4ac63142311`
- Build identity: `c2243b033f2bfcc93fc24a93b89a3fafb9ed652778aa4749f349b4b53c62eca3`

The exact command is retained in `native-sound-status-extended/process-result.json`.
Generate the original source input with
`python3 -m examples.resources.scumm_v5.actor_scene_fixture OUTPUT.zip --sound-status-probe`.
Cook all executable bodies/visuals using the existing fixture profile, then use
the normal streamed actor build with synthetic MAXS and no story overlay.
Run `tools/validate_scumm_sound_status_nexen.py` only through
`tools/run_visual_once.py`; its explicit ROM, output, Nexen/core, MCP-library
and port arguments keep this local native test separate from hosted CI.

## Cutscene callback retirement corruption

Fresh normal-game setup on the experimental E ROM reached the original map,
then failed with variable error2 in LSCR201. The package was intact. Native
write/execute journals isolated a CPU-width defect: the start-cutscene callback
enters the ordinary nonrecursive StartScript retirement scanner with X8.
`ScummV5_C4_StopNumber` declared `.i16` but did not clear the runtime X flag
before its immediate LDX. The CPU decoded the high immediate byte as BRK and
later executed a branch displacement as `STA long,X`. That wrote through bus
address `$001861` into executable WRAM, changing logical PC56 from `$40` to
`$20`. The subsequent variable error was a consequence, not a drawBox defect.
The write preceded the SFX ownership operation; it was not caused by that table.

The scanner now establishes X16 with `REP #$10` before its first indexed
instruction. This changes no C4 scheduling or script-number semantics and
requires no additional memory. A copyright-free fixture installs both original
cutscene callback variables, passes local0=`$1234`, and runs both callbacks
through the normal nested global resolver.

Native positive control `native-cutscene-width` finishes at frame24 with
variables `[2,4660,0,0,4951,0,0,0]`, error0, no BRK execution and no writes through
the executable WRAM mirror. A private negative build removing only this width
correction reaches the **same semantic sentinel and error0**, but produces
three BRKs and a cache-alias write. The validator correctly rejects it. Thus
checking only the sentinel or error counter would have missed the corruption.
Both runs clean up their owned processes; neither is authentic gameplay proof.

Positive identities:

- ROM: `6a88bfaed541ccf64586bf6a15cb2a112c265e4307924d7d206ee638efd5051e`
- Map: `0be2739b8e9661477f793b23269a2a0535bc30702c6bbb30651fb0e2c1f42e03`
- Package: `8da0272e59e7a630ec9f7761bbce207835683c1cca32d6f64bac0218fb6ebf0b`
- Build identity: `9fc054871556d61f0a7b1d103403e4ed00bf108ccad9d40aeb32465dd5722717`

Generate with `actor_scene_fixture --cutscene-callback-probe`; run the existing
supervised validator with `--case cutscene-callback`. Private journals include
`trace-operand-journal`, `trace-cache-mutation`, and `trace-cache-writer`.
Earlier observer limitations remain recorded; an asynchronous hook name is
not a claim of stopped CPU state at that instruction.

## State-selected object presentation

The new host OBIM decoder uses IMHD object IDs; OBIM and OBCD resource order
are not interchangeable. It shares the existing SMAP/ZP decoders, preserves
codec-specific transparent pixels separately from opaque color zero, and
composes in reverse local-object order with parent-state/owner filtering.
Classic v5 object mask strips replace the corresponding background masks.
State-only invalidations are consumed by the normal host composition tick.

The original room2 door's IM01 changes77 background pixels. The current
native renderer still has **no state-selected room-object image consumer**.
That is an explicit scene-fidelity gap, not permission to compare only the
base background. Object relocation and broader image families also require
coverage before general support can be claimed. All proprietary image bytes
and rendered comparisons remain private.

## Evidence and integration boundaries

Private evidence is under
`/home/chad/SAME-private-evidence/milestone-e-exploration-20261114`.
`office-boundary` preserves the early-input observer failure;
`office-retirement` preserves the actual original exit failure. Neither is
labeled an engine deadlock. All native sessions use private Xvfb/Nexen MCP,
bounded process trees and exact ROM/map/package/build identities.

A changed ROM requires fresh ordinary-game setup. Old D savestates are never
restored into E builds. The progression recovery worktree is untouched.
PR14→PR15→PR16 ancestry remains intact. E is a successor, not an amendment to
accepted D. No automatic merge. Whole-game readiness remains **NOT_READY**.
