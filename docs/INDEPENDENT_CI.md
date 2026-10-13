# Independent CI

`Independent validation` runs from a fresh GitHub-hosted Ubuntu 24.04 checkout
with read-only repository permissions. It runs the actual `make test` and
`make validate` targets and independently builds/verifies the copyright-free
SAMEPKG fixture. A manual `source_ref` input allows the workflow definition
from the CI branch to test a later feature-stack commit without importing
commercial source archives or generated artifacts.

The assembler job checks out the exact pinned Poppy and Pansy commits, builds
with .NET SDK 10.0.301, explicit deterministic compilation, no separate PDB,
and deterministic CI path mapping, then checks the resulting DLL SHA-256 before
using it. The initial clean hosted build exposed varying PE/PDB identity
metadata despite matching source revisions; disabling standalone debug symbols
and forcing deterministic output is the corrective build policy. Poppy's pinned
project references Pansy as a sibling checkout, so both source revisions are
part of the build identity.
Restore currently reports upstream ImageSharp 3.1.11 security advisories
(NU1902/NU1903); the build treats only those advisory warnings as warnings,
does not disable NuGet audit, and records the risk for dependency remediation.

When the tested source includes the generic SCUMM residency fixture builder,
the assembler job also builds the large-room MSU personality and audits the
ROM. Nexen is not installed by this workflow and no assembly job is described
as native emulator acceptance. No FATE/Monkey archive, private path, secret,
ROM, MSU package, or emulator trace is uploaded.

After the workflow is merged to `main`, configure required checks named
`Host tests, validation, and package reproducibility` and
`Pinned Poppy build and SNES ROM audit`. Until then, the workflow PR itself is
validated by its push-triggered hosted run but repository branch protection is
not active.
