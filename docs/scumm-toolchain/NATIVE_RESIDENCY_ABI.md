# Native SCUMM Resident-Program ABI

Status: **EXPERIMENTAL, bounded FATE route accepted**. The resolver remains
behind `SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY`; the canonical DOS-CD FATE
profile still defaults to the legacy static selector path. A separate
experimental build has now run the accepted deterministic route through room
3 and matched its static-selector control at the semantic checkpoints. This
does not certify the complete FATE corpus or every SCUMM capability. Portable
save formats and the production 178-selector byte ABI are unchanged.

## Identity layers

| Layer | Meaning | Representation |
| --- | --- | --- |
| `ProgramUnitIdentity` | Stable compiler/backend entity (for example a global script or object carrier) | Canonical source-oriented identity in the selector-free directory |
| canonical ProgramUnit ID | Dense per-game directory index; stable for identical compiler input | `u16`, `0xFFFF` reserved as unbound |
| resident binding | One canonical ID installed in a currently available selector slot | WRAM ID + generation + flags |
| selector | Ephemeral byte consumed by the existing VM and C4 slots | Existing 178-value allocator order: `$D0..$FF`, then `$CF..$4E` |
| bundle | Room-owned selector-bearing units loaded/released as a group | Generated room-directory ordinal and unit-ID list |

The canonical ID is not an SCUMM script number and not a selector. It is
assigned by the compiler from canonical ProgramUnit identities; the backend
uses it to locate the generated body/dispatch record. Object verbs remain
separate semantic IR entries inside one `ObjectProgram` carrier. Passive
objects are absent from the selector directory.

## Generated directory and resolver

The compiler-generated `scumm_v5_native_program_directory.json` is the source
for the runtime include. It contains canonical unit entries, a global-script
number-to-ID directory, and room-bundle offsets/counts/IDs. No selector value
is emitted in this directory. Dynamic object dispatch continues to select a
verb within its owning object carrier; it does not allocate one selector per
verb.

The feature-gated API in
[`scumm_v5_resident_resolver.pasm`](../../runtime/snes/engines/scumm_v5_resident_resolver.pasm)
currently provides:

| Entry point | Contract |
| --- | --- |
| `ResolveProgramUnit_Far` | Bind or find a canonical ID; returns selector/carry, or explicit invalid-ID/exhaustion error |
| `ResolveGlobalScript_Far` | Resolve a source script number through the generated global directory, then bind only that target |
| `ResolveLocalScript_Far` | Resolve a room-local source number against the active room directory |
| `LoadRoomBundle_Far` | Bind and room-pin every selector unit; partial load is rolled back on failure |
| `ReleaseRoomBundle_Far` | Remove that bundle's pins after room-owned activations have retired; immediately unbind units with no other pin or live C4 owner |
| `PinProgram_Far` / `UnpinProgram_Far` | Explicit pin ownership API |
| `ProgramUnitForSelector_Far` / `ValidateReference_Far` | Reverse lookup and stale `(ID, selector, generation)` validation |
| `RefreshDiagnostics_Far` | Recompute resident and room/explicit-pin census from binding flags |

Resolution first returns an existing binding, then uses the first empty pool
entry, then scans deterministically from pool index zero for the first
evictable binding. A room-bundle or explicit pin excludes a binding; an active
C4 slot is checked against the selector before eviction. Reassignment changes
the `u16` generation (zero is skipped). Invalid IDs and exhaustion fail
without aliasing or partially changing an existing binding. Exhaustion is
`SCUMM_ERR_RESIDENCY_EXHAUSTED`; an invalid directory ID is
`SCUMM_ERR_RESIDENCY_ID`.

## WRAM layout

The resolver tables occupy 890 bytes for 178 bindings:

| Range | Contents | Bytes |
| --- | --- | ---: |
| `$7E8C00..$7E8D63` | canonical ID per selector | 356 |
| `$7E8D64..$7E8EC7` | generation per selector | 356 |
| `$7E8EC8..$7E8F79` | valid / room-bundle / explicit / sampled-C4-live flags | 178 |

Resolver scratch, counters, and bounded diagnostic-control state continue
through `$7E8FBF`; the complete reserved block is 960 bytes from `$7E8C00`.
The resolver has an explicit 960-byte ownership block in the gap after the
name-length cache and before the encoded-name payload. Controller/input,
name-cache, C4, C19, room-lifecycle, and save-validator state are separately
owned. `tools/audit_scumm_residency_wram.py` checks the half-open intervals for
overlap and runs in validation and resolver-enabled builds. Engine-selection
tests verify resolver, controller, and save-validator configurations can be
selected together; the actual bounded FATE route exercised the controller
and name cache. A resolver + controller + save-validator synthetic ROM also
assembled and passed ROM audit; the full selected FATE route plus the optional
M20 save-validator code exceeded the existing bank-0 layout, so that combined
large-title configuration is not claimed as a tested FATE build. The save
validator's existing behavior remains covered by its separate tests.

Counters are 16-bit: resident/peak resident, current/peak room-or-explicit
pins, bind/reuse, bundle load/release, dynamic global lookup, exhaustion, and
stale-reference rejection. `RefreshDiagnostics_Far` is an explicit bounded
178-entry census used only by diagnostic controls; it does not scan or mutate
scheduler state. Active C4 owners are sampled separately by the native
acceptance observer from live slot selectors plus binding flags, and the
allocator independently checks those owners before eviction. Keeping C4
census out of this helper avoids perturbing production scheduling.

## Pin ownership and selector snapshots

| Production state | Current policy in the prototype | Release/reconstruction rule |
| --- | --- | --- |
| `C4_SLOT_PROGRAM` | `PINNED_SELECTOR` while its slot is live | Liveness scan treats non-stopped/non-error slots as owners; retirement releases the implicit pin |
| `PROGRAM_SELECT` | `TRANSIENT_ONLY` | Interpreter selection is rehydrated from the active C4 owner or resolved at a room/script entry boundary |
| Nested parent selector scratch (`M23B_NEST_PROGRAMS`) | `PINNED_SELECTOR` through the owning parent slot | Parent C4 activation remains live while child/continuation is outstanding |
| M23A return-program byte | `PINNED_SELECTOR` through its one-shot return slot/continuation | The continuation stores a slot owner; slot liveness prevents selector reuse until return/retirement |
| Dynamic room entry/exit directory | `CANONICAL_ID` | IDs are resolved when a room is committed; legacy builds retain their static byte tables |
| C19 override/cutscene continuation | `RECOMPUTED` from its owning C4 activation | The override record identifies/uses the activation; it does not independently own a selector binding |
| C19 native selected-program sample | `DIAGNOSTIC_ONLY` | Not consumed by production dispatch |
| Room bundle pins | `PINNED_SELECTOR` | Released only after outgoing EXCD and room-owned activation retirement; surviving globals remain slot-pinned |

The eviction guard checks actual live C4 slots in addition to flag pins. A
room release clears the selector mapping and valid flag when neither an
explicit pin nor a live C4 owner remains; if an activation still owns it, the
binding stays resident and becomes evictable only after that slot retires.
This matches the compiler simulator's eager room-bundle release policy. This
is what protects yielded activations, nested parents, sentence/global
execution, and a room-transition continuation when those references are
represented by an owning slot. `PROGRAM_SELECT` and temporary scratch are not
independent long-lived owners. The current proof does not claim that every
future asynchronous subsystem already has a canonicalizable continuation;
such a subsystem must either retain a live pinned owner or gain a canonical
identity before eviction is enabled for it.

## Room/global lifecycle

The dynamic room path performs the existing outgoing EXCD and retires
outgoing room/local slots before releasing the old bundle. It then unpins and
clears unowned outgoing bindings, loads and pins the incoming bundle, resolves
canonical entry/exit IDs to ephemeral selectors, and runs ENCD. The synthetic
native route verifies a yielded global remains at the same selector/generation
through four room transitions while unowned room bindings are reclaimed.

Global candidates are compiler metadata, not resident bindings. A dynamic
`StartScript` resolves only its requested source number and enters the normal
C4 allocation path. Missing numbers fail with the existing missing-script
error; no neighboring global is substituted.

## Portable and emulator save boundary

No save format changes are part of this prototype. A future portable save
must preserve canonical ProgramUnit identity, source PC, activation status and
delay, locals/arguments, room ownership, parent/child and room-return
relationships, and reconstructible pin reasons. Restore must resolve fresh
selectors and generations rather than trusting saved bytes.

An emulator savestate already captures raw WRAM selector bytes and the current
ROM's tables/code. It therefore remains tied to the exact ROM/build identity;
it is not a relocatable save across different resolver directories or builds.

## Acceptance boundary

**Implemented/prototype:** legacy static mode remains available; canonical
directory generation, native binding/reuse, room bundle pins, lazy global and
room-local resolution, generations, stale-reference rejection, explicit
exhaustion, diagnostic census, synthetic Nexen controls, and the bounded
DOS-CD FATE route. The route proves room transitions, selected object/verb
dispatch, and final room-3 semantics through the resolver, with zero stale
dispatches, aliases, or exhaustion.

The recorded route used the canonical DOS-CD English full-voice profile and
an experimental 151-ProgramUnit selected integration directory (not the full
2,195-SelectorUnit corpus). Its ROM SHA-256 is
`3370cfb36852b5f4bc2b2295c2c887073d174988d06f231a04cf7d3a7d45539a`; the
selector-free directory SHA-256 is
`9b7193d7cfd0f500414b46157e57bd3d791ceae9c06428e419cee22f9669cf23`. Static
and dynamic fresh-power-on replays matched the authored room/action sequence
and normalized semantic checkpoints through room 3. The route observer saw a
peak of 36 residents, 102 binds, six bundle loads/five releases, and 60 lazy
global resolutions. It derived 66 selector rebindings from event/sample
ownership changes; the native resolver's separate eviction counter remains
zero because outgoing room bundles are explicitly released before reuse. The
first directly observed released rebind changed selector `$D5` from
`RoomEntryProgram(68)` generation 1 to `ObjectProgram(room=4,object=61)`
generation 2. The route-level Python simulation consumed the same generated
directory and matched native peak residency, bind/load/release totals, and all
26 final `(ProgramUnit ID, selector, generation)` rows. Its abstract event
schedule is not a cycle-accurate execution trace.

**Still experimental / not certified:** dynamic residency is not the default
FATE profile and only the already-selected bounded integration set was
compiled. This result does not prove whole-game FATE playability, all 2,195
selector units, or complete capability coverage. Portable save migration and
a general-purpose paging policy for every SCUMM resource class remain
planned. Emulator savestates remain tied to the exact ROM/build identity.
