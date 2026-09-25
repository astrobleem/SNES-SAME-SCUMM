# M24R-B2 report — decoder correction passes; authentic short gate hard-stops earlier

Status: **decoder correction implemented and mechanically validated; M24R-B remains incomplete**.
The mandatory shortened authentic LSCR-208 gate does not reach LSCR 208, so the long loop,
room-63 transition, and three arbitrary-phase captures were not run.

No TAD source, M24R-A transition primitive, composite data, voice-reduction policy,
instrument mapping, route, save policy, or far-bank closure changed.

## Phase 1: authoritative queue ABI

The host owns queued commands as signed word lists in
`src/same/engines/scumm_v5/engine.py::_op_sound_kludge`; the SNES representation is declared
in `runtime/snes/kernel/memory.pasm` and populated by
`ScummV5_Op_SoundKludge`.

| Record offset | Field | Meaning | Width |
|---:|---|---|---:|
| `+0` | word count | Number of following words, valid range 1–32 | 1 byte |
| `+1` | encoded command | `words[0]`, little-endian signed word | 2 bytes |
| `+3` | logical sound | `words[1]` for the five forms in this gate | 2 bytes |
| `+5` | operand 2 | Priority, speed, fade target, marker, or nested payload | 2 bytes |
| `+7...` | remaining operands | Command-specific or deferred payload words | 0–58 bytes |

Each fixed slot is 65 bytes and the queue contains 16 slots at `$7F:D45A`. A record occupies
`1 + 2*count` meaningful bytes. Top-level `soundKludge[-1]` is not stored: it invokes the
flush operation directly. `soundKludge[0x010F,-1]` is a normal two-word queued record and
terminates the current deferred trigger group; these representations are distinct.

Working handlers load `record + 1` as a 16-bit word in
`ScummV5_C25_Flush__dispatch` after copying the bounded record to `LAST_COUNT/LAST_WORDS`.
The defective M24R-B path instead loaded `record + 0` in
`ScummV5_C25_Flush__command_present` and compared that eight-bit count against `0x0101`,
`0x0106`, `0x010D`, `0x010E`, and `0x010F` before copying the current record.

## Narrow correction

Changed `runtime/snes/engines/scumm_v5.pasm` only:

* `ScummV5_C25_Flush__command_present` now rejects zero counts and counts above 32 before any
  word copy;
* dispatch for all five affected commands moved after the 16-bit encoded-command load in
  `ScummV5_C25_Flush__dispatch`;
* handlers still validate their authoritative forms before reading command-specific operands;
* priority/speed and trigger values must fit 8 bits; fade targets must be 0–127;
* deferred construction requires at least the nested command word, reads a nested sound only
  in the three-word start form, and recognizes the terminator as full word `0xFFFF` rather
  than any value whose low byte is `0xFF`.

Before: `load u8 record[0] -> compare as command -> stale LAST_* or unknown-command error`.

After: `validate record[0] -> copy declared words -> load u16 record[1:3] -> compare command ->
validate exact/variable form -> read operands -> execute`.

`tests/test_scumm_v5_engine.py` adds two focused tests. They cover all five canonical host
forms, operand decoding, too-short forms, too-long fixed forms, authoritative variable-length
`0x010F`, range failures, wrong encoded command at the same count, and the old one-word/count-1
misdispatch. A source-bound assertion fixes the SNES field-loading order and queue bound check.
The isolated host and source/ABI tests pass. A standalone SNES execution-parity fixture was
not claimed because the required authentic step-one gate hard-stopped first.

## Layout and mechanical evidence

The integrated authentic profile assembles and audits successfully:

* bank 0 emitted end: `$00:FFA4`;
* free before mandatory header `$00:FFC0`: 28 bytes;
* header and vectors: reset `$8000`, NMI `$8062`, IRQ `$8084`;
* accepted far closure remains wholly at `$09:8000-$09:8502`;
* no new far caller, pointer, DBR/PBR dependency, trampoline, or cross-bank return was added;
* integrated short ROM SHA-256:
  `7d22dc2f272b2584cfbe617d0efd03c56783c54394d11f68b8352b3fb2ed5ac4`.

Poppy lint, assembly, and ROM audit pass. The unit suite is now 322/322 passing. Repository
validation passes with its established expected unregistered-demo diagnostics. The existing
M24R-A ROM remains untouched. Existing M24R-B APURAM content is also unchanged: 3,558-byte
driver upload, 4,584-byte low/driver/common base, 4,369-byte common item (4,241 sample bytes),
6,115-byte composite/transition data, 256-byte echo, 50,212 bytes free, peak 8 physical and
14 logical source voices.

## Mandatory shortened-gate result

Fresh-power-on evidence is in `build/m24rb-b2-short-nexen/`, including the DSP WAV and
`raw-observation.json`. The run does **not** satisfy the step-one gate:

* authentic room 49 loads and its accepted start-80/hook-14 flush completes;
* LSCR 208 is registered as scheduler slot 1, script number 208, generated program `$DA`, PC 0;
* before slot 1 executes, room-49 ENCD remains running in slot 0 at saved PC `$0070`;
* the scheduler resumes slot 0, advances to runtime PC `$007D`, and writes
  `SCUMM_ERR_SCRIPT ($0B)`;
* slot 1 consequently remains at PC 0; no `0x010E/0x010F` record reaches the corrected decoder;
* observed ownership is `82: absent -> marker-active shadow`, not
  `absent -> deferred -> active`; deferred count and frame-end flush count remain zero.

This is reproducible in both accepted M24R-B1 ROMs, before the decoder edit:

* short ROM `85b08271b78161d42ac2c5875179fd8b216e399e0ebb73f735d8a8abc4e529d9`;
* long ROM `5e751382430e7607d7737ce86eff2aa27e85cc955d7326440b36f974f5c896c3`.

Both reach the same room-49 state: ENCD PC `$007D`, VM error `$0B`, slot statuses all running,
LSCR-208 PC zero, and no deferred ownership. This precedes and masks the corrected queue
decoder. Repairing room-entry retirement/scheduler ordering is outside M24R-B2's explicitly
limited decoder scope. Per the hard-stop instruction, no long 103.447623-second capture, no
room-63 fade/admission run, and no arbitrary-phase reruns were attempted.

No new timbre approval required. M24R-B is not marked complete, and M25 was not started.
