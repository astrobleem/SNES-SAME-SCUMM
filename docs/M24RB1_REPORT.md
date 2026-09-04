# M24R-B1 report — far-bank relocation and combined-gate stop

Status: **relocation accepted mechanically; combined M24R-B gate still blocked**.
No M24R-B audio, TAD, composite, instrument, voice-reduction, or source-route data changed.

## Pre-relocation closure

The diagnostic Poppy map placed bank-0 code through `$1040E`; the production header begins
at `$FFC0`. Moving only the M24R-B driver (`$BD3E-$BE2A`, 237 bytes) and specialized C25
handlers (`$D644-$D6E0`, 157 bytes) could recover only 394 bytes. The smallest coherent cold
closure that exceeded the 1,056-byte deficit was:

* generated authentic cooked-record validator: `$95EC-$9742`, 343 bytes;
* authentic room lifecycle, M23C/M24R-B driver, and lifecycle trace: `$BCC9-$C030`, 872 bytes.

The validator's only caller is `Same_Storage_Handle`. Lifecycle public callers are
`ScummV5_Engine_Frame`, `ScummV5_Op_LoadRoom`, and the room-script stop path; storage also
calls the lifecycle trace. Internal callees remain same-bank. Bank-0 callees required by the
far closure are exposed through six explicit `JSL`/`RTL` ABI adapters: C25 flush, logical SFX
clear, local-script resolution, event staging, event push, and SCUMM error recording.

No generated address table contains a pointer to the moved routines. Program-byte and
program-size lookup remain in bank 0. The interpreter dispatch remains in bank 0. The far
closure has no fall-through caller and no 16-bit code pointer. All WRAM and generated ROM
table operands are long accesses. The sole hardware read is explicit long `$00:2141`; DBR is
therefore not changed or followed into bank 9. Internal bank-9 calls use `JSR`/`RTS`; every
cross-bank edge uses `JSL`/`RTL`.

## Resulting layout

The M24R-B profile reserves bank 9 for cold code:

* validator: `$09:8000-$09:815A`;
* lifecycle/driver and far entries: `$09:815B-$09:8502`;
* total far closure including entry veneers: 1,283 bytes;
* bank-0 emitted end: `$00:FF55`;
* free before mandatory header `$00:FFC0`: 107 bytes.

Poppy symbol/listing output is in `build/m24rb-reloc-after.{sym,map,lst}`. The finalized
512-KiB LoROM passes header/vector audit with reset `$8000`, NMI `$8062`, and IRQ `$8084`.
The long-delay integrated ROM is SHA-256
`5e751382430e7607d7737ce86eff2aa27e85cc955d7326440b36f974f5c896c3`.

## Relocation-neutral evidence

All 320 unit tests pass. Repository validation and Poppy lint pass. The integrated ROM
assembles, finalizes, and audits. A fresh-power-on shortened authentic run exercised the far
validator and lifecycle: rooms 49 and 63 produced two resource requests, two validations,
two entries, one exit, and three room-local retirements with zero SAME packet loss/rejection.
The accepted backend ROM identities remain byte-identical:

* low: `991e152258459d06fd52d7cfd90175e56839024628ee47999dd92cf179f324e3`;
* high: `b2980a96c74538f4982d9da74ce9234e26f4ed3d577845b94dbc6912aacc9c03`;
* sustain: `1decc173ed13cadf13065b1da6bb82da3da4caf3a08fef7313be0b79bb495f9f`;
* loop: `1816ccb5191c05d8f5c4c7cbd3885d09c95cce781af206e50c30647938af64a7`.

## Combined-gate blocker

The shortened combined run reached authentic room 49, registered authentic LSCR 208, crossed
the compiled marker, and transitioned through the relocated lifecycle into authentic room 63.
It then proved a pre-existing M24R-B SNES dispatcher defect that the split host/backend gates
could not execute.

`ScummV5_C25_Flush__command_present` loads the queue record's **word count** and immediately
compares that byte against encoded commands `0x0101`, `0x0106`, `0x010D`, `0x010E`, and
`0x010F`. The encoded command is not loaded until `ScummV5_C25_Flush__dispatch`, after history
copy. Therefore LSCR 208's deferred commands reach the generic unknown-command error path;
the M24R-B `LAST_*` handlers never receive the current command. Observed evidence:

* `LSCR_SCHEDULED=1`, but `DEFERRED_COUNT=0`, `FRAME_END_FLUSHES=0`;
* sound 82 changes directly from absent to the driver's marker-active shadow, never through
  deferred ownership;
* room 63's authentic `$7C 82` result is false and it takes the accepted absent-state branch;
* no async transition request/admission/fade-completion tokens are emitted;
* the authentic room/resource lifecycle and packet counters remain correct.

The raw trace is `build/m24rb-reloc-short-nexen-debug/raw-observation.json`. Fixing the command
selection point would alter SCUMM command-processing behavior, expressly frozen by M24R-B1's
ROM-layout-only authorization. It was not changed or disguised as a passing combined gate.
The 103.447623-second long capture was not rerun because the required deferred ownership was
already absent in the short gate.

No new timbre approval required. M24R-B is not marked complete, and M25 was not started.
