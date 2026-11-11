# Multibit text integration — unfinished

Milestone B has **not** passed its native text or gameplay gates. No new emulator
session or gameplay replay has been run for this change. Existing actor/walking
results remain bound to their earlier ROM identities.

## Implemented compiler boundary

`encode_charset(..., version=2)` explicitly opts into packed source slots for
1/2/4bpp glyphs. Default version1 output remains unchanged. Version2 retains
original dimensions and signed bearings; advance is width plus signed X bearing,
matching local ScummVM `CharsetRendererClassic::getCharWidth`. It does not clamp
negative bearings into a wider advance.

The original identity header is retained, with version2 and actual bpp. It is
followed by16 source-slot palette entries,256 directory entries and packed glyph
payloads. Directory entries use `<BhBBbbII`: presence, signed16 advance, byte
width/height, signed8 X/Y bearings, absolute32 record offset and length. Payload
slots are MSB-first, continuous across rows; unused final bits must be zero.
A trailing little-endian CRC32 covers all preceding bytes. The decoder rejects
CRC errors, overlapping/noncanonical payloads, invalid dimensions/counts,
unclaimed trailing data and malformed padding. Maximum record size is bounded.
The source SHA remains provenance, separate from transfer integrity.

Classic `loadCharset` copies15 resource colors beginning at resource offset14;
the provider removes the8-byte chunk header, so these are source offsets6..20.
Slot0 is transparent. Runtime ink replaces slot1. Nonzero slots mapped to color0
remain opaque. The bounded glyph oracle returns separate INDEX8 and opacity
planes, preserving this distinction and clipping signed bearings on all edges.
It does not interpret SCUMM string controls or claim multiline/message support.

The existing native include generator still requests version1. It cannot silently
rasterize version2 as a binary silhouette. There is no native version2 consumer
in this checkpoint.

## Private original-source measurements

Canonical external DOS-CD archive, unchanged:

| Source charset | bpp | Header height | Maximum glyph | Negative bearings | V2 bytes |
|---|---:|---:|---:|---:|---:|
|1|1|8|13×16|2|4655|
|2|2|10|39×10|106|5902|

Charset2's slot1 default is15 and slot2 maps to0. Its shadows therefore require
opaque black, not transparent holes. Records and detailed provenance remain in
`/home/chad/same-private-evidence/milestone-b-fonts`, outside Git.

## Native boundary still to implement

The present BG2 target is80×8 and emits palette group0. Merely enlarging that
buffer or removing the bpp check is insufficient. The captured authentic room
CGRAM has no opaque black alias in indices1..127 with a nonzero low nibble;
white is available at15. BG2 local zero is transparent. Truncating color indices,
dropping shadows, or substituting a font would be incorrect.

The implementation needs to connect this extended font data to the existing
indexed-surface/overlay composition, with explicit text damage/underlay ownership,
taller bounded layout, palette fidelity and completed-generation publication.
Any use of a reserved UI viewport must be a declared target layout, not an
assumption that every room has unused borders. No second renderer is proposed.

Authored verb lifetime is unchanged: room4 saves/disables its normal verbs.
The saved-bank observation does not authorize force-enabling them for a caption.
The eventual interaction must follow original scripts and normal controller input.

## Tests

Copyright-free tests cover300 randomized packed glyphs across all three depths,
signed advances/bearings, full-byte palette colors, opaque zero, clipping, missing
glyph rejection, CRC failure and CRC-valid malformed directories/padding. These
are host/compiler tests, not native acceptance or gameplay certification.
