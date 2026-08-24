# SAME service ABI revision 1

SAME 0.2 extends the service/opcode vocabulary but preserves the exact 0.1 wire
record.

## Packet layout

Every record is 16 bytes, little-endian:

| Offset | Size | Field | Meaning |
|---:|---:|---|---|
| 0 | 1 | revision | must be `1` |
| 1 | 1 | service | kernel/video/audio/input/storage/time/debug/memory/engine/save/jobs |
| 2 | 1 | opcode | service-specific operation |
| 3 | 1 | flags | acknowledgement, response, urgency, disposable, bulk, error |
| 4 | 1 | source | kernel/legacy target/S-CPU/SA-1/SPC/host/engine/profile |
| 5 | 1 | destination | endpoint or broadcast |
| 6 | 2 | sequence | monotonically increasing modulo 65536 |
| 8 | 4 | arg0 | operation-defined unsigned value |
| 12 | 4 | arg1 | operation-defined unsigned value |

The ABI byte order does not follow a guest CPU. A 68K or Z80 portal converts bus
values before creating a packet.

## Flags

- `ACK_REQUEST`: sender requires a response carrying the same sequence.
- `RESPONSE`: this packet answers a prior request.
- `URGENT`: prioritize within the backend’s safe window; never bypass PPU/NMI
  ownership.
- `DROP_OK`: queue overflow may discard and count this packet.
- `BULK`: arguments identify a validated memory/package descriptor.
- `ERROR`: response represents failure.

A packet lacking `DROP_OK` is never silently lost.

## Service groups

### Kernel

Heartbeat, panic, logging, budget overrun, queue overflow, host/legacy-target
ready/stopped state.

### Video

Legacy tile/sprite operations plus baseline surface creation/upload, dirty
rectangles, palette writes, cursor, presentation, and capability query.

### Audio

Music, SFX, volume, chip writes, PCM stream, speech, flush, and capability query.

### Input

Digital snapshot, profile/player change, pointer, text, and normalized events.

### Storage

Open/read/seek/close/prefetch/complete/fail plus enumerate and stat.

### Time

Frame ticks, timers, and monotonic query.

### Debug

Trace/assert/counter/marker plus state/video/audio hashes.

### Memory

Allocation, free, bounded copy/map, pin/unpin, completion/failure.

### Engine

Probe, boot, tick, event delivery, save/load, suspend/resume, shutdown,
capability query, ready/stopped/failure.

### Save

Read/write/delete/enumerate slots and complete/fail responses.

### Jobs

Submit/cancel/complete/fail and capability query. On the host this executes
synchronously; on SNES it is the SA-1 offload seam.

## Bulk safety

Packets carry handles and bounds, never unchecked SNES or guest pointers. The
backend validates:

```text
owner
address space
processor visibility
offset + length
writability
lifetime/pinning
```

before touching memory.

## Generated source

`same abi generate runtime/snes/generated/abi.inc.pasm` is authoritative. Do not
hand-maintain a second opcode list in assembly.
