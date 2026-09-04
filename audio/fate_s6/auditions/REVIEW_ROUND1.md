# Fate S6 instrument review — round 1

Reviewed by Chad on 2026-08-24 from real Nexen S-SMP/DSP captures of ROM
`f8d06bd49fe6a81581c1bd27a1f19fcc91deb3ab28ea7045746a41470c53d9c4`.

## Decisions

- Organ: reject. The transition/gaps become audible near 14 seconds and grow
  increasingly obvious toward the end.
- Marimba: reject the low zone. It sounds floaty or echo-like; the high zone is
  acceptable.
- Flute: reject the high zone. Around 14 seconds the tail/loop fails; everything
  after that point is unusable.
- Atmospheric pad: reject the low zone and transition. The first 0–12 seconds
  are grating; the main zone begins sounding relatively normal around 12 seconds.
- Soft bass: pass and lock. No adjustment requested.
- Kick/snare percussion: pass and lock.

## Engineering response

- Preserve bass and percussion byte-for-byte.
- Move organ to its exact MI-reviewed A3/A-sharp-3 boundary and replace the
  failing main source with the reviewed generic MT-32 organ source.
- Remove the rejected low marimba source; the reviewed main sample already has
  an MI-approved octave-2 range.
- Move flute to its exact MI-reviewed D-sharp-4/E4 boundary and replace the
  rejected high candidate with a compact Phantasia flute candidate.
- Remove the rejected pad-low source and test the acceptable main source across
  the required lower range before considering another sample.

The original captures remain immutable evidence under
`build/fate-instrument-auditions-f8d06bd49fe6a815/`.
