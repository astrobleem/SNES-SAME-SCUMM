# Fate sound 154 isolated AdLib review

Source files: `build/fate-sound154-adlib-auditions/`

## 01_patch00_ch09_scale.wav

- Verdict: expected percussion/noise character; exclude from melodic BRR zoning.
- Listener description: “sounds like a crash or static or something.”
- Technical context: this is the channel-9 definition, and sound 154 contains no
  channel-9 note attack. The scale deliberately exposes the patch but is not a
  claim that it is a pitched melodic instrument.

## 06_patch05_ch06_scale.wav

- Initial verdict: low-end popping/cracking.
- Audit finding: the first listener WAV began inside the first nonzero attack,
  introducing an artificial file-boundary pop despite unclipped source PCM.
- Correction: the file was recut with 255 ms of verified near-silent pre-roll.
- Status: low octave requires re-listening. Any remaining crackle is native to
  the Nuked-rendered definition and disqualifies that octave from BRR zoning.

## Whole-cue production A/B

The corrected channel-6 audition passed and the canonical candidate is built.

- Reference: `build/fate-sound154-source-reference/fate-sound-154-adlib-nuked-reference.wav`
- Candidate: `build/scumm-s6-tad-sound154-67daeb570fefb30b/fate-sound-154-tad.wav`
- Rejected predecessor: repeated hard-edged attack clipping; maximum adjacent
  PCM jump 2,260 versus 644 in the Nuked reference.
- Correction: 256-sample phase-correct attack prefixes and predictor-continuous
  BRR loops removed the repeated hard attack transients. The current
  oracle-level candidate's maximum adjacent jump is 846 versus 657 in the
  Nuked reference.
- Second correction: the SCUMM AdLib driver's nonlinear operator attenuation
  replaces linear `velocity * CC7`. This restores the velocity-1 G5/G6 finale,
  while `V96` normalized-source calibration matches oracle headroom (12,324 vs.
  12,055 peak, with zero clipped samples).
- [ ] pass
- [ ] wrong timbre/layer balance
- [ ] audible loop or clicking
- [ ] strained zone
- [ ] attack/release problem
- [ ] timing differs musically
- Notes:
