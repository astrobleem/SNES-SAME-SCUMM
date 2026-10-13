# Authentic FATE room 7: authored interaction graph

This note records the room-7 resource graph used to select the next
deterministic replay actions. It is based on the external
`/home/chad/ATLANTIS.zip` input, not on a walkthrough and not on room-number
intuition. The archive itself and extracted bodies remain external.

## Resource identity

| Resource | Archive source | Size | SHA-256 | Runtime selector |
|---|---|---:|---|---|
| Room 7 LFLF | `ATLANTIS/ATLANTIS.001`, offset `730022` | 51789-byte ROOM payload | `58cf45c4d2bd15cea5c4a3606003bdd6907d9586eb4864e0b672707ef18b269a` | active room record 7 |
| ENCD | same member, body offset `778827` | 487 | `339b0e605941eaee59bb95c8c9e7a8195c44ad7ff8f363554796fb749055aa8d` | room entry |
| EXCD | same member, body offset `778782` | 37 | `dd94e4b228fd5f64e1582da091279634b94ddc4183deb33b4a9ce169048b21c9` | room exit |
| LSCR201 | same member, body offset `779853` | 291 | `6a3565652f8d72261d357eb6ef0d497a0a15448f15a6842d6afd22f7a8eda752` | `$89` |
| LSCR203 | same member, body offset `780182` | 45 | `6e8e77dfc7f84b22851cc372ba09b9728c457c16791178edf75698f80182d043` | not selected; bit69 route is unreachable at this frontier |
| LSCR207 | same member, body offset `780810` | 112 | `8aaee88643be64efdc3b8826b4ff7569517e7493b658ad596a09eb29ad41cc6f` | `$88` |
| LSCR208 | same member, body offset `780931` | 31 | `436f6f57852a7ebd4c2da4f7c0f88a8c907eec58b8deed3496ba6bec44b26049` | `$92` |
| LSCR217 | same member, body offset `781677` | 150 | `873db744e8c3c9c18aa958a62a8aa8cf70ed9477646e934e811578fce417d184` | `$8A` |

All local scripts in the room resource (including scripts not selected by
this build) are accounted for here:

| Script | Body offset | Size | SHA-256 |
|---:|---:|---:|---|
| 200 | 779333 | 511 | `51d17179fefde0eafddb39e32ff78d5ba063222eed94fd4e299e3962ac7c2a2a` | `$91` |
| 201 | 779853 | 291 | `6a3565652f8d72261d357eb6ef0d497a0a15448f15a6842d6afd22f7a8eda752` | `$89` |
| 202 | 780153 | 20 | `925003bbae0fbf62eeea170b29281f97ee2f1b45812d7e3247949e07ae8ce702` | not selected |
| 203 | 780182 | 45 | `6e8e77dfc7f84b22851cc372ba09b9728c457c16791178edf75698f80182d043` | not selected |
| 204 | 780236 | 112 | `16e0003ef3a28338a535d9860605203fcf07600c226adb499901fbbb677f6da9` | not selected |
| 205 | 780357 | 202 | `3536ee3990b4a02c9e0ebe9d4ad27702bcf0b2c80e91a1649cc75ccb758af23e` | not selected |
| 206 | 780568 | 233 | `91ba342ae6eb8b8204197482f47ceaacf4f37562f4e6485a469ba0357f883c1b` | `$69` |
| 207 | 780810 | 112 | `8aaee88643be64efdc3b8826b4ff7569517e7493b658ad596a09eb29ad41cc6f` | `$88` |
| 208 | 780931 | 31 | `436f6f57852a7ebd4c2da4f7c0f88a8c907eec58b8deed3496ba6bec44b26049` | `$92` |
| 209 | 780971 | 59 | `7752cbd201835a427818925458a7b308abe6c2c7552490bd76eb958927e535e4` | `$90` |
| 210 | 781039 | 56 | `82296987168f24f953cfb06c4306ca79cd0b9c3440a31e328a18a0d17f9f52e4` | `$8E` |
| 211 | 781104 | 123 | `a51cf9b54a9fab5d092473d3d5a23d21bfc6e0e53985c496dd71ecccc8e5a381` | `$8F` |
| 212 | 781236 | 124 | `ecd665b21ddc582c8de0391fe0d0eb3a8cb68159ac4964250462b3ef35c74b29` | `$8D` |
| 213 | 781369 | 123 | `5ec7c926e8d184dbe2886121e2a259fa2b0146d650b7c4853965349b57497dec` | `$8C` |
| 214 | 781501 | 123 | `11e6f44ffd4e8fe1501885b0e1be6e4a1fc6ea9fc6da72cf9f1683b58c01018f` | `$8B` |
| 215 | 781633 | 6 | `f71fb01ae97868fa954768e5be3db44673e4d4840936441261d29cfc3bc51d4e` | `$7A` |
| 216 | 781648 | 20 | `8a4188235bc572f5a4dc4570c172db5743870f5ca669a63f35fdbbe497959bd7` | not selected |
| 217 | 781677 | 150 | `873db744e8c3c9c18aa958a62a8aa8cf70ed9477646e934e811578fce417d184` | `$8A` |

Decoded roles: LSCR200 is the first-visit roof/cellar cutscene; 201 is the
two-figure cat cutscene and room-3 handoff; 202 walks to the chute and restores
box-follow behavior; 203 is the bit69-gated alternate chute transition; 204
and 205 are pile-of-books/coal sequences; 206 handles cat look/pick-up
variants; 207 updates the selected figurine classes; 208 starts the room
entry cutscene and its override branch; 209–214 print credit cards; 215 sets
a short text timer; 216 is a bit-controlled script watcher; and 217 handles
the override path that can load room 1. This profile maps 200, 201, 206–215,
and 217; it does not map 202–205 or 216. In particular, the bit69 chute
script 203 is intentionally not selected because its authentic precondition
is false at this frontier.

Offsets are absolute byte offsets in the named `ATLANTIS.001` member. Script
body offsets exclude the enclosing chunk header (and the LSCR number byte).
The source checker also verifies the exact current generated-input identity
and the selected OBCD/local-script selectors before replay.

The ROOM has 16 walkboxes. The following object rows are decoded from its
authentic OBCD/CDHD/VERB records. Rectangles are half-open `(x,y,width,height)`
in room pixels; walk points are the authored actor coordinates. `owner 15`
means room-owned in the captured post-book room-7 state.

| ID | Authored name | Rect; walk point | Verbs | Post-book state/owner | OBCD SHA-256 |
|---:|---|---|---|---|---|
| 112 | wax cat | `56,112,32,32`; `55,141` | 8,9 | 0/15 | `8b42c0d14f983d47dc81b890b6942530a57914c2e83c22973e8b4add54a93ab3` |
| 113 | coal chute | `32,80,16,40`; `30,122` | 9,10 | 0/15 | `82b09c8bfc0bf204e18a68f6f7d02686d96e9b52ec3c1b992c6f5a29caaea8f8` |
| 114 | cellar-roof-1 | `128,48,80,24`; `175,122` | — | 0/15 | `45d3cd3e724e86d7e0c78afc37076050a5c06efe1fd66b580d41348d75ee51b5` |
| 115 | hole | `128,48,80,24`; `136,119` | — | 0/15 | `6347a1322f93b9bd349559c0e158340558d153f058a25e5c96293b0ac000ac87` |
| 116 | cat figurine | `56,120,24,24`; `61,140` | 9,10,11 | 0/15 | `a95bc3bff265f6b5f417f86ae8705d29d890b14b7aa4030d1aafe38b8a418a50` |
| 117 | cat figurine | `80,120,24,24`; `85,136` | 9,10,11 | 0/15 | `7d298b8cc695365116fd7d1ea7623ccf584a0087ab4e7460b73e4632724b708b` |
| 118 | cat figurine | `104,112,16,24`; `102,133` | 9,10,11 | 0/15 | `4ed263b154cc3b39937b95c69f863f909fb686428bd19e1335b9761153700466` |
| 119 | cat figurine | `120,112,16,24`; `118,129` | 9,10,11 | 0/15 | `540496ef75dd3037d5d82debb4d9df1e63256dfdaa1116773dd7094fcb41bd19` |
| 120 | shelves | `176,72,24,24`; `192,108` | 9 | 0/15 | `132cdf051bb28f79a32637431d162785cfda00f52e10b6b36ef4afe87f31fb70` |
| 121 | shelves | `152,72,24,24`; `168,111` | 9 | 0/15 | `ea1e7037c9ae869d04a52a2b186a05c1d5ae2d92b6ebae51e4d6ac15c120b3cf` |
| 122 | shelves | `112,72,32,24`; `135,115` | 9 | 0/15 | `7b46119026690e48185e939ea93dcd544808fa0be07f7c512a400a39045a4c94` |
| 123 | shelves | `64,64,40,32`; `92,120` | 9 | 0/15 | `a742a3731e7655d1c71194f79d1d4b1fb62f55f36fc3b66d9347b5abba034e44` |
| 124 | drawers | `72,96,32,16`; `100,120` | 3,4,8 | 0/15 | `2d5901389f93d62fa4324d8a05031b58b31992053f1a8c3652b91f81d21d424c` |
| 125 | drawers | `112,96,32,16`; `140,116` | 3,4,8 | 0/15 | `2155bd2aef2696b27151268ec61e35aa907a2a9e27664b6d058dc28e49c0548c` |
| 126 | drawers | `152,96,24,8`; `168,111` | 3,4,8 | 0/15 | `d5821fef4e5644009c286c77d250bd107e88d52dbadd5fa842776de9430adf44` |
| 127 | drawers | `176,96,24,8`; `192,108` | 3,4,9 | 0/15 | `017a38f29a54a35d21323e967312cf21a0f21dd6b9476bf2a2ce7545d0186f19` |
| 128 | real-cat-gone | `56,112,32,32`; `63,131` | — | 0/15 | `bb4246fb3e5a03eecc96fcac8d0440a3f0332fb8abd0bbc5b6a7036e94a0dc2f` |
| 129 | fake-cat-1-gone | `56,112,48,32`; `0,0` | — | 0/15 | `f10e610840685dd00ffd6160e2783fa88643c08e5f8d073559163127d4dba141` |
| 130 | pile of books | `152,112,48,16`; `184,130` | 9,10,11 | 1/15 | `eec52f0804cbd2d5822e3f3c1f05dfa9f083762a491abfefa414c604d95b742b` |
| 131 | inside of bookshelf | `152,56,40,8`; `136,119` | 9 | 0/15 | `be71ad0ee8575885062527158829400fd5890f1ebb63db9c47e4bac524fa98fc` |
| 132 | book | `176,56,8,8`; `136,119` | 8,9,11 | 1/15 | `d8b6853bd42a2b9454fdda02dc15467313ca559268ad08424a66828985e9ae6f` |
| 133 | Lost Dialogue book | `176,120,24,8`; `175,122` | 9,11 | 0/15 | `ca2ef144faa690c2f87cbfe92106a4b46f52e055b15dba24751be527eb61ae60` |
| 134 | scenery | `0,144,320,56`; `0,0` | — | 0/15 | `71cb2e45332e1a0892e7facc11c58b5bbb52c018ab9f12932eb767ca9c2dd8d2` |
| 135 | scenery | `0,136,320,8`; `0,0` | — | 0/15 | `2f227d4ba8ce408cc883de3d2b13fee58cd488f103c170863afcd1d6361fd85c` |

## Authored state and interaction edges

On the first-entry path, room ENCD tests bit 69 (global bit 4:5). When clear,
it clears variables V214 and V215–V218, initializes the room's cat classes, and enters
the first-visit sequence through LSCR208/LSCR200. After the accepted book
interaction, native state is V214=0 and V215–V218=0, Ego in room 7, and
inventory object 937 owned by Ego. The book's verb 11 starts Global144 with
`[21,4]`, performs its authored bit-clear operation, changes object 133's
state/class, transfers object 937 to Ego, and starts Global10; the observed
globals retire before the settled frontier. The flag operation and variable
V218 are distinct state namespaces; the replay records both where needed.

The room's currently relevant interaction graph is:

```text
object 112 / relevant room initialization
    -> cat display/classification support through V209/V210/V212/V213
    -> LSCR206 for cat look/pick-up variants

first distinct figurine object i in {116,117,118,119}, verb 10
    -> if bit69 clear and its per-figure variable is clear:
         if V214 == 1: start LSCR207([i]); chain LSCR201
         set that figure's variable (V215,V216,V217,V218); V214 += 1

second distinct figurine (different per-figure variable), verb 10
    -> same condition now sees V214 == 1
    -> LSCR207 changes the selected/random cat classes and sets V219
    -> LSCR201 runs the cutscene, changes actor/costume/box state,
       puts Ego in room 3, and actorFollowCamera(VAR_EGO)
    -> room 3 becomes the active scene

coal chute object 113, verb 9 or 10
    -> bit69 set: start LSCR203; actor walk/cutscene; loadRoom(3)
    -> bit69 clear: invoke the slippery verb-9 response

object 127, verb 3/4
    -> toggle its authored drawer state 0 <-> 1
    -> no room transition in the decoded body

object 130, pile of books, verb 10
    -> tests bits 13:7, 13:10, 13:12; may run LSCR204/205,
       alter coal-object ownership/state, then starts Global10/123

object 133, Lost Dialogue book, verb 11
    -> Global144([21,4]); state/class mutation; setOwnerOf(937,Ego);
       authored bit-clear; Global10; end cutscene
```

Bit 69 is read by room ENCD/EXCD, the coal chute, and the cat figurines. A
source-wide scan of the available original game script bodies found its
setters in room-2 ENCD at code offset `$016B` and room-10 ENCD at `$01DD`,
both under a V224==75 condition. It is therefore expected to remain zero on
this first room-7 visit (V224 is not 75); setting it from a replay or
debugger would falsify the authored state. It is one alternate chute path,
not a prerequisite for the two-distinct-figurine path.

The setter source bodies are independently identified as room-2 ENCD at
`ATLANTIS/ATLANTIS.001` offset `322484`, size 534, SHA-256
`dad669612ef8a9618dd1cb1df2d6ba1f4d9295e15698499438ff22484e57f56a`, and
room-10 ENCD at offset `980093`, size 923, SHA-256
`f099e966e95cec7213164ac64f1d61d13db3258065266bec16d7cdf4e479b372`.

Other active room verbs provide descriptions, delegate sibling shelf/drawer
objects to shared object scripts, or give authored refusal text (for example,
the bookshelf says it is not an exit and the high book says it cannot be
reached). The current scan found no other unconditional room transition in
those object bodies. Separate authored room paths include the state-gated
chute (LSCR203) and the LSCR217 override/cutscene branch to room 1. The room
exit script releases room sound and retires its temporary actors; it is not
the progression trigger.

## Chosen deterministic replay

The recipe chooses figures 118 then 119 because both bodies, hitboxes,
selectors, and preconditions are authenticated in the current ROM/build
identity. It does not claim these are the only valid pair. The replay requires
the post-book state, owner of object 937 equal to Ego, V214/V215–V218/object
state checks, and controller context checks before sending any input. It
performs the normal cursor/button path exactly once per sentence; it never
writes game state through the debugger.

The fresh-power-on Nexen replay confirmed the path. The first figure changed
`(V214,V217)` from `(0,0)` to `(1,1)` with one sentence submission. The second
distinct figure produced the second submission; event-time native samples
observed room-7 LSCR207 (program `$88`, slot 6) at frame 15497 and LSCR201
(program `$89`, slot 5) at frame 15503. LSCR201 moved Ego into room 3 and
followed the camera. Room 3 installed at frame 15783, then its entry lifecycle
settled by frame 18181 at room 3, phase 0, error 0, lifecycle RUNNING, with
Ego in room 3 at `(71,142)` and room-local LSCR213 (program `$80`) live.

The transitioned room is authentic `ATLANTIS/ATLANTIS.001` LFLF at offset
352294. Its ROOM payload is 55590 bytes, SHA-256
`3f7700ab0cdacbf7db6b3d5712e95fcfa6e6bd5fbd8b641da04d443aeec49a42`; ENCD
is 115 bytes, SHA-256 `ab3e9693d009c666948256224b348fc73170d0c2a0b60d82ead8b20479e32c3e`.
The live LSCR213 body is at archive offset 407823, size 77, SHA-256
`f4d56881433ef0aa6f8f337b5f7c17023765f5ace1d50beb948155f8f3fef089`,
selected as program `$80`. This is a new authentic room boundary, not a claim
that room 3's subsequent puzzle has been solved. The run used the exact ROM,
map, build identity, and Nexen hashes recorded in the replay recipe; it began
from power-on and used controller input only (no debugger game-state writes
or savestate load).
