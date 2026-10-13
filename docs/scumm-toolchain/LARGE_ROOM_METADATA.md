# Large SC5LIVE room metadata

## Result

The whole-source DOS-CD package compiler now emits SC5LIVE v3, retaining the
existing v2 decoder compatibility. V3 replaces the dense box_count-squared
portal index matrix with sorted (source * box_count + destination,
descriptor_id) rows and deduplicated seven-byte portal descriptors. Native
portal lookup uses the same representation without expanding it.

This is a storage reduction, not a large-record loader. The current native
transaction still reads one complete record into the 3,132-byte pending buffer,
validates it, retires the outgoing room at the existing lifecycle boundary,
and copies it to the 4,096-byte active record. The generated per-2-KiB chunk
checksums are host-side preflight evidence only; the runtime does not consume
them. The readiness report says so explicitly.

## Canonical corpus measurements

The clean compiler run against the external DOS-CD profile represented 4,108
semantic executable identities with 2,203 selector-bearing ProgramUnits, and
emitted SC5LIVE for all 96 indexed rooms. The maximum compact v3 SC5LIVE record
is 11,237 bytes (room 66).

Twenty-five records exceed the native pending capacity of 3,132 bytes:

10, 16, 23, 29, 32, 33, 40, 43, 46, 48, 50, 51, 55, 59, 66, 67, 72, 78, 85,
86, 87, 88, 91, 92, 95.

The other 71 room records fit the current whole-record transaction. The
resource-less room-0 lifecycle is separately represented; it is not an
SC5LIVE record.

Room 66 has 61 walkboxes, 37 objects, 13 verb entries, 17 locals, and 23
bundle references. Its largest sections are the 5,011-byte sparse portal
directory and 3,721-byte route matrix. Room 43's 4,096-byte route matrix alone
fills the active record, while the complete record is 8,962 bytes. Therefore
the limitation is not just a redundant dense portal matrix or an incorrectly
small source length field.

The active 4-KiB record is an explicit alias of the video layout's reserved
tail. The 3,132-byte incoming record shares the audited backend BWRAM
allocation. Together they account for 7,228 bytes during the existing
transaction, before palette staging and the separately-owned visual surface.
Neither allocation may be enlarged by overlapping interpreter state or Mode-3
working memory.

## Consumer and transaction boundary

The SCUMM runtime has direct consumers indexed from SCUMM_LIVE_ROOM_BASE:

- Object/verb and object-walk dispatch reads the active record.
- Room-local and bundle lookup reads the active record.
- Walkbox geometry, routes, and portals are read by movement callbacks.
- Object state and names are also projected into their existing mutable engine
  tables during installation.
- Flags are copied into the mutable walkbox table; matrixOps may mutate them.

The SAME package CRC currently authenticates a whole SC5LIVE record before the
record is published. The pending room must remain intact while EXCD and
pre-commit checks run. Simply fetching successive chunks into the same pending
window cannot both preserve the outgoing room and make the incoming complete
record available to the existing direct consumers.

Supporting all 25 oversized records therefore requires a generic
section-aware transactional consumer: package descriptors and checksums for
individually addressable sections, a pre-commit validation protocol, and an
installation policy that either materializes tables into their existing
engine-owned structures or retains bounded immutable sections for live
queries. A second fetch must be independently checked; a section may not be
published before its own validation. If installation can fail after outgoing
retirement, the engine must enter the existing explicit failure state rather
than claim rollback.

This work is not implemented by the chunk metadata. No hidden ROM fallback is
added. The current complete-corpus readiness remains NOT_READY; a room whose
SC5LIVE fits is only metadata-loadable, not necessarily semantically or
visually playable.

## Build artifacts

The source package and per-room preflight are generated under ignored build
directories from the user-supplied archive. They are not source assets and are
not committed. The preflight records source hashes, serialized table sizes,
native consumer descriptions, and the exact pending-capacity result for each
room.
