# M24R-A — bounded asynchronous TAD layer-transition primitive

## Result

M24R-A passes its synthetic backend gate. It does not implement Fate sound 82,
change a SCUMM opcode, or begin M24R-B/M25.

The final ROM is `e68f1b513076cb34039aee47c1ae1724d87ce87c438496fca061abd00478d8b6`.
The two-process emulator report is
`build/m24ra-nexen-e68f1b513076cb34/report.json` (SHA-256
`95cbdb01c02b71ae91dee76c30dc0c4d22afbb58187b76553fb39bb0b81c665b`).

## Primitive

The S-CPU command is TAD command 22 in this isolated toolchain only:

```text
parameter 0 = 0: bind/reset generation in parameter 1
parameter 0 = 1: request transition for generation in parameter 1
```

`process_music_channels` observes the request immediately after incrementing
TAD's song tick, before channel countdown processing. Consequently an outgoing
channel need not reach another bytecode instruction. The fixture proves this
with eight 4,000-tick notes whose countdowns all exceed 3,000 at request time.

One fixed table admits five precompiled B subroutines:

| Relative tick | B lane | Physical voice | Explicitly truncated A note |
|---:|---:|---:|---|
| 19 | 0 | 7 | C3 |
| 38 | 1 | 6 | B2 |
| 63 | 2 | 5 | A2 |
| 94 | 3 | 4 | G2 |
| 125 | 4 | 3 | F2 |

There is no free-voice search or runtime note scheduler. Admission keys off the
selected A voice, removes it from the A mask, resets that existing TAD channel,
and redirects it to the precompiled B subroutine. `update_vol_shadow` applies
the transition gain only when the physical voice remains in A's mask. A B voice
therefore does not inherit A's fade.

Generation 1 is superseded by generation 2. A stale generation-1 request emits
one stale token and performs no transition; the generation-2 request then emits
the exact token sequence:

```text
request, steal 7, steal 6, steal 5, steal 4, steal 3, A complete
ticks 0, 19, 38, 63, 94, 125, 256
```

The 8-bit transition counter wraps at completion, so the completion trace port
contains zero; the build identity and report declare the unambiguous 256-tick
fade duration.

## Emulator evidence

In both cold processes:

- one normal SAME `music_play 1` packet loads one physical song;
- all eight DSP voices and all eight long channel countdowns are active before
  the request;
- the request is observed one S-CPU frame later and within the driver's 8 ms
  tick-resolution bound;
- admission ticks are exactly `19,38,63,94,125`;
- TAD remains `$82` ready/playing song 1 through every transition frame, with
  zero packet rejection and no loader state;
- group A owns the fade until its one completion event, then its three remaining
  instruction pointers are zero;
- B owns mask `$F8` and all five B instruction pointers remain live afterward;
- TAD's lag detector remains zero;
- every 20 ms audio window after request has nonzero energy (minimum RMS
  770.328), peak is 8,614, and clipping is absent.

The normalized command/event trace is byte-identical across the two cold
processes. Nexen's 48 kHz capture begins at a different host-resampler offset
and is not bit-identical; after aligning each capture to its first audible DSP
sample, correlation is 0.999999925; the 20 ms energy-envelope correlation is
0.99999999996. This is reported as emulator-capture variance,
not hidden as exact PCM identity.

## Cost

| Item | Cost |
|---|---:|
| TAD patch code | 325 bytes |
| New writable driver state | 13 bytes |
| Fixed admission table | 10 bytes |
| Additional reserved APURAM page | 256 bytes |
| Conservative peak extra instructions/music tick | 88 |
| Conservative peak extra SPC cycles/music tick | 420 |
| Peak share of 8,192-cycle 125 Hz budget | 5.13% |

The cycle figure is a conservative static upper bound for the completion/steal
path, not a profiler-derived average. Runtime evidence is TAD's zero lag flag.
Inactive ticks take only the request/active guards; the bounded maximum handles
at most one admission or one completion in a tick.

Exact fixture APURAM accounting:

```text
driver upload                 3,543 bytes
driver low page                 512 bytes
reserved driver/common gap      529 bytes
common data                   1,928 bytes
  common non-sample data        128 bytes
  BRR sample data             1,800 bytes
song data                       194 bytes
echo                            256 bytes
usable free after song       58,574 bytes
peak physical voices              8
```

## Modified TAD surface

The maintained SAME-owned patch is
`audio/m24ra/terrific_audio_driver_m24ra.patch`, applied only to pinned TAD
commit `822164b09cb3d4750bd4c1960a430dc35b6ae04a`.

- `audio-driver/src/audio-driver.asm`
  - adds `cmd__same_layer_transition`;
  - calls `same_process_layer_transition` from `process_music_channels`;
  - adds the 13 state bytes and ten-byte schedule;
  - adds `same_process_layer_transition`;
  - gates A gain in `update_vol_shadow`.
- `audio-driver/src/io-commands.inc`
  - adds isolated command 22.
- `audio-driver/src/common-memmap.inc`
  - moves `COMMON_DATA_ADDR` forward one page to retain code-bank capacity.

SAME-side changes are confined to an explicit `SAME_BUILD_M24RA` personality,
its copyright-free score/catalog, build tooling, S-CPU evidence state, and
validator. The normal audio packet ABI and production SCUMM handlers do not
gain a public transition or mixer operation.

## Validation and regression

- 318 unit tests pass (315 accepted plus three M24R-A tests).
- repository validation and Poppy lint pass;
- M24R-A assembly and ROM audit pass;
- M20, M21 mechanical, M22 live transition/save, and M23C fresh-process gates
  pass on their unchanged accepted ROMs;
- all accepted M19-M23C ROM identities remain exact.

One explicit infrastructure caveat remains: the generic `make snes` target
still pairs the base Fate TAD project with the later route-expanded default
catalog and fails before assembly because `fate_sound_80_default` is absent.
This predates M24R-A; the dedicated M24R-A build assembles and audits normally.
Also, a fresh rerun of the unchanged M19 ROM reproduced its music/status/audio
but hit that validator's strict video/NMI pacing assertion during the 3,900-frame
capture. Its accepted ROM and prior evidence remain unchanged; this rerun is not
reported as a pass.

## Judgment

**Yes.** This primitive can support the authentic arbitrary-phase sound-82
fade / sound-80 admission with an explicit eight-voice reduction policy,
without becoming a general live music engine. It supplies only asynchronous
request observation, one outgoing-group gain, deterministic explicit steals,
and admission of precompiled lanes. Applying it to Fate still requires M24R-B's
source-bound composite plan and defensible musical reduction; M24R-A does not
claim that content work is complete.
