# SAME audio

## Score intent versus rendition

S4 introduces `same_score_v1`, a small backend-neutral score resource. It keeps
timed note/control events, stable voice identities, duration, and loop points.
The SCUMM adapter saves these logical playheads and reconstructs playback after
load; it never saves opaque SPC state.

This deliberately separates composition from SNES arrangement. The manually
reviewed Monkey Island MML/TAD projects remain valuable curated renditions and
may be selected by a profile. They are not the only route: a backend may instead
allocate the score's voices live on SPC/TAD or stream a rendered MSU track. All
three paths must preserve the same engine-visible timing and resource identity.

S4 proves selection and state convergence with synthetic data. It does not claim
that live TAD compilation or production SPC delivery is implemented; that
mechanism remains K3 work.

## Two source levels

SAME accepts:

1. **semantic commands** — play music, stop music, play SFX, start PCM stream;
2. **chip writes** — SN76489, YM2612, YM2610, AY/YM variants.

A target can start with chip writes for fidelity, then replace known driver paths
with semantic commands when measurement proves the substitution.

## Implemented host lab

`src/same/audio.py` implements:

- SN76489 latch/data register behavior;
- three tone channels and one noise channel;
- attenuation and a deterministic 16-bit mono WAV renderer;
- JSONL trace input;
- a YM2612 register/key-on retention model.

Generate the demonstration:

```bash
same audio demo \
  --trace examples/audio/sn76489-demo.jsonl \
  --wav out/sn76489-demo.wav \
  --duration 1.25
```

The WAV is proof of the CPU-independent source side. It is not proof that a TAD or
SPC translation is correct.

## SNES backend gate

The first backend should consume normalized `MUSIC_PLAY`, `MUSIC_STOP`, and
`SFX_PLAY` packets and call a currently proven local TAD integration from Monkey Island or BOR. Acceptance requires:

- one packet produces one expected TAD command;
- queue full/driver not-ready is reported, not dropped;
- an emulator audio capture contains nonzero sample energy;
- target and backend status agree;
- no video DMA or NMI budget regression.

## YM2612 boundary

No FM synthesizer is claimed in 0.2.0. The next useful step is not writing a full
FM core on the SNES. It is collecting real register traces, classifying how a
selected game's driver uses channels/operators, and deciding per game whether to:

- translate semantic music/SFX events;
- author TAD equivalents;
- stream rendered music through MSU-1;
- preserve only sound effects on SPC;
- or implement a bounded subset of YM2612 behavior.
