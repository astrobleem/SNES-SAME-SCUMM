# M25 authentic Fate `$14 print` preflight

Status: **Phase A hard stop (category D)**. Production `$14` behavior was not
changed. M24R-B remains paused.

## Costume presentation remains blocked

Costume presentation has two independent blockers:

1. The supplied Fate demo does not contain the authentic `costume.45` payload.
2. The SNES costume presentation subsystem is not implemented.

No costume was fabricated, substituted, inferred, or pre-rendered. The
accepted integrated ROM remains:

```text
aae7a5e1ab8e249e356509c86523a7f2be287528ba7fe44529bb67e32e49b9ea
```

## Host costume-oracle correction

The generic host costume decoder formerly treated the cardinal angles as
direction indices. It now uses canonical v5 `newDirToOldDir` ordering:

```text
0 -> 3, 90 -> 1, 180 -> 2, 270 -> 0
```

The inclusive boundary order is `71..109 -> 1`, `109..251 -> 2`,
`251..289 -> 0`, and everything else `-> 3`. Copyright-free tests cover the
four cardinals and `70, 71, 109, 110, 250, 251, 289, 290, 359`. This correction
does not provide costume 45 or SNES costume presentation.

## Authentic instruction

The complete LSCR 200 has 460 bytes, so only 36 bytes exist from `+$01A8` to
EOF; a 64-byte dump cannot be produced without reading beyond the script.

```text
01A8  14 01 0F 57 65 6C 6C 2C 20 68 65 72 65 20 49 20
01B8  61 6D 20 6F 6E 10 54 68 65 72 61 2E 00 D2 01 00
01C8  0A D8 FF A0
```

Provenance:

```text
resource                 room.49/LSCR.200
script SHA-256           dc34f2d549455fbd6ee30eb057470b39e97e4544ff3cbe49d94424158e3cbc6c
original PLAYFATE.001    $05892F
original ROOM-relative   $00EE50
original chunk-relative  $01B1
cooked-record offset     $00F6B8
normalized/runtime PC    $01A8
```

Canonical decode:

```text
$14               o5_print, direct actor operand (parameter bit $80 clear)
$01               speaker actor 1
$0F               SO_TEXTSTRING
57 ... 2E 00      "Well, here I am on\x10Thera." + terminator
next PC            $01C5
```

The `$10` byte is literal text/glyph code 16, not an `$FF` embedded-control
sequence. Fate charset 1 defines glyph 16 as a blank 4x8 advance. There are no
embedded `$FF` controls and no speech-offset/length (`$FF $0A`) metadata, so
this call requests no digital speech sample.

The call selects persistent text slot 0's existing defaults but contains no
position, color, clipping, center, left, overhead, charset, or save-default
subcommands. The current SAME defaults are `(2,5)`, right edge 319, color 15,
charset 0, left aligned, and not overhead. Actor 1 is the speaker; its current
talk frames are start 4 and stop 5 and its talk color is 15.

The subsequent LSCR tail is:

```text
+$01C5  D2 01 00    actorFollowCamera(actor from Var[1])
+$01C8  0A D8 FF    startScript(216), no arguments
+$01CB  A0          stopObjectCode
```

LSCR 200 does not execute `waitForMessage` after this print. That does not make
the message lifetime optional: `VAR_HAVE_MSG` is global and other scripts and
canonical wait semantics can observe it.

## Why this is category D

Canonical slot-0 printing calls `actorTalk`, which immediately entails more
than text decoding:

1. select talking actor 1;
2. stop/replace any prior talk ownership;
3. start actor 1's talk-start animation unless suppressed;
4. set internal message state and `VAR_HAVE_MSG` nonzero;
5. decode/display the text and establish a talk delay;
6. decrement the delay from engine timing;
7. stop the message exactly once;
8. run the actor's talk-stop animation, clear talking ownership, and make
   `VAR_HAVE_MSG` zero.

For this English v5 resource the canonical initial `VAR_CHARINC` is 4. With a
base delay of 60 and 25 non-terminator text bytes, the unmodified, unwrapped
line establishes a 160-jiffy logical delay. The current SAME pre-Thera run has
not initialized `Var[37]` to that canonical value, so using its present zero as
a timer would be incorrect.

The current host `$14` implementation records a message and rasterizes glyphs,
but has no talking-actor ownership, `VAR_HAVE_MSG`, talk timer, or talk-start/
stop lifecycle. The current SNES C23 implementation records style plus at most
16 encoded bytes and fails with `SCUMM_ERR_STRING` on this 26-byte terminated
message. It likewise has no message lifecycle.

The smallest honest future dependency cone is therefore:

| Area | Required bounded behavior | Current status |
|---|---|---|
| Text decoding | Preserve the 26-byte terminated stream and `$FF` controls safely | Host present; SNES buffer too short |
| Message lifecycle | Start/active/timed completion/stop with generation-safe ownership | Missing host and SNES |
| Timing | Canonical `VAR_CHARINC`, base delay, engine-delta countdown | Missing |
| Talk actor | Actor 1 ownership plus talk-start frame 4 and talk-stop frame 5 | Missing |
| Font delivery | Authentic charset 1 is available to the host | Not cooked/presented on SNES |
| Glyph rasterization | Not required for headless script state, but required for any visual claim | Host present; SNES absent |
| Positioning | Existing slot-0 defaults; this call has no style subcommands | State exists |
| Speech synchronization | No digital speech requested by this line | Not applicable to this call |
| Script waiting | LSCR 200 does not wait, but global `VAR_HAVE_MSG` remains observable | Lifecycle missing |

Implementing only a larger text buffer would advance the PC while lying about
the actor-message lifecycle. Clearing `VAR_HAVE_MSG` immediately or inventing a
completion timer from current zero-initialized state would also be incorrect.
The preflight therefore stops before production `$14` changes.

This gate does not claim actor or text visual rendering.
