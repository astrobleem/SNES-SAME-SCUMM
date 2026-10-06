# Milestone 6: True Selector Demand and Executable-Carrier Reconciliation

Status: **IMPLEMENTED as compiler analysis; production generation/runtime unchanged.**

## Identity layers

| Concept | Meaning in this milestone |
|---|---|
| `SemanticExecutable` | A source SCUMM body with its own canonical identity and source PC/body provenance. Each object verb remains distinct. |
| `ResourceRecord` | An OBCD object resource and its metadata/verb table. An object record may contain no executable verb. |
| `ExecutableCarrier` | A complete backend record that current VM dispatch can enter. Script bodies are direct carriers; one object's complete OBCD is the carrier for its verbs. |
| `SelectorUnit` | One callable carrier requiring one current byte selector. In the current ABI this is one-to-one with `ExecutableCarrier`. |
| `ResidentBinding` | A future temporary association of a SelectorUnit with a byte selector. Not implemented in production. |
| `Selector` | The current byte handle read by program-size/program-fetch dispatch. It is not source identity. |

The machine outputs are `selector_demand.json`, `selector_directory.json`,
and `selector_residency.json`. The directory uses canonical unit identities
and deterministic bundle-local indices; it assigns no selector bytes.

The older `program_units.json` and `residency.json` compatibility analysis
still describes the former projection of OBCD records as units. It includes
all parsed object records and is retained for historical comparison; do not
use its object-unit count as true selector demand. The new selector-demand
projection is authoritative for callable selector addressability.

## Selector lifecycle observed in the implementation

`tools/generate_snes_cooked_rooms.py` assigns `item["id"]` from
`ProgramIdAllocator` when a selected source record is included. It emits
program bodies as `ScummV5_M23A_Program_XX`, byte-program lookup through
`ScummV5_M23A_GetProgramSize` and `ScummV5_M23A_FetchProgramByte`, global
number-to-byte mappings through `ScummV5_M23A_ResolveGlobalScript`, and room
entry/exit/local selector arrays. The native VM stores/fetches the selected
byte using `SAME_SCUMM_PROGRAM_SELECT`; active activations copy it into
`SAME_SCUMM_C4_SLOT_PROGRAM`.

For object verbs, the source path is:

```text
ObjectVerb(room, object, verb)
  -> the object's complete OBCD carrier
  -> StartObject passes object and verb to ObjectProgram_Resolve
  -> ObjectProgram_Resolve calls Verb_Query first
  -> a matching verb-table entry supplies the OBCD-relative entry PC
  -> the object carrier selector is stored in the C4 slot
```

The verb identity is supplied separately in `SAME_SCUMM_VERB_ID`; the slot
also retains object identity, and the returned entry offset initializes PC.
Thus multiple verbs on one object safely share one selector: it identifies
the complete OBCD, not an individual verb body. `ScummV5_Verb_Query_Far`
enumerates authored verb entries and `ScummV5_ObjectProgram_Resolve_Far`
does not return an object selector until that query succeeds.

The generator currently assigns an ID to every included OBCD object record,
even when its verb table is empty. The generated object resolver contains a
mapping arm for such a record, but the preceding verb query has no matching
entry and returns failure. Therefore the empty object's assigned byte is not
runtime-referenced by the current dispatch path. This milestone reports that
over-allocation; it does not remove it or alter backend output.

Globals, room entry/exit programs, and executable locals each map to one
script-record carrier. A source global slot with no script body has no
executable identity, carrier, or selector demand.

## Canonical DOS-CD FATE result

Source: external `/home/chad/ATLANTIS.zip`, profile
`fate_of_atlantis_dos_cd.json` (`indy4-fate-dos-cd-en`). No source payload is
stored in the repository.

| Measure | Discovered value |
|---|---:|
| Semantic executable identities | 4,100 |
| Parsed OBCD object ResourceRecords | 1,362 |
| ExecutableCarriers / true SelectorUnits | 2,195 / 2,195 |
| Legacy backend record/ID candidates if all parsed records are included | 2,788 |
| Legacy projected object IDs with no runtime reference | 593 |
| Object records with verb entries and semantic IR | 769 |
| Verb-entry objects lacking semantic IR | 0 |
| Object records with structurally unknown or malformed verb bodies | 0 |

The 2,195 SelectorUnits comprise 163 globals, 93 room entries, 93 room exits,
1,077 locals, and 769 object carriers. The 593 other OBCD records are
data-only: metadata/resource records, not VM-callable program units.

Room 98 has two semantic executables (ENCD and EXCD), 126 object resource
records, zero object verb entries, zero object carriers, and two SelectorUnits.
If all its current generator records were included, the legacy generator
would assign 128 IDs; only two are dispatch-reachable selectors.

Room 7 has 79 semantic executable identities and 24 object ResourceRecords.
Eighteen objects have executable verb tables containing all 59 semantic verb
identities; six are data-only. Its selector-bearing breakdown is 2 lifecycle
carriers + 18 local carriers + 18 object carriers = **38 SelectorUnits**.
The former 44-unit count included those six passive object records.

The source index declares 200 global script slots, but 163 have an available
script body and therefore a global carrier/SelectorUnit; the other 37 slots
have no executable body and consume no selector. Among the available globals,
reachability is 1 root, 2 definite, 131 conditional, and 29 possible. The
decoded graph names 46 static and 125 conditional-static global targets;
dynamic global references conservatively range over all 163 available
globals. Eighty-two global scripts contain a yield, and 15 contain both a
yield and room-load operation. These are identity-retention candidates, not
proof of simultaneous execution.

## Capacity and backend decision

Current byte-selector pool: 178 values.

* Largest parsed room bundle: 60 SelectorUnits (room 40).
* Largest known room plus static/conditional global addressability set: 71.
  These known sets fit 178; three inventoried rooms are not parsed, so the
  source-wide room maximum remains a lower bound.
* Largest room plus decoded dynamic-global candidate universe: 216 (room 46).
  This is a candidate universe, **not** a simultaneous resident set.
* The 2,195-unit known source corpus definitely cannot use one static global
  selector map of size 178. The analysis does not prove how many units are
  live simultaneously; at most 25 scheduler activations can hold selector
  references, but directory/resource references also need a resolver design.

Recommendation remains **Model B: small indirection/resolver**. Keep source
identities and bundle-local directory indexes stable, resolve a global or
room-local identity on activation, and pin its resident binding while any
selector-bearing VM state refers to it. Dynamic global candidates need not all
be resident. The next implementation seam is a pure resolver/binding simulator
consuming this generated directory, including dynamic global lookup, active
room bundles, pin/unpin, and exhaustion behavior. No native ABI change should
precede that contract test.

## Save/restore boundary

Host save state preserves source executable identity and reconstructs code.
An emulator savestate preserves raw WRAM selector bytes and is meaningful only
against the matching ROM/program tables. A relocatable future save should
persist canonical SelectorUnit identity, PC, locals, room ownership, and
continuation relations, then rebuild ResidentBindings during restore; do not
persist a temporary selector as the portable identity. No save schema changes
are made here.

## Validation boundary

The synthetic compiler fixture exercises several objects without verbs,
multiple verb identities sharing one OBCD selector, room locals/globals, and a
dynamic global reference. FATE integration checks room 7 and room 98 through
the shared compiler pipeline. All output is deterministic and selector-free.
No production runtime, SNES backend execution behavior, allocator behavior,
or save format was changed.
