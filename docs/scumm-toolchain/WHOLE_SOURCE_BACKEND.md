# Whole-source SCUMM v5 backend and layout boundary

Status: **PARTIAL**. The compiler now emits and source-hash reconciles the
complete parsed executable directory, and a copyright-free multi-bank image
has assembled, passed ROM audit, and executed a previously unbound program in
Nexen. The canonical full FATE source is rejected by a deterministic LoROM
preflight before assembly because its directly addressed room/resource bytes
alone exceed the current cartridge mapping. This is not a whole-game
execution claim.

FATE remains an integration corpus. No FATE identities drive generic layout,
packing, or dispatch behavior.

## Implemented build boundary

- `tools/compile_scumm_v5_source_image.py` opens one source edition through
  the generic SCUMM v5 front end, cooks every indexed room, projects every
  selector-bearing ProgramUnit, emits a backend directory, and verifies each
  emitted body against its source identity and hash. The bounded selected
  route is no longer the definition of whole-source emission.
- A build output root must be fresh. Cooked-room inputs are read only from
  `manifest.json`; every listed record is path-contained and checked against
  its declared size and SHA-256. Unlisted stale `room-*.sc5c` files are not
  inputs. Generator split files are owned by a hash manifest: unowned or
  modified files cause a clear rejection, and only generator-owned outputs
  may be replaced.
- The Poppy input sidecar recursively hashes included assembly files and
  `.incbin` payloads. ROM, map, build identity, and generated inputs remain
  build-root-local. Independent builds use independent roots; a replay bound
  to one ROM cannot silently consume another build's generated tables.
- `strict` rejects non-certified ProgramUnits. The explicit
  `experimental-diagnostic` policy keeps unsupported/unverified semantics
  visible; it does not manufacture behavior or certify an executable game.
- `src/same/engines/scumm_v5/backend_layout.py` performs a pre-assembly
  capacity/address check and emits a byte-placement ledger. It distinguishes
  logical storage page, physical LoROM page, CPU bank/address, source offset,
  aliases, alignment, consumers, and generated machine-code sizes that still
  require a successful map.

## Canonical DOS-CD FATE source census

Input is the external `/home/chad/ATLANTIS.zip` archive with
`fate_of_atlantis_dos_cd.json`: game `indy4-fate-dos-cd-en`,
`DOS CD English, full voice (1993)`. The archive and derived source payloads
remain outside Git.

The fresh whole-source run discovered 96 indexed and parsed rooms, 4,108
semantic executable identities, 2,203 selector-bearing ProgramUnits, and
1,372 object resource records. The 2,203 units consist of 163 globals, 96
entry units, 96 exit units, 1,079 room-local units, and 769 object carriers.
All 2,203 directory entries and bodies were source-hash reconciled; the
source-emission check reports no missing, extra, or mismatched units. Passive
objects remain resource records, not selector units. All 59 object-verb
identities in room 7 remain represented within their owning object carriers.

This establishes source representation and backend body placement, not
runtime coverage. The lowering report classifies 55 ProgramUnits as
`LOWERABLE_WITH_EVIDENCE`, 2,144 as `UNVERIFIED`, and 4 as `BLOCKED`; strict
policy rejects this corpus. Structural/source coverage is not a substitute
for backend lowering, native conformance, asset support, or portable-state
certification.

The source census separately reports 617 resource entries inventoried, 104
parsed, and 85 unavailable. Room/object metadata is not equivalent to full
background/image conversion. Costume, charset/font, sound/iMUSE, complete
text rendering, and portable-state coverage remain separate requirements.

## Exact payload ledger and current target

The accepted target in this build path is ordinary LoROM (`$20` map mode).
`tools/finalize_snes_rom.py` rejects an assembled image above 4,194,304 bytes;
the carrier description and ROM audit validate the LoROM header, and the
runtime uses 32 KiB LoROM pages with mirrored CPU-bank windows. The supported
physical page capacity is therefore 128 pages / 4 MiB. A CPU bank number is
not an independent storage-page number: `$20` and `$A0`, for example, alias
the same physical LoROM page. Pages `$7E/$7F` are WRAM, not ROM.

The final generated ledger, after verified room-body and room-directory
aliasing, records:

| Payload class | Bytes | Accounting |
| --- | ---: | --- |
| Complete cooked ROOM records | 6,387,956 | Each source room record stored once |
| ProgramUnit source bodies | 1,000,867 | 774,373 bytes alias verified bytes in room records; 226,494 bytes are separately emitted |
| ProgramUnit body aliases | 2,011 units | Distinct semantic identities and provenance are retained |
| Generated lookup/navigation tables and non-aliased room directories | 737,250 | Includes 21,040 bytes of directory prefixes that cannot alias their room segment |
| **Non-double-counted placed payload** | **7,351,700** | Room records + separately emitted bodies + emitted tables/directories |
| Program-pointer directory | 11,015 | Subset of generated table payload |
| Resolver tables | 19,781 | Subset of generated table payload |
| Verified room-directory aliases | 86 / 123,248 bytes | References into room records; not extra ROM payload |
| Room-directory copies retained | 10 / 21,040 bytes | Prefix did not fit wholly in its source segment |
| Room page tail padding | 1,804 | Placement padding |
| Separate program page tail padding | 35,650 | Placement padding |
| Table page tail padding | 213,022 | Placement padding |
| Unclassified logical-span remainder | 1,310,720 | Runtime/header, generated code, allocation gaps, and reserves; not a payload lower bound |

The 663,223 bytes reported as exact script-body duplicates are a subset of
the 774,373 bytes safely aliased from complete room records. The additional
111,150 bytes are object-carrier/OBCD bytes also inside their complete room
records; the carrier and its multiple verb identities remain separately
represented in the directory. Equal body hashes never merge semantic
identities. Only source-verified immutable storage is shared.

The generated room-directory copy was another avoidable duplicate. Eighty-six
prefixes now resolve to their exact room-record bytes, reducing emitted
directory copies by 123,248 bytes and lowering the generated logical highwater
by four 32 KiB pages. Ten prefixes that cross the corresponding room segment
boundary retain a separate copy. No integrity check was removed.

Generated assembly source is 10,604,877 bytes / 223,814 lines; source text is
not machine-code size. A full-FATE assembler map does not exist because the
preflight rejects the placement first, so native runtime and generated
dispatch machine-code bytes are correctly `unknown`, not guessed from source
lines. The current layout requests a 272-page logical span (8,912,896 bytes),
which also exceeds the 256-bank 24-bit LoROM CPU-bank namespace. The layout
is a generator placement, not a theoretical minimum.

Preflight reports 127 out-of-capacity logical pages, 94 physical mirrored
overlap groups, 10 unrepresentable CPU-bank pages, and the highwater failure.
It rejects at the first 4 MiB boundary (logical page 128); for example,
`RoomResource(49)/segment-2` would occupy the physical page mirrored by
logical page 0. The issues are aggregated by page with source segments, rather
than emitted as thousands of pairwise assembler failures.

There is also an irreducible capacity result independent of layout quality:
the 6,387,956-byte cooked ROOM payload exceeds the entire 4 MiB cartridge by
2,193,652 bytes, before runtime code, directories, program bodies, headers,
or alignment. The final non-double-counted payload exceeds the target by
3,157,396 bytes before those unclassified runtime/code/reserved costs. The
usual generator reservation starts room storage at logical page 32, so the
usable payload budget in that placement is smaller still. Raising the image
size field, wrapping a bank, or truncating pointers is invalid and was not
attempted.

## Existing storage mechanisms and required boundary

`src/same/package.py` implements a host-side SAME package builder, inspector,
CRC verifier, and extractor. `src/same/resources.py` reads package sections
through host filesystem paths and caches them. These are useful compiler and
host-runtime tools, but they do not provide SNES ROM bytes beyond the LoROM
map. `runtime/snes/services/storage.pasm` is currently an ABI placeholder;
it does not implement package reads, MSU-1 seeks, or a general resource
stream. The current SCUMM bytecode and room consumers use directly addressable
ROM pointers. No external package/MSU-1 path can yet satisfy them.

Therefore the minimum follow-up is a generic SAME storage/read contract,
backed by a storage mechanism actually available to the target (for example,
a validated external data stream or a supported larger cartridge mapping).
It must map canonical resource/page offsets to checked reads, supply program
fetch and room-resource consumers, verify container/section integrity, bound
staging memory, and return explicit read/CRC failures. A package offset or
logical page number alone is not a CPU pointer. This milestone does not
implement that subsystem or assume an external device is already supported.

## Backend and native evidence

The copyright-free whole-source fixture has 191 ProgramUnits—more than the
178-selector pool—and emits all bodies plus canonical descriptors. A large
global body ends just before a 32 KiB page boundary; a previously unbound
global in the next page is resolved through the generated directory and
executed in Nexen, mutating its expected variable. The linked synthetic ROM
passed Poppy lint, ROM audit, cross-bank fetch acceptance, SCUMM error checks,
and native stack-balance checks. This validates multi-bank backend storage
inside the currently supported ROM, not the full FATE footprint.

The focused bank-fetch control cold-boots from the null scene and stops after
the marker global executes; it does not claim a room transition. Its complete
source still contains two room bundles, and independent native room-lifecycle
and resolver tests remain the transition/release/reuse evidence. Two clean
canonical FATE source-image runs emitted the same 583 declared artifacts and
the same `build-artifacts.json` SHA-256
`c454aaf54730e7149ba43de857fb3f6332cc8761b4e55cc1b4d84e75d88d6dc5`; both
were rejected before assembly with the same 232 layout issues and 8,912,896
byte logical span.

The full FATE compiler run stops at `LAYOUT_REJECTED_BEFORE_ASSEMBLY`, after
emitting and checking its source/body directories and the deterministic byte
ledger. It does not create a ROM, map, or build identity. Generated bytecode
and room data are not silently omitted, but they are not a linked image.
Poppy branch reach or full-FATE machine code cannot be certified without a
legal layout/map. The generated dynamic directories are data-driven and the
synthetic cross-bank dispatch has native acceptance; no separate full-FATE
short-branch failure was reproduced after the capacity gate was added.

Legacy static and selected dynamic modes remain supported. Their bounded
room-3 route remains a regression and is not the definition of full-source
emission. This milestone does not continue gameplay, enable dynamic
residency by default for FATE, or claim that the 2,203 source ProgramUnits are
fully executable.

## Readiness

**NOT READY for whole-game FATE execution.** Remaining blockers include the
measured ROM/resource capacity boundary; 2,144 unverified and 4 blocked
ProgramUnits under current lowering evidence; incomplete backend/runtime
capabilities; graphics, costume, font, text and audio/iMUSE resource paths;
dynamic/unresolved dependencies; and portable-state coverage. The accepted
bounded FATE route and selector residency proof remain narrower integration
evidence.

No proprietary archive, room payload, or generated FATE data is tracked.
