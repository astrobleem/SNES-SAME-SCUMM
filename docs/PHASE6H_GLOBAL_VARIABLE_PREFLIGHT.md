# Phase 6H dense-global preflight (deferred)

This file preserves the accepted design evidence only.  Phase 6H-A does not
compile or include the diagnostic dense-variable implementation.

- Source MAXS: decoded `PLAYFATE.000` offset `$03D3` (979), 26 bytes.
- MAXS SHA-256: `004c043e2371f1f75f81df26184eda89fef95c7d6886b84deeffa07ac1c0f98f`.
- Bytes: `4D4158530000001A200310000008C80032000500640014005000`.
- Decoded fields: 800 globals, ignored v5 second word 16, 2048 bit
  variables, 200 local objects, 50 arrays, 5 charsets, 100 verbs, 20 new
  names, and 80 inventory objects.
- Candidate table: `$7E0800-$7E0E3F` (800 little-endian u16 entries,
  `$0640` bytes), half-open end `$7E0E40`.
- Declared stack floor: `$7E1800`; proposed guard `$09C0` bytes.
- Preflight diagnostic ROM (not accepted):
  `3e5a73442ffde3c58c383d75c4cc70c4d89849971974dd221f54935b664715ea`.

The discarded diagnostic implementation generated a profile-owned variable
manifest/include, cleared the complete table at boot, and routed ordinary
global reads/results/writes through it.  Reconstruct that work from this
contract in Phase 6H-B; do not use Phase 6H-A artifacts as dense-table proof.
