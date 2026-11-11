# Native multibit text integration — Milestone B in progress

The source-font rasterization gate passes. Authentic verb/object interaction
remains unverified; this is not a completed gameplay milestone.

## Implemented

`surface_index8` extends the existing text-service facade, indexed surface,
dirty packet producer and NMI-owned Mode-3 presentation. It uses a declared
32-row UI viewport, rather than overlapping live-room metadata with the older
BG2 allocation. Room projection reserves that viewport explicitly. Actor
composition clips at its boundary; cursor restoration participates in damage
publication. Legacy configurations retain their existing overlay selection.

Five original source charsets fit as CRC-checked SC5FNT v2 records plus a source-ID
directory in one ROM bank: 29,146 bytes. Their original 1/2/4-bit source slots,
signed bearings, advances, and byte-sized glyph dimensions survive cooking.
Source slot zero is transparent. Other slots can map to opaque color zero;
text ink and palette colors are not masked to four bits. Missing charset IDs
fail explicitly. Original zero-offset glyphs draw nothing and advance zero,
as in classic prepareDraw/getCharWidth; no adjacent font or fabricated advance
is substituted. The synthetic scene golden hashes change for its absent space
because the former renderer invented a four-pixel gap.

128 bytes at $40:0780–07FF hold raster scratch, request ownership and generation
fence, with mechanical ownership validation. No new framebuffer is allocated.
The old BG2 configuration at $41:F000 is rejected when live SC5LIVE metadata
owns that range. Text bytes/style are captured before a busy surface can delay
consumption. The visible lifetime waits for the actual presentation generation;
hide requests persist until the surface becomes writable. Room/generation
checks prevent stale requests from writing the next room.

`initCharset` updates default string slots 0 and 1 as well as C7 state. C17 HUD
caption lookup rejects uninitialized, absent, hidden and dim verbs; it never
restores authored saved-away verbs. Native talk scanning consumes complete
encoded controls and separates glyph timing from raster byte lengths. Host
text supports multibit source slots, multiline controls, inline ink/charset
selection and exact charset identities. Unknown controls remain explicit.

## Native evidence

A data-only synthetic SCUMM driver displays `SAME text 24` using authentic source
charset 2 over the source room and real costume. It is a graphics diagnostic,
not authentic dialogue or gameplay. No guest acknowledgement or action was
injected. Private evidence: `/tmp/astra-font-native-text-fence-20261110`.

- rom_sha256: `ae55e5785ba90ce513c0a8c9fe57283bf483cd186a0337e16a6d16715f15202f`
- map_sha256: `1d0a3c073acb98eb122dd2be2a4971052fa162fbcd01e9f90fa041cf21a28d09`
- package_sha256: `9de63ae5247247a33c28a4fa1e85e85fce0adf4422f4586600dfd9dd0982ad15`
- build_identity_sha256: `18eb60eaa0e62178141b8e467037f0accb912ad80283082f5e28495f8c067a8d`
- audit_sha256: `bd73798c7c73cb75f9b980306f947a813472dad9c796bf9cac53fc2c4150eb13`
- source_font_sha256: `ce86c2b63044a2399762c0b849af0a30e9074be904218c4ec57239c471d06629`

Source/INDEX8 differences: 0. Source/decoded VRAM differences: 0. Actual captured
text RGB differences against CGRAM: 0. The observer requires a matching completed
**visible text** generation; a later hide or unrelated actor generation cannot
pass. It allows the existing scene to continue animating. The capture preserves
the emulator's full image rather than assuming its screenshot height is always
224. Earlier failed diagnostics remain private and are not upgraded to passes.

The accepted image was assembled from an isolated dirty-source snapshot before
the subsequent encoded-control scan and absent-glyph corrections. Those later
changes have source/host tests and a separately assembled authentic build; do
not transfer this narrow native result to every behavior on a later commit.

## Validation and limitations

1,401 tests ran: 1,389 passed, 12 skipped. `make validate` passes, including Poppy
lint and WRAM/BW-RAM ownership. The native diagnostic and authentic build use
the pinned Poppy DLL and pass ROM/map audits. Hosted CI is separate pending
publication evidence; no hosted Nexen claim.

The indexed native producer retains at most 255 encoded bytes per request.
Longer-message delivery, runtime charset-map
mutation, multiple distinct UI regions, inventory presentation and general
style layout remain incomplete. The current small UI raster supports newline,
inline color and charset, with clipping/wrapping; it does not certify every
SCUMM inline control or every glyph/font natively. Do not force verbs active to
conceal authored startup behavior. Whole-game readiness remains NOT_READY.

## Authored subtitle and replacement ownership correction

The indexed path now reserves $7F:FB80–FC7F for retained encoded message bytes
and $7F:FC80–FD7F for the immutable queued copy. These follow the one-record
18-byte geometry work area and precede actor walkbox state; the mechanical
ownership audit checks the boundaries. The legacy 32-byte path is unchanged.

Replacement retires the old talk owner before scanning the new message so
Stop cannot erase the new HAVE_MSG value. An outstanding text request retains
its message generation and is discarded before writes when superseded. Text
service observes backend completion before actor composition can claim the
newly writable surface. The lifetime starts after its own presentation fence.
Speech-cue words remain encoded, do not rasterize, and set a separate unavailable
voice-realization witness. This does not claim speech playback.

A read-only native checkpoint control captured the original authored room4
subtitle, without synthetic bytecode, gameplay writes, or controller input.
Original font2 interpretation, active INDEX8, decoded VRAM and actual screenshot
RGB against CGRAM all agree exactly. Local evidence is
`/tmp/astra-authentic-dialogue-direct-20261110/observations`; runtime 25.060s,
normal process-tree cleanup. It is dialogue evidence, not an object interaction.

ROM SHA256: `e47a904ed8c2c6e1540d359ee3f62ab1339f346a0da88a811889e89cc9285084`.
Build identity SHA256: `af46470237b28d9d1c6bada4eccda3ae792ec57db6909fb3ef830e05a7d67873`.
The private build is an isolated dirty-source snapshot. The subsequent widened
PC-before diagnostic arithmetic fix has source-instruction tests but is not
part of this ROM. Earlier broad-observer timeouts/stops are not engine deadlock
or graphics-failure evidence and remain preserved.

Current local suite: 1,406 tests, 12 skipped; make validate passes, 27 bounded
ownership regions. Public source-instruction tests exercise long strings,
control operands, replacement state, request generations and frame ordering.
Object-name substitution, distinct UI responsibilities, runtime font-map
mutation, complete long-message pagination and actual object-action acceptance
remain open. Whole-game readiness remains NOT_READY.
