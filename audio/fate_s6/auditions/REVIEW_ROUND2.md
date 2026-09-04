# Fate S6 instrument review — round 2

Reviewed by Chad on 2026-08-24 from real Nexen S-SMP/DSP captures of ROM
`f9c1dd17c051c5c1afcf7d2b24a7a1b7bc8d6b8fc2c89199e1423f7779666c02`.

## Decisions

- Organ: reject. Beginning around 15 seconds, the seam/overlap becomes audible.
- Marimba: pass and lock.
- Flute: reject. Beginning around 11 seconds, the tail fails. This aligns with
  entry into the p74 main zone, before the later Phantasia high candidate.
- Atmospheric pad: approve the low end; reject the highest notes because the
  source no longer has enough sampling resolution.

## Engineering response

- Preserve marimba byte-for-byte alongside the already locked bass/percussion.
- Remove the organ seam and use the reviewed generic MT-32 organ as one source
  across the required range.
- Preserve the accepted p74-low timbre, but preprocess octave-up mid and high
  sources with high-quality resampling. Do not reuse either rejected upper flute
  source.
- Preserve the accepted p88 pad source below the top zone and derive a 2x-base
  high source offline so the S-SMP no longer performs the harsh conversion.

The original captures remain immutable evidence under
`build/fate-instrument-auditions-round2-f9c1dd17c051c5c1/`.
