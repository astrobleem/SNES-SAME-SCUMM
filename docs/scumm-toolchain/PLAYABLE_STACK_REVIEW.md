# Playable SCUMM stack: review order

Repository state checked during Milestone E. This is a dependency and evidence
handoff, not human approval or authorization to merge. All five PRs remain drafts.

| PR | Head | Base | Scope | Hosted checks |
|---|---|---|---|---|
| [14](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/14) | `41305d9d32cf02907dc887d3f76e449c01d57389` | main `99127067adf6c2264e0217aa52ee91f3f3088e56` | Authentic room, walking and readable original interaction | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42974288606) |
| [15](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/15) | `b57224c130f550350a28184f4c7125682d0d9de2` | PR14 | Playable interface, persistent inventory, retained camera and packed code cache | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43344824185) |
| [16](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/16) | `0740cbca8ac0a9c522c0bc614c746d95c29af390` | PR15 | Input callbacks, scaled multi-actor scenes, masks and Barnett interaction | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43566269456) |
| [17](https://github.com/astrobleem/SNES-SAME-SCUMM/pull/17) | `575d02134bfa38e66b2fd81bf6ba9c0c94afd854` | PR16 | Office engine corrections; historical coat reachability qualified by PR18 | [Passed](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43631512302) |

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

## Source-default and name follow-up (PR18)

PR18 (`scumm-fate-office-progression`) remains additive on PR17. GitHub reports
all five current bases mergeable; PR14/15/16 retain their listed heads. PR17
requires the source-class correction before its historical coat observation
can be considered in a merge decision. Missing source classes made that object
incorrectly touchable. No human approval is implied by green checks.

PR18 runtime `2bdea03b8f3c810fb327c0350fea93c72f9f20c6` retains all1,395
source class defaults, bounded mutable overrides, class32 hit-test filtering,
and fixes the native SetObjectName JSR/RTL and encoded-length defects. Both
required hosted jobs passed [run43629978507](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43629978507).
Review the exact original office acceptance and evidence qualifications in
[OFFICE_PROGRESSION.md](OFFICE_PROGRESSION.md). These additive corrections do
not change the previous PRs, baseline tag, or recovery worktree.
