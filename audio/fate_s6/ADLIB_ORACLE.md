# Fate S6 AdLib oracle

Sound 154 now has an isolated DOS AdLib reference produced by ScummVM's SCUMM
iMUSE driver with its Nuked OPL core. This is the playback oracle for the `ADL`
rendition; it is independent of SAME's TAD conversion.

## Exact inputs

- Fate demo archive SHA-256:
  `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`
- Raw `sound.154` SHA-256:
  `d7a8f530d75b64e878def8ff61834748993d3c16331261106013483eaae9ded0`
- Extracted ADL SMF SHA-256:
  `e549ff7f85a3f450fe8829d1e697e5a734823588ba70ef5d32a259b2c8d9e647`
- ScummVM commit: `10a54c2696126a81ee2b2f7f10b1a8be90ed7711`
- ScummVM oracle patch: `tools/scummvm_fate154_adlib_oracle.patch`
- OPL selection: `--music-driver=adlib --opl-driver=nuked`
- Capture format: SDL disk driver, stereo signed 16-bit little-endian, 44.1 kHz

The resource contains six complete 30-byte iMUSE `$10` AdLib instruments. It
also contains an unconditional `$30` jump at 148,806 microseconds from tick 100
to beat 5/tick 0. Consequently canonical playback skips the score's long setup
silence; this is intentional and differs from a naive linear SMF render.

## Result

`build/fate-sound154-source-reference/fate-sound-154-adlib-nuked-reference.wav`

- 469,387 stereo frames
- 10.643696 seconds
- peak: -8.69 dBFS in the untrimmed capture
- SHA-256:
  `b35f72d3153ce5fef282d62cc1204346f71079a143cb6dd9fcf23c289b0e44f3`

The finalizer removes only host-startup silence, restores the exact 148,806-us
iMUSE lead-in, and retains one second after the last sample at magnitude 16 or
greater. It does not normalize, compress, or otherwise alter the captured PCM.

## Isolated patch auditions

The first production-bank gate now renders all six sound-154 `$10` definitions
through the same pinned iMUSE/Nuked path. Each file plays MIDI C2, C3, C4, C5,
and C6, with isolated attacks and release gaps:

`build/fate-sound154-adlib-auditions/`

The patch bytes are not stored in this repository. Generate the 186-byte local
input from the user-supplied demo, apply the audition-only ScummVM patch, capture
with SDL's disk driver, and finalize it with:

```bash
PYTHONPATH=src python3 tools/extract_fate_adlib_patches.py \
  --archive /home/chad/fatedemo-box.zip --sound 154 \
  --output /home/chad/fate154-adlib-patches.bin
git -C /home/chad/scummvm apply \
  /home/chad/SAME-0.2.0/tools/scummvm_fate154_adlib_auditions.patch
PYTHONPATH=src python3 tools/finalize_fate_adlib_auditions.py \
  build/fate-sound154-adlib-auditions/all-patches.raw \
  build/fate-sound154-adlib-auditions
```

The extracted-record SHA-256 is
`ef977c444e5a63843aae29b2bd9ff733a39a85d2aa811d7077cd6a94c8734b5f`.
The raw capture SHA-256 is
`9c63b135ce9d3e0a26c3db1cd894024950427bd357ed578b98b702f8d64822fb`.
Exact segment PCM identities and the listener checklist are in `report.json`
and `REVIEW.md` beside the WAVs. SDL disk audio does not advance at the same
rate as the harness's wall-clock delays; the finalizer therefore uses measured
audio onsets, not nominal timestamps.

This gate deliberately precedes BRR zoning. The original score uses melodic
channels 1, 2, 4, 5, and 6; channel 9's definition is retained for completeness.
Low-volume channels are texture layers and must not be discarded merely because
their MIDI velocities are small.

The first listener pass identified channel 9 as the expected crash/static-like
percussion definition; sound 154 never triggers a note on that channel, so it is
excluded from melodic zoning. It also exposed a bad segment boundary on channel
6: the original file began inside its C2 attack. The corrected channel-6 WAV has
255 ms of near-silent pre-roll and no clipping. See
`audio/fate_s6/REVIEW_ADLIB_SOUND154.md` for the continuing verdict record.

## Production SNES arrangement

The accepted lane now uses five independent per-patch captures (`--boot-param`
1 through 5), so no preceding OPL release leaks into a source. Seven BRR-aligned
zones cover only pitches the cue plays: channel 1 low/high, channel 2 mid,
channel 4 mid, channel 5 high, and channel 6 low/high. Loops retain 2,048..3,968
samples of slow OPL texture instead of collapsing each source to one period.
Exact local source identities and seam scores are in
`audio/fate_s6/samples/fate154_adlib_manifest.json`.

`tools/convert_fate_adlib154_to_tad_mml.py` flattens the canonical `$30` path.
It begins at the real 148,806-us jump, preserves all 26 post-jump attacks and
active-note CC7, retains five channel timbres, and fails if more than eight
voices overlap. The former ROL arrangement incorrectly retained the skipped
2.857-second setup delay.

Volume conversion follows the SCUMM AdLib driver's operator attenuation rather
than multiplying MIDI velocity by CC7. The driver uses each patch's waveform
volume-sensitivity bits and a nonlinear lookup table. Sound 154 channel 5 has
zero sensitivity, so its velocity-1 G5/G6 finale is intentional and audible;
the former linear conversion incorrectly reduced both attacks to TAD `V1`.
The BRR loops are normalized during extraction, so the reconstructed reference
level is `V96`, calibrated against the unnormalized whole-cue oracle.

Fresh real S-SMP/DSP evidence:

- ROM SHA-256:
  `67daeb570fefb30b6db540ef0618fdf7daf35ebe74939e94ce93c57ed8a63514`
- report SHA-256:
  `414e50f659feeb9754e37fb27602800c8ae2c310994e5cf3fa266419ae856f1d`
- first/last audible: 0.496 / 9.939 seconds
- video/SAME frame advance: 840 / 840
- rejected TAD requests: 0
- candidate/oracle PCM peak: 12,324 / 12,055; clipped samples: 0 / 0

Listener comparison:

- Nuked oracle:
  `build/fate-sound154-source-reference/fate-sound-154-adlib-nuked-reference.wav`
- real S-DSP candidate:
  `build/scumm-s6-tad-sound154-67daeb570fefb30b/fate-sound-154-tad.wav`

The first integrated candidate was rejected for hard-edged clipping. Its WAVs
began on arbitrary nonzero OPL phase and produced repeated attack transients up
to 2,260 PCM units per sample. Each source now has a BRR-aligned 256-sample,
phase-correct fade-in followed by a predictor-continuous loop. After nonlinear
volume correction and oracle-level calibration, the maximum adjacent jump is
846; the current Nuked reference measurement is 657. This comparison is a
transient diagnostic, not a substitute for listener acceptance.
