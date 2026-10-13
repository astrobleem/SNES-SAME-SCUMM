# Whole-source SAMEPKG generation

Status: compiler/package generation is implemented; whole-game execution is
not certified.

`tools/package_scumm_v5_source_msu.py` runs the generic DOS-CD profile analyzer,
all-source room cooker, ProgramUnit backend, and SAMEPKG writer into a fresh
output root. It refuses to reuse a nonempty root. The resulting manifest owns
the complete generated artifact set; no build step discovers files by globbing
a shared segment directory. Keep the external archive, generated package,
cooked resources, ROM, and emulator state outside Git.

The canonical source identity remains `indy4-fate-dos-cd-en` with the
`DOS CD English, full voice (1993)` profile. ProgramUnit IDs are the complete
directory's 16-bit canonical IDs, not resident selectors. Replacing a selected
directory may change numeric IDs; consumers must use the full manifest and
semantic identity together.

The current package layout is:

| SAMEPKG section | Bytes | Role |
| --- | ---: | --- |
| SC5ROOM | 6,387,956 | Complete cooked room source records, retained package-only |
| SC5LIVE | 239,981 | SC5LIVE v3 object/verb, lifecycle, local, and movement projection |
| SC5VIS | 5,776,320 | 96 indexed 256×224 projections with palettes |
| SC5CODE | 1,000,867 | 2,203 compiler-owned ProgramUnit bodies |
| Header and section directory | 160 | SAMEPKG v1 metadata |
| Inter-section / trailing padding | 0 | Sections use alignment 1 |
| **Total** | **13,405,284** | |

The SC5CODE directory has 2,376 integrity-checked instruction-aligned pages;
the largest body is 21,002 bytes and the page limit remains 2,048 bytes. Its
16-bit whole-body length field is sufficient for the observed maximum. The
ROM lookup payload is 54,404 bytes: 22,030 ProgramUnit records, 990 room
records, 990 SC5LIVE records, 2,574 SC5VIS records, and 27,820 page-directory
bytes, split across the existing directory banks. Package offsets are 32-bit;
resident selectors remain an independent 178-entry window.

The complete SC5ROOM containers include 857,071 bytes that are also present,
byte-for-byte and hash-for-hash, as room-owned SC5CODE carriers (2,040
ProgramUnits). Those copies are retained because SC5ROOM is a complete cooked
room record while SC5CODE is the independently indexed executable collection;
the current live-room runtime consumes SC5LIVE/SC5VIS and SC5CODE, not SC5ROOM.
The package does not deduplicate those identities or claim that the repeated
source-container bytes are needed by the current runtime. Another 7,513 bytes
are identical bodies belonging to distinct ProgramUnit identities; those
identities remain separate.

All 96 indexed rooms currently have SC5ROOM, SC5LIVE, and SC5VIS package
records. Room 0 remains resource-less and keeps its established lifecycle
behavior. The current native incoming-room staging allocation is 3,132 bytes.
SC5LIVE v3 sparse/deduplicated portal tables reduce the maximum record from
19,135 to 11,237 bytes (room 66), but 25 records still exceed staging. The
current native consumer requires a complete record before publication, so the
compiler's chunk checksums do not make those records native-loadable.
The largest retained cooked SC5ROOM is 131,487 bytes (room 91), but SC5ROOM is
package-only and is not passed through that native staging buffer. Therefore
the package represents every indexed room, while 71 SC5LIVE records fit the
current staging bound; including the separately modeled resource-less room 0
gives 72 entries classified native-loadable in the preflight. No capacity
constants were enlarged.

SC5VIS conversion is an aspect-fit projection, not proof of native PPU
equivalence. Rooms 89 and 90 expose a 16-pixel-wide source projection and are
marked with a source-geometry warning; their packaged pixels must not be
interpreted as a validated visual match. Room 5's full matching-ROM PPU
comparison also remains `NOT_CAPTURED`; comparisons for other rooms do not
fill that evidence gap.

The latest external DOS-CD corpus run represents 4,108 semantic executable
identities in 2,203 ProgramUnits: 163 globals, 96 room-entry, 96 room-exit,
1,079 room-local, and 769 object carriers. All 2,203 bodies reconcile against
the generated directory and source emission validator. The previously selected
287 ProgramUnits all match the complete directory by semantic identity, size,
and SHA-256; selected numeric IDs are not reused. First, middle, and final
directory entries are explicitly probed, and every body/page range is checked.

This is a source/package statement only. The latest lowering report has 55
ProgramUnits with lowering evidence, 4 blocked, and 2,144 unverified. The
resource census also includes inventoried, unavailable, and parsed categories
outside the room projections above. Audio/iMUSE, original asset codecs,
resource-service coverage, and portable save reconstruction remain incomplete.
Release readiness stays `NOT_READY`; full FATE playability is not claimed.

## Replay report durability

The long native continuation writes an identity-bound, append-only JSONL
snapshot journal and fsyncs each snapshot before replacing the readable report.
`tools/recover_fate_replay_evidence.py` verifies the hash chain and build
identity, then materializes the newest exact snapshot. Recovery preserves the
captured `result` value; it does not promote `running` or failure evidence to a
pass and does not fill missing observations. Native observations, reused
hash-bound report fields, and not-captured coverage (including the room-5 PPU
gap) remain distinct.

## Full-directory native image smoke

The complete 2,203-entry compiler directory also links into the feature-gated
native resolver image. The live-room build excludes its unused ROM-backed
verb/name lookup fallbacks at assembly time: those generated corpus-wide BRL
dispatches were unreachable in that build personality and exceeded the 16-bit
relative branch range. Static builds retain the ROM-backed implementation.
The generator regression checks both conditional branches; Poppy and full
image assembly validate the actual expansion.

A bounded Nexen cold boot using the DOS-CD profile's configured boot entry
resolved and executed `GlobalProgram(1)` (canonical ProgramUnit ID 0) through
the full directory, then loaded room 68 through its room bundle. At 2,000
frames, room 68 was committed, SCUMM error was zero, the checked provider had
read 65,317 bytes in 12 requests, and the resolver had 15 resident units / a
peak of 15, including room-68 entry, exit, locals, and callable object
carriers. Dynamic global lookups were 5; cache failures, stale rejections, and
selector exhaustion were zero. This is full-directory native boot and room-68
load evidence, not a whole-game execution or the bounded room-3 route.

The final 4 MiB ROM passes ROM and 21-region WRAM audits. The all-room
readiness report still has native_loadable=false because 25 SC5LIVE records
exceed the current 3,132-byte incoming staging limit. The booted room-68 record
fits; the smoke does not certify those other rooms. The 2,144 unverified plus
4 blocked backend units and the separate graphics, sound/iMUSE, text/font, and
save-state gaps continue to keep release readiness `NOT_READY`. Room 5's PPU
comparison remains `NOT_CAPTURED`.

The large-room follow-up documents the SC5LIVE v3 encoding, exact per-room
section sizes, native capacity, and the remaining section-aware transactional
consumer requirement in LARGE_ROOM_METADATA.md.
