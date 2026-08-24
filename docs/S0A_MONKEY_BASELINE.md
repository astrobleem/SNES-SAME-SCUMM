# Archived supplied Monkey binary observation

Observed on 2026-08-22 in MCP-enabled Nexen before the project adopted fully
independent SCUMM gates. This is a **forensic inventory of a known-broken ROM**,
not a gate, baseline, regression target, or semantic oracle. Nothing in this
document is a downstream pass condition. The lengthy run is not scheduled for
repetition.

## Exact inputs

The launch bundle is `/home/chad/SuperMonkeyIsland-pcm`, kept together so Nexen
can resolve adjacent MSU-1 assets.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `SuperMonkeyIsland.sfc` | 8,378,453 | `89090a712861492b2573812c220e2dd77d241c9e1b55c87e1e126207132fe803` |
| `SuperMonkeyIsland.msu` | 3,182,080 | `b2da89560389496968b11eaf9dca01699bb8884189c1d75c365aeee29fa240b2` |
| `SuperMonkeyIsland.sym` | 680,177 | `ede3933e989292fef2490cf9a68707006221bc153db9e623d8d221ef2a7b2f96` |

The directory also has 4,324 valid `MSU1` PCM files totaling 1,689,537,620
bytes. Numeric tracks cover 151–162, 164–168, and 1086–5392; track 163 is
absent. The root-level ROM/MSU/SYM copies are byte-identical.

The supplied SYM matches the ROM vectors (`NmiHandler=$008000`, `Boot=$008055`,
`IrqHookUp=$00806E`) but its WRAM layout does not match current GitHub source.
For example, supplied `SCUMM.currentRoom=$7EF7E5`; current source documents
`$7EF967`. Therefore the binary, old copied checkout, and latest checkout are
three distinct references:

- supplied binary bundle: this archived observation target;
- `/home/chad/SNES-SuperMonkeyIsland`: older dirty copy at
  `640e48359c5a17a9edd3a0c2208d62180757a2c1`;
- `/home/chad/SNES-SuperMonkeyIsland-latest`: clean GitHub HEAD
  `3247641c38d00aa2ce5388708ab7301d43d865aa`.

The older commit is an ancestor of the latest commit. Neither source checkout
was edited by the observation tooling.

## Frame-exact observation

`tools/validate_s0a_monkey.py` powered on fresh, advanced 300 frames, then used
16 exact input windows: START held for 40 frames followed by 760 released
frames. Persistent controller overrides plus `run_frames` actual-progress
accounting avoid Nexen's approximate legacy `set_input` timing.

| Video frame | Input checkpoint | Room | Observed image |
|---:|---|---:|---|
| 300 | boot | 10 | black transition |
| 1,100 | START 1 | 10 | title screen |
| 1,900 | START 2 | 38 | campfire intro |
| 2,700 | START 3 | 96 | Part One / The Three Trials |
| 3,500 | START 4 | 33 | dock scene and verb UI |
| 13,220 | START 16 | 33 | dock scene; engine still running |

The extra 120 frames are the pre-save settle. The scene sequence is visually
coherent through the dock. Room 33 remains active for the rest of this scripted
run. The exception hook never fires, `excErr=0`, `excPc=0`, and the final CPU
state is `Running`.

This is the observed boundary, not a claim that the dock or later game is
correct. START-only input does not walk Guybrush, select verbs, traverse an
exit, exercise dialog, or reach the user's known-bad post-dock behavior.

## MSU and audio evidence

The short `--deep-msu-hooks` probe proves the ROM reads the `.msu` data file. At
frame 19 it seeks offset zero and reads 31 bytes containing
`S-MSU1SUPER MONKEY ISLAND`, version/index fields, and the first room-count byte.
At frame 188 it selects track 1086, writes PLAY, and sets volume 255; it stops at
frame 228.

Track 1086 is a 1,764-byte, roughly 10 ms silent placeholder, SHA-256
`5d5ac17f8c3105d1c97648a95538fd5aaccaead360512074a990e5204a12d995`.
The full-run stereo capture is nevertheless nonzero (48 kHz, 222.964 seconds,
peak 18,579, RMS 1,323.405). This proves audible mixed output during the intro;
it does **not** prove talkie speech or a non-silent MSU PCM track.

## Save/reload evidence

At room 33, save/reload restores the captured SCUMM WRAM, upper WRAM, VRAM,
CGRAM, and OAM digests exactly. The immediate framebuffer differs by 337 pixels
in a 24×81 strip at the left-edge Guybrush sprite even though those memory
digests match. This records an emulator output-frame history caveat rather than
hiding it.

`tools/validate_s0a_monkey_save.py` loads the same state twice and advances both
branches exactly 180 frames. The two settled branches have identical memory
digests and identical screenshots. The state is therefore a deterministic dock
replay checkpoint after advancement, not an immediately pixel-exact framebuffer
restore.

## Evidence artifacts

| Artifact | SHA-256 |
|---|---|
| `build/s0a-monkey-89090a712861492b/report.json` | `cf37dc199d0fe639b1f196fcafdc7e7bfed57b2580a6ab5ea58455539e5ed04e` |
| `build/s0a-monkey-89090a712861492b/dock-frontier.mss` | `edbb5724031225392ec7376a278c4325d0087e64a55a9f451d68d097d6d6b83c` |
| `build/s0a-monkey-89090a712861492b/intro-through-frontier.wav` | `6275eb5099c0f9a77c130112e114109f1be09fc8186a04a33fad06262a65ca04` |
| `build/s0a-monkey-89090a712861492b/contact-sheet.png` | `f832b2bffd6832177544b233177b77b1d89be1750e1b5b0c44a8aee57a46015d` |
| `build/s0a-monkey-save-89090a712861492b/report.json` | `adb44e7e52af52b775b82e25b0149e53524cc4aade1df4b7179278fb16760d1d` |
| `build/s0a-msu-probe-89090a712861492b/report.json` | `31f2c7b0f2eb607ddf97e8019de3c28874ce648bf44339d5ccb67ee2870c5c8d` |

This record closes the Monkey investigation. There is no S0B gate. Future SAME
SCUMM work is accepted with copyright-free fixtures and upstream opcode
semantics; Monkey may be examined only when a narrowly identified compatibility
question actually requires it.
