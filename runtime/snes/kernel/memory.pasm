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
SAME_INPUT_EDGE_SEQUENCE    = $7E2208 ; u16, advances once per newly sampled edge
SAME_INPUT_TALK_OWNED_SEQUENCE = $7E220A ; u16 edge sequence captured by active talk
SAME_INPUT_TALK_OWNED_VALID = $7E220C ; u8 token survives polls until controller consumes it
SAME_INPUT_AUTOJOY_TIMEOUTS = $7E220D ; u8 saturated count; poll resumes next frame
SAME_FRAME_COUNTER           = $7E2210
SAME_VIDEO_BACKDROP_SHADOW   = $7E2212
SAME_VIDEO_BG1_CONFIG_VALID  = $7E2249 ; NMI-owned PPU register shadow
SAME_VIDEO_BG1_MODE          = $7E224A ; u8 BGMODE
SAME_VIDEO_BG1_SCREEN        = $7E224B ; u8 BG1SC
SAME_VIDEO_BG1_CHARS         = $7E224C ; u8 BG12NBA
SAME_VIDEO_MAIN_LAYERS       = $7E224D ; u8 TM shadow
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
SAME_ENGINE_FRAME_BUSY        = $7E2231 ; u8 observable frame transaction guard

; Production TAD/SPC backend. This compact state occupies the final bytes
; before the kernel DMA descriptor block and is intentionally observable.
SAME_TAD_STATE                = $7E2250 ; TAD loader/driver lifecycle
SAME_TAD_PREVIOUS_COMMAND     = $7E2251 ; last APUIO0 command token
SAME_TAD_TRANSFER_OFFSET      = $7E2252 ; offset from SAME_TAD_AUDIO_DATA
SAME_TAD_TRANSFER_SIZE        = $7E2254 ; bytes remaining
SAME_TAD_TRANSFER_SPIN        = $7E2256 ; loader spinlock token
SAME_TAD_NEXT_SONG            = $7E2257 ; zero blank, mapped TAD song id otherwise
SAME_TAD_NEXT_COMMAND         = $7E2258 ; $FF empty
SAME_TAD_NEXT_PARAMETER0      = $7E2259
SAME_TAD_NEXT_PARAMETER1      = $7E225A
SAME_TAD_LAST_COMMAND         = $7E225B ; exact TAD command emitted
SAME_TAD_REJECTED             = $7E225C ; non-dropping queue-full count
SAME_TAD_PROBE_REQUEST        = $7E225D ; debugger requests real sound id
SAME_TAD_DEFERRED_SONG        = $7E225E ; M20 backend follow-up after blank
SAME_TAD_READY                = $7E225F ; driver playing/paused state reached
SAME_TAD_STATE_END           = $7E2260 ; exclusive kernel/TAD ownership boundary

; Generic SAME checked-read provider state. The single MSU-1 data cursor and
; request state are service-owned; callers supply their own destination. This
; 72-byte record lives in the audited gap before the SCUMM C8 table at $7E3000.
SAME_MSU1_STATE               = $7E2F00
SAME_MSU1_STATUS              = $7E2F00 ; u8 provider/init/read state
SAME_MSU1_ERROR               = $7E2F01 ; u8 explicit provider error
SAME_MSU1_FLAGS               = $7E2F02 ; u8 stream/ring flags
SAME_MSU1_INIT_INDEX          = $7E2F03 ; u8 initialization phase
SAME_MSU1_REQUEST_OFFSET      = $7E2F04 ; u32 package byte offset
SAME_MSU1_REQUEST_LENGTH      = $7E2F08 ; u32 requested bytes
SAME_MSU1_DESTINATION         = $7E2F0C ; 24-bit WRAM address
SAME_MSU1_DEST_CAPACITY       = $7E2F0F ; u16 caller-owned capacity
SAME_MSU1_EXPECTED_CRC        = $7E2F11 ; u32 request CRC32
SAME_MSU1_REMAINING            = $7E2F15 ; u32 untransferred bytes
SAME_MSU1_DEST_INDEX           = $7E2F19 ; u16 destination/ring cursor
SAME_MSU1_CRC_STATE            = $7E2F1B ; u32 reflected CRC state
SAME_MSU1_STEP_REMAINING       = $7E2F1F ; u16 per-frame transfer budget
SAME_MSU1_BYTE_SCRATCH         = $7E2F21 ; u8 data byte
SAME_MSU1_TIMEOUT              = $7E2F22 ; u8 bounded status poll budget
SAME_MSU1_PREFIX_INDEX         = $7E2F23 ; u16 trusted metadata cursor
SAME_MSU1_END_OFFSET           = $7E2F25 ; u32 overflow-checked exclusive end
SAME_MSU1_CRC_LSB              = $7E2F29 ; u8 CRC polynomial scratch
SAME_MSU1_CRC_BITS             = $7E2F2A ; u8 CRC bit count
SAME_MSU1_SEEK_COUNT           = $7E2F2B ; u16 diagnostic seeks
SAME_MSU1_BYTES_READ           = $7E2F2D ; u32 diagnostic transfer count
SAME_MSU1_READ_COUNT           = $7E2F31 ; u16 completed/failed request count
SAME_MSU1_TIMEOUT_COUNT        = $7E2F33 ; u16 bounded timeout count
SAME_MSU1_RANGE_REJECT_COUNT   = $7E2F35 ; u16 range/capacity rejects
SAME_MSU1_VERIFY_COUNT         = $7E2F37 ; u16 accepted metadata identities
SAME_MSU1_LAST_OFFSET          = $7E2F39 ; u32 last request offset
SAME_MSU1_LAST_LENGTH          = $7E2F3D ; u32 last request length
SAME_MSU1_AUDIO_TRACK          = $7E2F41 ; u16 selected PCM track
SAME_MSU1_AUDIO_FLAGS          = $7E2F43 ; u16 play flags
SAME_MSU1_AUDIO_LAST_STATUS    = $7E2F45 ; u8 latest MSU status snapshot
SAME_MSU1_SECTION_TEMP         = $7E2F46 ; u16 generated-section index math
SAME_MSU1_STATE_END            = $7E2F48 ; exclusive

.if SAME_BUILD_SCUMM_MSU1_PROGRAMS
; Three bounded executable-body windows. The third SA-1 cache page is a
; feature-exclusive alias of the unused Mode-3 conformance fixture workspace.
SAME_SCUMM_MSU_PROGRAM_CACHE_BASE       = $7E1000
SAME_SCUMM_MSU_PROGRAM_CACHE_SLOT_SIZE = $0800
SAME_SCUMM_MSU_PROGRAM_CACHE0           = $7E1000
SAME_SCUMM_MSU_PROGRAM_CACHE1           = $7E1800
SAME_SCUMM_MSU_PROGRAM_CACHE_END        = $7E2000
; Mode-3 conformance and streamed SCUMM are mutually exclusive personalities.
.if SAME_BUILD_SCUMM_MSU1_PROGRAMS && SAME_CARRIER_IS_SA1_BWRAM
SAME_SCUMM_MSU_PROGRAM_CACHE2           = $41E800
SAME_SCUMM_MSU_PROGRAM_CACHE2_BANK      = $41
SAME_SCUMM_MSU_PROGRAM_CACHE2_END       = $41F000
SAME_SCUMM_MSU_CACHE_HAS_PAGE2           = $01
.else
SAME_SCUMM_MSU_PROGRAM_CACHE2           = $000000
SAME_SCUMM_MSU_PROGRAM_CACHE2_BANK      = $00
SAME_SCUMM_MSU_PROGRAM_CACHE2_END       = $000000
SAME_SCUMM_MSU_CACHE_HAS_PAGE2           = $00
.endif
; Page-fault lookup/request scratch in the audited gap before provider cache
; metadata. Logical PCs remain source-body offsets; no cache address is saved.
SAME_SCUMM_MSU_PAGE_REQUEST_PC          = $7E2EAC ; u16 current logical PC
SAME_SCUMM_MSU_PAGE_REQUEST_START       = $7E2EAE ; u16 selected segment start PC
SAME_SCUMM_MSU_PAGE_REQUEST_LENGTH      = $7E2EB0 ; u16 checked segment length
SAME_SCUMM_MSU_PAGE_SCAN_INDEX          = $7E2EB2 ; u16 global page-record index
SAME_SCUMM_MSU_PAGE_SCAN_COUNT          = $7E2EB4 ; u16 remaining records
SAME_SCUMM_MSU_CACHE_PAGE_START0        = $7E2EB6 ; u16 logical start in slot 0
SAME_SCUMM_MSU_CACHE_PAGE_START1        = $7E2EB8 ; u16 logical start in slot 1
SAME_SCUMM_MSU_PAGE_BODY_LENGTH         = $7E2EBA ; u16 canonical full-body size
SAME_SCUMM_MSU_PAGE_REQUEST_CRC         = $7E2EBC ; u32 segment CRC-32
SAME_SCUMM_MSU_PAGE_REQUEST_ID          = $7E2ECD ; u16 current lookup identity; never owns an in-flight read
SAME_SCUMM_MSU_CACHE_LRU0               = $7E2EC0 ; u8 relative LRU rank, 0 oldest
SAME_SCUMM_MSU_CACHE_LRU1               = $7E2EC1
SAME_SCUMM_MSU_CACHE_LRU2               = $7E2EC2 ; u8 rank 2 is most recent
SAME_SCUMM_MSU_CACHE_STATE2             = $7E2EC3
SAME_SCUMM_MSU_CACHE_ID2                = $7E2EC4 ; u16 canonical directory ID
SAME_SCUMM_MSU_CACHE_SIZE2              = $7E2EC6 ; u16 validated page bytes
SAME_SCUMM_MSU_CACHE_PINS2              = $7E2EC8
SAME_SCUMM_MSU_CACHE_GENERATION2        = $7E2EC9 ; u16
SAME_SCUMM_MSU_CACHE_PAGE_START2        = $7E2ECB ; u16 logical body PC
SAME_SCUMM_MSU_PAGE_LOOKUP_END          = $7E2ECD
; One completion owner per executable page, so independent WAIT_RESOURCE
; activations cannot overwrite one another's validated-page protection.
SAME_SCUMM_MSU_CACHE_WAITER_SELECTOR0   = $7E2ED0 ; u8 selector owning page-0 completion hold
SAME_SCUMM_MSU_CACHE_WAITER_SLOT0       = $7E2ED1 ; u8 C4 slot owning page-0 completion hold
SAME_SCUMM_MSU_CACHE_WAITER_SELECTOR1   = $7E2ED2
SAME_SCUMM_MSU_CACHE_WAITER_SLOT1       = $7E2ED3
SAME_SCUMM_MSU_CACHE_WAITER_SELECTOR2   = $7E2ED4
SAME_SCUMM_MSU_CACHE_WAITER_SLOT2       = $7E2ED5
SAME_SCUMM_MSU_CACHE_WAITER_END         = $7E2ED6
; Cache metadata stays in the provider's audited WRAM gap.
SAME_SCUMM_MSU_CACHE_STATE0              = $7E2F48
SAME_SCUMM_MSU_CACHE_STATE1              = $7E2F49
SAME_SCUMM_MSU_CACHE_ID0                 = $7E2F4A
SAME_SCUMM_MSU_CACHE_ID1                 = $7E2F4C
SAME_SCUMM_MSU_CACHE_SIZE0               = $7E2F4E
SAME_SCUMM_MSU_CACHE_SIZE1               = $7E2F50
SAME_SCUMM_MSU_CACHE_PINS0               = $7E2F52
SAME_SCUMM_MSU_CACHE_PINS1               = $7E2F53
SAME_SCUMM_MSU_CACHE_GENERATION0         = $7E2F54
SAME_SCUMM_MSU_CACHE_GENERATION1         = $7E2F56
SAME_SCUMM_MSU_CACHE_REQUEST_ID          = $7E2F58
SAME_SCUMM_MSU_CACHE_REQUEST_SLOT        = $7E2F5A
SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT          = $7E2F5B
SAME_SCUMM_MSU_CACHE_ACTIVE_ID           = $7E2F5C
SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION   = $7E2F5E
SAME_SCUMM_MSU_CACHE_CURRENT_BYTES       = $7E2F60 ; validated resident page bytes
SAME_SCUMM_MSU_CACHE_PEAK_BYTES          = $7E2F62 ; exact simultaneous cache high-water
SAME_SCUMM_MSU_CACHE_LOADS               = $7E2F64
SAME_SCUMM_MSU_CACHE_EVICTIONS            = $7E2F66
SAME_SCUMM_MSU_CACHE_FAILURES             = $7E2F68
SAME_SCUMM_MSU_CACHE_TABLE_INDEX          = $7E2F6A ; u16 indexed 10-byte record
SAME_SCUMM_MSU_CACHE_TEMP                 = $7E2F6C ; u16 multiply scratch
SAME_SCUMM_MSU_CACHE_RETURN_P             = $7E2F6E ; u8 saved interpreter P
SAME_SCUMM_MSU_ACTIVE_SELECTOR             = $7E2F6F ; ephemeral selector owning active fetch
SAME_SCUMM_MSU_PENDING_CHILD_SLOT         = $7E2F70 ; 25 u8, slot+1 or zero
SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM      = $7E2F89 ; 25 u8 selector identity
SAME_SCUMM_MSU_C19_ERROR_STAGE             = $7E2FA2 ; u8 C19 failure call-site
SAME_SCUMM_MSU_C19_ERROR_OPCODE            = $7E2FA3 ; u8 last decoded opcode
SAME_SCUMM_MSU_C19_ERROR_PROGRAM           = $7E2FA4 ; u8 ephemeral selector
SAME_SCUMM_MSU_C19_ERROR_PC                = $7E2FA5 ; u16 logical body PC
SAME_SCUMM_MSU_C19_ERROR_SLOT              = $7E2FA7 ; u8 C4 owner
SAME_SCUMM_MSU_PROCESS_TURNS               = $7E2FA8 ; u16 storage frame turns
SAME_SCUMM_MSU_PROCESS_LAST_STATUS         = $7E2FAA ; u8 state at last turn
SAME_SCUMM_MSU_FRAME_ENTRIES               = $7E2FAB ; u16 logical kernel frame entries
SAME_SCUMM_MSU_ENGINE_RETURNS              = $7E2FAD ; u16 SCUMM engine frame returns
SAME_SCUMM_MSU_FRAME_STAGE                 = $7E2FAF ; u8 last frame boundary
; Bounded interpreter-entry stack. The VM's existing common completion paths
; call Leave to release a body pin and restore a nested caller's cache context.
; The 25-entry limit matches C4's activation ceiling; source PCs remain in the
; existing C4 logical-PC tables, never as cache pointers.
SAME_SCUMM_MSU_EXEC_DEPTH                  = $7E2FB0 ; u8 active interpreter entries
SAME_SCUMM_MSU_EXEC_PREV_SLOT              = $7E2FB1 ; 25 u8 parent cache slot/FF
SAME_SCUMM_MSU_EXEC_PREV_SELECTOR          = $7E2FCA ; 25 u8 parent selector/FF
SAME_SCUMM_MSU_DIRECT_ROOM_CALL            = $7E2FE3 ; u8 Engine_Frame tail-call marker
SAME_SCUMM_MSU_RESOLVE_CALLS               = $7E2FE4 ; u16 resolver adapter entries
SAME_SCUMM_MSU_LAST_SELECTOR               = $7E2FE6 ; u8 most recent adapter selector
SAME_SCUMM_MSU_CACHE_END                   = $7E2FEB ; end of executable-cache metadata
; Incoming cooked-room preflight reuses one unpinned ProgramUnit window. It is
; not published as executable; the checked room directory/header is validated
; before M23A is allowed to run EXCD or retire the current room.
SAME_SCUMM_MSU_ROOM_STATE                  = $7E2FEB ; 0 idle, 1 requested, 2 reading, 3 validated, FF failed
SAME_SCUMM_MSU_ROOM_ID                     = $7E2FEC ; requested logical room
SAME_SCUMM_MSU_ROOM_REQUESTS               = $7E2FED ; u16
SAME_SCUMM_MSU_ROOM_VALIDATIONS            = $7E2FEF ; u16
SAME_SCUMM_MSU_ROOM_FAILURES               = $7E2FF1 ; u16
SAME_SCUMM_MSU_MAX_FETCH_LATENCY            = $7E2FF3 ; u16 transfer-to-validated frames, code or room
SAME_SCUMM_MSU_ROOM_START_FRAME            = $7E2FF5 ; u16
SAME_SCUMM_MSU_ROOM_LAST_LENGTH            = $7E2FF7 ; u16
SAME_SCUMM_MSU_ROOM_SCRIPT_COUNT            = $7E2FF9 ; u16 parse scratch/result
SAME_SCUMM_MSU_ROOM_DATA_OFFSET             = $7E2FFB ; u16 cooked SC5ROOM payload offset
SAME_SCUMM_MSU_ROOM_TEMP                    = $7E2FFD ; u16 arithmetic scratch
SAME_SCUMM_MSU_ROOM_CACHE_SLOT              = $7E2FFF ; u8 staging window owner
SAME_SCUMM_MSU_ROOM_STATE_END               = $7E3000
.endif

.if SAME_BUILD_WINSTON_IO
; Diagnostic-client staging only. It is not provider state and is deliberately
; unavailable to SCUMM builds, whose object-name cache owns $7E9000-$7F1000.
.if SAME_BUILD_SCUMM_M19
    .error "Winston IO staging cannot share the SCUMM engine personality"
.endif
SAME_WINSTON_IO_STAGE          = $7E6000 ; 20,480-byte image/staging buffer
SAME_WINSTON_IO_STAGE_SIZE     = $5000
SAME_WINSTON_IO_RING            = $7EB000 ; 256-byte rolling test read window
SAME_WINSTON_IO_RING_SIZE       = $0100
SAME_WINSTON_IO_GUARD           = $7EB100 ; canaries and frame/result state
SAME_WINSTON_IO_STATE_END       = $7EB200
SAME_WINSTON_IO_STATUS          = $7EB100 ; u8 0=init, 1=cases, 2=pass, $FF=fail
SAME_WINSTON_IO_CASE_INDEX      = $7EB101 ; u8 current generated read case
SAME_WINSTON_IO_CASES_PASSED    = $7EB102 ; u16 completed positive/reject checks
SAME_WINSTON_IO_CASES_EXPECTED  = $7EB104 ; u16 generated native oracle count
SAME_WINSTON_IO_FAILED_CASE     = $7EB106 ; u16 first failure, $FFFF means none
SAME_WINSTON_IO_AUDIO_STARTED   = $7EB108 ; u8 background track is active
SAME_WINSTON_IO_DEST_MODE       = $7EB109 ; u8 0=stage, 1=rolling ring
SAME_WINSTON_IO_SAMPLE_LENGTH   = $7EB10A ; u8 generated prefix sample length
SAME_WINSTON_IO_COMPARE_INDEX   = $7EB10B ; u8 sample cursor
SAME_WINSTON_IO_GUARD_BEFORE    = $7EB10C ; u8 rolling-buffer canary
SAME_WINSTON_IO_GUARD_AFTER     = $7EB10D ; u8 rolling-buffer canary
SAME_WINSTON_IO_TOTAL_READS     = $7EB10E ; u16 requests begun
SAME_WINSTON_IO_REJECTS         = $7EB110 ; u16 expected range rejects observed
SAME_WINSTON_IO_EXPECTED_STATUS = $7EB112 ; u8 generated status expectation
SAME_WINSTON_IO_TEMP            = $7EB114 ; u16 case-table arithmetic scratch
SAME_WINSTON_IO_ASSET_STAGE     = $7EB116 ; u8 visual-demo state machine
SAME_WINSTON_IO_TILE_OFFSET     = $7EB118 ; u16 staged tile DMA cursor
SAME_WINSTON_IO_SCENE_ID        = $7EB11A ; u8 0=hidden, 1=closed, 2=open, 3=verge, 4=slate
SAME_WINSTON_IO_ASSET_SUBSTATE  = $7EB11B ; u8 0=read, 1=queue, 2=DMA pending
SAME_WINSTON_IO_ASSET_SECTION   = $7EB11C ; u16 last generated section index
SAME_WINSTON_IO_ASSET_SIZE      = $7EB11E ; u16 last validated resource size
SAME_WINSTON_IO_ASSET_READS     = $7EB120 ; u16 validated visual-section reads
SAME_WINSTON_IO_ASSET_CRC_OK    = $7EB122 ; u8 last checked read passed CRC
SAME_WINSTON_IO_ASSET_FAILURE   = $7EB123 ; u8 explicit visual/demo failure class
SAME_WINSTON_IO_TILE_DMA_COUNT  = $7EB124 ; u16 accepted tile DMA chunks
SAME_WINSTON_IO_AUDIO_CHECK_FRAMES = $7EB126 ; u16 track-2 loop observation frames
.endif
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
; Authored SCUMM profiles use the complete generated variable table.  Keep
; the compact bootstrap window for the small conformance fixtures, but do not
; let VAR_SENTENCE_SCRIPT (or any other variable above 15) alias the live
; interpreter selector at $7E2362.
.if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
SAME_SCUMM_VARIABLES          = $7FF500 ; 512-word authored table
SAME_SCUMM_VARIABLES_BOOTSTRAP_RESERVED = $7E2320 ; historical window
.elseif SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY
; The resolver prototype is an engine integration build, not a 16-variable
; micro-fixture. Keep authored variables out of the interpreter scratch window
; so high-numbered synthetic sentinels remain real SCUMM variables.
SAME_SCUMM_VARIABLES          = $7FF500 ; 512-word authored table
SAME_SCUMM_RESIDENCY_VARIABLES_BASE = $7FF500
SAME_SCUMM_RESIDENCY_VARIABLES_END = $7FF900 ; exclusive table end
SAME_SCUMM_VARIABLES_BOOTSTRAP_RESERVED = $7E2320 ; historical window
.else
SAME_SCUMM_VARIABLES          = $7E2320 ; historical bootstrap allocation
.endif
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
SAME_SCUMM_C1_HOLD_AFTER      = $7E2364 ; debugger-only committed-frame hold
SAME_SCUMM_CONTROL_END        = $7E2365
.if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
; Count/base/extent come from generated/scumm_v5_variables.inc.pasm.
SAME_SCUMM_MAX_OPS_PER_FRAME  = $1000
.elseif SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY
SAME_SCUMM_VARIABLE_COUNT     = $0200 ; authored residency-fixture variable table
SAME_SCUMM_MAX_OPS_PER_FRAME  = $1000
.elseif SAME_BUILD_SCUMM_M23B
SAME_SCUMM_VARIABLE_COUNT     = $0200 ; bounded Fate demo profile closure
SAME_SCUMM_MAX_OPS_PER_FRAME  = $1000
.else
SAME_SCUMM_VARIABLE_COUNT     = $0010
SAME_SCUMM_MAX_OPS_PER_FRAME  = $0020
.endif

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
SAME_SCUMM_C4_PARENT_RETURN_MODE    = $7E2B27 ; u8 nested caller return mode
SAME_SCUMM_C4_STATE_SIZE       = $07A6
SAME_SCUMM_LOCAL_COUNT         = $0020
; Streamed body cache misses share one checked-read cursor. Rotate the first
; scheduler slot per frame so a later WAIT_RESOURCE activation cannot starve
; behind earlier scripts which repeatedly fault different cache pages.
SAME_SCUMM_C4_SCHED_CURSOR     = $7E2B2A ; u8 next streamed scheduler start slot
SAME_SCUMM_C4_SCHED_REMAINING  = $7E2B2B ; u8 slots left in this scan
SAME_SCUMM_C4_SCHED_FAIR_END   = $7E2B2C

; Backend-owned normalized-audio trace for bounded service evidence. This is
; not engine state and contains no SPC/TAD implementation detail.
SAME_AUDIO_TRACE_COUNT         = $7E2B30 ; u8 records retained
SAME_AUDIO_TRACE_OPCODE        = $7E2B31 ; 8 u8 opcodes
SAME_AUDIO_TRACE_SOURCE        = $7E2B39 ; 8 u8 endpoints
SAME_AUDIO_TRACE_DESTINATION   = $7E2B41 ; 8 u8 endpoints
SAME_AUDIO_TRACE_ARG0          = $7E2B4A ; 8 u16 low argument words
SAME_AUDIO_TRACE_ARG1          = $7E2B5A ; 8 u16 low argument words
SAME_AUDIO_TRACE_CAPACITY      = $08

; Optional engine-neutral compiled-music lifecycle. It is linked only by
; personalities that request lifecycle responses, leaving existing engines'
; emitted service code unchanged.
SAME_MUSIC_LIFECYCLE_STATUS    = $7E2B6A ; u8 SAME_MUSIC_STATUS_*
SAME_MUSIC_LIFECYCLE_LOGICAL   = $7E2B6B ; u8 active logical catalog identity
SAME_MUSIC_LIFECYCLE_DURATION  = $7E2B6C ; u16 zero means looping/no completion
SAME_MUSIC_LIFECYCLE_DEADLINE  = $7E2B6E ; u16 semantic-frame deadline

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
SAME_SCUMM_C10_PARAM5             = $7F34FA ; u16 far-handler continuation scratch
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
SAME_SCUMM_C14_A_VISIBLE            = $15
SAME_SCUMM_C14_A_ROOM               = $16
SAME_SCUMM_C14_A_HIT_LEFT           = $17 ; s16 inclusive logical bounds
SAME_SCUMM_C14_A_HIT_TOP            = $19 ; s16
SAME_SCUMM_C14_A_HIT_RIGHT          = $1B ; s16
SAME_SCUMM_C14_A_HIT_BOTTOM         = $1D ; s16
SAME_SCUMM_C14_A_PRESENT            = $1F
SAME_SCUMM_C14_A_PALETTE            = $20

SAME_SCUMM_C29_X                    = $7F5F0A ; s16 query point
SAME_SCUMM_C29_Y                    = $7F5F0C ; s16 query point
SAME_SCUMM_C29_ACTOR                = $7F5F0E ; u8 scan/result actor

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
SAME_SCUMM_C16_INITIALIZED           = $7F6F1B ; deterministic-state marker
SAME_SCUMM_C16_STATE_END             = $7F6F1C
SAME_SCUMM_C16_STATE_SIZE            = $100C

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
SAME_SCUMM_C21_R_PARENT_STATE         = $0F ; expected low-nibble parent state
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
; The high byte is otherwise zero for all four transient print-slot offsets.
; Reuse it only while one encoded print message is being consumed.
SAME_SCUMM_C23_TEXT_TRUNCATED           = $7FD457 ; u8, compact talk payload overflow
SAME_SCUMM_C23_RAW_INDEX                = $7FD458 ; bounded decoder cursor
SAME_SCUMM_C23_STATE_END                = $7FD459
SAME_SCUMM_C23_STATE_SIZE               = $0051

; C25 canonical v5 soundKludge queue. Each packed record stores a byte word
; count followed by up to 32 signed words. The queue budget is the original
; 256-word iMUSE queue (one count word plus each argument per command).
SAME_SCUMM_C25_QUEUE_COUNT               = $7FD459 ; u8
SAME_SCUMM_C25_QUEUE                     = $7FD45A ; packed records, max $0200 bytes
SAME_SCUMM_C25_MAX_WORDS                 = $0020
SAME_SCUMM_C25_MAX_QUEUE_WORDS           = $0100
SAME_SCUMM_C25_QUEUE_CAPACITY_BYTES      = $0200
SAME_SCUMM_C25_QUEUE_END                 = $7FD65A
SAME_SCUMM_C25_LAST_COUNT                = $7FD86A ; u8
SAME_SCUMM_C25_LAST_WORDS                = $7FD86B ; 32 x s16
SAME_SCUMM_C25_FLUSH_COUNT               = $7FD8AB ; u8
SAME_SCUMM_C25_PENDING_COUNT             = $7FD8AC ; u8 transient record
SAME_SCUMM_C25_PENDING_WORDS             = $7FD8AD ; 32 x s16
SAME_SCUMM_C25_COMMAND_INDEX             = $7FD8ED ; u8 scratch
SAME_SCUMM_C25_SELECTOR                  = $7FD8EE ; u8 scratch
SAME_SCUMM_C25_RECORD_OFFSET             = $7FD8EF ; u16 scratch
SAME_SCUMM_C25_WORD_INDEX                = $7FD8F1 ; u8 scratch
SAME_SCUMM_C25_QUEUE_WORDS_USED          = $7FD8F2 ; u16, includes each record count word
SAME_SCUMM_C25_CLEAR_QUEUE_COUNT          = $7FD8F4 ; u16 observed iMUSE clear-queue ops
SAME_SCUMM_C25_STATE_END                 = $7FD8F6
SAME_SCUMM_C25_STATE_SIZE                = $049B

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

; C30 canonical v5 findObject state. Parent indexes are one-based indexes into
; the bounded C21 room-object table, matching the raw v5 CDHD representation.
SAME_SCUMM_C30_STATE                     = $7FF190
SAME_SCUMM_C30_PARENTS                   = $7FF190 ; 3 x u8 local indexes
SAME_SCUMM_C30_X                         = $7FF194 ; signed query coordinate
SAME_SCUMM_C30_Y                         = $7FF196 ; signed query coordinate
SAME_SCUMM_C30_RECORD_OFFSET             = $7FF198 ; candidate byte offset
SAME_SCUMM_C30_CURRENT_OFFSET            = $7FF19A ; parent-chain byte offset
SAME_SCUMM_C30_DEPTH                     = $7FF19C ; bounded chain depth
SAME_SCUMM_C30_MASK                      = $7FF19D ; operand flag mask
SAME_SCUMM_C30_STATE_END                 = $7FF19E
SAME_SCUMM_C30_STATE_SIZE                = $000E

; C31 actor placement state supplements the compact C14 actor records with
; canonical logical positions and movement flags. putActorInRoom itself only
; changes the room, except room zero also performs putActor(0,0,0).
SAME_SCUMM_C31_STATE                     = $7FF1A0
SAME_SCUMM_C31_POSITIONS                 = $7FF1A0 ; 32 x (s16 x, s16 y)
SAME_SCUMM_C31_MOVING                    = $7FF220 ; 32 x u8 movement flags
SAME_SCUMM_C31_ACTOR                     = $7FF240 ; u8 selected actor
SAME_SCUMM_C31_ROOM                      = $7FF241 ; u8 selected room
SAME_SCUMM_C31_INITIALIZED               = $7FF242 ; deterministic-state marker
SAME_SCUMM_C31_STATE_END                 = $7FF244
SAME_SCUMM_C31_STATE_SIZE                = $00A4

; C32 canonical v5 putActorAtObject scratch. Placement is stored in C31;
; object walk points come from the bounded C21 raw-room records.
SAME_SCUMM_C32_STATE                     = $7FF244
SAME_SCUMM_C32_ACTOR                     = $7FF244 ; u8 selected actor
SAME_SCUMM_C32_OBJECT                    = $7FF245 ; u16 selected object
SAME_SCUMM_C32_X                         = $7FF247 ; resolved s16 x
SAME_SCUMM_C32_Y                         = $7FF249 ; resolved s16 y
SAME_SCUMM_C32_RECORD_OFFSET             = $7FF24B ; candidate byte offset
SAME_SCUMM_C32_STATE_END                 = $7FF24D
SAME_SCUMM_C32_STATE_SIZE                = $0009

; Logical SCUMM audio ownership. This is engine semantics used by synchronous
; isSoundRunning; compiled song ids and TAD/SPC state remain backend-private.
SAME_SCUMM_ACTIVE_MUSIC                  = $7FF24D ; u8 logical sound id or zero

; M20's one-slot SRAM transaction uses a fixed WRAM staging record. The
; compiled-music position is advisory metadata only; cold load restarts a
; running cue from its compiled beginning.
SAME_SCUMM_MUSIC_POSITION                = $7FF24E ; u32 advisory semantic frames
SAME_SAVE_STATUS                         = $7FF252 ; u8 SAME_SAVE_STATUS_*
SAME_SAVE_LAST_ERROR                     = $7FF253 ; u8 SAME_SAVE_ERROR_*
SAME_SAVE_WRITE_COUNT                    = $7FF254 ; u16 committed SRAM writes
SAME_SAVE_LOAD_COUNT                     = $7FF256 ; u16 successful cold loads
SAME_SAVE_REJECT_COUNT                   = $7FF258 ; u16 transactional rejects
; M21 route ownership is logical SCUMM state.  It never represents a live TAD
; instruction pointer or a source-sequencer cursor.
SAME_SCUMM_MUSIC_ROUTE_KIND              = $7FF25A ; 0 default, 1 hook
SAME_SCUMM_MUSIC_ROUTE_VALUE             = $7FF25B ; bounded u8 route value
SAME_SCUMM_MUSIC_ROUTE_SONG              = $7FF25C ; resolved backend song evidence
SAME_SCUMM_M21_ROUTE_COUNT               = $7FF25D ; route resolutions
SAME_SCUMM_M21_HISTORY_COUNT             = $7FF25E ; bounded logical history
SAME_SCUMM_M21_HISTORY_OP                = $7FF25F ; 16 u8: 1 start, 2 hook, 3 resolve, 4 stop
SAME_SCUMM_M21_HISTORY_KIND              = $7FF26F ; 16 u8 route kinds
SAME_SCUMM_M21_HISTORY_VALUE             = $7FF27F ; 16 u8 route values
SAME_SCUMM_M21_HISTORY_SONG              = $7FF28F ; 16 u8 resolved compiled songs
SAME_SCUMM_M21_HISTORY_LOGICAL           = $7FF29F ; 16 u8 logical sounds
SAME_SCUMM_M21_HISTORY_CAPACITY          = $0010
; M22 owns one bounded pending compiled-section decision. Stable numeric ids
; are profile data; none of these fields is a TAD instruction pointer.
SAME_SCUMM_M22_CUE_GENERATION            = $7FF2AF ; u8, zero is never live
SAME_SCUMM_M22_ROUTE_HISTORY             = $7FF2B0 ; stable bounded route-history id
SAME_SCUMM_M22_CURRENT_SECTION           = $7FF2B1 ; stable compiled-section id
SAME_SCUMM_M22_PENDING_HOOK              = $7FF2B2 ; zero means none
SAME_SCUMM_M22_ELIGIBLE_BOUNDARY         = $7FF2B3 ; generic boundary token
SAME_SCUMM_M22_SELECTED_CONTINUATION     = $7FF2B4 ; stable compiled-section id
SAME_SCUMM_M22_CONSUMPTION               = $7FF2B5 ; 0 none, 1 pending, 2 consumed
SAME_SCUMM_M22_ARM_COUNT                 = $7FF2B6 ; accepted pending selections
SAME_SCUMM_M22_CONSUME_COUNT             = $7FF2B7 ; exact one-shot consumption evidence
SAME_SCUMM_M22_STALE_COUNT               = $7FF2B8 ; ignored stale notifications
SAME_SCUMM_M22_GENERATION_AT_ARM         = $7FF2B9 ; ownership proof
; Backend evidence is colocated with the bounded M22 state rather than the
; kernel DMA ring at $7E2260-$7E229F.
SAME_TAD_SECTION_DEFERRED                = $7FF2BA ; $FF none, compiled selector otherwise
SAME_TAD_SECTION_TOKEN                   = $7FF2BB ; expected compiled boundary token
SAME_TAD_BOUNDARY_TOKEN                  = $7FF2BC ; most recently observed token
SAME_TAD_BOUNDARY_COUNT                  = $7FF2BD ; observed source-bound notifications
; M23A generic cooked-room lookup and lifecycle evidence. All title/resource
; identities live in generated profile tables; this block stores only generic
; registry ownership and bounded transition history.
SAME_SCUMM_M23A_ACTIVE_RECORD            = $7FF2BE ; generated resource index
SAME_SCUMM_M23A_ACTIVE_ROOM              = $7FF2BF ; logical room identity
SAME_SCUMM_M23A_PENDING_RECORD           = $7FF2C0
SAME_SCUMM_M23A_PENDING_ROOM             = $7FF2C1
SAME_SCUMM_M23A_PHASE                    = $7FF2C2 ; 0 driver, 1 EXCD, 2 ENCD, 3 hold
SAME_SCUMM_M23A_RETURN_PROGRAM           = $7FF2C3
SAME_SCUMM_M23A_HOLD                     = $7FF2C4 ; registration-only dispatch barrier
SAME_SCUMM_M23A_REQUEST_COUNT            = $7FF2C5
SAME_SCUMM_M23A_VALIDATION_COUNT         = $7FF2C6
SAME_SCUMM_M23A_REGISTER_COUNT           = $7FF2C7
SAME_SCUMM_M23A_RETIRE_COUNT             = $7FF2C8
SAME_SCUMM_M23A_ENTRY_COUNT              = $7FF2C9
SAME_SCUMM_M23A_EXIT_COUNT               = $7FF2CA
SAME_SCUMM_M23A_DESCRIPTOR_COUNT         = $7FF2CB
SAME_SCUMM_M23A_LOCAL_COUNT              = $7FF2CC
SAME_SCUMM_M23A_ENTRY_PROGRAM            = $7FF2CD
SAME_SCUMM_M23A_EXIT_PROGRAM             = $7FF2CE
SAME_SCUMM_M23A_CURRENT_KIND             = $7FF2CF
SAME_SCUMM_M23A_CHECKSUM                 = $7FF2D0 ; compact record sum
SAME_SCUMM_M23A_BYTE                     = $7FF2D2 ; zero-extended sum byte
SAME_SCUMM_M23A_DESCRIPTOR_CHECKSUM      = $7FF2D4
SAME_SCUMM_M23A_LIFECYCLE_COUNT          = $7FF2D6
SAME_SCUMM_M23A_LIFECYCLE                = $7FF2D7 ; 14 ordered phase codes
SAME_SCUMM_M23A_RETURN_PC                = $7FF2E5 ; u16 driver continuation
SAME_SCUMM_M23A_SLOT_ROOMS               = $7FF2E7 ; 25 room-owner bytes
SAME_SCUMM_M23A_CHAIN_SLOT               = $7FF2D8 ; lifecycle chain target, $FF when idle
SAME_SCUMM_M23A_CHAIN_PHASE              = $7FF2D9 ; nonzero while slot-zero continuation is chained
; First malformed lifecycle-poll witness; occupies the final six bytes of the
; M23A block before its declared STATE_END. Written only on a poll error.
SAME_SCUMM_M23A_CHAIN_ERROR_KIND         = $7FF2FA ; 1 bad slot, 2 unknown status, 3 error status without engine error
SAME_SCUMM_M23A_CHAIN_ERROR_SLOT         = $7FF2FB ; captured chain slot
SAME_SCUMM_M23A_CHAIN_ERROR_STATUS       = $7FF2FC ; captured C4 status, $FF if slot invalid
SAME_SCUMM_M23A_CHAIN_ERROR_PHASE        = $7FF2FD ; captured chain phase
SAME_SCUMM_M23A_STATE_END                = $7FF300
SAME_SCUMM_M23A_STATE_SIZE               = $0042
SAME_SAVE_STAGING                        = $7FF300 ; complete versioned save record
SAME_SAVE_STAGING_MAX_END                 = $7FF454 ; max M21+M22 record end
.if SAME_BUILD_SCUMM_M21
.if SAME_BUILD_SCUMM_M22
SAME_SAVE_RECORD_SIZE                    = $0154
.else
SAME_SAVE_RECORD_SIZE                    = $00CC
.endif
.else
SAME_SAVE_RECORD_SIZE                    = $00AC
.endif

; M23B gate-only observation state. The named pre-Thera fixture is applied at
; engine boot; these bytes never carry source commands or force branch results.
SAME_SCUMM_M23B_STATE                    = $7FF460
SAME_SCUMM_M23B_FIXTURE_APPLIED          = $7FF460
SAME_SCUMM_M23B_AUTH_FLUSH_SEEN          = $7FF461
SAME_SCUMM_M23B_AUTH_FLUSH_QUEUE_COUNT   = $7FF462
SAME_SCUMM_M23B_HOLD_AFTER_FLUSH         = $7FF463
SAME_SCUMM_M23B_HOLD_AFTER_CONDITION     = $7FF464
SAME_SCUMM_M23B_NEST_DEPTH               = $7FF465
SAME_SCUMM_M23B_ERROR_SITE               = $7FF466
; A nested frame retains the suspended slot/return mode and accumulated opcode
; count. PC, delay, status, flags, room owner, and locals live in the
; authoritative 25-slot table. Twenty-four frames are the maximum once one slot
; is executing, so overflow is bounded by the existing slot contract.
SAME_SCUMM_M23B_NEST_FRAMES              = $7FF900 ; 24 x (u8 mode:slot,u16 ops)
SAME_SCUMM_M23B_NEST_FRAME_STRIDE        = $0003
SAME_SCUMM_M23B_NEST_MAX_DEPTH           = $18
SAME_SCUMM_M23B_NEST_STATE_END           = $7FF948
; Program selection is live interpreter context, not merely slot-owned state.
; It must remain exact across a long nested child and intervening NMIs.
SAME_SCUMM_M23B_NEST_PROGRAMS            = $7E5420 ; 24 x u8 program identity
SAME_SCUMM_M23B_STATE_END                = $7FF467
; Room-return activation metadata is in the audited gap after M23B's
; seven-byte diagnostic block and before the optional $7FF500 variable table.
; It is outside the checksum scratch words at $7FF2D0-$7FF2D5 and all M23A
; bulk-cleared descriptor/state ranges.
SAME_SCUMM_M23A_RETURN_VALID             = $7FF467 ; u8 one-shot continuation validity
SAME_SCUMM_M23A_RETURN_SLOT              = $7FF468 ; u8 surviving C4 activation owner
SAME_SCUMM_M23A_RETURN_MODE              = $7FF469 ; u8 saved scheduler return mode
SAME_SCUMM_M23A_REQUEST_API_ACTIVE       = $7FF46A ; u8 API request origin during dispatch
SAME_SCUMM_M23A_REQUEST_API_ACTIVE_END   = $7FF46B ; exclusive continuation-state end
.if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
SAME_SCUMM_M23B_VARIABLES                = SAME_SCUMM_VARIABLES ; compatibility name only
SAME_SCUMM_M23B_VARIABLES_END            = SAME_SCUMM_VARIABLE_END
.else
SAME_SCUMM_M23B_VARIABLES                = $7FF500 ; provisional 512-word table
SAME_SCUMM_M23B_VARIABLES_END            = $7FF900
.endif

; Canonical v5 global object-state table and bounded active-room redraw
; descriptors. The table is dense because DOBJ declares the legal object
; range; local records are generated from the complete cooked ROOM resource.
SAME_SCUMM_OBJECT_COUNT                   = $7E5FF0 ; u16 declared DOBJ count
; Fixture-gated controller scene state. This is input/presentation glue, not
; semantic game state; the sentence API remains the only producer of C20.
SAME_SCUMM_CONTROLLER_MODE                = $7E5FE0 ; 0 hover,1 verb,2 action,3 secondary hover,4 secondary selected
SAME_SCUMM_CONTROLLER_CURSOR_X            = $7E5FE1 ; u16 logical scene cursor
SAME_SCUMM_CONTROLLER_CURSOR_Y            = $7E5FE3 ; u16 logical scene cursor
SAME_SCUMM_CONTROLLER_VERB                = $7E5FE5 ; u8 selected authored verb
SAME_SCUMM_CONTROLLER_OBJECT              = $7E5FE6 ; u16 selected authored object
SAME_SCUMM_CONTROLLER_HUD_DIRTY           = $7E5FE8 ; u8 overlay refresh request
SAME_SCUMM_CONTROLLER_SUBMISSIONS         = $7E5FE9 ; u8 controller-origin sentences
SAME_SCUMM_CONTROLLER_LAST_ACTION         = $7E5FEA ; u8 last submitted authored verb
SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED  = $7E5FEB ; u8 fixture room-42 handoff
; Generic source-object interaction scratch.  This is a bounded service
; interface, not a room-specific hotspot table.  The active-room records at
; SAME_SCUMM_SETSTATE_LOCAL_RECORDS remain the source-backed metadata.
SAME_SCUMM_INTERACTION_X                 = $7E5F90 ; s16 room/world cursor x
SAME_SCUMM_INTERACTION_Y                 = $7E5F92 ; s16 room/world cursor y
SAME_SCUMM_INTERACTION_OBJECT            = $7E5F94 ; u16 hit object/result
SAME_SCUMM_INTERACTION_FLAGS             = $7E5F96 ; u8 hit object flags
SAME_SCUMM_INTERACTION_INDEX             = $7E5F97 ; u8 active record index
SAME_SCUMM_INTERACTION_LIMIT             = $7E5F98 ; u16 rectangle arithmetic
SAME_SCUMM_INTERACTION_VERB_FIRST        = $7E5F9A ; u16 verb-cycle first
SAME_SCUMM_INTERACTION_VERB_AFTER        = $7E5F9C ; u8 verb-cycle cursor state
SAME_SCUMM_CONTROLLER_TEXT_INDEX         = $7E5F9E ; u16 encoded HUD destination index
; Generic text-service handoff for controller-owned prompts.  This is kept
; separate from the logical C23 talk stream because authored text may update
; that stream after a controller frame has staged a HUD prompt.
SAME_VIDEO_TEXT_CONTROLLER_BUFFER        = $7E5FA4 ; 32 encoded bytes
SAME_VIDEO_TEXT_CONTROLLER_LENGTH        = $7E5FC4 ; u8, includes terminator
SAME_VIDEO_TEXT_CONTROLLER_VALID         = $7E5FC5 ; u8 pending controller text
SAME_SCUMM_OBJECT_NAME_OBJECT            = $7E5FA0 ; u16 $54 operand scratch
SAME_SCUMM_OBJECT_NAME_INDEX             = $7E5FA2 ; u8 encoded-name cursor
SAME_SCUMM_CONTROLLER_INPUT_RAW         = $7E5F8E ; debug-only last raw pressed word
; First-error capture latch for the experimental streamed-room VM diagnostic.
; The C25 fixture owns $7E5F0E-$7E5F12 and its error counters begin at $7E5F20;
; reserve only the verified six-byte gap between them. Controller input begins
; at $7E5F8E and is not diagnostic scratch.
SAME_SCUMM_STREAM_ERROR_REQUEST_ID      = $7E5F13 ; u16 failing ProgramUnit ID
SAME_SCUMM_STREAM_ERROR_REQUEST_PC      = $7E5F15 ; u16 requested logical PC
SAME_SCUMM_STREAM_ERROR_SITE            = $7E5F17 ; u8 first generic resource-error site
SAME_SCUMM_STREAM_ERROR_CAPTURE_VALID   = $7E5F18 ; u8, feature-gated diagnostic only
SAME_SCUMM_STREAM_ZERO_SELECT           = $7E5F19 ; u8 invalid selector witness
SAME_SCUMM_STREAM_ZERO_CURRENT_SLOT     = $7E5F1A ; u8 C4 current slot
SAME_SCUMM_STREAM_ZERO_SLOT_PROGRAM     = $7E5F1B ; u8 owner slot selector
SAME_SCUMM_STREAM_ZERO_SLOT_STATUS      = $7E5F1C ; u8 owner slot status
SAME_SCUMM_STREAM_ZERO_SCHED_SLOT       = $7E5F1D ; u8 scheduler slot
SAME_SCUMM_STREAM_ZERO_LAST_ALLOCATED   = $7E5F1E ; u8 latest allocator result
SAME_SCUMM_STREAM_ZERO_SCAN_SLOT        = $7E5F1F ; u8 allocation/scheduler scratch
; Site-0x14 shares the selector-zero witness bytes as a typed error union.
SAME_SCUMM_STREAM_LENGTH_SUBSITE         = $7E5F19 ; u8 1..6 length check stage
SAME_SCUMM_STREAM_LENGTH_PAGE_START     = $7E5F1A ; u16 page logical start
SAME_SCUMM_STREAM_LENGTH_PAGE_SIZE      = $7E5F1C ; u16 page bytes
SAME_SCUMM_STREAM_LENGTH_BODY_SIZE      = $7E5F1E ; u16 canonical body bytes
; The render scratch occupies the documented diagnostic gap $7E5E10-$7E5E21,
; after the opcode trace ($7E5A02-$7E5E01) and before the persistent
; scenario breadcrumbs ($7E5F00+).
; It must not overlap the controller mailbox ($7E5FE0), object-count word
; ($7E5FF0), setState diagnostics ($7E5FF2-$7E5FFE), or scenario evidence.
SAME_SCUMM_CONTROLLER_RENDER_X           = $7E5E10 ; s16 last actor x
SAME_SCUMM_CONTROLLER_RENDER_Y           = $7E5E12 ; s16 last actor y
SAME_SCUMM_CONTROLLER_RENDER_FRAME       = $7E5E14 ; u8 last cooked frame
SAME_SCUMM_CONTROLLER_RENDER_ROOM        = $7E5E15 ; u8 last rendered room
SAME_SCUMM_CONTROLLER_RENDER_VALID       = $7E5E16 ; u8 cached composition valid
SAME_SCUMM_CONTROLLER_RENDER_SRC         = $7E5E18 ; u16 sprite source cursor
SAME_SCUMM_CONTROLLER_RENDER_DST         = $7E5E1A ; u16 surface destination cursor
SAME_SCUMM_CONTROLLER_RENDER_ROW         = $7E5E1C ; u16 current row
SAME_SCUMM_CONTROLLER_RENDER_COL         = $7E5E1E ; u16 current column
SAME_SCUMM_CONTROLLER_RENDER_BASE        = $7E5E20 ; u16 surface anchor offset
SAME_SCUMM_CONTROLLER_RENDER_ROWSRC      = $7E5E22 ; u16 immutable row source
SAME_SCUMM_CONTROLLER_RENDER_ACTOR_BASE  = $7E5E38 ; u16 captured actor anchor
SAME_SCUMM_CONTROLLER_RENDER_ACTOR_FRAME = $7E5E3A ; u16 captured pose base
SAME_SCUMM_CONTROLLER_RENDER_ACTOR_SELECT = $7E5E3C ; u8 0=standing,1=walking
SAME_SCUMM_CONTROLLER_RENDER_MOVING_SAMPLE = $7E5E3D ; u8 sampled movement
SAME_SCUMM_CONTROLLER_RENDER_MODE_SAMPLE = $7E5E3E ; u8 sampled controller mode
SAME_SCUMM_CONTROLLER_RENDER_DEST_SAMPLE = $7E5E40 ; s16 sampled walk target
; Semantic snapshot published after SCUMM movement and consumed by the late
; surface phase. The room guard keeps this fixture state inert elsewhere.
SAME_SCUMM_CONTROLLER_DESIRED_X         = $7E5E42 ; s16
SAME_SCUMM_CONTROLLER_DESIRED_Y         = $7E5E44 ; s16
SAME_SCUMM_CONTROLLER_DESIRED_SELECT    = $7E5E46 ; u8 0=standing,1=walking
SAME_SCUMM_CONTROLLER_DESIRED_DEST      = $7E5E48 ; s16
SAME_SCUMM_CONTROLLER_DESIRED_FACING    = $7E5E4A ; u16 internal actor angle
SAME_SCUMM_CONTROLLER_DESIRED_COSTUME   = $7E5E4C ; u8
SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE   = $7E5E4D ; u8
SAME_SCUMM_CONTROLLER_RENDER_FACING     = $7E5E4E ; u16 accepted angle
SAME_SCUMM_CONTROLLER_RENDER_COSTUME    = $7E5E50 ; u8 accepted costume
SAME_SCUMM_CONTROLLER_RENDER_VISIBLE    = $7E5E51 ; u8 accepted visibility
; Successful actor-publication witness.  Written only after the actor's
; complete indexed composition has accepted its PRESENT packet.  It is
; fixture/debug evidence, not semantic state and is never written on retry.
SAME_SCUMM_CONTROLLER_WITNESS_SERIAL    = $7E5E52 ; u16
SAME_SCUMM_CONTROLLER_WITNESS_FRAME     = $7E5E54 ; u16 logical frame
SAME_SCUMM_CONTROLLER_WITNESS_X         = $7E5E56 ; s16
SAME_SCUMM_CONTROLLER_WITNESS_Y         = $7E5E58 ; s16
SAME_SCUMM_CONTROLLER_WITNESS_MOVING    = $7E5E5A ; u8
SAME_SCUMM_CONTROLLER_WITNESS_DEST_X    = $7E5E5B ; s16
SAME_SCUMM_CONTROLLER_WITNESS_DEST_Y    = $7E5E5D ; s16
SAME_SCUMM_CONTROLLER_WITNESS_POSE      = $7E5E5F ; u8 cooked pose
SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_X  = $7E5E60 ; u16
SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_Y  = $7E5E62 ; u16
SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_W  = $7E5E64 ; u16
SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_H  = $7E5E66 ; u16
SAME_SCUMM_CONTROLLER_WITNESS_PRESENT   = $7E5E68 ; u16 generation
SAME_SCUMM_CONTROLLER_WITNESS_VALID     = $7E5E6A ; u8
SAME_SCUMM_CONTROLLER_RESTORE_INPUT_X   = $7E5E6C ; debug-only u16 raw restore x
SAME_SCUMM_CONTROLLER_RESTORE_INPUT_Y   = $7E5E6E ; debug-only u16 raw restore y
SAME_SCUMM_CONTROLLER_RESTORE_INPUT_W   = $7E5E70 ; debug-only u16 raw restore width
SAME_SCUMM_CONTROLLER_RESTORE_INPUT_H   = $7E5E72 ; debug-only u16 raw restore height
SAME_SCUMM_CONTROLLER_RESTORE_CALLS     = $7E5E74 ; debug-only u16 restore entries
SAME_SCUMM_CONTROLLER_RESTORE_AFTER_A   = $7E5E76 ; debug-only u16 after CanWrite A
SAME_SCUMM_CONTROLLER_RESTORE_AFTER_X   = $7E5E78 ; debug-only u16 after CanWrite X
SAME_SCUMM_CONTROLLER_RESTORE_CALL_A    = $7E5E7A ; debug-only u16 caller A
SAME_SCUMM_CONTROLLER_RESTORE_CALL_X    = $7E5E7C ; debug-only u16 caller X
SAME_SCUMM_CONTROLLER_RESTORE_LOOP_ROW  = $7E5E7E ; debug-only u16 row
SAME_SCUMM_CONTROLLER_RESTORE_LOOP_COL  = $7E5E80 ; debug-only u16 column
SAME_SCUMM_CONTROLLER_RESTORE_LOOP_W    = $7E5E82 ; debug-only u16 width
SAME_SCUMM_CONTROLLER_RESTORE_LOOP_H    = $7E5E84 ; debug-only u16 height
SAME_SCUMM_CONTROLLER_RESTORE_LOOP_DST  = $7E5E86 ; debug-only u16 destination
SAME_SCUMM_CONTROLLER_RESTORE_LOOP_SRC  = $7E5E88 ; debug-only u16 source
SAME_SCUMM_CONTROLLER_RENDER_RETRY       = $7E5E24 ; u8 bounded native-present retry
SAME_SCUMM_CONTROLLER_CURSOR_RENDER_X    = $7E5E26 ; s16 cached logical x
SAME_SCUMM_CONTROLLER_CURSOR_RENDER_Y    = $7E5E28 ; s16 cached logical y
SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID = $7E5E2A ; u8 cached cursor pose
SAME_SCUMM_CONTROLLER_CURSOR_RENDER_RETRY = $7E5E2B ; u8 bounded native-present retry
SAME_SCUMM_CONTROLLER_RENDER_SUPPRESS_PRESENT = $7E5E2C ; u8 cursor composite guard
; Set only by the established room-installed callback after the controller
; lifetime reset has run. This is a generic interaction-service readiness
; latch, not a room-number or fixture-object selector.
SAME_SCUMM_CONTROLLER_ROOM_READY       = $7E5E8A ; u8 installed-room latch
SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0    = $7E5E2E ; u16 union left
SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0    = $7E5E30 ; u16 union top
SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1    = $7E5E32 ; u16 union right
SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1    = $7E5E34 ; u16 union bottom
SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_ACTIVE = $7E5E36 ; u8 bounded restore
; Scenario-fixture witness for bytecode executed during outgoing room phase 1.
; Eight circular records: program, source PC, opcode. The video diagnostic
; block ends at $7E5EC7, leaving this interval available.
SAME_SCUMM_SCENARIO_PHASE1_TRACE_COUNT    = $7E5EC7 ; u8 circular write count
SAME_SCUMM_SCENARIO_PHASE1_TRACE         = $7E5EC8 ; 8 x 4-byte records
SAME_SCUMM_CONTROLLER_STATE_END           = $7E5FEC
SAME_SCUMM_CONTROLLER_DIAG                = $7E5FEC ; fixture-only gate breadcrumb
SAME_SCUMM_CONTROLLER_DIAG_ROOM           = $7E5FED
SAME_SCUMM_CONTROLLER_DIAG_PHASE          = $7E5FEE
SAME_SCUMM_CONTROLLER_DIAG_INPUT          = $7E5FEF
; setOwner scratch used to overlap the hardware stack window. The explicit
; MSU program-cache layout requires it to live in this audited gap.
SAME_SCUMM_OWNER_INDEX                     = $7E2B28 ; u16 setOwner scratch
SAME_SCUMM_OWNER_INDEX_END                 = $7E2B2A
SAME_SCUMM_SETSTATE_OBJECT                = $7E5FF2 ; u16 operand/trace
SAME_SCUMM_SETSTATE_VALUE                 = $7E5FF4 ; u8 operand/trace
SAME_SCUMM_SETSTATE_LOCAL_FOUND           = $7E5FF5 ; u8
SAME_SCUMM_SETSTATE_BG_REDRAW             = $7E5FF6 ; u8
SAME_SCUMM_SETSTATE_EXEC_COUNT            = $7E5FF7 ; u8
SAME_SCUMM_SETSTATE_PC_BEFORE             = $7E5FF8 ; u16
SAME_SCUMM_SETSTATE_PC_AFTER              = $7E5FFA ; u16
SAME_SCUMM_SETSTATE_LOCAL_COUNT           = $7E5FFC ; u8
SAME_SCUMM_SETSTATE_DIRTY_COUNT           = $7E5FFD ; u8
SAME_SCUMM_SETSTATE_LOCAL_OFFSET          = $7E5FFE ; u16 scratch

; Dedicated reset/control-flow diagnostics.  A low-WRAM diagnostic address
; can overlap profile-owned global-variable storage in larger profiles.  This
; 96-byte validator-only block occupies the audited gap after M23A return
; metadata and before the optional $7FF500 variable table; its end remains
; below that table in both low- and high-WRAM profiles.
SAME_RESET_DIAG_BASE                      = $7FF46B
SAME_RESET_DIAG_SIZE                      = $0068
SAME_RESET_DIAG_END                       = SAME_RESET_DIAG_BASE+SAME_RESET_DIAG_SIZE
SAME_RESET_DIAG_COUNT                     = SAME_RESET_DIAG_BASE ; u16 reset-entry count
SAME_RESET_DIAG_FRAME                     = SAME_RESET_DIAG_BASE+$02 ; u16 last frame
SAME_RESET_DIAG_STAGE                     = SAME_RESET_DIAG_BASE+$04 ; u8 last stage breadcrumb
SAME_RESET_DIAG_LAST_PBR                  = SAME_RESET_DIAG_BASE+$05 ; u8 production PBR hint
SAME_RESET_DIAG_LAST_PC                   = SAME_RESET_DIAG_BASE+$06 ; u16 production PC hint
SAME_RESET_DIAG_LAST_S                    = SAME_RESET_DIAG_BASE+$08 ; u16 S at reset entry
SAME_RESET_DIAG_LAST_P                    = SAME_RESET_DIAG_BASE+$0A ; u8 P at reset entry
SAME_RESET_DIAG_LAST_DBR                  = SAME_RESET_DIAG_BASE+$0B ; u8 DBR at reset entry
SAME_RESET_DIAG_LAST_D                    = SAME_RESET_DIAG_BASE+$0C ; u16 D at reset entry
SAME_RESET_DIAG_NMI                       = SAME_RESET_DIAG_BASE+$0E ; u16 NMI entries
SAME_RESET_DIAG_IRQ                       = SAME_RESET_DIAG_BASE+$10 ; u16 IRQ entries
SAME_RESET_DIAG_BRK                       = SAME_RESET_DIAG_BASE+$12 ; u16 BRK entries
SAME_RESET_DIAG_COP                       = SAME_RESET_DIAG_BASE+$14 ; u16 COP entries
SAME_RESET_DIAG_ROOM                      = SAME_RESET_DIAG_BASE+$16 ; u8 room breadcrumb
SAME_RESET_DIAG_PROGRAM                   = SAME_RESET_DIAG_BASE+$17 ; u8 program breadcrumb
SAME_RESET_DIAG_SLOT                      = SAME_RESET_DIAG_BASE+$18 ; u8 slot breadcrumb
SAME_RESET_DIAG_SCRIPT_PC                 = SAME_RESET_DIAG_BASE+$19 ; u16 script PC breadcrumb
SAME_RESET_DIAG_LIFECYCLE                 = SAME_RESET_DIAG_BASE+$1B ; u8 room lifecycle
SAME_RESET_DIAG_ENGINE_PHASE              = SAME_RESET_DIAG_BASE+$1C ; u8 frame phase
SAME_RESET_DIAG_COOKIE                    = SAME_RESET_DIAG_BASE+$1D ; u16 reserved signature
SAME_RESET_DIAG_LAST_A                    = SAME_RESET_DIAG_BASE+$20 ; u16 captured at BRK entry
SAME_RESET_DIAG_LAST_X                    = SAME_RESET_DIAG_BASE+$22 ; u16 captured at BRK entry
SAME_RESET_DIAG_LAST_Y                    = SAME_RESET_DIAG_BASE+$24 ; u16 captured at BRK entry
SAME_RESET_DIAG_STACK                     = SAME_RESET_DIAG_BASE+$26 ; 24 bytes from native S+1
SAME_RESET_DIAG_STACK_SIZE                = $0018
SAME_RESET_DIAG_STACK_SOURCE              = SAME_RESET_DIAG_BASE+$3E ; u16 source offset in bank 0
SAME_RESET_DIAG_SP_ENTRY                  = SAME_RESET_DIAG_BASE+$40 ; u16 per-frame entry S
SAME_RESET_DIAG_SP_CURRENT                = SAME_RESET_DIAG_BASE+$42 ; u16 sampled S
SAME_RESET_DIAG_SP_STAGE                  = SAME_RESET_DIAG_BASE+$44 ; u16 zero=baseline, else checkpoint
SAME_RESET_DIAG_SP_FAILURES               = SAME_RESET_DIAG_BASE+$46 ; u16 imbalance count
SAME_RESET_DIAG_INPUT_SP_ENTRY            = SAME_RESET_DIAG_BASE+$48 ; u16 Same_Input_Poll entry S
SAME_RESET_DIAG_INPUT_SP_CURRENT          = SAME_RESET_DIAG_BASE+$4A ; u16 sampled input S
SAME_RESET_DIAG_INPUT_SP_STAGE            = SAME_RESET_DIAG_BASE+$4C ; u16 zero=baseline, else checkpoint
SAME_RESET_DIAG_INPUT_SP_FAILURES         = SAME_RESET_DIAG_BASE+$4E ; u16 input imbalance count
SAME_RESET_DIAG_FRAME_PRE_INPUT_S         = SAME_RESET_DIAG_BASE+$50 ; u16 caller S before input poll
SAME_RESET_DIAG_FRAME_POST_INPUT_S        = SAME_RESET_DIAG_BASE+$52 ; u16 caller S after input poll
SAME_RESET_DIAG_FRAME_POST_INPUT_CHECK_S  = SAME_RESET_DIAG_BASE+$54 ; u16 caller S before stack checker
SAME_RESET_DIAG_FRAME_RETURN_SP           = SAME_RESET_DIAG_BASE+$56 ; u16 S before engine PLP/RTS
SAME_RESET_DIAG_FRAME_RETURN_BYTES        = SAME_RESET_DIAG_BASE+$58 ; u6 status + return frame bytes
SAME_RESET_DIAG_SP_BEFORE_ACTIVE          = SAME_RESET_DIAG_BASE+$60 ; u16 S before host JSR active engine
SAME_RESET_DIAG_SP_AFTER_ACTIVE           = SAME_RESET_DIAG_BASE+$62 ; u16 S after active engine returns
SAME_RESET_DIAG_SP_BEFORE_SCUMM            = SAME_RESET_DIAG_BASE+$64 ; u16 S before active JSR SCUMM frame
SAME_RESET_DIAG_SP_AFTER_SCUMM             = SAME_RESET_DIAG_BASE+$66 ; u16 S after SCUMM frame returns
SAME_SCUMM_OBJECT_STATES                  = $7E6000 ; 4096 u8 global states
SAME_SCUMM_OBJECT_OWNERS                  = $7E8000 ; 2048 u8 mutable owner table
; Runtime names established by canonical $54/$D4 setObjectName.  A compact
; fixed record is sufficient for the target-neutral controller HUD while
; retaining the authored encoded bytes (including controls) until display.
; The controller name-length cache is 1024 entries (the payload cache itself
; is capped at SAME_SCUMM_OBJECT_NAME_COUNT). Keep it live in all runtime
; personalities: room object parsing writes these entries even when the
; controller presentation layer is absent.
SAME_SCUMM_OBJECT_NAME_LENGTH             = $7E8800 ; 1024 u8 bounded lengths
.if SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY
; Explicit ownership boundary: the always-live name-length cache ends at
; $7E8C00; resolver state owns $7E8C00-$7E8FBF; $7E8FC0-$7E8FFF is reserved
; padding; encoded names begin at $7E9000. Controller/input, C4, C19, room
; lifecycle, and save-validation ranges are independently declared and checked
; by tools/audit_scumm_residency_wram.py.
SAME_SCUMM_RESIDENT_WRAM_BASE              = $7E8C00
SAME_SCUMM_RESIDENT_UNIT_IDS              = $7E8C00 ; 178 x u16 canonical IDs
SAME_SCUMM_RESIDENT_GENERATIONS           = $7E8D64 ; 178 x u16 binding generations
SAME_SCUMM_RESIDENT_FLAGS                 = $7E8EC8 ; 178 x u8 VALID/BUNDLE/MANUAL pins
SAME_SCUMM_RESIDENT_REQUEST_ID            = $7E8F7A ; u16 resolver input
SAME_SCUMM_RESIDENT_SELECTOR              = $7E8F7C ; u8 result/candidate
SAME_SCUMM_RESIDENT_POOL_INDEX            = $7E8F7D ; u16 pool index
SAME_SCUMM_RESIDENT_CURRENT_COUNT         = $7E8F7F ; u16 diagnostics
SAME_SCUMM_RESIDENT_PEAK_COUNT            = $7E8F81 ; u16 diagnostics
SAME_SCUMM_RESIDENT_PINNED_COUNT          = $7E8F83 ; u16 diagnostics
SAME_SCUMM_RESIDENT_PEAK_PINNED           = $7E8F85 ; u16 diagnostics
SAME_SCUMM_RESIDENT_BIND_COUNT            = $7E8F87 ; u16 diagnostics
SAME_SCUMM_RESIDENT_REUSE_COUNT            = $7E8F89 ; u16 diagnostics
SAME_SCUMM_RESIDENT_BUNDLE_LOADS           = $7E8F8B ; u16 diagnostics
SAME_SCUMM_RESIDENT_BUNDLE_RELEASES        = $7E8F8D ; u16 diagnostics
SAME_SCUMM_RESIDENT_DYNAMIC_LOOKUPS        = $7E8F8F ; u16 diagnostics
SAME_SCUMM_RESIDENT_EXHAUSTIONS             = $7E8F91 ; u16 diagnostics
SAME_SCUMM_RESIDENT_SCAN_SLOT               = $7E8F93 ; u8 C4 scan cursor
SAME_SCUMM_RESIDENT_SCAN_STATUS             = $7E8F94 ; u8 scratch
SAME_SCUMM_RESIDENT_FLAGS_SCRATCH           = $7E8F95 ; u8 scratch
SAME_SCUMM_RESIDENT_COUNT_SCRATCH           = $7E8F96 ; u16 scratch
SAME_SCUMM_RESIDENT_EXPECTED_ID              = $7E8F98 ; u16 stale-reference check
SAME_SCUMM_RESIDENT_EXPECTED_GENERATION      = $7E8F9A ; u16 stale-reference check
SAME_SCUMM_RESIDENT_STALE_COUNT               = $7E8F9C ; u16 stale-generation diagnostics
SAME_SCUMM_RESIDENT_BUNDLE_RECORD            = $7E8F9E ; u8 active room-bundle index
SAME_SCUMM_RESIDENT_BUNDLE_REMAINING          = $7E8F9F ; u8 load/release loop
SAME_SCUMM_RESIDENT_BUNDLE_OFFSET             = $7E8FA0 ; u16 bundle directory index
SAME_SCUMM_RESIDENT_LOCAL_SCRIPT              = $7E8FA2 ; u8 local lookup input
SAME_SCUMM_RESIDENT_LOCAL_REMAINING           = $7E8FA3 ; u8 local lookup loop
SAME_SCUMM_RESIDENT_LOCAL_OFFSET              = $7E8FA4 ; u16 local directory index
SAME_SCUMM_RESIDENT_PINNED_SCRATCH            = $7E8FA6 ; u16 diagnostic accumulator
SAME_SCUMM_RESIDENT_GLOBAL_SCRIPT             = $7E8FA8 ; u8 dynamic global number
SAME_SCUMM_RESIDENT_LOOKUP_INDEX              = $7E8FA9 ; u16 table cursor
SAME_SCUMM_RESIDENT_BUNDLE_FAILURE            = $7E8FAB ; u8 last binding/bundle error site
SAME_SCUMM_RESIDENT_SELECTOR_CALLER            = $7E8FAC ; u8 diagnostic: selector lookup caller
SAME_SCUMM_RESIDENT_ERROR_CALLER_PC            = $7E8FAD ; u16 JSL return PC at selector rejection
SAME_SCUMM_RESIDENT_ERROR_CALLER_BANK          = $7E8FAF ; u8 JSL return bank at selector rejection
SAME_SCUMM_RESIDENT_DIAG_STATUS                = $7E8FB0 ; u8 diagnostic pass/fail code
SAME_SCUMM_RESIDENT_DIAG_EXHAUSTION_ERROR       = $7E8FB1 ; u8 expected $20
SAME_SCUMM_RESIDENT_DIAG_STALE_REJECTED         = $7E8FB2 ; u8 boolean
SAME_SCUMM_RESIDENT_DIAG_REBOUND_SELECTOR       = $7E8FB3 ; u8
SAME_SCUMM_RESIDENT_DIAG_REBOUND_GENERATION     = $7E8FB4 ; u16
SAME_SCUMM_RESIDENT_DIAG_TABLE_UNCHANGED        = $7E8FB6 ; u8 boolean
SAME_SCUMM_RESIDENT_DIAG_INDEX                 = $7E8FB8 ; u16 loop scratch
SAME_SCUMM_RESIDENT_DIAG_POOL_INDEX            = $7E8FBA ; u16 loop scratch
SAME_SCUMM_RESIDENT_DIAG_SCRATCH               = $7E8FBC ; u16 scratch
SAME_SCUMM_RESIDENT_DIAG_RETURNED              = $7E8FBE ; u8 caller-return sentinel
SAME_SCUMM_RESIDENT_DIAG_STAGE                 = $7E8FBF ; u8 bounded-control progress
SAME_SCUMM_RESIDENT_WRAM_END                   = $7E8FC0 ; exclusive resolver end
.endif
; The target-neutral name cache is bounded to the contiguous gap before C10.
; $7E9000 + 1024*$20 = $7F1000, leaving C10/C17 and all later state intact.
; Authored $54 names outside this cache are still decoded/consumed, but are
; not exposed to the bounded controller HUD.
SAME_SCUMM_OBJECT_NAMES                   = $7E9000 ; 1024 x 32 encoded bytes
SAME_SCUMM_OBJECT_NAME_STRIDE             = $0020
SAME_SCUMM_OBJECT_NAME_COUNT              = $0400
SAME_SCUMM_OBJECT_NAMES_END               = $7F1000
SAME_SCUMM_SETSTATE_LOCAL_RECORDS         = $7E7000 ; 200 x 11 bytes
SAME_SCUMM_SETSTATE_LOCAL_STRIDE          = $000B
SAME_SCUMM_SETSTATE_LOCAL_MAX             = $00C8
SAME_SCUMM_SETSTATE_L_ID                  = $00 ; u16
SAME_SCUMM_SETSTATE_L_X                   = $02 ; s16
SAME_SCUMM_SETSTATE_L_Y                   = $04 ; s16
SAME_SCUMM_SETSTATE_L_WIDTH               = $06 ; u16
SAME_SCUMM_SETSTATE_L_HEIGHT              = $08 ; u16
SAME_SCUMM_SETSTATE_L_FLAGS               = $0A ; raw resource flags
SAME_SCUMM_SETSTATE_DIRTY_RECT             = $7E7898 ; last x/y/w/h invalidation
SAME_SCUMM_SETSTATE_DRAW_QUEUE_COUNT       = $7E78A0 ; bounded logical queue
SAME_SCUMM_SETSTATE_TRACE_COUNT            = $7E78A1
SAME_SCUMM_SETSTATE_TRACE                  = $7E78B0 ; 8 x 8-byte records
SAME_SCUMM_SETSTATE_TRACE_CAPACITY         = $0008

; Canonical internal actor angles are independent of rendered costume state.
; $63/$E3 observes this table without changing it or any actor record.
SAME_SCUMM_ACTOR_FACINGS                   = $7E78F0 ; 32 x u16 internal angle
SAME_SCUMM_GET_FACING_ACTOR                = $7E7930 ; u8 decoded actor
SAME_SCUMM_GET_FACING_VALUE                = $7E7932 ; u16 raw internal angle
SAME_SCUMM_GET_FACING_RESULT               = $7E7934 ; u8 old-style direction
SAME_SCUMM_GET_FACING_EXEC_COUNT           = $7E7935 ; successful queries
SAME_SCUMM_GET_FACING_PC_BEFORE            = $7E7936 ; u16
SAME_SCUMM_GET_FACING_PC_AFTER             = $7E7938 ; u16
SAME_SCUMM_GET_FACING_RESULT_OFFSET        = $7E793A ; canonical result target
SAME_SCUMM_GET_FACING_TRACE_COUNT          = $7E793C
SAME_SCUMM_GET_FACING_STAGE                = $7E793D ; persistent decode stage
SAME_SCUMM_GET_FACING_RESULT_BEFORE        = $7E793E ; u16 pre-query value
SAME_SCUMM_GET_FACING_TRACE                = $7E7940 ; 16 x 14-byte records
SAME_SCUMM_GET_FACING_TRACE_STRIDE         = $000E
SAME_SCUMM_GET_FACING_TRACE_CAPACITY       = $0010

; Canonical v5 headless slot-0 actor-talk lifecycle. The 32-byte encoded
; buffer is the smallest power-of-two bound covering Fate's 26-byte message;
; bytes (including $10 and the terminator) survive until completion.
SAME_SCUMM_TALK_STATE                      = $7E7A20
SAME_SCUMM_TALK_ACTIVE                     = $7E7A20 ; u8
SAME_SCUMM_TALK_HAVE_MSG                   = $7E7A21 ; canonical internal _haveMsg
SAME_SCUMM_TALK_ACTOR                      = $7E7A22 ; u8, $ff after stop
SAME_SCUMM_TALK_CHARINC                    = $7E7A23 ; u8 canonical VAR_CHARINC
SAME_SCUMM_TALK_DELAY                      = $7E7A24 ; u16 jiffies
SAME_SCUMM_TALK_GENERATION                 = $7E7A26 ; u16
SAME_SCUMM_TALK_RAW_LENGTH                 = $7E7A28 ; includes terminator
SAME_SCUMM_TALK_START_COUNT                = $7E7A29
SAME_SCUMM_TALK_STOP_COUNT                 = $7E7A2A
SAME_SCUMM_TALK_COMPLETE_COUNT             = $7E7A2B
SAME_SCUMM_TALK_STARTED_FRAME              = $7E7A2C ; u16
SAME_SCUMM_TALK_COMPLETED_FRAME            = $7E7A2E ; u16
SAME_SCUMM_TALK_RAW                        = $7E7A30 ; 32 encoded bytes
SAME_SCUMM_TALK_MAX_RAW                    = $0020
SAME_SCUMM_TALK_EVENT_COUNT                = $7E7A50
SAME_SCUMM_TALK_EVENTS                     = $7E7A51 ; 16 x 8-byte records
SAME_SCUMM_TALK_EVENT_STRIDE               = $0008
SAME_SCUMM_TALK_EVENT_CAPACITY             = $000E
SAME_SCUMM_TALK_WAIT_BLOCK_COUNT           = $7E7AD1
SAME_SCUMM_TALK_WAIT_RESUME_COUNT          = $7E7AD2
SAME_SCUMM_TALK_WAIT_PC                     = $7E7AD3 ; u16
SAME_SCUMM_TALK_PC_BEFORE                   = $7E7AD5 ; u16 print opcode PC
SAME_SCUMM_TALK_PC_AFTER                    = $7E7AD7 ; u16 first byte after text
; The final two formerly-unused event slots provide twelve bounded bytes for
; segmented-message state without extending or overlapping the following
; getActorWalkBox block.
SAME_SCUMM_TALK_CURSOR                      = $7E7AC1 ; next encoded byte
SAME_SCUMM_TALK_SEGMENT_START               = $7E7AC2
SAME_SCUMM_TALK_SEGMENT_LENGTH              = $7E7AC3 ; encoded printable bytes
SAME_SCUMM_TALK_SEGMENT_GLYPHS              = $7E7AC4
SAME_SCUMM_TALK_SEGMENT_INDEX               = $7E7AC5
SAME_SCUMM_TALK_KEEP_TEXT                   = $7E7AC6
SAME_SCUMM_TALK_VISUAL_STATUS               = $7E7AC7
SAME_SCUMM_TALK_OVERLAY_GENERATION          = $7E7AC8 ; u16
SAME_SCUMM_TALK_ACTOR_FRAME                 = $7E7ACA ; logical animation frame
SAME_SCUMM_TALK_CONTINUE_COUNT              = $7E7ACB
SAME_SCUMM_TALK_PUBLISH_CLEAR               = $7E7ACC
SAME_SCUMM_TALK_CONTROL_COUNT              = $7E7ACD
SAME_SCUMM_TALK_CONTROL_FIRST_POS         = $7E7ACE ; u16
SAME_SCUMM_TALK_CONTROL_LAST              = $7E7AD0 ; $80 means FF pending
SAME_SCUMM_TALK_STATE_END                   = $7E7AD1
SAME_SCUMM_TALK_STATE_SIZE                  = $00AD

; Canonical v5 $7B/$FB pure stored-walkbox query and bounded diagnostics.
SAME_SCUMM_GET_WALKBOX_STATE               = $7E7AD9
SAME_SCUMM_GET_WALKBOX_ACTOR               = $7E7AD9 ; u8 decoded actor
SAME_SCUMM_GET_WALKBOX_VALUE               = $7E7ADA ; u8 stored walkbox
SAME_SCUMM_GET_WALKBOX_EXEC_COUNT          = $7E7ADB
SAME_SCUMM_GET_WALKBOX_PC_BEFORE           = $7E7ADC ; u16
SAME_SCUMM_GET_WALKBOX_PC_AFTER            = $7E7ADE ; u16
SAME_SCUMM_GET_WALKBOX_RESULT_OFFSET       = $7E7AE0 ; canonical result target
SAME_SCUMM_GET_WALKBOX_RESULT_BEFORE       = $7E7AE2 ; u16
SAME_SCUMM_GET_WALKBOX_TRACE_COUNT         = $7E7AE4
SAME_SCUMM_GET_WALKBOX_TRACE               = $7E7AE5 ; 16 x 12-byte records
SAME_SCUMM_GET_WALKBOX_TRACE_STRIDE        = $000C
SAME_SCUMM_GET_WALKBOX_TRACE_CAPACITY      = $0010
SAME_SCUMM_GET_WALKBOX_NEXT_PROGRAM        = $7E7BA5 ; later unsupported opcode evidence
SAME_SCUMM_GET_WALKBOX_NEXT_OPCODE         = $7E7BA6
SAME_SCUMM_GET_WALKBOX_NEXT_PC             = $7E7BA7 ; opcode PC, u16
SAME_SCUMM_GET_WALKBOX_NEXT_SEEN           = $7E7BA9
SAME_SCUMM_GET_WALKBOX_STATE_END           = $7E7BAA
SAME_SCUMM_GET_WALKBOX_STATE_SIZE          = $00D1

; M25 canonical read-only sentence prelude and actor movement state.  Immutable
; OBCD VERB metadata, BOXD geometry, BOXM routes, and object walk points remain
; profile-owned ROM data.  These fields retain only active-room/generation-safe
; query scratch and per-actor canonical walking state.
SAME_SCUMM_MOVE_STATE                       = $7E7BAA
SAME_SCUMM_MOVE_DEST_Y                      = $7E7BAA ; 32 x s16
SAME_SCUMM_MOVE_CURRENT_BOX                 = $7E7BEA ; 32 x u8
SAME_SCUMM_MOVE_LEG_ORIGIN_X                = $7E7C0A ; 32 x s16
SAME_SCUMM_MOVE_LEG_ORIGIN_Y                = $7E7C4A ; 32 x s16
SAME_SCUMM_MOVE_LEG_TARGET_X                = $7E7C8A ; 32 x s16
SAME_SCUMM_MOVE_LEG_TARGET_Y                = $7E7CCA ; 32 x s16
SAME_SCUMM_MOVE_FRACTION_X                  = $7E7D0A ; 32 x u16
SAME_SCUMM_MOVE_FRACTION_Y                  = $7E7D4A ; 32 x u16
SAME_SCUMM_MOVE_DELTA_X_LO                  = $7E7D8A ; 32 x u16, 16.16
SAME_SCUMM_MOVE_DELTA_X_HI                  = $7E7DCA ; 32 x s16
SAME_SCUMM_MOVE_DELTA_Y_LO                  = $7E7E0A ; 32 x u16, 16.16
SAME_SCUMM_MOVE_DELTA_Y_HI                  = $7E7E4A ; 32 x s16
SAME_SCUMM_MOVE_FINAL_OLD_DIR               = $7E7E8A ; 32 x u8
SAME_SCUMM_MOVE_ROUTE_SOURCE                = $7E7EAA ; u8 query source
SAME_SCUMM_MOVE_ROUTE_DEST                  = $7E7EAB ; u16 query destination/index
SAME_SCUMM_MOVE_OBJECT                      = $7E7EAD ; u16
SAME_SCUMM_MOVE_REQUEST_X                   = $7E7EAF ; s16
SAME_SCUMM_MOVE_REQUEST_Y                   = $7E7EB1 ; s16
SAME_SCUMM_MOVE_RESULT_BOX                  = $7E7EB3 ; u8
SAME_SCUMM_MOVE_ACTOR                       = $7E7EB4 ; u8
SAME_SCUMM_MOVE_TEMP                        = $7E7EB5 ; u16
SAME_SCUMM_MOVE_TEMP2                       = $7E7EB7 ; u16
SAME_SCUMM_MOVE_TICK                        = $7E7EB9 ; u16
SAME_SCUMM_MOVE_WAIT_BLOCKS                 = $7E7EBB ; u16
SAME_SCUMM_MOVE_WAIT_RELEASES               = $7E7EBD ; u16
SAME_SCUMM_VERB_OBJECT                      = $7E7EBF ; u16
SAME_SCUMM_VERB_ID                          = $7E7EC1 ; u16
SAME_SCUMM_VERB_RESULT                      = $7E7EC3 ; u16
SAME_SCUMM_OWNER_RESULT                     = $7E7EC5 ; u16
SAME_SCUMM_SENTENCE_INJECTED                = $7E7FDB ; u8 validation profile boundary
; Production semantic sentence-input mailbox.  The SCUMM adapter consumes
; this request at the normal frame boundary and converts it into a C20 record.
SAME_SCUMM_SENTENCE_API_PENDING             = $7E7EC7
SAME_SCUMM_SENTENCE_API_VERB                = $7FD3A6
SAME_SCUMM_SENTENCE_API_OBJECT1             = $7FD3A8
SAME_SCUMM_SENTENCE_API_OBJECT2             = $7FD3AA
SAME_SCUMM_ROOM_REQUEST_API_PENDING         = $7E7F8E
SAME_SCUMM_ROOM_REQUEST_API_ROOM            = $7E7F8F
SAME_SCUMM_MOVE_GATE_X                      = $7E7EC8 ; s16
SAME_SCUMM_MOVE_GATE_Y                      = $7E7ECA ; s16
SAME_SCUMM_MOVE_ROUTE_NEXT                  = $7E7ECC ; u8
SAME_SCUMM_MOVE_PORTAL_TYPE                 = $7E7ECD ; 0 none,1 vertical,2 horizontal
SAME_SCUMM_MOVE_PORTAL_FIXED                = $7E7ECE ; s16
SAME_SCUMM_MOVE_PORTAL_LOW                  = $7E7ED0 ; s16
SAME_SCUMM_MOVE_PORTAL_HIGH                 = $7E7ED2 ; s16
SAME_SCUMM_MOVE_QUERY_DIR                   = $7E7ED4 ; u8 object lookup result
SAME_SCUMM_M25_PHASE_NORMALIZE_CALLS        = $7E7ED5 ; diagnostic, u8
SAME_SCUMM_M25_PHASE_NORMALIZE_COMMITS      = $7E7ED6 ; diagnostic, u8
SAME_SCUMM_M25_START_TRACE_COUNT            = $7E7ED7 ; diagnostic, u8
SAME_SCUMM_M25_START_TRACE                  = $7E7ED8 ; 16 x 4-byte records
SAME_SCUMM_M25_MOVE_START_COUNT             = $7E7F18 ; diagnostic, u8
SAME_SCUMM_M25_MOVE_START_PC                = $7E7F1A ; diagnostic, u16
SAME_SCUMM_M25_MOVE_START_PROGRAM           = $7E7F1C ; diagnostic, u8
SAME_SCUMM_M25_MOVE_START_ACTOR             = $7E7F1D ; diagnostic, u8
SAME_SCUMM_M25_MOVE_STEP_COUNT              = $7E7F1E ; diagnostic, u8
SAME_SCUMM_M25_MOVE_STEP_PRE_X              = $7E7F1F ; diagnostic, s16 (overlaps query scratch only after probe)
SAME_SCUMM_MOVE_POSITION_AXIS               = $7E7F20 ; 0=x, 2=y query scratch
SAME_SCUMM_MOVE_POSITION_OFFSET             = $7E7F21 ; u16 actor * 4 position offset
; Canonical v5 $34/$74/$B4/$F4 getDist query scratch and evidence.  This is
; transient diagnostic/query state, not actor or object state.
SAME_SCUMM_GET_DIST_STATE                   = $7E7F23
SAME_SCUMM_GET_DIST_PC_BEFORE               = $7E7F23 ; u16
SAME_SCUMM_GET_DIST_PC_AFTER                = $7E7F25 ; u16
SAME_SCUMM_GET_DIST_RESULT_OFFSET           = $7E7F27 ; u16
SAME_SCUMM_GET_DIST_RESULT_BEFORE           = $7E7F29 ; u16
SAME_SCUMM_GET_DIST_OPERAND1                = $7E7F2B ; u16
SAME_SCUMM_GET_DIST_OPERAND2                = $7E7F2D ; u16
SAME_SCUMM_GET_DIST_TYPE1                   = $7E7F2F ; 1 actor, 2 object
SAME_SCUMM_GET_DIST_TYPE2                   = $7E7F30 ; 1 actor, 2 object
SAME_SCUMM_GET_DIST_X1                      = $7E7F31 ; s16
SAME_SCUMM_GET_DIST_Y1                      = $7E7F33 ; s16
SAME_SCUMM_GET_DIST_X2_RAW                  = $7E7F35 ; s16
SAME_SCUMM_GET_DIST_Y2_RAW                  = $7E7F37 ; s16
SAME_SCUMM_GET_DIST_X2                      = $7E7F39 ; s16 after asymmetric projection
SAME_SCUMM_GET_DIST_Y2                      = $7E7F3B ; s16 after asymmetric projection
SAME_SCUMM_GET_DIST_DX                      = $7E7F3D ; u16
SAME_SCUMM_GET_DIST_DY                      = $7E7F3F ; u16
SAME_SCUMM_GET_DIST_RESULT                  = $7E7F41 ; u16
SAME_SCUMM_GET_DIST_ADJUSTED                = $7E7F43 ; u8
SAME_SCUMM_GET_DIST_EXEC_COUNT              = $7E7F44 ; u8
SAME_SCUMM_GET_DIST_STAGE                   = $7E7F45 ; bounded decode/query diagnostic
SAME_SCUMM_GET_DIST_STATE_END               = $7E7F46
SAME_SCUMM_GET_DIST_STATE_SIZE              = $0023
SAME_SCUMM_MOVE_STATE_END                   = $7E7FA2
SAME_SCUMM_MOVE_STATE_SIZE                  = $03F8

; Canonical room-object script ownership and bounded startObject evidence.
; Object identity is 16-bit and therefore cannot alias the historical u8
; global/local script-number table. WHERE follows the v5 WIO values.
SAME_SCUMM_C4_SLOT_WHERE                    = $7E7F46 ; 25 u8 WIO values
SAME_SCUMM_C4_SLOT_OBJECT_NUMBER            = $7E7F5F ; 25 u16 object IDs
SAME_SCUMM_START_OBJECT_OBJECT              = $7E7F91 ; u16
SAME_SCUMM_START_OBJECT_ENTRY               = $7E7F93 ; u8
SAME_SCUMM_START_OBJECT_PROGRAM             = $7E7F94 ; u8
SAME_SCUMM_START_OBJECT_ENTRY_OFFSET        = $7E7F95 ; u16
SAME_SCUMM_START_OBJECT_PC_BEFORE           = $7E7F97 ; u16
SAME_SCUMM_START_OBJECT_PC_AFTER_ARGS       = $7E7F99 ; u16
SAME_SCUMM_START_OBJECT_SLOT                = $7E7F9B ; u8
SAME_SCUMM_START_OBJECT_ARG_COUNT           = $7E7F9C ; u8
SAME_SCUMM_START_OBJECT_EXEC_COUNT          = $7E7F9D ; u8
SAME_SCUMM_START_OBJECT_CHAIN_TARGET        = $7E7F9E ; u8
SAME_SCUMM_START_OBJECT_OBJECT_RETIRED      = $7E7F9F ; u8
SAME_SCUMM_START_OBJECT_LSCR_PROGRAM        = $7E7FA0 ; u8
SAME_SCUMM_START_OBJECT_LSCR_ENTRY_SEEN     = $7E7FA1 ; u8
SAME_SCUMM_START_OBJECT_ARG0                = $7E7FA2 ; u16 evidence
SAME_SCUMM_START_OBJECT_ARG1                = $7E7FA4 ; u16 evidence
SAME_SCUMM_START_OBJECT_SELECTOR            = $7E7FA6 ; u8 decode scratch
; Reused only after the encoded selector/arguments have been fully decoded.
; This operation-local decision must survive target resolution and slot
; allocation, both of which may change the shared VM status byte.
SAME_SCUMM_START_OBJECT_CALLER_REPLACED      = SAME_SCUMM_START_OBJECT_SELECTOR
SAME_SCUMM_START_OBJECT_REPLACED_SLOT       = $7E7FA7 ; M25A self-replacement evidence
SAME_SCUMM_START_OBJECT_STATE_END           = $7E7FA8

; Canonical v5 camera state and Phase-6F immediate/published evidence.  The
; camera is engine state; the target video facade consumes only the published
; virtual-screen origin and remains unaware of SCUMM scripts or strips.
SAME_SCUMM_CAMERA_STATE                     = $7E7FA8
SAME_SCUMM_CAMERA_CURRENT_X                 = $7E7FA8 ; s16
SAME_SCUMM_CAMERA_CURRENT_Y                 = $7E7FAA ; s16
SAME_SCUMM_CAMERA_DEST_X                    = $7E7FAC ; s16
SAME_SCUMM_CAMERA_DEST_Y                    = $7E7FAE ; s16
SAME_SCUMM_CAMERA_LAST_X                    = $7E7FB0 ; s16
SAME_SCUMM_CAMERA_LAST_Y                    = $7E7FB2 ; s16
SAME_SCUMM_CAMERA_SCREEN_START_STRIP        = $7E7FB4 ; s16
SAME_SCUMM_CAMERA_SCREEN_END_STRIP          = $7E7FB6 ; s16
SAME_SCUMM_CAMERA_VSCREEN_XSTART            = $7E7FB8 ; s16 pixels
SAME_SCUMM_CAMERA_REQUEST_X                 = $7E7FBA ; s16 diagnostic
SAME_SCUMM_CAMERA_PC_BEFORE                 = $7E7FBC ; u16
SAME_SCUMM_CAMERA_PC_AFTER                  = $7E7FBE ; u16
SAME_SCUMM_CAMERA_IMMEDIATE_COUNT           = $7E7FC0 ; u16
SAME_SCUMM_CAMERA_PUBLISH_COUNT             = $7E7FC2 ; u16
SAME_SCUMM_CAMERA_SCROLL_SCRIPT_COUNT       = $7E7FC4 ; u16
SAME_SCUMM_CAMERA_UPDATE_PENDING            = $7E7FC6 ; u8
SAME_SCUMM_CAMERA_SCROLL_SCRIPT             = $7E7FC7 ; u8 callback identity retained across nested setup
SAME_SCUMM_CAMERA_FRAME_PHASE_COUNT         = $7E7FC8 ; u16 outer-frame camera phase calls
SAME_SCUMM_CAMERA_STATE_END                 = $7E7FCA
SAME_SCUMM_CAMERA_STATE_SIZE                = $0022
SAME_SCUMM_FRAME_ENTRY_STACK                = $7E7FCA ; u16 terminal semantic unwind boundary

; Canonical loadRoomWithEgo transition operands.  The room lifecycle may
; retire the decoding slot before storage completes, so the fully decoded
; request lives in engine-owned state rather than in script locals/scratch.
SAME_SCUMM_LOAD_EGO_STATE                   = $7E7FCC
SAME_SCUMM_LOAD_EGO_ACTIVE                  = $7E7FCC ; u8 pending/postamble owner
SAME_SCUMM_LOAD_EGO_OBJECT                  = $7E7FCD ; u16 entry object
SAME_SCUMM_LOAD_EGO_ROOM                    = $7E7FCF ; u8 target room
SAME_SCUMM_LOAD_EGO_X                       = $7E7FD0 ; s16 optional post-entry walk
SAME_SCUMM_LOAD_EGO_Y                       = $7E7FD2 ; s16
SAME_SCUMM_LOAD_EGO_PC_AFTER                = $7E7FD4 ; decoded boundary evidence
SAME_SCUMM_LOAD_EGO_CALLER_SLOT             = $7E7FD6 ; u8 diagnostic
SAME_SCUMM_LOAD_EGO_CALLER_PROGRAM          = $7E7FD7 ; u8 diagnostic
SAME_SCUMM_LOAD_EGO_PREVIOUS_ROOM           = $7E7FD8 ; u8
SAME_SCUMM_LOAD_EGO_EGO                     = $7E7FD9 ; u8 resolved actor
SAME_SCUMM_LOAD_EGO_STATE_END               = $7E7FDA
; Long StartObject replacement ABI observations. The range is the measured
; gap between LoadEgo diagnostics and the object-owner table at $7E8000.
SAME_SCUMM_START_OBJECT_CALLER_SP            = $7E7FDA ; u16 before replacement JSL
SAME_SCUMM_START_OBJECT_ADAPTER_SP            = $7E7FDC ; u16 far-adapter entry
SAME_SCUMM_START_OBJECT_ADAPTER_RETURN_SP     = $7E7FDE ; u16 after inner JSR/RTS
SAME_SCUMM_START_OBJECT_CALLER_RETURN_SP      = $7E7FE0 ; u16 after JSL/RTL
SAME_SCUMM_START_OBJECT_SLOT_INDEX             = $7E7FE2 ; u16 X at descriptor access
SAME_SCUMM_START_OBJECT_FRAME_OPS              = $7E7FE4 ; u16 live count at handoff
SAME_SCUMM_START_OBJECT_NATIVE_DIAG_END        = $7E7FE6
; Synchronous target-neutral indexed rectangle request shared by the SCUMM
; producer and video-surface service. This uses the measured gap before the
; global object-owner table; the service consumes it before returning.
SAME_VIDEO_DRAW_RECT_X0                       = $7E7FE6 ; u16 viewport x
SAME_VIDEO_DRAW_RECT_Y0                       = $7E7FE8 ; u16 viewport y
SAME_VIDEO_DRAW_RECT_X1                       = $7E7FEA ; u16 inclusive viewport x
SAME_VIDEO_DRAW_RECT_Y1                       = $7E7FEC ; u16 inclusive viewport y
SAME_VIDEO_DRAW_RECT_COLOR                    = $7E7FEE ; u8 INDEX8 color
SAME_VIDEO_DRAW_RECT_END                      = $7E7FEF
SAME_SCUMM_LOAD_EGO_STATE_SIZE              = $000E

; Movement-observer scratch is outside the M23B nested-program vector
; ($5420-$5437), room/service/query evidence ($5450-$5478), and object-query
; work ring ($54FE+). The bounded 50-byte probe ends at $54B1.
SAME_SCUMM_MOVE_DIAG_BASE                  = $7E5480
SAME_SCUMM_MOVE_DIAG_END                   = $7E54B2
SAME_SCUMM_ENGINE_BOOT_COUNT               = $7E5451 ; u8 diagnostic; increments on each engine boot

; The room-root fixture can be built without the M25A validator personality.
; Keep its two lifecycle bytes available to that lean diagnostic profile.
SAME_SCUMM_SCENARIO_FIXTURE_REQUESTED     = $7E5600 ; u8 one-shot root request
SAME_SCUMM_SCENARIO_FIXTURE_READY         = $7E5601 ; u8 accepted room checkpoint
; Dedicated diagnostic latch for a synthetic cold-start carrier. 5672 is the
; otherwise unused byte between the scenario evidence fields at 5670-5671 and
; 5674; it survives active-engine reinitialization and is reset only by the
; CPU reset vector.
SAME_SCUMM_SYNTHETIC_BOOTSTRAP_REQUESTED   = $7E5672 ; u8 one-shot bootstrap
SAME_SCUMM_AUTHENTIC_BOOTSTRAP_STARTED     = $7E5673 ; u8 one-shot top-level boot global

.if SAME_BUILD_SCUMM_M25A_VALIDATOR
; Dedicated copyright-free validator evidence. This region is not part of a
; game personality or save format and is never referenced by integrated Fate.
SAME_SCUMM_M25A_STATE                     = $7E5000
SAME_SCUMM_M25A_TRACE_COUNT               = $7E5000
SAME_SCUMM_M25A_TRACE_OVERFLOW            = $7E5001
SAME_SCUMM_M25A_MAX_DEPTH                 = $7E5002
SAME_SCUMM_M25A_FAULT_DEPTH               = $7E5003
SAME_SCUMM_M25A_TRACE_EVENT               = $7E5004 ; saved before near/far adapter frames
SAME_SCUMM_M25A_TRACE                     = $7E5010 ; 128 x 8-byte transition records
SAME_SCUMM_M25A_TRACE_STRIDE              = $0008
SAME_SCUMM_M25A_TRACE_CAPACITY            = $0080
SAME_SCUMM_M25A_TRACE_END                 = $7E5410
SAME_SCUMM_M25A_STATE_SIZE                = $0410
SAME_SCUMM_SCENARIO_SENTENCE_CALLS        = $7E5602 ; u8 fixture breadcrumb
SAME_SCUMM_SCENARIO_SENTENCE_RETURNS      = $7E5603 ; u8 fixture breadcrumb
SAME_SCUMM_SCENARIO_SENTENCE_LAST_COUNT   = $7E5604 ; u8 fixture breadcrumb
SAME_SCUMM_SCENARIO_SENTENCE_DEQUEUES     = $7E5605 ; u8 fixture breadcrumb
SAME_SCUMM_SCENARIO_SENTENCE_ALLOCS       = $7E5606 ; u8 fixture breadcrumb
SAME_SCUMM_SCENARIO_CHILD_SLOT            = $7E5607 ; u8
SAME_SCUMM_SCENARIO_CHILD_PROGRAM         = $7E5608 ; u8
SAME_SCUMM_SCENARIO_CHILD_PC              = $7E5609 ; u16
SAME_SCUMM_SCENARIO_CHILD_NUMBER          = $7E560B ; u16
SAME_SCUMM_SCENARIO_CHILD_WHERE           = $7E560D ; u8
SAME_SCUMM_SCENARIO_PARENT_SLOT           = $7E560E ; u8
SAME_SCUMM_SCENARIO_PARENT_PROGRAM        = $7E560F ; u8
SAME_SCUMM_SCENARIO_PARENT_PC             = $7E5610 ; u16
SAME_SCUMM_SCENARIO_NEST_DEPTH            = $7E5612 ; u8
SAME_SCUMM_SCENARIO_FIRST_FETCH_PROGRAM   = $7E5613 ; u8
SAME_SCUMM_SCENARIO_FIRST_FETCH_PC        = $7E5614 ; u16
SAME_SCUMM_SCENARIO_FIRST_FETCH_OPCODE    = $7E5616 ; u8
SAME_SCUMM_SCENARIO_SENTENCE_SLOT         = $7E5617 ; u8
SAME_SCUMM_SCENARIO_SENTENCE_PROGRAM      = $7E5618 ; u8
SAME_SCUMM_SCENARIO_SENTENCE_PC           = $7E5619 ; u16
SAME_SCUMM_SCENARIO_SENTENCE_STATUS       = $7E561B ; u8
SAME_SCUMM_SCENARIO_SENTENCE_ACTIVE       = $7E561C ; u8
SAME_SCUMM_SCENARIO_SCHED_CALLS           = $7E561D ; u8 fixture breadcrumb
SAME_SCUMM_SCENARIO_SCHED_READY           = $7E561E ; u8 carry/result
SAME_SCUMM_SCENARIO_SCHED_DIDEXEC         = $7E561F ; u8 slot 1
SAME_SCUMM_SCENARIO_SCHED_FREEZE          = $7E5620 ; u8 slot 1
SAME_SCUMM_SCENARIO_SCHED_PHASE           = $7E5621 ; u8
SAME_SCUMM_SCENARIO_SCHED_GATE            = $7E5622 ; u8 reason/result
SAME_SCUMM_SCENARIO_C4_CALLS              = $7E5623 ; u8 scheduler entry count
SAME_SCUMM_SCENARIO_STOP_SLOT             = $7E5624 ; u8
SAME_SCUMM_SCENARIO_STOP_PC               = $7E5625 ; u16
SAME_SCUMM_SCENARIO_STOP_COUNT             = $7E5627 ; u8
SAME_SCUMM_SCENARIO_STOP_STATUS            = $7E5628 ; u8 after terminal stop
SAME_SCUMM_SCENARIO_SAVE_STATUS            = $7E5629 ; u8 after slot save
SAME_SCUMM_SCENARIO_SENTENCE_FETCH_COUNT   = $7E562A ; u8 script-2 fetches
SAME_SCUMM_SCENARIO_SENTENCE_FETCH_PC      = $7E562B ; u16
SAME_SCUMM_SCENARIO_SENTENCE_FETCH_OPCODE  = $7E562D ; u8
SAME_SCUMM_SCENARIO_SENTENCE_LOCAL0        = $7E562E ; u16
SAME_SCUMM_SCENARIO_SENTENCE_LOCAL1        = $7E5630 ; u16
SAME_SCUMM_SCENARIO_SENTENCE_LOCAL2        = $7E5632 ; u16
SAME_SCUMM_SCENARIO_DRIVER_REACHED         = $7E5634 ; u8
SAME_SCUMM_SCENARIO_PHASE_BRANCH          = $7E5635 ; u8
; Keep this flag outside sentence evidence ($5640-$564C), title evidence
; ($565C-$5662), and C19 evidence ($5680-$569F).
SAME_SCUMM_SCENARIO_SOURCE_ACTOR_INIT     = $7E5670 ; u8 source-backed fixture setup
SAME_SCUMM_SCENARIO_SENTENCE_PREREQ_ARMED  = $7E5671 ; u8 fixture-only post-mailbox state
SAME_SCUMM_SCENARIO_START_REQUEST          = $7E5636 ; u8
SAME_SCUMM_SCENARIO_START_CURRENT          = $7E5637 ; u8
SAME_SCUMM_SCENARIO_START_ACTIVE_BEFORE    = $7E5638 ; u8
SAME_SCUMM_SCENARIO_START_ACTIVE_AFTER     = $7E5639 ; u8
SAME_SCUMM_SCENARIO_START_SCAN             = $7E563A ; u8
SAME_SCUMM_SCENARIO_START_STATUS1          = $7E563B ; u8
SAME_SCUMM_SCENARIO_START_STATUS2          = $7E563C ; u8
SAME_SCUMM_SCENARIO_START_STATUS3          = $7E563D ; u8
SAME_SCUMM_SCENARIO_START_PROGRAM          = $7E563E ; u8
SAME_SCUMM_SCENARIO_START_RESULT           = $7E563F ; u8
SAME_SCUMM_SCENARIO_START_WRITTEN          = $7E5650 ; u8
SAME_SCUMM_SCENARIO_START_RETURN_SLOT      = $7E5651 ; u8
SAME_SCUMM_SCENARIO_START_RETURN_PROGRAM   = $7E5652 ; u8
SAME_SCUMM_SCENARIO_START_RETURN_PARENT    = $7E5653 ; u8
; Startup-root allocation breadcrumb: fixture-only, 16 records of
; (requested,current,scan,current-status,active-count,current-program,pc).
SAME_SCUMM_SCENARIO_ALLOC_TRACE_COUNT      = $7E5900 ; u8
SAME_SCUMM_SCENARIO_ALLOC_TRACE            = $7E5901 ; 16 x 8 bytes
SAME_SCUMM_SCENARIO_M24RB_ALLOC_COUNT       = $7E5980 ; u8 diagnostic
SAME_SCUMM_SCENARIO_M24RB_ALLOC_STATUS1     = $7E5981 ; u8 diagnostic
SAME_SCUMM_SCENARIO_M24RB_ALLOC_STATUS2     = $7E5982 ; u8 diagnostic
SAME_SCUMM_SCENARIO_M24RB_ALLOC_CHOSEN      = $7E5983 ; u8 diagnostic
SAME_SCUMM_SCENARIO_C25_ERROR_OPCODE        = $7E5990 ; u8 diagnostic
SAME_SCUMM_SCENARIO_C25_ERROR_PROGRAM       = $7E5991 ; u8 diagnostic
SAME_SCUMM_SCENARIO_C25_ERROR_PC            = $7E5992 ; u16 diagnostic
SAME_SCUMM_SCENARIO_C25_ERROR_COUNT         = $7E5994 ; u8 diagnostic
SAME_SCUMM_SCENARIO_C25_ERROR_WORD0         = $7E5995 ; u16 diagnostic
SAME_SCUMM_SCENARIO_C25_ERROR_WORD1         = $7E5997 ; u16 diagnostic
SAME_SCUMM_SCENARIO_C25_ERROR_WORD2         = $7E5999 ; u16 diagnostic
; Fixture-only decoded-opcode breadcrumb: (program,u16 PC-before,opcode), 256 entries.
SAME_SCUMM_SCENARIO_OP_TRACE_COUNT          = $7E5A00 ; u16
SAME_SCUMM_SCENARIO_OP_TRACE               = $7E5A02 ; 256 x 4 bytes
; Keep these after the 0x400-byte opcode ring (which ends at 0x5E02); the
; earlier 0x5E00 placement let the ring overwrite its own failure evidence.
SAME_SCUMM_SCENARIO_LAST_OP_PROGRAM        = $7E5F00 ; u8, persistent breadcrumb
SAME_SCUMM_SCENARIO_LAST_OP_PC             = $7E5F01 ; u16, persistent breadcrumb
SAME_SCUMM_SCENARIO_LAST_OP_OPCODE         = $7E5F03 ; u8, persistent breadcrumb
; M25A-only actor-query native ABI witness. SP is sampled around the JSL/RTL
; boundary, and the returned byte proves control reached the dispatcher again.
SAME_SCUMM_M25A_QUERY_SP_BEFORE            = $7E56A0 ; u16
SAME_SCUMM_M25A_QUERY_SP_AFTER             = $7E56A2 ; u16
SAME_SCUMM_M25A_QUERY_RETURNED             = $7E56A4 ; u8
; Isolated C19 native-control witnesses; never read by production execution.
SAME_SCUMM_C19_NATIVE_STACK_ENTRY          = $7E56B0 ; u16 after helper PHP
SAME_SCUMM_C19_NATIVE_STACK_PRE_RTL        = $7E56B2 ; u16 before RTL
SAME_SCUMM_C19_NATIVE_STACK_CALLER         = $7E56B4 ; u16 after JSL returns
SAME_SCUMM_C19_NATIVE_SKIP_SAMPLE          = $7E56B6 ; u16 logical X edge at gate
SAME_SCUMM_C19_NATIVE_SELECTED_SLOT        = $7E56B8 ; u8 selected C4 slot
SAME_SCUMM_C19_NATIVE_SELECTED_PROGRAM     = $7E56B9 ; u8 selected program
SAME_SCUMM_C19_NATIVE_SELECTED_PC          = $7E56BA ; u16 PC at LoadSlot handoff
SAME_SCUMM_C19_NATIVE_SELECTION_COUNT      = $7E56BC ; u8 selected activations
SAME_SCUMM_SCENARIO_C25_ERROR_LAST_PROGRAM = $7E5F04 ; u8, snapshot at C25 error
SAME_SCUMM_SCENARIO_C25_ERROR_LAST_PC      = $7E5F05 ; u16, snapshot at C25 error
SAME_SCUMM_SCENARIO_C25_ERROR_LAST_OPCODE  = $7E5F07 ; u8, snapshot at C25 error
SAME_SCUMM_SCENARIO_C25_ERROR_SITE         = $7E5F08 ; u8, parser/flush branch id
SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_COUNT  = $7E5F09 ; u8
SAME_SCUMM_SCENARIO_C25_ERROR_PENDING      = $7E5F0A ; u8
SAME_SCUMM_SCENARIO_C25_ERROR_INDEX        = $7E5F0B ; u8
SAME_SCUMM_SCENARIO_C25_ERROR_OFFSET       = $7E5F0C ; u16
SAME_SCUMM_SCENARIO_C25_ERROR_RECORD       = $7E5F0E ; 5 bytes
; Stable fixture error breadcrumb.  This is written by the common error setter,
; so it distinguishes a new production error from a stale status byte even if
; the failing routine later restores the current slot.
SAME_SCUMM_SCENARIO_ERROR_COUNT            = $7E5F20 ; u8
SAME_SCUMM_SCENARIO_ERROR_CODE             = $7E5F21 ; u8
SAME_SCUMM_SCENARIO_ERROR_PROGRAM          = $7E5F22 ; u8
SAME_SCUMM_SCENARIO_ERROR_PC               = $7E5F23 ; u16
SAME_SCUMM_SCENARIO_ERROR_OPCODE           = $7E5F25 ; u8
SAME_SCUMM_SCENARIO_ERROR_ROOM             = $7E5F26 ; u8
SAME_SCUMM_SCENARIO_C25_ERROR_INDEX2       = $7E5F27 ; u8
SAME_SCUMM_SCENARIO_C25_ERROR_OFFSET2      = $7E5F28 ; u16
SAME_SCUMM_SCENARIO_C25_ERROR_WORD2_0      = $7E5F2A ; u16
SAME_SCUMM_SCENARIO_C25_ERROR_PENDING2     = $7E5F2C ; u8
SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE2       = $7E5F2D ; u8
SAME_SCUMM_SCENARIO_ERROR_RET              = $7E5F2E ; u16, SetError caller return
SAME_SCUMM_SCENARIO_ERROR_STACK             = $7E5F30 ; 8 bytes at SetError
SAME_SCUMM_SCENARIO_ERROR_LHS               = $7E5F38 ; u16 decoder reference
SAME_SCUMM_SCENARIO_ERROR_OPERAND           = $7E5F3A ; u16 decoded operand
SAME_SCUMM_SCENARIO_ERROR_RESULT            = $7E5F3C ; u16 resolved result
SAME_SCUMM_SCENARIO_ERROR_C14_ACTOR         = $7E5F3E ; u8 actor at SetError
SAME_SCUMM_SCENARIO_ERROR_C14_SUBOP         = $7E5F3F ; u8 actor sub-op at SetError
SAME_SCUMM_SCENARIO_C25_OBS_PENDING         = $7E5F40 ; u8 parser count
SAME_SCUMM_SCENARIO_C25_OBS_WORDS           = $7E5F41 ; 8 bytes parser words
SAME_SCUMM_SCENARIO_C25_OBS_FLUSH_COUNT     = $7E5F49 ; u8 copied record count
SAME_SCUMM_SCENARIO_C25_OBS_FLUSH_WORDS     = $7E5F4A ; 8 bytes copied words
SAME_SCUMM_SCENARIO_C25_PRODUCER_PROGRAM    = $7E5F52 ; u8 queued producer
SAME_SCUMM_SCENARIO_C25_PRODUCER_PC         = $7E5F53 ; u16 queued producer PC
SAME_SCUMM_SCENARIO_C25_PRODUCER_COUNT      = $7E5F55 ; u8 queued word count
SAME_SCUMM_SCENARIO_C25_PRODUCER_WORDS      = $7E5F56 ; 8 bytes queued words
SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD  = $7E5F60 ; first 16 bytes of failing record
SAME_SCUMM_STREAM_LENGTH_REQUEST_HIGH      = $7E5F5E ; u16 site-0x14 request-length high word
SAME_SCUMM_SCENARIO_C25_DISPATCH_COMMAND    = $7E5F80 ; u16 command loaded by flush
SAME_SCUMM_SCENARIO_C25_DISPATCH_OFFSET     = $7E5F82 ; u16 record offset
SAME_SCUMM_SCENARIO_C25_DISPATCH_COUNT      = $7E5F84 ; u8 record count
; Scheduler-save identity witness: shared interpreter context versus the
; scheduler-selected slot immediately before the continuation is stored.
SAME_SCUMM_SCENARIO_SAVE_SHARED_PROGRAM    = $7E5F86 ; u8
SAME_SCUMM_SCENARIO_SAVE_SLOT_PROGRAM      = $7E5F87 ; u8
SAME_SCUMM_SCENARIO_SAVE_SLOT              = $7E5F88 ; u8
SAME_SCUMM_SCENARIO_SAVE_SHARED_PC         = $7E5F89 ; u16
SAME_SCUMM_SCENARIO_SAVE_SLOT_PC           = $7E5F8B ; u16
SAME_SCUMM_SCENARIO_ERROR_SLOT             = $7E5F8D ; u8 current C4 slot at SetError
; Scheduler handoff trace for the currently published sentence slot.  This is
; fixture-only observation; it deliberately lives after the error evidence
; and before the generated object table.
SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PHASE     = $7E5674 ; u8: 1 before, 2 after run, 3 after save
SAME_SCUMM_SCENARIO_SENTENCE_SCHED_SLOT      = $7E5675 ; u8
SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PROGRAM   = $7E5676 ; u8
SAME_SCUMM_SCENARIO_SENTENCE_SCHED_VM_PC     = $7E5677 ; u16
SAME_SCUMM_SCENARIO_SENTENCE_SCHED_SLOT_PC   = $7E5679 ; u16
SAME_SCUMM_SCENARIO_SENTENCE_SCHED_STATUS    = $7E567B ; u8
SAME_SCUMM_SCENARIO_SENTENCE_SCHED_CURRENT   = $7E567C ; u8
SAME_SCUMM_SCENARIO_FRAME_STAGE              = $7E567D ; u8 last M23A frame stage
; Scheduler eligibility trace (fixture-only; reserved diagnostic scratch).
SAME_SCUMM_SCENARIO_SCHED_SCAN_GATE          = $7E57A4 ; u8 last sentence-slot gate
SAME_SCUMM_SCENARIO_SCHED_SCAN_SLOT          = $7E57A5 ; u8 last slot visited
SAME_SCUMM_SCENARIO_SCHED_SCAN_COUNT         = $7E57A6 ; u8 scans in latest pass
SAME_SCUMM_SCENARIO_SCHED_MATCH_COUNT        = $7E57A7 ; u8 sentence-slot matches
SAME_SCUMM_SCENARIO_SENTENCE_ALLOC_FRAME     = $7E57A8 ; u16 allocation frame
SAME_SCUMM_SCENARIO_SENTENCE_ALLOC_C4        = $7E57AA ; u8 C4 count at allocation
SAME_SCUMM_SCENARIO_FRAME_ENTRY_COUNT        = $7E57AB ; u8 Engine_Frame entries
SAME_SCUMM_SCENARIO_PREPASS_COUNT            = $7E57AC ; u8 sentence prepass calls
SAME_SCUMM_SCENARIO_POST_ALLOC_ENTRY         = $7E57AD ; u8 entries after latest allocation
SAME_SCUMM_SCENARIO_POST_ALLOC_C4            = $7E57AE ; u8 C4 count at latest entry
SAME_SCUMM_SCENARIO_POST_ALLOC_PHASE         = $7E57AF ; u8 M23A phase at latest entry
SAME_SCUMM_SCENARIO_FRAME_STAGE_COUNT        = $7E567E ; u8 stage visits
SAME_SCUMM_SCENARIO_C4_ERROR_ORIGIN          = $7E57B1 ; u8 last C4 subcall
SAME_SCUMM_SCENARIO_C4_RETURN_P              = $7E57B2 ; u8 processor status immediately after RunSelected
SAME_SCUMM_SCENARIO_C4_RETURN_SLOT           = $7E57B3 ; u8 scheduler-selected slot
SAME_SCUMM_SCENARIO_C4_RETURN_PROGRAM        = $7E57B4 ; u8 selected slot program
SAME_SCUMM_SCENARIO_C4_RETURN_PC             = $7E57B5 ; u16 selected slot PC after RunSelected
SAME_SCUMM_SCENARIO_C4_RETURN_STATUS         = $7E57B7 ; u8 selected slot VM status
SAME_SCUMM_SCENARIO_C4_RETURN_ERROR          = $7E57B8 ; u8 SCUMM error at return
; Pending-room validator snapshots are written synchronously by the native
; request routine. Each 24-byte record captures the decision boundary before
; a debugger can observe later frame/service progress.
SAME_SCUMM_PENDING_DIAG_COUNT               = $7E57BF ; u8
SAME_SCUMM_PENDING_DIAG_RECORDS             = $7E57C0 ; 8 x 24-byte records
SAME_SCUMM_PENDING_DIAG_STRIDE              = $0018
SAME_SCUMM_PENDING_DIAG_CAPACITY            = $0008
SAME_SCUMM_PENDING_DIAG_INDEX               = $7E5880 ; u16 helper scratch
SAME_SCUMM_PENDING_DIAG_STAGE               = $7E5882 ; u8 helper scratch
SAME_SCUMM_PENDING_DIAG_X_SAVE              = $7E5883 ; u16 helper scratch
SAME_SCUMM_PENDING_DIAG_INJECT_MODE         = $7E5885 ; validator: 0 off, 1 phase4, 2 phase5
SAME_SCUMM_PENDING_DIAG_INJECT_TARGET       = $7E5886 ; second API request target
SAME_SCUMM_PENDING_DIAG_INJECTED            = $7E5887 ; one-shot marker
SAME_SCUMM_PENDING_DIAG_INJECT_X_SAVE       = $7E5888 ; u16 helper scratch
SAME_SCUMM_PENDING_DIAG_INJECT_ROUTE        = $7E588A ; validator: 0 near, 1 far request entry
SAME_SCUMM_PENDING_DIAG_INJECT_ORIGIN       = $7E588B ; validator: 0 direct VM, 1 public API
SAME_SCUMM_PENDING_DIAG_END                 = $7E588C
SAME_SCUMM_SCENARIO_C25_ENTRY               = $7E5654 ; u8 entry breadcrumb
SAME_SCUMM_SCENARIO_C25_STABLE_INDEX        = $7E5655 ; u8
SAME_SCUMM_SCENARIO_C25_STABLE_OFFSET       = $7E5656 ; u16
SAME_SCUMM_SCENARIO_C25_STABLE_PENDING      = $7E5658 ; u8
SAME_SCUMM_SCENARIO_C25_STABLE_QUEUE        = $7E5659 ; u8
SAME_SCUMM_SCENARIO_C25_STABLE_WORD         = $7E565A ; u16
.endif

; M23C authentic room-63 observation and ordinary logical SFX ownership.
; The opcode trace stores 32 source-program/PC/opcode tuples and is reset when
; the profile-owned room transition is requested; it never supplies operands.
SAME_SCUMM_M23C_STATE                     = $7FF948
SAME_SCUMM_M23C_FIXTURE_APPLIED           = $7FF948
SAME_SCUMM_M23C_PHASE                     = $7FF949
SAME_SCUMM_M23C_READY_WAIT                = $7FF94A
SAME_SCUMM_M23C_ROOM49_READY              = $7FF94B
SAME_SCUMM_M23C_TRANSITION_REQUESTED      = $7FF94C
SAME_SCUMM_M23C_AUTH_FLUSH_SEEN           = $7FF94D
SAME_SCUMM_M23C_AUTH_FLUSH_QUEUE_COUNT    = $7FF94E
SAME_SCUMM_M23C_CLASS_EVAL_COUNT          = $7FF94F
SAME_SCUMM_M23C_CLASS_TRUE_COUNT          = $7FF950
SAME_SCUMM_M23C_SOUND80_RESULT            = $7FF951
SAME_SCUMM_M23C_SCRIPT151_STARTED         = $7FF952
SAME_SCUMM_M23C_SCRIPT151_STATUS          = $7FF953
SAME_SCUMM_M23C_SOUND82_RESULT            = $7FF954
SAME_SCUMM_M23C_CLEAR_QUEUE_COUNT         = $7FF955
SAME_SCUMM_M23C_SOUND_CONTROL_HOLD        = $7FF956
SAME_SCUMM_M23C_TRACE_COUNT               = $7FF957
SAME_SCUMM_M23C_TRACE_OVERFLOW            = $7FF958
SAME_SCUMM_M23C_ERROR_SUBOP               = $7FF959 ; roomOps invalid flags/sub-op
SAME_SCUMM_M23C_ERROR_PROGRAM             = $7FF95A ; program at invalid branch
SAME_SCUMM_M23C_ERROR_OPCODE              = $7FF95B ; opcode at invalid branch
SAME_SCUMM_M23C_ACTIVE_SFX                = $7FF95C ; 256 logical ids as bits
SAME_SCUMM_M23C_ACTIVE_SFX_SIZE           = $0020
SAME_SCUMM_M23C_TRACE                     = $7FF97C ; 32 x (program,u16 PC,opcode)
SAME_SCUMM_M23C_TRACE_STRIDE              = $0004
SAME_SCUMM_M23C_TRACE_CAPACITY            = $0020
SAME_SCUMM_M23C_STATE_END                 = $7FF9FC
SAME_SCUMM_M23C_STATE_SIZE                = $00B4


; M24R-A backend-only synthetic evidence.  This is absent from production
; personalities and carries no SCUMM or Fate semantics.
SAME_M24RA_STATE                          = $7FFA00
SAME_M24RA_PHASE                          = $7FFA00
SAME_M24RA_EVENT_COUNT                    = $7FFA01
SAME_M24RA_LAST_EVENT                     = $7FFA02
SAME_M24RA_GROUP_A_MASK                   = $7FFA03
SAME_M24RA_GROUP_B_MASK                   = $7FFA04
SAME_M24RA_GENERATION                     = $7FFA05
SAME_M24RA_COMMAND_COUNT                  = $7FFA06
SAME_M24RA_STALE_COUNT                    = $7FFA07
SAME_M24RA_TARGET_FRAME                   = $7FFA08 ; u16
SAME_M24RA_REQUEST_FRAME                  = $7FFA0A ; u16
SAME_M24RA_COMPLETE_FRAME                 = $7FFA0C ; u16
SAME_M24RA_REQUEST_TICK                   = $7FFA0E
SAME_M24RA_EVENT_TOKENS                   = $7FFA10 ; 8 u8
SAME_M24RA_EVENT_TICKS                    = $7FFA18 ; 8 u8 transition-relative
SAME_M24RA_EVENT_FRAMES                   = $7FFA20 ; 8 u16 S-CPU frames
SAME_M24RA_EVENT_CAPACITY                 = $0008
SAME_M24RA_STATE_END                      = $7FFA30
SAME_M24RA_STATE_SIZE                     = $0030
SAME_M24RB_STATE                          = $7FFA30
SAME_M24RB_LOGICAL82_STATE                = $7FFA30 ; 0 absent,1 deferred,2 active,3 fading,4 stopped
SAME_M24RB_DEFERRED_COUNT                 = $7FFA32
SAME_M24RB_MARKER_COUNT                   = $7FFA33
SAME_M24RB_FADE_COMPLETE_COUNT            = $7FFA34
SAME_M24RB_LSCR_SCHEDULED                 = $7FFA35
SAME_M24RB_FRAME_END_FLUSHES              = $7FFA36
SAME_M24RB_FRAME_END_ACTIVE               = $7FFA37
SAME_M24RB_TRIGGER_MARKER                 = $7FFA38 ; u16 SCUMM/iMUSE marker word
SAME_M24RB_C25_RETURN_FRAME                = $7FFA3A ; wrapper-owned far-flush JSL return
SAME_M24RB_C25_DEBUG_STAGE                 = $7FFA3B ; diagnostic build only
SAME_M24RB_C25_DEBUG_ENTRY_SP              = $7FFA3C ; u16 diagnostic stack snapshot
SAME_M24RB_C25_DEBUG_RETURN_SP             = $7FFA3E ; u16 diagnostic stack snapshot
SAME_M24RB_STATE_END                      = $7FFA40

; Canonical v5 mutable walkbox flags. Geometry and BOXM routes remain immutable
; resource data; matrixOps sub-op 1 overwrites only this active-room byte field.
SAME_SCUMM_MATRIX_STATE                   = $7FFA40
SAME_SCUMM_MATRIX_BOX_COUNT               = $7FFA40 ; u8, active ROOM BOXD count
SAME_SCUMM_MATRIX_BOX_FLAGS               = $7FFA41 ; 255 raw u8 flag values
SAME_SCUMM_MATRIX_LAST_SUBOP              = $7FFB40 ; diagnostic, fetched byte
SAME_SCUMM_MATRIX_LAST_BOX                = $7FFB41 ; diagnostic, decoded operand
SAME_SCUMM_MATRIX_LAST_FLAGS              = $7FFB42 ; diagnostic, decoded operand
SAME_SCUMM_MATRIX_EXEC_COUNT              = $7FFB43 ; successful mutations
SAME_SCUMM_MATRIX_TRACE_COUNT             = $7FFB44 ; decoded matrixOps records
SAME_SCUMM_MATRIX_TRACE                   = $7FFB45 ; 4 x (subop,box,flags,u16 before,u16 after,pad)
SAME_SCUMM_MATRIX_TRACE_STRIDE            = $0008
SAME_SCUMM_MATRIX_TRACE_CAPACITY          = $0004
SAME_SCUMM_MATRIX_STATE_END               = $7FFB65
SAME_SCUMM_MATRIX_STATE_SIZE              = $0125
; SCUMM v5 createBoxMatrix uses a 64-box routing domain. Keep its two 64x64
; byte tables in the audited gap after object-name storage and before C10.
; The C10 state tail byte at $34FA is outside all named fields/parameters and
; holds only the active-room validity flag; room commit/reset owns its lifetime.
SAME_SCUMM_MATRIX_DISTANCE                 = $7F1000 ; 64 x 64 u8 distances
SAME_SCUMM_MATRIX_DYNAMIC_ROUTES           = $7F2000 ; 64 x 64 u8 next hops
SAME_SCUMM_MATRIX_DYNAMIC_VALID            = $7F34FA ; C10 free tail, active-room validity
SAME_SCUMM_MATRIX_BUILD_I                   = SAME_SCUMM_C10_PARAM0 ; u16 scratch
SAME_SCUMM_MATRIX_BUILD_J                   = SAME_SCUMM_C10_PARAM1 ; u16 scratch
SAME_SCUMM_MATRIX_BUILD_K                   = SAME_SCUMM_C10_PARAM2 ; u16 scratch
SAME_SCUMM_MATRIX_BUILD_OFFSET_IK          = SAME_SCUMM_C10_PARAM3 ; u16 scratch
SAME_SCUMM_MATRIX_BUILD_OFFSET_KJ          = SAME_SCUMM_C10_PARAM4 ; u16 scratch

; Canonical v5 putActor placement state.  Immutable active-room BOXD geometry
; is copied from profile-generated data; this is not a pathfinding graph.
SAME_SCUMM_PUT_ACTOR_STATE                = $7FFB65
; Immutable BOXD geometry is generated ROM data.  The former 32-record RAM
; image is now one bounded working record populated by the generic accessor.
SAME_SCUMM_PUT_ACTOR_BOX_CAPACITY         = $00FF
SAME_SCUMM_PUT_ACTOR_BOX_STRIDE           = $0012 ; 8 x s16 coords + u16 scale
SAME_SCUMM_PUT_ACTOR_BOXES                = $7FFB65 ; compatibility alias
SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK        = $7FFB65 ; one fetched BOXD record
SAME_SCUMM_PUT_ACTOR_WALKBOX              = $7FFDA5 ; 32 x u8
SAME_SCUMM_PUT_ACTOR_DESTBOX              = $7FFDC5 ; 32 x u8
SAME_SCUMM_PUT_ACTOR_DEST_X               = $7FFDE5 ; 32 x s16; -1 cancels walk
SAME_SCUMM_PUT_ACTOR_REDRAW               = $7FFE25 ; 32 x u8
SAME_SCUMM_PUT_ACTOR_LAST_VALID           = $7FFE45 ; 32 x (s16 x,s16 y)
SAME_SCUMM_PUT_ACTOR_ACTOR                = $7FFEC5 ; u8
SAME_SCUMM_PUT_ACTOR_REQUEST_X            = $7FFEC6 ; s16
SAME_SCUMM_PUT_ACTOR_REQUEST_Y            = $7FFEC8 ; s16
SAME_SCUMM_PUT_ACTOR_RESULT_X             = $7FFECA ; s16
SAME_SCUMM_PUT_ACTOR_RESULT_Y             = $7FFECC ; s16
SAME_SCUMM_PUT_ACTOR_RESULT_BOX           = $7FFECE ; u8
SAME_SCUMM_PUT_ACTOR_SCAN_BOX             = $7FFECF ; u8
SAME_SCUMM_PUT_ACTOR_BEST_DISTANCE        = $7FFED0 ; u16
SAME_SCUMM_PUT_ACTOR_POINT_DISTANCE       = $7FFED2 ; u16
SAME_SCUMM_PUT_ACTOR_POINT_X              = $7FFED4 ; s16
SAME_SCUMM_PUT_ACTOR_POINT_Y              = $7FFED6 ; s16
SAME_SCUMM_PUT_ACTOR_XMIN                 = $7FFED8 ; s16
SAME_SCUMM_PUT_ACTOR_XMAX                 = $7FFEDA ; s16
SAME_SCUMM_PUT_ACTOR_GEOM_OFFSET          = $7FFEDC ; u16
SAME_SCUMM_PUT_ACTOR_TEMP0                = $7FFEDE ; s16
SAME_SCUMM_PUT_ACTOR_TEMP1                = $7FFEE0 ; s16
SAME_SCUMM_PUT_ACTOR_PC_BEFORE            = $7FFEE2 ; u16 diagnostic
SAME_SCUMM_PUT_ACTOR_PC_AFTER             = $7FFEE4 ; u16 diagnostic
SAME_SCUMM_PUT_ACTOR_EXEC_COUNT           = $7FFEE6 ; u8
SAME_SCUMM_PUT_ACTOR_ULX                  = $7FFEE8 ; binary-side scratch
SAME_SCUMM_PUT_ACTOR_LLX                  = $7FFEEA
SAME_SCUMM_PUT_ACTOR_URX                  = $7FFEEC
SAME_SCUMM_PUT_ACTOR_LRX                  = $7FFEEE
SAME_SCUMM_PUT_ACTOR_TOP                  = $7FFEF0
SAME_SCUMM_PUT_ACTOR_BOTTOM               = $7FFEF2
SAME_SCUMM_PUT_ACTOR_CURRENT_Y            = $7FFEF4
SAME_SCUMM_PUT_ACTOR_TRACE_COUNT          = $7FFF00
SAME_SCUMM_PUT_ACTOR_TRACE                = $7FFF01 ; 8 x 14-byte decode records
SAME_SCUMM_PUT_ACTOR_TRACE_STRIDE         = $000E
SAME_SCUMM_PUT_ACTOR_TRACE_CAPACITY       = $0008
SAME_SCUMM_PUT_ACTOR_BOX_SCALE_RAW        = $7FFF71 ; 32 x canonical u16 box scale
SAME_SCUMM_PUT_ACTOR_STATE_END            = $7FFFB1
SAME_SCUMM_PUT_ACTOR_STATE_SIZE           = $044C

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
