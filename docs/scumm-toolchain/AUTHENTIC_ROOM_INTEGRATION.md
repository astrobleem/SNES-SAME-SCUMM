# Authentic room integration

The actor subsystem was merged through PR #13 as `99127067adf6c2264e0217aa52ee91f3f3088e56`.
Main's hosted run [42749057867](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42749057867)
passed. This branch continues from that commit; the historical progression
recovery worktree and experimental baseline tag remain unchanged.

## Sparse source poses

The opening source costume has 100 cooked poses, 78 nonempty. Its largest
bounding rectangle covers 23,084 pixels, but its maximum opaque payload is
739 bytes. Its largest run journal (16-byte header plus four bytes per run
and original overwritten pixels) needs only 1,248 bytes. This is a resource
measurement, not a production costume-number exception.

The existing indexed surface service now saves the pixels beneath clipped
opaque runs in the unused tail of the installed SC5LIVE allocation. The engine
validates all spans, captures every run, commits the journal, then draws.
Restoration validates the entire journal before writing and consumes its magic.
Room/generation ownership, exact lengths, row boundaries, capacity, signed
coordinate overflow, and register/stack contracts are checked. No new pixel
buffer, executable-cache lease, package format, or selector scheme is added.
Capacity exhaustion remains explicit; this does not certify every costume or
room tail, multi-chunk poses, multiple actors, scaling, or occlusion.

### Native evidence

A single supervised private-Xvfb Nexen control completed in 69.187 seconds.
It uses original externally supplied costume bytes with a **synthetic SCUMM
control script**, not authentic gameplay. Five completed frames cover facing,
animation steps, and movement. All five indexed images match the host source
costume decoder exactly; VRAM/CGRAM comparison is exact, old-position residue
is zero, and SCUMM error is zero. Test-owned processes were cleaned up.

- ROM: `f539f54c9e0b9cfbff55c59bebf10478810bf23a924ead14605f264f2cf72fd9`
- Map: `1b5fd3d7f2c4c583a272fcb99172e2746b46d620607e57968a82432fd5487d41`
- Package: `281589a71af44c7476d79d7109977439bc94c31832653deb9cb0eb775183297a`
- Build identity: `f9506f780543e7810dc8ba7893efaeea44e1ab89ba3c552e903c375159695ed9`
- Probe audit: `dd1fee2033e5f9a5aaa3306ccf06f12f196dc4690bbaddf41c53cf8e67e3d146`

Local evidence: `/tmp/astra-sparse-costume26-proof-20261110/observations`.
Build: `/tmp/astra-sparse-actor-build.s2rroyv3`.
Immutable source: `/tmp/astra-sparse-ready-source.j1uycv58`.
That snapshot deliberately excludes the subsequent native palette hooks. Its
native acceptance must not be transferred to a later combined ROM identity.
Commercial captures and payloads remain outside Git.

## Palette integration

Classic-v5 intensity derives colors from the original installed room palette,
not cumulatively from the already darkened colors. Direct palette changes
modify the effective palette. The v5 intensity result is capped at 252.
The host oracle uses the existing serialized effective palette overrides.
Host schema 6 also stores an optional original base palette for resource-less
room restores; older resource-backed saves reconstruct it from the resource.

Native allocation is explicit within the formerly unused low BW-RAM reservation:

| Range | Owner |
|---|---|
| `$40:0000–02FF` | Immutable installed source palette |
| `$40:0300–05FF` | Ordered desired palette |
| `$40:0600–061F` | Palette publication/control scratch |
| `$40:0620–07FF` | Still reserved |
| `$40:0800–0FFF` | Existing save storage, unchanged |

Incoming room preflight cannot replace the installed palette. Desired colors
may change while presentation owns the live video palette; publication waits
for the existing surface service and NMI-owned presentation path. Native
portable save migration is not implemented by this allocation. Emulator
savestates remain ROM-specific. Physical hardware has not been tested.

The cold replay helper has an explicit actor-entry capture-only mode. It stops
before object/controller actions and does not label a screenshot as gameplay
acceptance. The existing seven-action route is not rerun for this work.

Whole-game readiness remains **NOT_READY**. Authentic interactive scene,
projection, multiple actors, masks, text, audio and persistence coverage remain
separate requirements.

The combined original-script build assembled and passed the ROM audit:
`0e56a33e862c60fb46f54653d4037b53c64d6bf5ec5b5f408f6e6060d1862886`.
Native palette source SHA is
`60201d5137b47a1710211905917ba373fe488461c520b432a8c9ce64cd960b05`.
Seven source-instruction palette controls pass; this is not native palette
acceptance. The first authentic entry attempt was rejected before emulator
launch because the observer still assumed a selected-build report directory.
The observer now follows the identity-owned whole-source root, with regression
coverage; it does not bypass ROM/map/directory identity checks.

## Original startup observation (not accepted)

The corrected full-directory observer ran once for 241.784 seconds and exited
with a bounded actor-presentation timeout, below its 600-second process-tree
limit. Original startup reached room 4 with SCUMM error zero, but no composed
actor reached the PPU during the observation window. No controller actions
were submitted. The final snapshot has pending presentation generation 6 and
committed generation 4; that snapshot alone does not establish a deadlock or
a renderer failure. The test-owned emulator exited; the unrelated user session
was left untouched.

Evidence remains under
`/tmp/astra-authentic-room-entry-directoryfix-20261110/`. The full final state is
in `process.log`; `observations/authentic-entry.json` retains the source/build
identities and room publication observation. No native acceptance is claimed
for the combined palette build.

The independent host projection oracle now compares sparse actors against
compositing in logical room space followed by the existing SC5VIS aspect-fit
projection. It covers signed offsets, sampling phase, letterboxing, transparent
holes, and opaque mapped-zero colors. Five tests include 100 randomized
differential cases. Native projection is still pending; actor scaling is a
separate unimplemented capability in this oracle.
