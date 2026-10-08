# Whole-source SCUMM v5 backend integration

Status: **PARTIAL — full source corpus is emitted and reconciled; a complete
SNES image is not linkable with the current mapper/address model.**

FATE remains an integration corpus, not a source of generic compiler rules.
This milestone does not claim whole-game execution readiness.

## Implemented

- `tools/compile_scumm_v5_source_image.py` drives the existing generic game
  front end, all-source room cooker, ProgramUnit projection, and SNES room
  generator. It has no title-specific room/script selection list.
- The complete source ProgramUnit directory is emitted with stable canonical
  IDs, source identity/provenance, object-verb dispatch metadata, generated
  code labels, source-body SHA-256, code size, and bank/offset descriptors.
- Every source body is reconciled against its GameIR source identity and hash.
  Object verbs remain separate IR entries carried by their owning object
  ProgramUnit; passive object records remain resource metadata.
- Dynamic room/global directories can place their array payloads in banked
  ROM data instead of expanding fixed-bank code. This is opt-in for the
  whole-source path; the legacy generator path remains available.
- `strict` rejects any ProgramUnit without complete backend/runtime/native
  evidence. `experimental-diagnostic` retains source bytecode and reports
  unsupported/unverified operations; that output is not release eligible and
  does not claim unsupported operations will execute successfully.
- `resource-status.json` separates script/room emission from visual, costume,
  charset, sound, text-rendering, runtime-resource-loading, and portable-state
  coverage.

## Canonical DOS-CD FATE result

Source: external `/home/chad/ATLANTIS.zip`; profile
`fate_of_atlantis_dos_cd.json`; game identity
`indy4-fate-dos-cd-en` (`DOS CD English, full voice (1993)`).

The current source analysis discovers 96 indexed and parsed rooms, 4,108
semantic executable identities, and 2,203 selector-bearing ProgramUnits:
163 globals, 96 entry units, 96 exit units, 1,079 room locals, and 769 object
carriers. It also inventories 1,372 object resource records, including
data-only objects that do not acquire selectors. The source ProgramUnit
directory contains 2,203 entries; all 2,203 body records were emitted and
source-hash reconciled. No runtime selector was assigned to the source corpus.

The backend retains 1,000,867 bytes of source executable bodies. Cooked room
bundle records occupy 6,387,956 bytes. The provenance-rich backend JSON
directory is 3,235,369 bytes on disk; it is build metadata, not ROM payload.
There are 3,795 cross-bank ProgramUnit dependency edges.

The current analysis reports 96 parsed rooms, 116,730 structurally decoded
instruction occurrences, and no structural-unknown or truncated occurrences.
This is not execution certification: 9 executable CFGs remain unresolved or
have invalid control-flow targets. Of 2,203 ProgramUnits, 55 are
`LOWERABLE_WITH_EVIDENCE`, 2,144 are `UNVERIFIED`, and 4 are `BLOCKED`.
Strict compilation therefore rejects the image. The unsupported/unverified
operation diagnostics remain explicit in `backend/lowering-report.json`.

Resource census: 617 entries are inventoried, 104 parsed, and 85 unavailable.
The 96 room structures and 1,372 object records are emitted, but this image
does not include room visual conversion, costume or charset conversion,
sound/iMUSE binding, complete text rendering, or portable-state certification.

## Measured storage and link boundary

The generated layout uses 32 KiB LoROM pages and occupies through bank 344
(generator high-water `last_generated_bank=345`): the minimum mapped span is
11,337,728 bytes, or 346 pages. The current ROM finalizer accepts
at most 4,194,304 bytes (128 such pages). The current 24-bit LoROM bank-number
namespace addresses at most 256 pages (8,388,608 bytes); all 2,203 ProgramUnit
bodies in this emitted layout begin beyond bank `$FF`. The current mapped span
is therefore 2.70 times the finalizer capacity and also exceeds the present
24-bit LoROM page address space.

The full build was attempted with M20, controller, C19/room lifecycle,
save-validator, and dynamic residency enabled. The WRAM ownership audit passed
for all 13 regions, and the generated directory tables no longer overlap the
fixed bank-0 header/code region. Poppy lint passed. Assembly then failed on
high-bank address operands and associated out-of-range generated references;
there is no ROM, map, or build identity for a full-source image. The link
failure is not repaired by selector residency: storage in the ROM image and
simultaneous 178-selector residency are independent capacities.

The next required subsystem is a generic segmented ROM/resource address
model, not a larger selector pool. It must define storage-page identity and
page offset separately from 24-bit CPU addresses, provide a hardware-supported
window/streaming service for pages that cannot be directly addressed, and
make program fetch plus room-resource loading use that service. The current
LoROM/SA-1 finalizer and runtime expose no such extended storage mechanism.
Even a future 8 MiB LoROM page map would be smaller than this measured layout;
the backend must first choose and validate a supported larger mapping or
reduce stored payload through a generic, runtime-supported representation.
Do not encode high bank numbers as oversized 24-bit literals.

## Readiness and regressions

`whole-source-backend.json` remains `NOT_READY`: CFG/dependency closure,
backend lowering, SNES runtime evidence, host semantics, asset conversion,
rendering, and portable-state coverage are incomplete. A compiler-owned
ProgramUnit directory is not a playable whole-game ROM.

The source-only synthetic integration adds 180 global scripts, exceeds the
178-selector pool, emits the full generated directory and every body, and
checks body bytes against source hashes. This proves complete-corpus emission
and selector-free addressing metadata, not native execution of this new
whole-source image. Existing native residency acceptance remains a separate
conformance result.

The static route replay attempt in this worktree did not produce valid route
evidence: the whole-source build had replaced generated room includes, so the
replay helper correctly rejected their hashes against the prebuilt static
control ROM. The previously accepted static/dynamic route evidence is not
overwritten or reinterpreted here. No runtime or SCUMM semantic behavior was
changed by this milestone.

No proprietary payloads or generated FATE room/code bodies belong in Git.
