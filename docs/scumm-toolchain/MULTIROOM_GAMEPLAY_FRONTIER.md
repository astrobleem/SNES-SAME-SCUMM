# First continuous source-authored room exit

Milestone C is functionally qualified in [CAMERA_PIPELINE.md](CAMERA_PIPELINE.md).
Milestone D has begun; sustained destination gameplay is **not accepted**.
The runtime is `be553385b7419e5d8d1e6e6fa492ab48e40b80ab`, with the same complete
2,203-ProgramUnit package and ROM identities recorded in that document.

## Observed original transition

A matching-ROM checkpoint descended from the accepted newspaper/inventory and
reverse-camera session was restored. The continuation used ordinary SNES
controller input to choose **Use taxi**, select original object 140, confirm
once, walk to its source walk point, read the original travel dialogue, and
acknowledge it. No guest gameplay state was written and no script was replaced.

The original OBCD entry at PC85 requests room75 after its message wait, writing
globals315/316 to 10/1. A separate host component test executes that exact
external carrier through the existing interpreter/message lifecycle. It reaches
the room-service request at PC154 with destination75 and variables10/1 in
17 host frames. The destination loader is an explicitly observed boundary in
that component test; it is not host acceptance of the destination's full game.

Native observations show room10 retiring, room75 publishing, its entry/local
scripts running, error0 and lifecycle RUNNING. Newspaper owner/state remain1/1.
The original travel map and palette are loaded through the full-source package.
A correctly fenced destination capture at generation379 has:

- zero original SC5VIS projection versus INDEX8 differences;
- zero source projection versus committed VRAM raster differences;
- zero source palette versus CGRAM differences;
- an actual Nexen screenshot, retained privately.

Projection: source origin(32,4), 256x192 scene, fixed interface area below.
Original visual pixels SHA256:
`ab608fc86e891b3716a5e224da2fd6d6f441bc7c30cfe64e675d9a0d37e61770`.
Source room identity:
`654a37756cd9a1f721a79a3bb7f7d1506656d72fc9f0d49fe78f557adcdecd1c`.

The first transition observer confused room-install phase0 with the separate
lifecycle enum RUNNING=2. It reached its bounded observation limit after the
room had loaded. That report remains labeled unverified, with its failure
intact. The corrected capture restored its exact destination checkpoint; it
did not replay startup or the taxi trip. These continuations are explicitly
separate sessions, not an edited continuous recording of the whole trip.

## Concrete next input-service boundary

Room75's original entry saves the prior global32 value and installs local204
as **VAR_VERB_SCRIPT**, the source input callback. Its local205 updates hover
selection from the logical pointer. Local204 handles the map selection and
invokes the chosen object's original verb10 after its authored travel behavior.

The current controller bridge implements semantic sentence selection/submission
through C20 and **VAR_SENTENCE_SCRIPT (global33)**. It has no corresponding
raw scene/verb/key input callback dispatch through global32. These interfaces
are different; changing the sentence launcher to32 would be incorrect.

Two distinct normal input steps were observed from the matching destination:

1. A selects Barnett College, object1028, default verb10. The source input
   callback remains unobserved; selection alone was not treated as a failure.
2. A confirms that selection exactly once. Submission count rises238 to239,
   then the sentence drains. After192 bounded frames, room75 and variables10/1
   remain, local204 has not been observed, and error remains0. Newspaper
   ownership/state remain1/1. No automatic repetition followed.

The native submission site is
`ScummV5_Controller_Frame__select_verb_a_pressed`; it always populates the
semantic sentence mailbox. `ScummV5_SentenceProcess_Far` intentionally reads
variable33. The host likewise exposes `queue_sentence` and its sentence
scheduler, but its input event adapter does not implement the missing callback
contract. The local ScummVM reference at commit
`10a54c2696126a81ee2b2f7f10b1a8be90ed7711` confirms variable32 in `vars.cpp` and
`runInputScript` in `script.cpp`: click area, selected value and mouse mode are
script arguments, distinct from sentence verb/object operands.

The next generic deliverable is that input-callback service, with canonical
local/global resolution, ordinary C4 ownership, resource-wait handling,
one-edge ownership, and host/native conformance. It must coexist with the
compact controller UI and authored verb disable/restore behavior. It must not
special-case this room, script204 or object1028, or invoke the destination
object directly to bypass the source callback.

The source also uses actor10/costume58 for map behavior; the accepted actor
renderer is still configured for one actor and costumes1,2,26. Map-marker
animation is not certified. The settled captured actor10 was not in room75,
so its absence alone is **not** evidence of an erroneous native hide.

## Evidence and limits

Private root:
`/home/chad/SAME-private-evidence/milestone-c-final-multiroom-20261112`.

- `multiroom-taxi-bound-listing/observations`: once-only original action,
  dialogue, room lifecycle and preserved destination checkpoint.
- `map-input-continuation/observations`: exact completed map generation,
  independent source comparison, and first destination-selection edge.
- `map-confirmation/observations`: normal confirmation and bounded callback
  frontier observation.
- `host-taxi-contract.json`: original-carrier host component result.
- `room10-source-interactions.json`, `room75-source-programs.json`,
  `map-input-source.json`: private source disassembly, never public fixtures.

No complete playable destination, multi-actor rendering, travel audio, portable
save restoration, physical hardware, or whole-game readiness is claimed.
The restored checkpoints are exact-ROM Nexen states, not portable game saves.
No new FATE-specific production hooks were introduced.
