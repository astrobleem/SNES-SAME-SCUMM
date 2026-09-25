# Phase 6E — authentic room-49 backdrop-only presentation

## Scope and preflight

Classification **B** applied: the host `ScummV5Room` decoder already produced
the complete 640×144 INDEX8 backdrop and 256-entry RGB8 palette, while the
production cooker retained only the semantic ROOM record. Phase 6E adds a
source-neutral visual record and target delivery; it does not add actors,
costumes, text, verbs, cursor, or dynamic camera redraw.

The authoritative host projection for the accepted initial frame is:

```text
room/generation:       49 / 1
logical source:        640×144, pitch 640
source rectangle:      (192,0) 256×144
physical destination:  (0,40) 256×144
clear index:           0
```

The backdrop is restored and actors/costumes are composed on the host logical
surface before projection. Runtime text is a logical overlay composed before
that projection. Phase 6E intentionally takes the decoded backdrop before
either visual layer and projects it once during forced-blank boot.

## Resource contract

`SC5VIS` schema version 1 contains INDEX8 width, height and pitch, a complete
256-entry RGB8 palette, a complete linear pixel payload, a row directory, the
archive/index/data/ROOM identities, decoded payload identities, and a complete
record identity. It contains no crop, SNES tile data, CGRAM image, actor, text,
or cursor data. Authentic payloads remain generated under `build/` from the
user-supplied archive.

Target delivery uses one 24-bit pointer per source row. No row crosses a LoROM
bank boundary. Authentic room 49 is segmented as follows:

```text
bank $10: rows   0..50, 32640 bytes
bank $11: rows  51..101, 32640 bytes
bank $12: rows 102..143, 26880 bytes
bank $13: visual directory, palette, and 144 row pointers
```

The generic target facade validates and resolves by room identity, checks the
Mode-3 surface lock, clears the fixed display surface, computes the established
centered viewport, copies rows through bank-safe pointers, copies all 768 RGB8
palette bytes, and publishes `SURFACE_DIRTY`, `PALETTE_WRITE`, and `PRESENT`
through the normal SAME event queue.

## Initial lifecycle

```text
forced blank
→ normal M23A Storage READ for room 49
→ normal room semantic installation
→ generation-owned visual lookup
→ clear + backdrop blit + RGB8 palette copy
→ three production video events
→ one event drain (no SCUMM logical frame)
→ production Mode-3 conversion and channel-7 DMA batches
→ generation 1 committed
→ display enabled
→ normal SCUMM frame loop begins
```

This required 896 runtime tile conversions and 30 committed DMA descriptors
(29 character/palette batches plus static tilemap setup). No phantom SCUMM
logical ticks were introduced.

## Authentic provenance and evidence

```text
archive SHA-256:       558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798
PLAYFATE.000 SHA-256:  4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9
PLAYFATE.001 SHA-256:  e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240
ROOM 49 SHA-256:       fbf234f2ffe3530ba365980abfae556636d83e5cada9bdc649c43d4cce7242f6
decoded pixels:        16825b7347336ae512c1f4e13053fd599ae1b6fcd9cd3996b51ed150c5851f72
decoded palette:       8747a8331e54aeb371292fc6770db3566b28af0eb31418cc73273aefd7ec471a
cooked visual record:  51d851605e721e5c03d9ca7d85f4a2dbd3ea3cf812701a6861890e3f0d91446b
```

Fresh Nexen, fresh power-on, and zero debugger writes produced:

```text
new production ROM:    d9b31598c794d3726082bff07c8ce481042e5c1449f54bd3e4462dfb7d755584
live INDEX8 surface:   ddafb02158bc47e59c5d01f0a27dfb826948594cdcee8b2684c9fe4335a2528a
live RGB8 palette:     8747a8331e54aeb371292fc6770db3566b28af0eb31418cc73273aefd7ec471a
tile shadow / VRAM:    a9d99ceb3408996d77742ebc2f53fa545d89e78e29dee57638d148eca44e3102
tilemap:               f8a259423a98274f819f0d957364a390fdef4161271e911eeb077e960a34d4e4
CGRAM shadow / CGRAM:  6433d8ed1927a90517418bf63067a18283bf4ffcccbd267e395505a260e379fd
reference PNG:         c43a0838afad29febd19c806122e25e116bc2f3269720d9fa8abfce17dcd59ce
emulator PNG:          c43a0838afad29febd19c806122e25e116bc2f3269720d9fa8abfce17dcd59ce
visible pixel diffs:   0
```

The Mode-3 registers remain `BGMODE=$03`, `BG1SC=$70`, `BG12NBA=$00`,
`TM=$01`, `TS=$00`, `BG1HOFS=$0000`, and corrected `BG1VOFS=$03FF`.
SA-1 architectural state stayed at reset (`K:PC=00:0000`) throughout.

The same generator, room-install hook, surface facade, event queue, backend,
NMI, and DMA path also passed with a copyright-free 320×224, pitch-328 room-1
fixture. Its production ROM is
`4cec48fe3798f94d01f9e6c129104d4a01e9da00c61a1cddf5d8de1a2c87ce72`;
the independent reference and emulator PNGs are both
`2ca750d1e2c90302c116fb375abfb494d5cf7cd50d121d503bbb7da0daa4eba3`
with zero differing pixels.

The M25 semantic probe remained exact: all established box transitions, the
91-tick movement, 91 blocked waits, `getDist=0`, object 596 verb 10,
`chainScript(211)`, and LSCR 211 execution still reach the unsupported
`room.49/LSCR.211 +$026E: B2 02 00` (`setCameraAt(Var[2])`). The validator now
accepts both the legacy-invalid and Mode-3-valid carrier control records; every
semantic, carrier-control, and SA-1-reset assertion passed.

This is an **authentic room-49 backdrop-only presentation**, not a fully
rendered room or playable visual frame. The live surface is not updated for
the later actor walk, messages, or camera state.
