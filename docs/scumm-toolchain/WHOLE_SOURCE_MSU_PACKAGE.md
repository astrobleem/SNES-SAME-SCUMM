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
| SC5LIVE | 381,925 | Object/verb, lifecycle, local, and movement projection |
| SC5VIS | 5,776,320 | 96 indexed 256×224 projections with palettes |
| SC5CODE | 1,000,867 | 2,203 compiler-owned ProgramUnit bodies |
| Header and section directory | 160 | SAMEPKG v1 metadata |
| Inter-section / trailing padding | 0 | Sections use alignment 1 |
| **Total** | **13,547,228** | |

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
behavior. The current native incoming-room staging allocation is 3,132 bytes;
32 SC5LIVE records exceed it, with the largest record 19,135 bytes (room 66).
The largest retained cooked SC5ROOM is 131,487 bytes (room 91), but SC5ROOM is
package-only and is not passed through that native staging buffer. Therefore
the package can represent every indexed room, while only 64 room records fit
the current live incoming staging bound; including resource-less room 0 gives
65 entries classified loadable in the report. No capacity constants were
silently enlarged.

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
