# Fate S6 instrument auditions

These dry, isolated songs are listener-facing acceptance tests for the first
Fate instrument bank. They reuse samples from the user-authorized
`SNES-SuperMonkeyIsland` audio library. Melodic tests expose the low/main sample
zones separately and repeat notes across the proposed boundary. The bass test
deliberately extends one octave beyond its MI-approved range. The percussion
test presents isolated velocity steps before a simple kick/snare beat.

Review each emulator capture with one or more verdicts:

- `pass`
- `wrong timbre`
- `low strained`
- `high strained`
- `transition audible`
- `out of tune`
- `bad loop`
- `attack/tail problem`

Add a timestamp and a short note whenever possible. These verdicts determine
the final program-to-zone map; passing compilation alone does not approve an
instrument.

Round-one listener decisions are preserved in `REVIEW_ROUND1.md`. Bass and
percussion passed and are locked. That pass led to corrected MI boundaries and
removal of the initially rejected source zones.

Round-two decisions are preserved in `REVIEW_ROUND2.md`. Marimba joined bass and
percussion as a locked keeper. That pass led to a seam-free organ attempt and
offline octave preprocessing for flute and pad.

Round-three hard failures are preserved in `REVIEW_ROUND3.md`. Round four's
pitch concern and the corrected objective audit are preserved in
`REVIEW_ROUND4.md`; TAD's C4-middle-C convention proved there was no octave
error. Active round-five MML retains the phase-averaged exact-period wavetables
but replaces the duplicated-block hack with filter-reset loops, which TAD
documents as guaranteeing a perfect loop. Every sustained capture must also
pass the automated clock-corrected pitch gate before listener review.

Round-five decisions are preserved in `REVIEW_ROUND5.md`. Organ, flute, and pad
pass as usable sounds, with the explicit caveat that the periodic sources have
little texture. Isolated-bank review is closed; subsequent refinement happens in
complete musical cues.
