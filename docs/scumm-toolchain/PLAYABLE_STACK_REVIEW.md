# Playable SCUMM stack: review order

Repository state checked during Milestone E. This is a dependency and evidence
handoff, not human approval or authorization to merge. All four PRs remain drafts.

| PR | Head | Base | Scope | Hosted checks |
|---|---|---|---|---|
| [14](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/14) | `41305d9d32cf02907dc887d3f76e449c01d57389` | main `99127067adf6c2264e0217aa52ee91f3f3088e56` | Authentic room, walking and readable original interaction | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42974288606) |
| [15](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/15) | `b57224c130f550350a28184f4c7125682d0d9de2` | PR14 | Playable interface, persistent inventory, retained camera and packed code cache | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43344824185) |
| [16](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/16) | `0740cbca8ac0a9c522c0bc614c746d95c29af390` | PR15 | Input callbacks, scaled multi-actor scenes, masks and Barnett interaction | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43566269456) |
| [17](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/17) | `ed6d376b62b9f25e3839899e4696211687a02811` (native runtime) | PR16 | Office exploration and coat inventory; continuous native acceptance passed | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43601748173) |

GitHub reported the three completed feature PRs open and mergeable against
those exact bases. Their branches and histories are unchanged. PR17 is a clean
successor; Milestone E experiments have not been added to the accepted PR16 head.

Review #14, then #15, then #16 against their documented scopes. If integration
is later approved, preserve ancestry with merge commits, retarget only the next
child to main, inspect its incremental diff, and obtain fresh protected checks
for that new base. Keep branches while descendants depend on them. No merge,
force push, baseline-tag edit or protection bypass was performed here.

The boundaries remain canonical 16-bit ProgramUnit identities, 178 resident
selectors, checked executable/resource transfers, one shared actor/room scratch
owner, and NMI-owned video publication. Milestone E adds eight room-hook ticket
bytes after reset diagnostics; it does not change executable-cache capacity.
The authentic rebuilt package is byte-identical to the prior object-image build;
its ROM and matching states are new. Private evidence links both build identities.

Hosted assembly is not Nexen execution. Native pixels and gameplay are certified
only at the documented captures. Source representation is not whole-game support.
Full object-state refresh remains conservative and expensive; broader object
relocation, lifecycle combinations, audio and portable native saves are not
qualified by these narrow routes. The full game remains NOT_READY.

PR17 observer/evidence follow-up retains those runtime bytes. Its final hosted
checks are reported on the PR; runtime CI is not substituted for final-head CI.
No human approval or merge is implied by this technical qualification.
