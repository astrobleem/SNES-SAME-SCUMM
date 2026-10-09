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
- `SAME_SCUMM_PACK_SOURCE_TABLES=1` opts selected source-backed builds into
  the same compact table packing used by the whole-source compiler. It keeps
  small per-room metadata tables from consuming one full ROM page apiece;
  dynamic-residency builds also use the banked room-directory representation.
- `SAME_SCUMM_FAR_PROGRAMS=1` keeps the legacy static selector namespace but
  uses the existing banked body-fetch path for executable bytes, avoiding
  bank-0 inline-body overflow without changing selector semantics. Dynamic
  residency enables this representation automatically.
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

The bank-fetch control was rebuilt from the current fixture-payload-gating
commit and rerun in Nexen: 191 ProgramUnits were emitted, `GlobalProgram(6)`
(32,764 bytes) occupied bank 5, and the previously unbound
`GlobalProgram(7)` in bank 6 executed through its generated directory. Native
acceptance passed with variable 200 equal to `0xA55A`, room/error zero, stack
`$1FFF`, peak residency 2, and zero stale rejections or exhaustion. Its ROM
SHA remains `f479db6c86f11a5cb919bf12b6df15b51eb16029611957e040849d828d07f628`;
the current build identity is `4a9ad5db81f419a88635fa471106023de5cbd6900d57209f426fd773619c8ee4`,
and its map SHA is
`3ad85337e6e99ec5ef9c4e4511087de936ebaadfd468fee02ae951b7e1e817d9`. This is
cross-bank code-fetch acceptance, not a complete-game or room-transition
claim.

The full FATE compiler run stops at `LAYOUT_REJECTED_BEFORE_ASSEMBLY`, after
emitting and checking its source/body directories and the deterministic byte
ledger. It does not create a ROM, map, or build identity. Generated bytecode
and room data are not silently omitted, but they are not a linked image.
Poppy branch reach or full-FATE machine code cannot be certified without a
legal layout/map. The generated dynamic directories are data-driven and the
synthetic cross-bank dispatch has native acceptance; no separate full-FATE
short-branch failure was reproduced after the capacity gate was added.

## Source-backed fixture-payload exclusion and isolated control builds

`SAME_BUILD_SCUMM_EMBEDDED_TEST_PROGRAMS` defaults to `1` for the established
conformance builds. Source-backed M23A builds may set it to `0`: the generated
C1/C2 fixture program bytes (2,989 bytes in the generated fixture include)
are then excluded, the embedded C2 fixture count is zero, and a missing M23A
source body reports `SCUMM_ERR_RESOURCE` instead of falling through into the
fixture byte range. This changes no source SCUMM body, selector ABI, or room
record layout. It resolves the previously measured fixed-header collision:
the source-backed static image now ends its bank-0 payload at `$DB48`, below
the LoROM header at `$FFC0` (9,335 bytes free before the header).

Fresh, isolated DOS-CD-profile builds at source commit
`ead3b4bd21bb88dcbc9b262cbdbcc2b6172e4461` both finalized as 4 MiB LoROM
images and passed the ROM/map audit:

| Build | Selected ProgramUnits | ROM SHA-256 | Map SHA-256 | Build-identity SHA-256 | Bank-0 end |
| --- | ---: | --- | --- | --- | --- |
| Static source-backed control | 64 | `99677f074698363f8b35cc2f2fd98f4a840a083240b1e715fab2d1cadfb11a0d` | `414993b81b6dd4493829023cb8e3178780e6558f2b2561efbec51bab2852fddd` | `db83130d1a7ebe47b8a342249f3bdf7e4936fc359488af622fa6448c30118306` | `$DB48` |
| Dynamic-residency source-backed control | 64 | `a547fb154cff4bc30c560b08d07282c78e540865a18a201aeba5285c0360821b` | `cddd6ca39e1e1f7f6e2360a6c2aab888f39c19b68ceecff0105bec8cf44818f4` | `a4bc0c52be50efb895ff9ddc48ae834059c9c227c32c5b0b00a5259accea178b` | `$D9BE` |

These builds have independent worktree-local generated includes, reports,
ROMs, maps, and identities; the build identity records the exact ROM and map
hashes and the embedded-fixture option. They are valid assembly/layout
controls, but **not** replacements for the accepted bounded route: their
generated directory contains 64 ProgramUnits, whereas the historical accepted
route used a 151-ProgramUnit directory. The available 64-unit replay scratch
stalled in the null scene before requesting a room. It was rejected as route
evidence, not retried against the byte-identical selection, and its result is
not transferred to these new ROM/map identities. The accepted room-3 result
remains bound only to the historical ROM/build identity recorded in
`NATIVE_RESIDENCY_ABI.md`; this repair does not claim a fresh route replay.

The whole-source FATE output remains separately generated and rejected by the
same source-derived LoROM capacity preflight. Excluding 2,989 conformance
fixture bytes repairs the selected source-build header collision; it cannot
make the 6,387,956-byte complete cooked-room payload fit inside the 4 MiB
LoROM, even before other payload and runtime costs.

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
