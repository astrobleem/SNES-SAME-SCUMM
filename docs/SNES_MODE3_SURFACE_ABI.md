# SNES Mode-3 Surface Video Packets (Phase 6D)

This contract is implemented only by the selectable `mode3_surface` backend
and requires the `sa1_bwram` carrier. The legacy backdrop backend remains the
default. The packet remains the existing 16-byte SAME packet.

`SURFACE_DIRTY` (`$0C`) packs unsigned `x`, `y`, `width`, and `height` as
`arg0 = x | y << 16` and `arg1 = width | height << 16`. Width and height must
be nonzero. The backend clips to the fixed 256x224 display and accumulates a
896-bit candidate-tile set.

`PALETTE_WRITE` (`$0D`) packs `arg0 = first | count << 16`; `arg1` must be
zero. The source RGB8 entries already reside in the backend's carrier-owned
live-palette region. Count must be nonzero and the range must stay within 256
entries.

`PRESENT` (`$11`) packs an unsigned, nonzero generation in `arg0`; `arg1` must
be zero. A generation must be newer than the committed generation and the
backend must be idle. Acceptance locks the fixed surface until conversion,
queueing, and every corresponding DMA commit are complete. Dirty, palette,
and present requests received while locked are rejected and counted.

The backend is synchronous only at the event-service boundary. Large accepted
generations are visibly incremental across NMIs; completion is not atomic.
No packet contains or exposes BW-RAM, VRAM, CGRAM, or DMA addresses.
