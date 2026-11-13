# Checked source-resolution camera integration (in progress)

The optional `SAME_SCUMM_VISUAL_PROJECTION=camera-viewport` build retains
original source pixels instead of aspect-fitting an entire room. SC5VIS v2
stores checked eight-pixel vertical strips; v1 remains supported and the
legacy default is unchanged. This is the existing SAMEPKG/video/provider
path, with no additional framebuffer, selector pool or executable cache.

The camera uses the existing 320-pixel logical SCUMM origin and a centered
256-pixel visible viewport. Actor and cursor projections retain world
coordinates. The bottom 32 pixels remain reserved for the interface.
Vertical projection retains the existing centered room behavior; arbitrary
vertical scrolling and actor scaling are not certified here.

Each strip fits the existing pending scratch allocation and has an independent
CRC. The old display remains installed while the existing tile-shadow alias
stages a new viewport. Incoming room publication belongs to M24; same-room
camera publication cannot consume that transaction. Queue backpressure retains
an installed viewport until PRESENT is accepted, without recopying reclaimed
staging. A room request drains an in-flight camera read before taking ownership.

Camera metadata owns `$7E8FC0..$7E8FE7`, 40 bytes of previously reserved
resolver/name-cache padding. Resolver and name-cache allocations are unchanged.
The mechanical ownership audit treats this as a separate region. The first
native attempt incorrectly allocated camera state inside the lifecycle trace
ring; captured opcode bytes demonstrated the corruption. That allocation was
removed, and a regression now rejects it. That failed run is not acceptance.

## Native evidence

A corrected full-source authentic startup reached room 10 through the existing
three original cutscene acknowledgements. No story variables were written.
The settled source viewport was `(32,0,256,144)`, placed at `(0,24)` on screen.
Indy stood at original world position `(84,60)`, chore 3, scale 255.
Generation 17 matched independent original costume/room interpretation with
**zero INDEX8 and zero PPU pixel differences**. SCUMM error was zero.
The private-Xvfb supervisor completed in 229.190 seconds and cleaned up.

- ROM SHA-256: `7ac50dbb39cc3ebbfcdf0f722ad7cb710512ed8828d993f58b7559517ab55713`
- Map SHA-256: `19be93033435ca5786652da1f99df7991c80bbc65f9ccdc51dc41eb599bace24`
- Build identity SHA-256: `c6667d391b47f601ca64e33767e06fc907922680524fce53a82a77fd929bd8e6`
- Package SHA-256: `70564585c15538ed04b7f614b5b4d929a07eedf7a8545b510ff0ed66e9ad29d0`
- Private evidence: `/tmp/astra-camera-owned-native-20261111/observations`

The package contains all 2,203 ProgramUnits and 96 visual records. Its size is
14,480,229 bytes; source-resolution SC5VIS uses 6,677,952 bytes. The native ROM
remains 4 MiB. No commercial payloads or captures are committed.

This native image precedes the additional room-priority drain guard; that
specific correction has source-instruction tests, not transferred emulator
acceptance. Source-level instruction runners also verify strip copying at
all eight alignments and room edges, cursor projection, opaque actor pixels,
restoration, lifecycle exclusion, and queue backpressure. They are host tests,
not Nexen tests. The full suite ran 1,450 tests with 12 skips before the two
room-priority cases were added; validation and pinned ROM audit passed.

## Still required for Milestone C

Native scrolling and object-target agreement; a visible verb/inventory UI;
a continuous original action changing persistent state; matching current-head
hosted CI. The first camera image is not whole-game or milestone acceptance.

## Completed-view publication ownership

The037fd3d native session verified the original pickup and readable inventory
then loaded all32 checked viewport strips. Camera STATE3 remained installed
from frame8710, while the Mode3 backend was idle, unlocked and had no queued
events. The camera publisher retained its external staging lock while calling
PushDirtyPresent; the shared CanWrite preflight correctly rejected that lock.
This was an owner handoff defect, not an MSU CRC failure or emulator timeout.
The owned session was stopped at504.797seconds and all observations retained.

The camera now releases its completed staging ownership only for the
synchronous shared video publication call. Other engine producers cannot run
inside that call; NMI retains normal video ownership. Refused publication
reclaims STATE3 and retries without recopying the reclaimed tile-shadow alias.
The regression executes the actual CanWrite guard at this boundary rather than
a permissive queue stub, including refusal and successful retry.

A completed old crop also no longer clears a newer pending camera position.
After PRESENT, the normal idle comparison reconciles the latest desired crop:
identical requests clear; newer requests retain input/resource gating and
initiate their own checked read. Incoming-room lifecycle remains exclusive.
This changes no logical source camera timing, source coordinates or buffers.
Current-image native acceptance is recorded separately.
