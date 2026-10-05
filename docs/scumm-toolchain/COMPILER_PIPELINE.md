# Compiler Pipeline and Resource Dependencies

## Intended flow

```text
external game files + thin edition profile
  -> SCUMM front end: identify/decrypt/parse resources
  -> GameIR + source map
  -> capability and dependency analysis
  -> SNES backend: layout/encode/package
  -> generated resource tables and ROM data
  -> existing generic SCUMM/SAME runtime
```

This is incremental. Existing profile loading,
`LucasartsScummV5ResourceProvider`, room decoders, cooked-room codecs and
cookers are retained and adapted; a second resource parser is not proposed.

## Front-end boundary

The front end owns dialect/version, archive/index structures, resource
discovery, rooms/chunks, objects/verbs, scripts and operands, actor/variable/
string/costume/sound references, source offsets, control-flow checks and
source-level dependencies. Its public output is target-neutral. It must not
import Poppy, name WRAM, encode LoROM addresses or know 65816 register width.

Current seeds include `policy.py`, `resources.py`, `room.py`, `costume.py`,
`font.py`, `text.py`, `embedded_audio.py` and `cook_scumm_v5_rooms.py`. Separate
discovery/parse APIs from CLI orchestration gradually.

## Thin profile boundary

Keep in a game/edition profile: stable game and edition identity, dialect,
original archive/member layout, resource key templates, authentic source
quirks that are actually demonstrated, and title audio import policy. The
Fate templates' `snes_global_script_sets`, execution gates, and long lists of
selected rooms/executables are useful transitional build roots, but are not
language semantics. Move their derived portions to an analyzed build manifest
containing selected roots, transitive closure, target capacities and backend
choices. Retain explicit root overrides for diagnostics and intentionally
partial builds.

Do not hand-maintain hundreds of room/script/object records in profile JSON.
The front end should derive resource inventories and metadata from source;
the profile should identify which source edition and any genuine policy
exceptions.

## Dependency graph

Nodes use typed identities such as `Global(n)`, `Room(r)`, `RoomLocal(r,n)`,
`ObjectVerb(r,o,v)`, `Costume(n)`, `String(n)` and `Sound(n)`. Each edge records
kind, source span, confidence and resolution:

| Edge | Static source | Confidence policy |
|---|---|---|
| Script → global/local script | Literal `startScript` / `chainScript`; source context resolves namespace | `definite` for literal target; `possible` for variable target/range |
| Object verb → script body | OBCD verb entry offset and decoded object code | `definite` when the verb directory is complete |
| Script → object verb | Literal `startObject` target/verb | `definite` for literals; `possible` for dynamic operands |
| Room → entry/exit/local scripts | ENCD, EXCD, LSCR chunks | `definite` for selected room resources present |
| Script → room | `loadRoom`, `loadRoomWithEgo`, pseudo-room mapping | `definite` for literal physical target; conservative for variables/maps |
| Room → objects | OBCD/CDHD tables | `definite` for decoded local objects |
| Actor → costume | Actor setup and costume operations | Definite or possible based on operand constancy |
| Script → string/sound | Text/audio operands and source directories | `definite` for literal IDs; `possible` for indirect IDs |

Runtime events add `observed` edges containing ROM/build identity, frame and
executing source span. They supplement rather than overwrite static
uncertainty. Static analysis distinguishes selected roots from proven
transitive closure; dynamic IDs and conditional branches remain possible.

## SNES backend boundary

The backend owns selector allocation, ROM-bank layout, generated Poppy/data,
WRAM/capacity checks, compact operation encoding, room/verb directories,
resource packaging, image/palette/tile conversion, charset packing, audio
binding and target-to-source maps.

Representation may vary by item:

- scripts: retain SCUMM bytecode initially; later use compact semantic ops or
  threaded/native sequences where measurements justify it; very hot, stable
  operations may become direct native primitives behind the same semantic
  contract;
- dispatch and directory metadata: ROM tables/generated assembly;
- static room geometry/object/verb defaults: precomputed tables, separate from
  mutable runtime state;
- backgrounds/costumes/fonts: backend-oriented payloads plus descriptors;
- large immutable assets: binary ROM data/incbin segments with generated
  descriptors and source maps;
- scheduler, actor motion, interaction, room-transaction state: runtime.

## Existing compiler-like chain

`cook_scumm_v5_rooms.py` reads source resources, selects rooms/globals,
retains offsets/hashes, emits SC5C rooms and manifests, and can emit SC5VIS
visuals. `generate_snes_cooked_rooms.py` allocates selectors and emits
directories/banked code and data. Specialized generators handle variables,
visuals, charset, actor/object sprites, engine selection and save identity.
These are pipeline assets to modularize, not replace.

The missing seam is a compiler-owned semantic result between parsing and
target generation: typed IR and analysis that can be tested without Poppy and
consumed by current generators before the runtime ABI changes.
