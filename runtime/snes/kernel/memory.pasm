; SAME v0.2 fixed WRAM bootstrap layout.
; This is deliberately a contract, not a general allocator yet.
SAME_EVENT_HEAD              = $7E2000 ; u16 slot index
SAME_EVENT_TAIL              = $7E2002 ; u16 slot index
SAME_EVENT_COUNT             = $7E2004 ; u16 records present
SAME_EVENT_DROPPED           = $7E2006 ; u16 DROP_OK records lost
SAME_EVENT_REJECTED          = $7E2008 ; u16 required records rejected
SAME_EVENT_SEQUENCE          = $7E200A ; u16 next sequence
SAME_EVENT_STAGING           = $7E2020 ; 16-byte packet staging record
SAME_EVENT_BUFFER            = $7E2100 ; 16 records * 16 bytes
SAME_EVENT_CAPACITY          = $0010
SAME_EVENT_MASK              = $000F

SAME_INPUT_HELD              = $7E2200
SAME_INPUT_PREVIOUS          = $7E2202
SAME_INPUT_PRESSED           = $7E2204
SAME_INPUT_RELEASED          = $7E2206
SAME_FRAME_COUNTER           = $7E2210
SAME_VIDEO_BACKDROP_SHADOW   = $7E2212
SAME_AUDIO_LAST_OPCODE       = $7E2214
SAME_AUDIO_LAST_ARG0         = $7E2216
SAME_AUDIO_LAST_ARG1         = $7E221A
SAME_DEBUG_LAST_OPCODE       = $7E221E
SAME_ENGINE_ID                = $7E2220 ; u8 active engine module
SAME_ENGINE_LIFECYCLE         = $7E2221 ; u8 SAME_ENGINE_* state
SAME_ENGINE_LAST_STATUS       = $7E2222 ; u8 last asynchronous engine status
SAME_ENGINE_FRAME_OPS         = $7E2224 ; u16 current-frame semantic operations
SAME_ENGINE_TOTAL_OPS         = $7E2226 ; u16 rolling operation counter
SAME_ENGINE_PRIVATE_STATE     = $7E2228 ; u16 active-engine private bootstrap state
SAME_ENGINE_HEARTBEAT_NEXT    = $7E222A ; u16 demo-engine heartbeat deadline
SAME_ENGINE_PROFILE_ID        = $7E222C ; u16 generated profile identifier
SAME_ENGINE_CAPS_LO           = $7E222E ; u16 negotiated capability bits 0..15
SAME_ENGINE_CAPS_HI           = $7E2230 ; u16 negotiated capability bits 16..31

; Kernel-owned DMA request staging and queue.  A descriptor contains no
; hardware channel field: channel 7 is an implementation detail of the SNES
; commit backend.  Slots are marked active only after every other field lands.
SAME_DMA_REQUEST_SOURCE_LO    = $7E2232 ; u16 source low/mid
SAME_DMA_REQUEST_SOURCE_BANK  = $7E2234 ; u8 source bank
SAME_DMA_REQUEST_TYPE_FLAGS   = $7E2235 ; u8 semantic type/flags
SAME_DMA_REQUEST_TARGET       = $7E2236 ; u16 PPU-memory byte address
SAME_DMA_REQUEST_LENGTH       = $7E2238 ; u16 bytes, 1..SAME_DMA_FRAME_BUDGET
SAME_DMA_CURRENT_SLOT         = $7E223A ; u16 byte offset into ring
SAME_DMA_PENDING              = $7E223C ; u16 active requests
SAME_DMA_COMMITTED            = $7E223E ; u16 completed requests
SAME_DMA_DEFERRED_BLANK       = $7E2240 ; u16 forced-blank deferrals
SAME_DMA_DEFERRED_BUDGET      = $7E2242 ; u16 vblank-budget deferrals
SAME_DMA_REJECTED             = $7E2244 ; u16 invalid/full requests
SAME_DMA_FRAME_BYTES          = $7E2246 ; u16 bytes committed this NMI
SAME_VIDEO_DISPLAY_SHADOW     = $7E2248 ; u8 last INIDISP value requested
SAME_DMA_QUEUE                = $7E2260 ; 8 descriptors * 8 bytes
SAME_DMA_QUEUE_SLOTS          = $0008
SAME_DMA_QUEUE_SLOT_SIZE      = $0008
SAME_DMA_QUEUE_MASK           = $003F
SAME_DMA_FRAME_BUDGET         = $0800

; Copyright-free SCUMM v5 conformance lane.  This is engine state, not a game
; profile and not donor state.  Sixteen signed 16-bit variables are sufficient
; for the ROM-resident semantic fixture.
SAME_SCUMM_PC                 = $7E2300 ; u16 script byte offset
SAME_SCUMM_STATUS             = $7E2302 ; u8 SCUMM_VM_*
SAME_SCUMM_ERROR              = $7E2303 ; u8 SCUMM_ERR_*
SAME_SCUMM_DELAY              = $7E2304 ; u16 remaining frame delays
SAME_SCUMM_LAST_OPCODE        = $7E2306 ; u8 last decoded opcode
SAME_SCUMM_FRAME_COUNT        = $7E2308 ; u16 adapter frames
SAME_SCUMM_FRAME_OPS          = $7E230A ; u16 operations this frame
SAME_SCUMM_TOTAL_OPS          = $7E230C ; u16 operations since boot
SAME_SCUMM_VARIABLES          = $7E2320 ; 16 signed u16 variables
SAME_SCUMM_RESULT_OFFSET      = $7E2340 ; u16 scratch byte offset
SAME_SCUMM_OPERAND            = $7E2342 ; u16 operand scratch
SAME_SCUMM_BUDGET             = $7E2344 ; u16 remaining per-frame op budget
SAME_SCUMM_FETCH_BYTE         = $7E2346 ; u8 fetch scratch
SAME_SCUMM_CONDITION          = $7E2347 ; u8 conditional scratch
SAME_SCUMM_LHS                = $7E2348 ; u16 arithmetic scratch
SAME_SCUMM_PRODUCT            = $7E234A ; u16 product/quotient scratch
SAME_SCUMM_REMAINDER          = $7E234C ; u16 division scratch
SAME_SCUMM_LOOP               = $7E234E ; u16 arithmetic loop counter
SAME_SCUMM_SLOT0_PC           = $7E2350 ; u16 C3 scheduler slot zero PC
SAME_SCUMM_SLOT0_DELAY        = $7E2352 ; u16 C3 scheduler slot zero delay
SAME_SCUMM_SLOT0_STATUS       = $7E2354 ; u8 C3 scheduler slot zero status
SAME_SCUMM_SLOT1_PC           = $7E2356 ; u16 C3 scheduler slot one PC
SAME_SCUMM_SLOT1_DELAY        = $7E2358 ; u16 C3 scheduler slot one delay
SAME_SCUMM_SLOT1_STATUS       = $7E235A ; u8 C3 scheduler slot one status
SAME_SCUMM_SCHED_OPS          = $7E235C ; u16 aggregate operations this frame
SAME_SCUMM_STATE_END          = $7E235E
SAME_SCUMM_STATE_SIZE         = $005E
; Test control is deliberately outside resettable VM state. A debugger can
; request another copyright-free fixture; the engine acknowledges it and
; resets before executing that case.
SAME_SCUMM_FIXTURE_REQUEST    = $7E235E ; u8 requested generated fixture
SAME_SCUMM_FIXTURE_ACTIVE     = $7E235F ; u8 fixture currently executing
SAME_SCUMM_PROGRAM_SIZE       = $7E2360 ; u16 selected program size scratch
SAME_SCUMM_PROGRAM_SELECT     = $7E2362 ; u8 selected slot/program bytecode
SAME_SCUMM_RETURN_MODE        = $7E2363 ; u8 zero=outer frame, one=slot return
SAME_SCUMM_CONTROL_END        = $7E2364
SAME_SCUMM_VARIABLE_COUNT     = $0010
SAME_SCUMM_MAX_OPS_PER_FRAME  = $0020

; C4 lifecycle conformance state. The 25-entry slot table mirrors the v5
; capacity contract; each slot owns 32 signed local variables. It is separate
; from debugger control so selecting a fixture cannot erase its own request.
SAME_SCUMM_C4_SLOT_STATUS      = $7E2380 ; 25 u8 SCUMM_VM_* values
SAME_SCUMM_C4_SLOT_NUMBER      = $7E2399 ; 25 u8 script numbers
SAME_SCUMM_C4_SLOT_PROGRAM     = $7E23B2 ; 25 u8 generated program selectors
SAME_SCUMM_C4_SLOT_DIDEXEC     = $7E23CB ; 25 u8 per-frame nested-run markers
SAME_SCUMM_C4_SLOT_PC          = $7E23E4 ; 25 u16 byte offsets
SAME_SCUMM_C4_SLOT_DELAY       = $7E2416 ; 25 u16 delays
SAME_SCUMM_C4_SLOT_LOCALS      = $7E2448 ; 25 * 32 signed u16 locals
SAME_SCUMM_C4_CURRENT_SLOT     = $7E2A88 ; u8 slot being decoded
SAME_SCUMM_C4_LAST_ALLOCATED   = $7E2A89 ; u8 last first-free allocation
SAME_SCUMM_C4_ACTIVE_COUNT     = $7E2A8A ; u8 occupied slot count
SAME_SCUMM_C4_SCAN_SLOT        = $7E2A8B ; u8 scheduler/allocation scratch
SAME_SCUMM_C4_PARENT_SLOT      = $7E2A8C ; u8 nested caller scratch
SAME_SCUMM_C4_PARENT_STATUS    = $7E2A8D ; u8 nested caller scratch
SAME_SCUMM_C4_PARENT_PROGRAM   = $7E2A8E ; u8 nested caller scratch
SAME_SCUMM_C4_ARG_COUNT        = $7E2A8F ; u8 decoded local argument count
SAME_SCUMM_C4_PARENT_PC        = $7E2A90 ; u16 nested caller scratch
SAME_SCUMM_C4_PARENT_DELAY     = $7E2A92 ; u16 nested caller scratch
SAME_SCUMM_C4_PARENT_OPS       = $7E2A94 ; u16 nested caller operation count
SAME_SCUMM_C4_ARGS             = $7E2A96 ; 32 signed u16 decoded arguments
; C5 appends scheduler flags after the stable C4 layout so existing debugger
; offsets and C4 reports remain valid.
SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT = $7E2AD6 ; 25 u8 booleans
SAME_SCUMM_C4_SLOT_RECURSIVE        = $7E2AEF ; 25 u8 booleans
SAME_SCUMM_C4_SLOT_FREEZE_COUNT     = $7E2B08 ; 25 u8 nested freeze counts
; C6 separates the scheduler cursor from allocator scratch because a nested
; start/chain may allocate while the outer slot scan is still in progress.
SAME_SCUMM_C4_CHAIN_MODE            = $7E2B21 ; u8 chain handoff in progress
SAME_SCUMM_C4_SCHED_SLOT            = $7E2B22 ; u8 outer scheduler cursor
SAME_SCUMM_C4_CHAIN_FLAGS           = $7E2B23 ; u8 inherited startScript flag bits
SAME_SCUMM_C4_CHAIN_OPS             = $7E2B24 ; u16 replacement operation scratch
SAME_SCUMM_C4_STATE_END        = $7E2B26 ; rounded for the 16-bit clear loop
SAME_SCUMM_C4_STATE_SIZE       = $07A6
SAME_SCUMM_LOCAL_COUNT         = $0020

; Backend-owned normalized-audio trace for bounded service evidence. This is
; not engine state and contains no SPC/TAD implementation detail.
SAME_AUDIO_TRACE_COUNT         = $7E2B30 ; u8 records retained
SAME_AUDIO_TRACE_OPCODE        = $7E2B31 ; 8 u8 opcodes
SAME_AUDIO_TRACE_SOURCE        = $7E2B39 ; 8 u8 endpoints
SAME_AUDIO_TRACE_DESTINATION   = $7E2B41 ; 8 u8 endpoints
SAME_AUDIO_TRACE_ARG0          = $7E2B4A ; 8 u16 low argument words
SAME_AUDIO_TRACE_ARG1          = $7E2B5A ; 8 u16 low argument words
SAME_AUDIO_TRACE_CAPACITY      = $08

; C7 generic SCUMM cursor-command and bit-variable state. The bit array is
; engine-owned and represents all 4096 v5 bit variables exactly.
SAME_SCUMM_C7_CURSOR_STATE      = $7E2B70 ; s16 soft cursor nesting state
SAME_SCUMM_C7_USERPUT_STATE     = $7E2B72 ; s16 soft user-input nesting state
SAME_SCUMM_C7_CURSOR_IMAGE      = $7E2B74 ; u8 cursor image id
SAME_SCUMM_C7_CURSOR_CHAR       = $7E2B75 ; u8 cursor image character
SAME_SCUMM_C7_HOTSPOT_CURSOR    = $7E2B76 ; u8 hotspot cursor id
SAME_SCUMM_C7_HOTSPOT_X         = $7E2B77 ; u8 hotspot x
SAME_SCUMM_C7_HOTSPOT_Y         = $7E2B78 ; u8 hotspot y
SAME_SCUMM_C7_CURSOR_ID          = $7E2B79 ; u8 active cursor id
SAME_SCUMM_C7_CHARSET_ID         = $7E2B7A ; u8 active charset id
SAME_SCUMM_C7_COLOR_COUNT        = $7E2B7B ; u8 charset-color count
SAME_SCUMM_C7_SUBOP              = $7E2B7C ; u8 operand flags/sub-op scratch
SAME_SCUMM_C7_PARAM_INDEX        = $7E2B7D ; u8 parameter scratch
SAME_SCUMM_C7_COLORS             = $7E2B80 ; 16 u16 charset colors
SAME_SCUMM_C7_BITS               = $7E2BA0 ; 4096 packed bit variables
SAME_SCUMM_C7_STATE_END          = $7E2DA0
SAME_SCUMM_C7_STATE_SIZE         = $0230

; C8 generic SCUMM string resources. All 256 byte-sized string IDs retain
; independent 256-byte storage; a zero size denotes an absent resource and
; the largest canonical allocation is 255 bytes.
SAME_SCUMM_C8_SIZES               = $7E2DA0 ; 256 u8 logical allocation sizes
SAME_SCUMM_C8_SUBOP               = $7E2EA0 ; u8 operand flags/sub-op scratch
SAME_SCUMM_C8_STRING_ID           = $7E2EA1 ; u8 primary/destination id
SAME_SCUMM_C8_SECOND_ID           = $7E2EA2 ; u8 source id
SAME_SCUMM_C8_INDEX               = $7E2EA3 ; u8 character/write offset
SAME_SCUMM_C8_VALUE               = $7E2EA4 ; u8 character/control scratch
SAME_SCUMM_C8_LENGTH              = $7E2EA5 ; u8 logical size scratch
SAME_SCUMM_C8_SOURCE_BASE         = $7E2EA6 ; u16 source slot WRAM offset
SAME_SCUMM_C8_DEST_BASE           = $7E2EA8 ; u16 destination slot WRAM offset
SAME_SCUMM_C8_PENDING             = $7E2EAB ; u8 value preserved across address calculation
SAME_SCUMM_C9_COUNT               = $7E2EAA ; u16 remaining setVarRange assignments
SAME_SCUMM_C8_DATA                = $7E3000 ; 256 slots x 256 bytes, through $7F2FFF
SAME_SCUMM_C8_MAX_BYTES           = $FF
SAME_SCUMM_C8_SIZE_TABLE_BYTES    = $0100

; C10 roomOps state is an engine-owned intent block. The video/save backends
; consume these semantics; the opcode core never touches PPU or filesystem I/O.
SAME_SCUMM_C10_STATE              = $7F3000
SAME_SCUMM_C10_SUBOP              = $7F3000 ; u8 current operand flags/sub-op
SAME_SCUMM_C10_SCROLL_MIN         = $7F3002 ; u16 clamped camera minimum
SAME_SCUMM_C10_SCROLL_MAX         = $7F3004 ; u16 clamped camera maximum
SAME_SCUMM_C10_SCREEN_TOP         = $7F3006 ; u16 virtual-screen top
SAME_SCUMM_C10_SCREEN_BOTTOM      = $7F3008 ; u16 virtual-screen bottom
SAME_SCUMM_C10_SHAKE              = $7F300A ; u8 boolean
SAME_SCUMM_C10_ROOM_WIDTH         = $7F300C ; u16 logical room width
SAME_SCUMM_C10_SCALE_SLOTS        = $7F3010 ; 4 slots x 4 u8 values
SAME_SCUMM_C10_INTENSITY          = $7F3020 ; 5 u8 values
SAME_SCUMM_C10_SAVE_FLAG          = $7F3025 ; u8 temporary save/load flag
SAME_SCUMM_C10_SAVE_SLOT          = $7F3026 ; u8 canonical temporary slot 99
SAME_SCUMM_C10_FADE               = $7F3028 ; u16 room-switch effect
SAME_SCUMM_C10_RGB_INTENSITY      = $7F302A ; 5 u8 values
SAME_SCUMM_C10_SHADOW             = $7F302F ; 5 u8 values
SAME_SCUMM_C10_TRANSFORM          = $7F3034 ; 4 u8 values
SAME_SCUMM_C10_CYCLE_DELAYS       = $7F3038 ; 16 u16 delays
SAME_SCUMM_C10_PALETTE_PRESENT    = $7F3058 ; 256 packed presence bits
SAME_SCUMM_C10_PALETTE_RGB        = $7F3078 ; 256 x RGB888
SAME_SCUMM_C10_AUX_NAME_SIZE      = $7F3378 ; u8 saved filename size
SAME_SCUMM_C10_AUX_NAME           = $7F3379 ; 63 saved filename bytes
SAME_SCUMM_C10_REQUEST_NAME_SIZE  = $7F33B8 ; u8 decoded filename size
SAME_SCUMM_C10_REQUEST_NAME       = $7F33B9 ; 63 request filename bytes
SAME_SCUMM_C10_AUX_SIZE           = $7F33F8 ; u8 saved string size
SAME_SCUMM_C10_AUX_DATA           = $7F3400 ; 255 saved string bytes
SAME_SCUMM_C10_PARAM0             = $7F34F0 ; u16 operand scratch
SAME_SCUMM_C10_PARAM1             = $7F34F2 ; u16 operand scratch
SAME_SCUMM_C10_PARAM2             = $7F34F4 ; u16 operand scratch
SAME_SCUMM_C10_PARAM3             = $7F34F6 ; u16 operand scratch
SAME_SCUMM_C10_PARAM4             = $7F34F8 ; u16 operand scratch
SAME_SCUMM_C10_STATE_END          = $7F3500
SAME_SCUMM_C10_STATE_SIZE         = $0500

; C11 deterministic engine-owned random source. The nonzero LFSR state is
; persisted engine state; range operands and samples are bounded scratch.
SAME_SCUMM_C11_RANDOM_STATE       = $7F3500 ; nonzero u16 Galois LFSR state
SAME_SCUMM_C11_MAXIMUM            = $7F3502 ; u16 inclusive upper bound scratch
SAME_SCUMM_C11_SAMPLE             = $7F3504 ; u16 reduced sample scratch
SAME_SCUMM_C11_STATE_END          = $7F3506
SAME_SCUMM_C11_STATE_SIZE         = $0006

; C12 pseudo-room resource indirection. Entries 0..127 are physical u8 room
; identifiers selected when a script addresses the matching high-bit room.
SAME_SCUMM_C12_ROOM               = $7F3506 ; decoded physical room scratch
SAME_SCUMM_C12_INITIALIZED        = $7F3507 ; mapper has deterministic zero base
SAME_SCUMM_C12_MAPPER             = $7F3510 ; 128 x u8 pseudo-room map
SAME_SCUMM_C12_STATE_END          = $7F3590
SAME_SCUMM_C12_STATE_SIZE         = $008A

; C13 resource routines retain engine-owned cache and lock intent. Each
; resource class uses one packed 256-bit table; source resources remain owned
; by the resource service and are never destroyed by a script nuke request.
SAME_SCUMM_C13_LOADED              = $7F3590 ; 5 x 32-byte bitsets
SAME_SCUMM_C13_LOCKED              = $7F3630 ; 4 x 32-byte bitsets
SAME_SCUMM_C13_LAST_OBJECT_ROOM    = $7F36B0 ; u8 mapped room id
SAME_SCUMM_C13_LAST_OBJECT_ID      = $7F36B2 ; u16 object id
SAME_SCUMM_C13_SELECTOR            = $7F36B4 ; u8 flags/sub-op scratch
SAME_SCUMM_C13_OPERATION           = $7F36B5 ; u8 normalized operation
SAME_SCUMM_C13_RESOURCE            = $7F36B6 ; u8 normalized resource id
SAME_SCUMM_C13_KIND                = $7F36B7 ; u8 resource kind 0..4
SAME_SCUMM_C13_INITIALIZED         = $7F36B8 ; deterministic-state marker
SAME_SCUMM_C13_STATE_END           = $7F36BA
SAME_SCUMM_C13_STATE_SIZE          = $012A

; C14 full-header actorOps intent. Thirty-two v5 actors each own a compact
; 64-byte scalar/palette record plus independent 255-byte encoded name storage.
SAME_SCUMM_C14_ACTORS               = $7F36C0 ; 32 x 64-byte actor records
SAME_SCUMM_C14_NAME_SIZES           = $7F3EC0 ; 32 x u8 encoded sizes
SAME_SCUMM_C14_NAMES                = $7F3F00 ; 32 x 256-byte name slots
SAME_SCUMM_C14_ACTOR                = $7F5F00 ; u8 selected actor
SAME_SCUMM_C14_SUBOP                = $7F5F01 ; u8 flags/sub-op scratch
SAME_SCUMM_C14_BASE                 = $7F5F02 ; u16 actor-record offset
SAME_SCUMM_C14_NAME_BASE            = $7F5F04 ; u16 actor-name offset
SAME_SCUMM_C14_NAME_INDEX           = $7F5F06 ; u16 encoded-name index
SAME_SCUMM_C14_INITIALIZED          = $7F5F08 ; deterministic-state marker
SAME_SCUMM_C14_STATE_END            = $7F5F0A
SAME_SCUMM_C14_STATE_SIZE           = $284A

SAME_SCUMM_C14_ACTOR_STRIDE         = $0040
SAME_SCUMM_C14_A_COSTUME            = $00
SAME_SCUMM_C14_A_SPEED_X            = $01
SAME_SCUMM_C14_A_SPEED_Y            = $02
SAME_SCUMM_C14_A_SOUND              = $03
SAME_SCUMM_C14_A_INIT_FRAME         = $04
SAME_SCUMM_C14_A_WALK_FRAME         = $05
SAME_SCUMM_C14_A_STAND_FRAME        = $06
SAME_SCUMM_C14_A_TALK_START         = $07
SAME_SCUMM_C14_A_TALK_STOP          = $08
SAME_SCUMM_C14_A_TALK_COLOR         = $09
SAME_SCUMM_C14_A_ELEVATION          = $0A
SAME_SCUMM_C14_A_WIDTH              = $0C
SAME_SCUMM_C14_A_SCALE_X            = $0D
SAME_SCUMM_C14_A_SCALE_Y            = $0E
SAME_SCUMM_C14_A_BOX_SCALE          = $0F
SAME_SCUMM_C14_A_FORCE_CLIP         = $10
SAME_SCUMM_C14_A_IGNORE_BOXES       = $11
SAME_SCUMM_C14_A_ANIM_SPEED         = $12
SAME_SCUMM_C14_A_SHADOW             = $13
SAME_SCUMM_C14_A_ANIMATION          = $14
SAME_SCUMM_C14_A_PRESENT            = $1F
SAME_SCUMM_C14_A_PALETTE            = $20

; C15 camera-follow intent remains separate from actor configuration. Future
; movement/render slices may consume the selected actor without coupling the
; opcode core to video timing or room-transition policy.
SAME_SCUMM_C15_CAMERA_FOLLOWS       = $7F5F0A ; u8 actor id, $FF means none
SAME_SCUMM_C15_CAMERA_MODE          = $7F5F0B ; u8 0 normal, 1 follow actor
SAME_SCUMM_C15_MOVING_TO_ACTOR      = $7F5F0C ; u8 canonical transition flag
SAME_SCUMM_C15_INITIALIZED          = $7F5F0D ; deterministic-state marker
SAME_SCUMM_C15_STATE_END            = $7F5F0E
SAME_SCUMM_C15_STATE_SIZE           = $0004

; C16 stores only objects whose 32-bit v5 class mask is nonzero. The bounded
; 512-record table keeps 16-bit object identity without reserving a dense 64K
; object array. Empty records are reusable after clear-all or the final remove.
SAME_SCUMM_C16_RECORDS              = $7F5F10 ; 512 records * 8 bytes
SAME_SCUMM_C16_RECORD_STRIDE        = $0008
SAME_SCUMM_C16_RECORD_COUNT         = $0200
SAME_SCUMM_C16_R_PRESENT            = $00
SAME_SCUMM_C16_R_OBJECT             = $02 ; u16 object id
SAME_SCUMM_C16_R_MASK               = $04 ; u32 classes 1..32
SAME_SCUMM_C16_RECORDS_END          = $7F6F10
SAME_SCUMM_C16_OBJECT               = $7F6F10 ; u16 operand scratch
SAME_SCUMM_C16_CLASS                = $7F6F12 ; u16 raw class operation
SAME_SCUMM_C16_RECORD_OFFSET        = $7F6F14 ; u16 found record, $FFFF absent
SAME_SCUMM_C16_FREE_OFFSET          = $7F6F16 ; u16 first free record
SAME_SCUMM_C16_MASK_OFFSET          = $7F6F18 ; u16 record byte offset
SAME_SCUMM_C16_BIT_MASK             = $7F6F1A ; u8 class bit
SAME_SCUMM_C16_INITIALIZED          = $7F6F1B ; deterministic-state marker
SAME_SCUMM_C16_STATE_END            = $7F6F1C
SAME_SCUMM_C16_STATE_SIZE           = $100C

; C17 verb configuration is dense by the canonical u8 verb identity. Records
; retain presentation-neutral configuration and a bounded 64-byte encoded name;
; drawing and mouse-over policy remain in the video/input adapters.
SAME_SCUMM_C17_VERBS                = $7F6F20 ; 256 records * $60 bytes
SAME_SCUMM_C17_VERB_STRIDE          = $0060
SAME_SCUMM_C17_V_PRESENT            = $00
SAME_SCUMM_C17_V_MODE               = $01
SAME_SCUMM_C17_V_COLOR              = $02
SAME_SCUMM_C17_V_HICOLOR            = $03
SAME_SCUMM_C17_V_DIMCOLOR           = $04
SAME_SCUMM_C17_V_BKCOLOR            = $05
SAME_SCUMM_C17_V_TYPE               = $06 ; 0 text, 1 image
SAME_SCUMM_C17_V_CHARSET            = $07
SAME_SCUMM_C17_V_KEY                = $08
SAME_SCUMM_C17_V_CENTER             = $09
SAME_SCUMM_C17_V_LEFT               = $0A ; s16
SAME_SCUMM_C17_V_TOP                = $0C ; s16
SAME_SCUMM_C17_V_ORIG_LEFT          = $0E ; s16
SAME_SCUMM_C17_V_IMAGE_INDEX        = $10 ; u16
SAME_SCUMM_C17_V_IMAGE_ROOM         = $12 ; u8
SAME_SCUMM_C17_V_IMAGE_PRESENT      = $13 ; boolean
SAME_SCUMM_C17_V_IMAGE_OBJECT       = $14 ; u16
SAME_SCUMM_C17_V_SAVE_ID            = $16 ; u16
SAME_SCUMM_C17_V_NAME_LENGTH        = $18 ; 0 absent, otherwise includes NUL
SAME_SCUMM_C17_V_NAME               = $20 ; 64 encoded bytes
SAME_SCUMM_C17_NAME_MAX             = $40
SAME_SCUMM_C17_VERBS_END            = $7FCF20
SAME_SCUMM_C17_VERB                 = $7FCF20 ; u8 operand scratch
SAME_SCUMM_C17_SUBOP                = $7FCF21 ; selector flags scratch
SAME_SCUMM_C17_NAME_INDEX           = $7FCF22 ; u8 copy cursor
SAME_SCUMM_C17_CONTROL_ARGS         = $7FCF23 ; encoded control bytes remaining
SAME_SCUMM_C17_RECORD_OFFSET        = $7FCF24 ; u16 verb record offset
SAME_SCUMM_C17_PARAM0               = $7FCF26 ; u16 operand scratch
SAME_SCUMM_C17_PARAM1               = $7FCF28 ; u16 operand scratch
SAME_SCUMM_C17_INITIALIZED          = $7FCF2A ; deterministic-state marker
SAME_SCUMM_C17_CURRENT_ROOM         = $7FCF2B ; u8 image-source room snapshot
SAME_SCUMM_C17_STATE_END            = $7FCF2C
SAME_SCUMM_C17_STATE_SIZE           = $600C

; C18 evaluates canonical v5 expressions on the engine's bounded 256-entry
; signed 32-bit stack. Arithmetic stays 32-bit until the destination write.
SAME_SCUMM_C18_STACK                = $7FCF30 ; 256 signed u32 entries
SAME_SCUMM_C18_STACK_SIZE           = $0400
SAME_SCUMM_C18_STACK_END            = $7FD330
SAME_SCUMM_C18_SP                   = $7FD330 ; u16 byte offset
SAME_SCUMM_C18_DESTINATION          = $7FD332 ; processed result offset
SAME_SCUMM_C18_TOKEN                = $7FD334 ; selector/opcode scratch
SAME_SCUMM_C18_NESTED               = $7FD335 ; nested expression dispatch depth
SAME_SCUMM_C18_LHS_LO               = $7FD336
SAME_SCUMM_C18_LHS_HI               = $7FD338
SAME_SCUMM_C18_RHS_LO               = $7FD33A
SAME_SCUMM_C18_RHS_HI               = $7FD33C
SAME_SCUMM_C18_RESULT_LO            = $7FD33E
SAME_SCUMM_C18_RESULT_HI            = $7FD340
SAME_SCUMM_C18_SIGN                 = $7FD342
SAME_SCUMM_C18_LOOP                 = $7FD343
SAME_SCUMM_C18_REMAINDER_LO         = $7FD344
SAME_SCUMM_C18_REMAINDER_HI         = $7FD346
SAME_SCUMM_C18_STATE_END            = $7FD348
SAME_SCUMM_C18_STATE_SIZE           = $0418

; C19 canonical v5 cutscene/override state. The zero stack entry is the
; underflow sentinel, matching the original pointer discipline; entries 1..4
; are active nested cutscenes.
SAME_SCUMM_C19_STACK_POINTER         = $7FD348 ; u8, active depths 0..4
SAME_SCUMM_C19_DATA                  = $7FD34A ; 5 x s16 first callback argument
SAME_SCUMM_C19_OVERRIDE_PC           = $7FD354 ; 5 x u16, zero means absent
SAME_SCUMM_C19_OVERRIDE_SLOT         = $7FD35E ; 5 x u8 slot indices
SAME_SCUMM_C19_SLOT_DEPTH            = $7FD363 ; 25 x u8 cutsceneOverride
SAME_SCUMM_C19_SCRIPT_INDEX          = $7FD37C ; u8, $FF outside callbacks
SAME_SCUMM_C19_SELECTOR              = $7FD37D ; operand/override scratch
SAME_SCUMM_C19_ARGUMENT0             = $7FD37E ; s16 first word-vararg
SAME_SCUMM_C19_STATE_END             = $7FD380
SAME_SCUMM_C19_STATE_SIZE            = $0038

; C20 canonical v5 sentence queue. Six dense records retain the LIFO verb,
; object pair, preposition-derived state, and nested freeze depth.
SAME_SCUMM_C20_COUNT                 = $7FD380 ; u8 active records 0..6
SAME_SCUMM_C20_INITIALIZED           = $7FD381 ; deterministic-state marker
SAME_SCUMM_C20_RECORDS               = $7FD382 ; 6 records * 6 bytes
SAME_SCUMM_C20_RECORD_STRIDE         = $0006
SAME_SCUMM_C20_RECORD_COUNT          = $0006
SAME_SCUMM_C20_R_VERB                = $00 ; u8
SAME_SCUMM_C20_R_FREEZE              = $01 ; u8
SAME_SCUMM_C20_R_OBJECT_A            = $02 ; u16
SAME_SCUMM_C20_R_OBJECT_B            = $04 ; u16
SAME_SCUMM_C20_RECORDS_END           = $7FD3A6
SAME_SCUMM_C20_VERB                  = $7FD3A6 ; operand scratch
SAME_SCUMM_C20_OBJECT_A              = $7FD3A8 ; operand scratch
SAME_SCUMM_C20_OBJECT_B              = $7FD3AA ; operand scratch
SAME_SCUMM_C20_STATE_END             = $7FD3AC
SAME_SCUMM_C20_STATE_SIZE            = $002C

; C21 canonical v5 drawObject state. Three copyright-free local objects are
; enough to prove lookup, relocation, overlap clearing, state, and queue order.
SAME_SCUMM_C21_INITIALIZED            = $7FD3AC ; deterministic-state marker
SAME_SCUMM_C21_RECORD_COUNT           = $7FD3AD ; u8, fixture uses three
SAME_SCUMM_C21_QUEUE_COUNT            = $7FD3AE ; u8, bounded to eight
SAME_SCUMM_C21_POSITIONED             = $7FD3AF ; nonzero for sub-op 1
SAME_SCUMM_C21_RECORDS                = $7FD3B0 ; 3 records * 16 bytes
SAME_SCUMM_C21_RECORD_STRIDE          = $0010
SAME_SCUMM_C21_MAX_RECORDS            = $0003
SAME_SCUMM_C21_R_ID                   = $00 ; u16
SAME_SCUMM_C21_R_X                    = $02 ; s16
SAME_SCUMM_C21_R_Y                    = $04 ; s16
SAME_SCUMM_C21_R_WIDTH                = $06 ; u16
SAME_SCUMM_C21_R_HEIGHT               = $08 ; u16
SAME_SCUMM_C21_R_WALK_X               = $0A ; s16
SAME_SCUMM_C21_R_WALK_Y               = $0C ; s16
SAME_SCUMM_C21_R_STATE                = $0E ; u8
SAME_SCUMM_C21_RECORDS_END            = $7FD3E0
SAME_SCUMM_C21_QUEUE                  = $7FD3E0 ; 8 x u16 object ids
SAME_SCUMM_C21_MAX_QUEUE              = $0008
SAME_SCUMM_C21_OBJECT                 = $7FD3F0 ; operand scratch, u16
SAME_SCUMM_C21_SELECTOR               = $7FD3F2 ; operand scratch, u8
SAME_SCUMM_C21_STATE                  = $7FD3F3 ; requested state, u8
SAME_SCUMM_C21_X                      = $7FD3F4 ; requested script x, s16
SAME_SCUMM_C21_Y                      = $7FD3F6 ; requested script y, s16
SAME_SCUMM_C21_TARGET_OFFSET          = $7FD3F8 ; record byte offset, u16
SAME_SCUMM_C21_RECT_X                 = $7FD3FA
SAME_SCUMM_C21_RECT_Y                 = $7FD3FC
SAME_SCUMM_C21_RECT_WIDTH             = $7FD3FE
SAME_SCUMM_C21_RECT_HEIGHT            = $7FD400
SAME_SCUMM_C21_STATE_END              = $7FD402
SAME_SCUMM_C21_STATE_SIZE             = $0056

; C22 canonical room-transition state. Room zero is a resource-less null
; scene, but still commits the transition and clears room-local draw state.
SAME_SCUMM_C22_INITIALIZED             = $7FD402 ; deterministic-state marker
SAME_SCUMM_C22_CURRENT_ROOM            = $7FD403 ; resolved logical room, u8
SAME_SCUMM_C22_TRANSITION_COUNT        = $7FD404 ; successful transitions, u8
SAME_SCUMM_C22_OBJECT_COUNT            = $7FD405 ; room-local objects, u8
SAME_SCUMM_C22_QUEUE_COUNT             = $7FD406 ; pending draw intents, u8
SAME_SCUMM_C22_NULL_SCENE              = $7FD407 ; room zero has no resource
SAME_SCUMM_C22_STATE_END               = $7FD408
SAME_SCUMM_C22_STATE_SIZE              = $0006

; C23 canonical v5 print-slot state. Four persistent defaults feed one
; transient working style; the bounded last-message record proves text parsing.
SAME_SCUMM_C23_INITIALIZED              = $7FD408
SAME_SCUMM_C23_SLOTS                    = $7FD409 ; 4 x 11-byte records
SAME_SCUMM_C23_SLOT_STRIDE              = $000B
SAME_SCUMM_C23_P_X                      = $00 ; s16
SAME_SCUMM_C23_P_Y                      = $02 ; s16
SAME_SCUMM_C23_P_RIGHT                  = $04 ; s16
SAME_SCUMM_C23_P_HEIGHT                 = $06 ; u16
SAME_SCUMM_C23_P_COLOR                  = $08 ; u8
SAME_SCUMM_C23_P_CHARSET                = $09 ; u8
SAME_SCUMM_C23_P_FLAGS                  = $0A ; bit0 center, bit1 overhead
SAME_SCUMM_C23_MESSAGE_COUNT            = $7FD435
SAME_SCUMM_C23_LAST_ACTOR               = $7FD436
SAME_SCUMM_C23_LAST_SLOT                = $7FD437
SAME_SCUMM_C23_LAST_LENGTH              = $7FD438
SAME_SCUMM_C23_LAST_RAW                 = $7FD439 ; 16 encoded bytes
SAME_SCUMM_C23_WORK                     = $7FD449 ; 11-byte transient style
SAME_SCUMM_C23_ACTOR                    = $7FD454
SAME_SCUMM_C23_SELECTOR                 = $7FD455
SAME_SCUMM_C23_SLOT_OFFSET              = $7FD456 ; u16
SAME_SCUMM_C23_RAW_INDEX                = $7FD458 ; bounded decoder cursor
SAME_SCUMM_C23_STATE_END                = $7FD459
SAME_SCUMM_C23_STATE_SIZE               = $0051

; C25 canonical v5 soundKludge queue. Each bounded record stores its word
; count followed by up to 32 signed words; command -1 flushes queued records.
SAME_SCUMM_C25_QUEUE_COUNT               = $7FD459 ; u8
SAME_SCUMM_C25_QUEUE                     = $7FD45A ; 16 x 65-byte records
SAME_SCUMM_C25_MAX_COMMANDS              = $0010
SAME_SCUMM_C25_MAX_WORDS                 = $0020
SAME_SCUMM_C25_RECORD_STRIDE             = $0041
SAME_SCUMM_C25_QUEUE_END                 = $7FD86A
SAME_SCUMM_C25_LAST_COUNT                = $7FD86A ; u8
SAME_SCUMM_C25_LAST_WORDS                = $7FD86B ; 32 x s16
SAME_SCUMM_C25_FLUSH_COUNT               = $7FD8AB ; u8
SAME_SCUMM_C25_PENDING_COUNT             = $7FD8AC ; u8 transient record
SAME_SCUMM_C25_PENDING_WORDS             = $7FD8AD ; 32 x s16
SAME_SCUMM_C25_COMMAND_INDEX             = $7FD8ED ; u8 scratch
SAME_SCUMM_C25_SELECTOR                  = $7FD8EE ; u8 scratch
SAME_SCUMM_C25_RECORD_OFFSET             = $7FD8EF ; u16 scratch
SAME_SCUMM_C25_WORD_INDEX                = $7FD8F1 ; u8 scratch
SAME_SCUMM_C25_STATE_END                 = $7FD8F2
SAME_SCUMM_C25_STATE_SIZE                = $0499

; C26 canonical saveRestoreVerbs storage. Active verbs remain dense in the
; C17 table; saved banks need independent physical slots because an active
; replacement may reuse the same canonical verb id before restore.
SAME_SCUMM_C26_SAVED                     = $7FD900 ; 64 x $62-byte records
SAME_SCUMM_C26_SAVED_STRIDE              = $0062
SAME_SCUMM_C26_SAVED_COUNT               = $0040
SAME_SCUMM_C26_S_PRESENT                 = $00
SAME_SCUMM_C26_S_VERB                    = $01
SAME_SCUMM_C26_S_PAYLOAD                 = $02 ; one C17 $60-byte record
SAME_SCUMM_C26_SAVED_END                 = $7FF180
SAME_SCUMM_C26_OPERATION                 = $7FF180 ; exact sub-op, u8
SAME_SCUMM_C26_FIRST                     = $7FF181 ; range first/current, u8
SAME_SCUMM_C26_LAST                      = $7FF182 ; range last, u8
SAME_SCUMM_C26_BANK                      = $7FF183 ; save bank, u8
SAME_SCUMM_C26_SCAN                      = $7FF184 ; slot scan index, u8
SAME_SCUMM_C26_FREE_OFFSET               = $7FF186 ; first free slot, u16
SAME_SCUMM_C26_SAVED_OFFSET              = $7FF188 ; matching/selected slot, u16
SAME_SCUMM_C26_ACTIVE_OFFSET             = $7FF18A ; C17 record offset, u16
SAME_SCUMM_C26_COPY_INDEX                = $7FF18C ; payload copy cursor, u16
SAME_SCUMM_C26_STATE_END                 = $7FF18E
SAME_SCUMM_C26_STATE_SIZE                = $188E

; SAME 0.1 source-compatible names. Do not allocate new state through these.
SAME_TARGET_STATE            = SAME_ENGINE_PRIVATE_STATE
SAME_TARGET_HEARTBEAT_NEXT   = SAME_ENGINE_HEARTBEAT_NEXT

; Planned S-CPU <-> SA-1 mailbox. Neither side may overwrite a nonzero command.
SAME_SA1_MAILBOX_COMMAND     = $003000
SAME_SA1_MAILBOX_STATUS      = $003001
SAME_SA1_MAILBOX_SEQUENCE    = $003002
SAME_SA1_MAILBOX_ARG0        = $003004
SAME_SA1_MAILBOX_ARG1        = $003008
SAME_SA1_MAILBOX_RESULT0     = $00300C
SAME_SA1_MAILBOX_RESULT1     = $003010
SAME_SA1_MAILBOX_IDLE        = $00
SAME_SA1_MAILBOX_PENDING     = $01
SAME_SA1_MAILBOX_RUNNING     = $02
SAME_SA1_MAILBOX_COMPLETE    = $03
SAME_SA1_MAILBOX_FAULT       = $FF
