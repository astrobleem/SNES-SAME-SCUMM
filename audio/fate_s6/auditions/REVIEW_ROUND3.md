# Fate S6 instrument review — round 3

Reviewed by Chad on 2026-08-24 from real Nexen S-SMP/DSP captures of ROM
`018b78b08fdcf27b4bf44ea5bb8e31c2f7278df0cdd89e6806cb1913bbf14430`.

## Decisions

- Organ: hard reject. An audible seam begins around 13 seconds despite use of
  one source, proving that the source's own long loop is exposed at higher pitch.
- Flute: hard reject. The 2x zone enters around 11 seconds and is extremely
  grating; offline octave resampling preserved or magnified the loop defect.
- Atmospheric pad: hard reject. The first sustained note is acceptable, the
  second exposes a seam, the third clicks, and the high zone clicks severely
  around 11 seconds.

## Engineering response

- Discard every round-three octave-derived source.
- Stop treating an arrangement-reviewed long MT-32 loop as an isolated-instrument
  acceptance source. Long chorus/modulation loops can hide in a mix but remain
  periodic artifacts in dry sustained notes.
- Derive phase-averaged single-cycle wavetables from the accepted timbres. Make
  every cycle exactly one BRR-aligned period and use TAD's loop-safe duplicated
  block mode. Derive upper zones directly from the averaged phase waveform,
  rather than accelerating a flawed long loop.
- Keep locked marimba, bass, and percussion unchanged.

The failed captures remain immutable evidence under
`build/fate-instrument-auditions-round3-018b78b08fdcf27b/`.
