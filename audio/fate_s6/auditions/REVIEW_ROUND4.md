# Fate S6 isolated instrument review — round 4

ROM SHA-256: `5d097a9489ae83bc91bba8c9b6cff3b4db50d59918aee058149113b5bc7f4eae`

The listener reported that several intervals felt off by more than a cent, while
explicitly noting that the intended notes were unknown and the estimate was not
measured. That concern triggered the first objective pitch audit.

The initial audit incorrectly interpreted TAD octave numbers one octave high.
TAD defines C4 as middle C, so the reported octave-low flute/pad conclusion was
invalid. Reanalysis with the compiler's canonical note map found every sustained
note at the intended octave. Captures were uniformly about 2.2 cents above the
nominal 32 kHz reference because Nexen was configured for a 32,040 Hz SPC clock.
After that clock was accounted for, all 16 notes were within 0.65 cents.

Round four therefore has no listener timbre verdict. It was superseded by round
five so the duplicated-block loop hack could be removed before asking for more
listening.
