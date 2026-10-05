# Runtime Versus Offline Compilation

Offline work is valuable when it removes repeated parsing, uncertain lookup,
target-size logic or runtime failure paths. Mutable game behavior and
frame-dependent scheduling remain runtime work.

| Area | Direction | Rationale / target effect |
|---|---|---|
| Resource container/index decoding | `COMPILE_OFFLINE` | Parse, decrypt and bounds-check on host; remove container parsing/directory scans from ROM. Runtime still reads packaged resources. |
| Opcode/script decoding | `HYBRID` | Front end decodes and validates; initially keep interpreter execution. Later compact ops can save operand-decode cycles and error surface. |
| Jump/label resolution | `COMPILE_OFFLINE` validation; runtime branch decision remains | Validate targets and encode offsets offline; variables still choose dynamic branches. |
| Program selection/resource lookup tables | `COMPILE_OFFLINE` | Resolve source identities to stable selectors and ROM directories; runtime keeps indexed lookup and dynamic scheduling. |
| Room/object/verb static metadata | `COMPILE_OFFLINE` | Precompute geometry, verb directories, initial defaults and walkbox graph; runtime owns mutations and hit-test decisions. Saves decode cycles/scratch. |
| Walkbox graph | `HYBRID` | Compile static geometry/portals/initial matrix; runtime owns actor position, box disabling and script-created route mutations. Never overwrite saved/authored dynamic state. |
| Script dependency discovery | `COMPILE_OFFLINE` with conservative dynamic edges | Detect missing bodies/capacity before ROM build; runtime still starts/stops scripts and reports errors. Replaces manual missing-script loop. |
| Encoded strings | `HYBRID` | Pack immutable source messages/controls; keep mutable strings, generated messages and waits as runtime state. |
| Costume decode | `COMPILE_OFFLINE` | Convert source codec/cels/palette to SNES frames; runtime retains animation choice/timing and actor state. Removes target codec work. |
| Background/video conversion | `COMPILE_OFFLINE` | Decode/repack pixels/palette/tiles for target; runtime owns camera, dynamic composition and presentation lifecycle. |
| Sound command mapping | `HYBRID` | Analyze/import/bind resources offline; runtime issues logical play/stop/state requests and backend realizes TAD/MSU/chip audio. |
| Save-state layout | `HYBRID` | Compiler emits schema/identity/field descriptors and capacity; runtime snapshots mutable variables, slots, actors, objects, routes and logical audio. |

These are per-representation choices, not a mandate to compile every opcode.
Keep runtime decisions where they depend on mutable state, ordering, input or
frame timing.

## Runtime contract

Generic SCUMM runtime owns activation/locals, scheduling, variables/bits,
mutable object/inventory state, movement, sentence dispatch, input ownership,
talk/cutscene waits, room lifecycle transactions, timers, dynamic routes and
logical audio intent. SAME/SNES owns frames, memory, services, DMA/video, input
hardware, ROM banking and native capacity. The compiler supplies validated
static tables and executable representation with provenance.
