# Multi-actor scene transaction — native checkpoint

The opt-in `SAME_SCUMM_ACTOR_SCENE=1` path enumerates the 32 C14 actors,
keeps per-actor pose/animation/palette identity, and composes visible actors in
source Y order (actor ID breaks ties). It uses the existing checked source-cel
compositor, shared actor scratch, INDEX8 surface and NMI presentation service.

One scene transaction restores the old journal, captures every new actor's
underlay **before drawing any actor**, then draws each complete checked pose in
painter order. Only the completed scene is published. This avoids restoring
one actor's footprint over another actor. A full 32-bit presentation fence
separates candidate scene state from displayed state.

The SA-1 carrier optionally reserves S-CPU-accessed I-RAM `$003100..$0037FF`
for metadata. The carrier explicitly grants S-CPU write access to those pages;
the SA-1 CPU remains reset, and the first mailbox page remains untouched.
The allocation and feature requirements are mechanically audited. There is
no extra pixel buffer or executable-cache lease.

## Native evidence

The copyright-free original SCUMM fixture has two different costumes, scales
231/231 and 128/200, overlapping coverage, swapped Y order, facing changes,
two animation steps and a moved actor. Four completed captures match the
independent source compositor, complete INDEX8 surface, decoded PPU and CGRAM
with **zero differences**. Native execution completed at frame1976 in
205.009 wall-clock seconds. The supervisor reports normal exit and no owned
survivors. This is synthetic renderer acceptance, not Barnett gameplay.

Private evidence: `milestone-d-scene-20261113/native-two-actors-idle-placement`.
ROM SHA-256: `2939f7fc19122026532ddd8b7afd3affd4a032a5923fed47bb20c1d3d22f92f3`
Map SHA-256: `0a34f626db70da86f333f8db7a0d21e900e4056ce99d526754e10e8ea39a6daa`
Package SHA-256: `4f81139c76b5e8a9b73bddd280b92cadcc19397aaa824fe7d9f2483f268a2605`
Build identity SHA-256: `0565159bfa3428695c43eb01dead7a6726ec17c58f119c241971f38d888f131c`

That ROM was built from a private source snapshot before this public commit;
its build identity records that exact snapshot. Subsequent mask work is not
covered by these four images. Original foreground masks, authentic Barnett
full-scene rendering and destination interaction remain NOT_VERIFIED.

Adjacent fixes permit an empty trailing SC5LIVE name table whose offset equals
the checked record length, and accept ordinary idle `putActor` position changes
with the no-walk-destination sentinel. The publisher runs after movement's
complete scheduler update; the sentinel does not denote a partial actor.
