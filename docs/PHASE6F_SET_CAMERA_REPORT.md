# Phase 6F — Canonical setCameraAt and Camera Reprojection

Phase 6F passes. The authentic room-49 path executes `B2 02 00` at
`LSCR.211 +$026E`, publishes the canonical camera viewport in the following
camera phase, presents the changed backdrop through the active-display Mode-3
pipeline, and stops at the next unsupported encoded-talk operation.

## Canonical opcode finding

The authoritative v5 opcode table does **not** define one four-member
`$32/$72/$B2/$F2` setCameraAt family. It defines:

- `$32`: `setCameraAt` with a direct word operand.
- `$B2`: `setCameraAt` with a variable word operand.
- `$72/$F2`: `loadRoom`, retained unchanged.

The production and host implementations therefore add only the canonical
`$32/$B2` family. The authentic instruction is:

```text
room.49 / LSCR.211 +$026E
B2 02 00
setCameraAt(Var[2])
Var[2] = 0
PC $026E -> $0271
```

## Camera oracle

Before `$B2`, the room is 49, its visual is 640x144 at pitch 640, and the
camera limits are both 160. The engine screen is 320x200 (40 strips). Camera
current/destination/last are `(160,100)`, mode is NORMAL, no actor is followed,
`movingToActor` is false, strips are 0..39, and virtual-screen xstart is 0.
`VAR_CAMERA_POS_X` is 0, `VAR_SCROLL_SCRIPT` is 214, and the fast-camera
variable is 0. No message is active and no charset mask is present. The accepted
Phase-6E viewport is source `(192,0,256,144)` to destination `(0,40,256,144)`
with clear index 0.

Immediately after the opcode, before the normal camera phase:

```text
mode                  NORMAL
requested X           0 (literal)
current X             160 (clamped)
destination X         0 (not yet clamped by moveCamera)
movingToActor         false
screenStartStrip      0 (not newly fabricated by the opcode)
virtual-screen xstart 0 (not newly fabricated by the opcode)
camera-update pending true
```

On the next canonical camera phase:

```text
current X             160
destination X         160
screenStartStrip      0
screenEndStrip        39
virtual-screen xstart 0
published source      (32,0,256,144)
published destination (0,40,256,144)
```

The authentic scroll script 214 is nonzero and runs once through normal nested
script execution. `Var[2]` is consequently published as camera X = 160. The
talk-stop condition is inactive: no visible charset mask is present at this
point, so the established logical talk state is not stopped by the camera cut.

The production order is:

```text
script scheduler -> actor movement -> camera update/publication
-> pending visual service -> event drain -> backend step -> audio -> NMI commit
```

The opcode changes camera state only. The later camera phase publishes the
viewport and retains one latest room-generation-owned visual request. An
unchanged source X is discarded without surface mutation or presentation. If
the surface is locked, the request is retained and revalidated after unlock;
later camera publications overwrite that one bounded request. A room-generation
change retires it as stale.

## Mode-3 visual result

The complete Phase-6E SC5VIS resource is reused. No camera-specific pixels or
tiles are cooked. The generic surface facade clears the 256x224 surface, blits
the new opaque source rectangle, submits one full-screen `SURFACE_DIRTY`, and
submits `PRESENT` generation 2. The palette is unchanged and no
`PALETTE_WRITE` is submitted.

The fresh-emulator gate observed:

```text
opcode checkpoint frame       966
camera publication frame      967
generation 2 accepted frame  1016
candidate conversion ends    1500
generation committed frame   1583
commit latency                568 host frames
changed tiles                 495
unchanged candidates          401
tile bytes                    31,680
CGRAM bytes                   0
DMA batches                   16
```

The target uses the accepted active conversion budget and the existing `$0800`
NMI DMA limit. The configured conversion budget is four tiles per completed
backend step (the established Phase-6D timing-safe value). It remains visible
throughout; no forced blank or extra SCUMM
logical tick is introduced. The image converges incrementally, and generation 2
is not committed until every changed tile reaches VRAM.

Changed tile runs are:

```text
(160,2), (192,2), (224,8), (253,483)
```

The first batch contains `(160,2),(192,2),(224,8),(253,20)` for 2048 bytes.
Fourteen following batches carry 32 consecutive tiles each, and the final batch
carries 15 tiles (960 bytes).

Hashes:

```text
old live surface  ddafb02158bc47e59c5d01f0a27dfb826948594cdcee8b2684c9fe4335a2528a
new live surface  2b79a81e61b5e0e067a21d2979f75a1f5d69ed07272df201919f29de73dad78a
live RGB8 palette 8747a8331e54aeb371292fc6770db3566b28af0eb31418cc73273aefd7ec471a
tile shadow       1699c4abb220ab668092f6e25a5461093c24853090e926d39a7e704afe300cb4
VRAM characters   1699c4abb220ab668092f6e25a5461093c24853090e926d39a7e704afe300cb4
CGRAM shadow      6433d8ed1927a90517418bf63067a18283bf4ffcccbd267e395505a260e379fd
CGRAM             6433d8ed1927a90517418bf63067a18283bf4ffcccbd267e395505a260e379fd
reference PNG     37a03d5961c38d7f609a6fd77e2b7ba45345420d5d17548936095530180c881c
emulator PNG      37a03d5961c38d7f609a6fd77e2b7ba45345420d5d17548936095530180c881c
visible differences 0
```

This is backdrop-only presentation. It makes no actor, costume, text-pixel,
verb UI, cursor, dynamic follow-camera, or room-63 visual claim.

## New artifacts

Each new artifact was built twice with byte-identical results:

```text
ordinary LoROM + legacy
8d85d7df50aaba8353cff52db60bb071edc7a8227bc0d815f9a261ddc0f07ff1

SA-1 + legacy
05c3fc1f0a382bc8aae66e099d9384b9e1131a230dc2d8b0e184104544c1bbba

SA-1 + Mode-3 room 49
9e8357631a82fc941d2d6b3f53edaf1c2f574145a59c3fcfcb077537a2736dd4
```

Cross-carrier traces agree at logical tick 93 on script PC, variables, actor
position `(57,46)`, walkbox 1, movement completion, getDist result 0,
startObject/object 596/verb 10, chainScript 211, camera state, viewport
publication, scroll-script count, and the next blocker. Carrier/backend-only
state and host video-frame counts are excluded from the comparison.

The SA-1 state is unchanged from power-on through the completed Mode-3 gate:
`K:PC=00:0000`, A/X/Y/D/DBR unchanged, no IRQ, mailbox, SA-1 DMA, or character
conversion. The S-CPU is waiting normally at `00:805F` after completion.

## Next blocker (not implemented)

```text
resource: room.49 / LSCR.211
offset:   +$027B
bytes:    14 02 0F 49 27 6C 6C 20 77 61 69 74 20 68 65 72
          65 2E FF 03 2A 73 69 67 68 2A 00
decode:   print actor 2, "I'll wait here.", control FF 03, "*sigh*"
post-decode PC: $0296
classification: encoded talk/text subsystem gap
```

The VM stops with opcode `$14`, error `$0E`, and yielded status. The outer SAME
frame owner remains alive so the already-submitted video generation can finish.
No print/talk rendering or semantics were added.

## Validation

Commands run included:

```text
PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine tests.test_scumm_v5_room tests.test_scumm_v5_room_visual -q
python3 -m unittest discover -s tests -q
make test
make validate
make demo
PYTHONPATH=src python3 tools/validate_scumm_set_camera_nexen.py ...  # three carriers, sequential
PYTHONPATH=src python3 tools/compare_scumm_set_camera_traces.py ...
PYTHONPATH=src python3 tools/validate_scumm_set_camera_mode3_nexen.py
PYTHONPATH=src python3 tools/validate_mode3_surface_backend_nexen.py
PYTHONPATH=src python3 tools/validate_scumm_room49_mode3_nexen.py
PYTHONPATH=src python3 tools/validate_snes_surface_proof_nexen.py
PYTHONPATH=src python3 tools/validate_sa1_bwram_proof_nexen.py
PYTHONPATH=src python3 tools/validate_sa1_carrier_persistence_nexen.py
python3 tools/audit_snes_rom.py ...  # all historical and new M25 artifacts
python3 tools/lint_poppy.py ...      # performed by production builds
git diff --check
```

The final full suite contains 437 passing tests. `make test`, `make validate`,
`make demo`, S3, all four VDP goldens/eight expected-generated PNG comparisons,
all historical M25 audits, and all historical Nexen regressions pass. Nexen
validations were run sequentially.

Historical identities remain exact, including:

```text
Phase 6C ordinary integrated  a48c0db782b6d1df304d164527f2123a0fd99e0f56617e4404a64aeb35765a8c
Phase 6C ordinary conformance a14b56f0cf8307a5ff2ccb604769ccf82daf499751eaff303c51546014f12778
Phase 6C SA-1 integrated      451a1d769b2bb6df5cfd9f17997aff353758918fcd1ef16b5b189d9623115ca4
Phase 6C SA-1 conformance     90619a24992b5a7e8b0a5ab2737068dfa0c6ec456720e799a860a9b2e588ff0c
Phase 6D backend proof        3ba6d8e0e9f84b12a1d066354ba7fc8684aa9aaa0cf6fca68a1e087294937707
Phase 6E room-49 backdrop     d9b31598c794d3726082bff07c8ce481042e5c1449f54bd3e4462dfb7d755584
Phase 6A proof                e980b827c4dc452a49d6a04265f2f35edfb29d7e6518acc34e1c7fb9a3cdeb06
Phase 6B proof                c126c0badb6251900d4ea9ab321f1b43bb646f982b24d8a66f786821efa8a4df
legacy framebuffer            04500d0905c9df798d76366bc7af0ed507b4f8693ad9f7d35188957cffbea63b
cursor-excluded PNG           fbb97dd8d61c7a192ae147b67abbb61fccafca206309e77834012aa2fce8dcf2
cursor-included PNG           86214297f8274d9ef7da46cb0bf67234595c0c1a29e2d9c6fe6d970c48fe6347
S3 report                     23dc2bd7b8faef09770df554cd339dc300e3f01dd582c7202267837473a9aef4
S3 logical PNG                9c2aeb3e62a81de19ebda55c7918c78f7c845a7b69bc7937d4471336cee82ca0
S3 physical PNG               a0d7a2d079bba5fc35a10512fbfdc2b27dea83ebca8ad66ed35d3a8af79d6832
VDP manifest                  ab13ca51d24fd1f068565c7ce10e3bba125812b7064c7c55a3504bbc4dd55988
```

The unrelated `fate_sound_80_default` generic-build discrepancy was not changed.
No actor, costume, target text, cursor, room-63 visual, SA-1 execution, or next
semantic blocker work began.
