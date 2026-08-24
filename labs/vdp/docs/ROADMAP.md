# SAME-VDP gates

The order is intentional: each gate must pass in the Python oracle and the Poppy
SNES player before the next gate begins.

| Gate | Feature | Current state |
|---|---|---|
| V0 | CRAM, one Genesis tile, Plane A 32x32, H32 256x224 | Implemented |
| V1 | Whole-tile horizontal/vertical scroll | Next |
| V2 | Sub-tile scroll and 64-wide/64-high maps | Planned |
| V3 | Plane B and priority composition | Planned |
| V4 | Window plane | Planned |
| V5 | Sprites, links, flips, size and line limits | Planned |
| V6 | Per-cell and per-line H-scroll; 2-cell V-scroll | Planned |
| V7 | Mid-frame register/CRAM writes through HDMA/IRQ plans | Planned |
| V8 | H40 policy: crop, letterbox, or Mode 5/6 experiment | Planned |
| V9 | DMA fill/copy semantics and captured commercial traces | Planned |

The generic SAME video IR comes after V3. Before then, the raw Genesis VDP state is
kept intact so an abstraction cannot hide hardware facts prematurely.
