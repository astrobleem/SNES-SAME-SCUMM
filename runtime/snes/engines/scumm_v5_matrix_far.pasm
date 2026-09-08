; Cold canonical SCUMM v5 matrixOps sub-op 1 closure. Included after either
; generated profile room data or the established M24R-B far closure.
; The production room scheduler eligibility check shares this cold bank so
; bank 0 retains only a JSL/branch/jump veneer.  Carry set means that an idle,
; validated active room owns at least one runnable scheduler slot.
ScummV5_SchedulerReady_FarEntry:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_PHASE
    beq ScummV5_SchedulerReady_FarEntry__phase_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_SCHED_GATE
    .endif
    bra ScummV5_SchedulerReady_FarEntry__no
ScummV5_SchedulerReady_FarEntry__phase_ok:
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$FF
    bne ScummV5_SchedulerReady_FarEntry__record_ok
    ; Room zero is the canonical SCUMM null scene. It has no generated
    ; profile record, but global scripts remain schedulable in that namespace.
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    beq ScummV5_SchedulerReady_FarEntry__record_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$02
    sta.l SAME_SCUMM_SCENARIO_SCHED_GATE
    .endif
    bra ScummV5_SchedulerReady_FarEntry__no
ScummV5_SchedulerReady_FarEntry__record_ok:
    rep #$10
    .i16
    ldx #$0000
ScummV5_SchedulerReady_FarEntry__scan:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_SchedulerReady_FarEntry__next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_SchedulerReady_FarEntry__next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_SchedulerReady_FarEntry__next
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$04
    sta.l SAME_SCUMM_SCENARIO_SCHED_GATE
    .endif
    sec
    rtl
ScummV5_SchedulerReady_FarEntry__next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_SchedulerReady_FarEntry__scan
ScummV5_SchedulerReady_FarEntry__no:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    .a8
    lda.l SAME_SCUMM_SCENARIO_SCHED_GATE
    bne ScummV5_SchedulerReady_FarEntry__no_record
    lda #$03
    sta.l SAME_SCUMM_SCENARIO_SCHED_GATE
ScummV5_SchedulerReady_FarEntry__no_record:
    .endif
    clc
    rtl

; Once the scheduler-owned ENCD slot has stopped, room entry is complete even
; when room-local/global children remain runnable. Those children belong to
; the ordinary scheduler, not the one-shot lifecycle interpreter.
ScummV5_M23A_NormalizeEntryLifecycle_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M25_PHASE_NORMALIZE_CALLS
    inc
    sta.l SAME_SCUMM_M25_PHASE_NORMALIZE_CALLS
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$02
    bne ScummV5_M23A_NormalizeEntryLifecycle_Far__done
    lda.l SAME_SCUMM_C4_SLOT_STATUS
    beq ScummV5_M23A_NormalizeEntryLifecycle_Far__complete
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_M23A_NormalizeEntryLifecycle_Far__complete
    ; A nested child can return with the shared VM status/current-slot pair
    ; belonging to that child even though slot zero has consumed the final
    ; ENCD byte.  Use the slot-owned PC and generated program length as the
    ; authoritative terminal test, then retire through the same room-script
    ; primitive used by opcode 00.
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM
    jsl ScummV5_M23A_GetProgramSize_Far
    bcc ScummV5_M23A_NormalizeEntryLifecycle_Far__done
    sta.l SAME_SCUMM_PROGRAM_SIZE
    rep #$20
    .a16
    lda.l SAME_SCUMM_PROGRAM_SIZE
    dec
    sta.l SAME_SCUMM_PROGRAM_SIZE
    lda.l SAME_SCUMM_C4_SLOT_PC
    cmp.l SAME_SCUMM_PROGRAM_SIZE
    bcc ScummV5_M23A_NormalizeEntryLifecycle_Far__done16
    sep #$20
    .a8
    jsl ScummV5_M23A_EndRoomScript_FarEntry
    bra ScummV5_M23A_NormalizeEntryLifecycle_Far__complete
ScummV5_M23A_NormalizeEntryLifecycle_Far__done16:
    sep #$20
    .a8
ScummV5_M23A_NormalizeEntryLifecycle_Far__complete:
    .a8
    lda.l SAME_SCUMM_M25_PHASE_NORMALIZE_COMMITS
    inc
    sta.l SAME_SCUMM_M25_PHASE_NORMALIZE_COMMITS
    lda #$00
    sta.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
ScummV5_M23A_NormalizeEntryLifecycle_Far__done:
    clc
    rtl

; Temporary production-path diagnostic: requested script, current slot,
; selected allocation slot, and current-slot status.
ScummV5_M25_DebugStartAlloc_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M25_START_TRACE_COUNT
    cmp #$10
    bcs ScummV5_M25_DebugStartAlloc_Far__done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    tax
    phx
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_M25_START_TRACE,x
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_M25_START_TRACE+1,x
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_M25_START_TRACE+2,x
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    rep #$20
    .a16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    plx
    sta.l SAME_SCUMM_M25_START_TRACE+3,x
    lda.l SAME_SCUMM_M25_START_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_M25_START_TRACE_COUNT
ScummV5_M25_DebugStartAlloc_Far__done:
    clc
    rtl

ScummV5_M25_DebugOpcode_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_SENTENCE_INJECTED
    beq ScummV5_M25_DebugOpcode_Far__done
    lda.l SAME_SCUMM_M25_START_TRACE_COUNT
    and #$0F
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M25_START_TRACE,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_M25_START_TRACE+1,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_M25_START_TRACE+3,x
    lda.l SAME_SCUMM_M25_START_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_M25_START_TRACE_COUNT
ScummV5_M25_DebugOpcode_Far__done:
    clc
    rtl

; Canonical end-of-pass semantic sentence launch.  This consumes the existing
; C20 production queue, derives the launcher from VAR_SENTENCE_SCRIPT, resolves
; it through the generated global-script directory, and allocates an ordinary
; scheduler slot.  The new slot is marked didexec so it cannot run until the
; next scheduler pass, matching the host loop ordering.
ScummV5_SentenceProcess_Far:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    jsl ScummV5_Scenario_Fixture_EnsureActor2Room42_Far
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    bne ScummV5_SentenceProcess_Far__has_sentence
    brl ScummV5_SentenceProcess_Far__done
ScummV5_SentenceProcess_Far__has_sentence:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_M23B_VARIABLES+(33 * 2)
    and #$00FF
    bne ScummV5_SentenceProcess_Far__has_launcher
    brl ScummV5_SentenceProcess_Far__done16
ScummV5_SentenceProcess_Far__has_launcher:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    ; An active, unfrozen sentence script blocks dequeuing another sentence.
    ldx #$0001
ScummV5_SentenceProcess_Far__active_scan:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_SentenceProcess_Far__active_next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_SentenceProcess_Far__active_next
    lda.l SAME_SCUMM_C4_SLOT_NUMBER,x
    rep #$20
    .a16
    and #$00FF
    cmp.l SAME_SCUMM_OPERAND
    bne ScummV5_SentenceProcess_Far__active_next16
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    bne ScummV5_SentenceProcess_Far__active_next
    brl ScummV5_SentenceProcess_Far__done
ScummV5_SentenceProcess_Far__active_next:
    .a8
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_SentenceProcess_Far__active_scan
    bra ScummV5_SentenceProcess_Far__dequeue
ScummV5_SentenceProcess_Far__active_next16:
    sep #$20
    .a8
    bra ScummV5_SentenceProcess_Far__active_next
ScummV5_SentenceProcess_Far__dequeue:
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    dec
    sta.l SAME_SCUMM_C20_COUNT
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_DEQUEUES
    inc
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_DEQUEUES
    .endif
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    asl
    clc
    adc.l SAME_SCUMM_PRODUCT
    asl
    tax
    txa
    sta.l $7E5636
    ; Retain the selected record byte offset separately.  The C20 operand
    ; scratch is also used by global-resource resolution, so sentence locals
    ; must be sourced from the record selected before that call.
    txa
    sta.l SAME_SCUMM_RESULT_OFFSET
    sta.l $7E5646
    sta.l SAME_SCUMM_C4_PARENT_PC
    sep #$20
    .a8
    ; C20 is a dense LIFO queue.  A producer may leave a stale count after a
    ; boundary, but it must never make an empty record appear selected while a
    ; populated record remains at the queue head.  Preserve the generic
    ; decoded sentence by falling back to the first populated record.
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_VERB,x
    bne ScummV5_SentenceProcess_Far__record_selected
    ldx #$0000
    txa
    sta.l SAME_SCUMM_RESULT_OFFSET
    sta.l $7E5646
    sta.l SAME_SCUMM_C4_PARENT_PC
ScummV5_SentenceProcess_Far__record_selected:
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    beq ScummV5_SentenceProcess_Far__record_ready
    brl ScummV5_SentenceProcess_Far__restore_count
ScummV5_SentenceProcess_Far__record_ready:
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_VERB,x
    sta.l SAME_SCUMM_C20_VERB
    rep #$20
    .a16
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_A,x
    sta.l SAME_SCUMM_C20_OBJECT_A
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_B,x
    sta.l SAME_SCUMM_C20_OBJECT_B
    ; Preserve the decoded tuple before global-resource resolution can reuse
    ; the C20 operand scratch used by the resolver.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_VERB
    sta.l SAME_SCUMM_C4_ARGS
    sta.l $7E5640
    rep #$20
    .a16
    lda.l SAME_SCUMM_C20_OBJECT_A
    sta.l SAME_SCUMM_C4_ARGS+2
    sta.l $7E5642
    lda.l SAME_SCUMM_C20_OBJECT_B
    sta.l SAME_SCUMM_C4_ARGS+4
    sta.l $7E5644
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Dedicated sentence-launch evidence: retain the decoded C20 tuple before
    ; allocation/local initialization can reuse the operand scratch fields.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_VERB,x
    sta.l $7E5708
    rep #$20
    .a16
    lda.l SAME_SCUMM_C20_OBJECT_A
    sta.l $7E5709
    lda.l SAME_SCUMM_C20_OBJECT_B
    sta.l $7E570B
    .endif
    beq ScummV5_SentenceProcess_Far__resolve
    cmp.l SAME_SCUMM_C20_OBJECT_A
    bne ScummV5_SentenceProcess_Far__resolve
    brl ScummV5_SentenceProcess_Far__done16
ScummV5_SentenceProcess_Far__resolve:
    sep #$20
    .a8
    lda.l SAME_SCUMM_OPERAND
    jsl ScummV5_M23A_ResolveGlobalScript_Far
    bcs ScummV5_SentenceProcess_Far__resolved
    brl ScummV5_SentenceProcess_Far__resource_error
ScummV5_SentenceProcess_Far__resolved:
    .a8
    .i16
    sta.l SAME_SCUMM_FETCH_BYTE
    ldx #$0001
ScummV5_SentenceProcess_Far__slot_scan:
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_SentenceProcess_Far__slot_found
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_SentenceProcess_Far__slot_found
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_SentenceProcess_Far__slot_scan
    lda #SCUMM_ERR_SLOT_CAPACITY
    brl ScummV5_SentenceProcess_Far__error
ScummV5_SentenceProcess_Far__slot_found:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Start a fresh per-launch execution witness.  A cumulative fetch count
    ; cannot identify the current sentence instance after a second mailbox
    ; transaction and made a live PC=0 observation ambiguous.
    lda #$00
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_FETCH_COUNT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PHASE
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_COUNT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_ALLOC_FRAME
    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENARIO_C4_CALLS
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_ALLOC_C4
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_ALLOCS
    inc
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_ALLOCS
    .endif
    txa
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    ; A sentence launch is a fresh scheduler owner.  Do not carry a
    ; per-slot cutscene depth from the slot's previous occupant into the
    ; terminal stop of the new global sentence script.
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    txa
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_PROGRAM
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_STATUS
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_ACTIVE
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_PC
    sep #$20
    .a8
    .endif
    ; The evidence read above uses the word-indexed PC table. Restore the
    ; byte-indexed scheduler slot before continuing the production allocation.
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    ; SentenceProcess runs after the current C4 scan has completed. A slot
    ; allocated here must be eligible on the next canonical pass; marking it
    ; didexec would make it look as though it already ran in that pass.
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    rep #$30
    .a16
    .i16
    txa
    and #$00FF
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    lda #$0000
    ldy #$0000
ScummV5_SentenceProcess_Far__clear_locals:
    .a16
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    iny
    cpy #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_SentenceProcess_Far__clear_locals
    ; Restore the selected slot's local base and publish the three sentence
    ; args.  C20_VERB/OBJECT_A/OBJECT_B are the decoded record values retained
    ; before global-resource resolution.  They are the canonical handoff
    ; scratch; the record-offset scratch is shared by other lookup helpers and
    ; is not a stable source after allocation.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    txa
    sta.l SAME_SCUMM_RESULT_OFFSET
    lda.l SAME_SCUMM_C4_PARENT_PC
    tax
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_VERB,x
    pha
    lda.l SAME_SCUMM_RESULT_OFFSET
    tax
    pla
    and #$00FF
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    sta.l $7E5648
    ; Sentence dispatch exposes the selected verb through the ordinary global
    ; variable table as well as the launcher slot's locals.  This is the
    ; source-visible VAR_SENTENCE_SCRIPT handoff used by generated sentence
    ; launchers and remains valid after the C4 owner is switched.
    sta.l SAME_SCUMM_M23B_VARIABLES+(16 * 2)
    lda.l SAME_SCUMM_C4_PARENT_PC
    tax
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_A,x
    pha
    lda.l SAME_SCUMM_RESULT_OFFSET
    tax
    pla
    sta.l SAME_SCUMM_C4_SLOT_LOCALS+2,x
    sta.l $7E564A
    lda.l SAME_SCUMM_C4_PARENT_PC
    tax
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_B,x
    pha
    lda.l SAME_SCUMM_RESULT_OFFSET
    tax
    pla
    sta.l SAME_SCUMM_C4_SLOT_LOCALS+4,x
    sta.l $7E564C
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SLOT_LOCALS,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_LOCAL0
    lda.l SAME_SCUMM_C4_SLOT_LOCALS+2,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_LOCAL1
    lda.l SAME_SCUMM_C4_SLOT_LOCALS+4,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_LOCAL2
    .endif
    clc
    rtl

.if SAME_BUILD_SCUMM_M25_MOVEMENT
; The hash-bound pre-Thera fixture declares an exact sparse bit-variable set.
; Clear the packed state before bank 0 installs bit 425; OR-ing into cold WRAM
; otherwise makes indexed sentence predicates depend on power-on residue.
ScummV5_M25_ResetBitState_Far:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_M25_ResetBitState_Far__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C7_BITS,x
    inx
    inx
    cpx #$0200
    bcc ScummV5_M25_ResetBitState_Far__loop
    sep #$20
    .a8
    rtl

; Validation-profile producer for one already-decoded semantic action.  This
; routine writes the ordinary C20 production queue; sentence launch remains
; owned by ScummV5_SentenceProcess_Far and VAR_SENTENCE_SCRIPT.
ScummV5_M25_MaybeQueueSentence_Far:
    ; Standalone scenario fixtures submit their action through the semantic
    ; mailbox.  The authored M25 producer sentence belongs only to the
    ; transition fixture and must not preempt a focused object scenario.
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    jmp ScummV5_M25_MaybeQueueSentence_Far__done
    .endif
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    ; Forced-blank visual bootstrap installs room 49 before the first normal
    ; SCUMM frame. Preserve the legacy lifecycle boundary: frame 1 owns the
    ; already-scheduled room entry, and the semantic sentence boundary opens
    ; on frame 2 exactly as it does when room installation occurs in frame 1.
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_COUNT
    cmp #$0002
    bcs ScummV5_M25_MaybeQueueSentence_Far__visual_ready
    brl ScummV5_M25_MaybeQueueSentence_Far__done16
ScummV5_M25_MaybeQueueSentence_Far__visual_ready:
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_SENTENCE_INJECTED
    bne ScummV5_M25_MaybeQueueSentence_Far__done
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$00
    bne ScummV5_M25_MaybeQueueSentence_Far__done
    lda.l SAME_SCUMM_C31_MOVING+1
    bne ScummV5_M25_MaybeQueueSentence_Far__done
    lda.l SAME_SCUMM_PUT_ACTOR_WALKBOX+1
    cmp #$0B
    bne ScummV5_M25_MaybeQueueSentence_Far__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    cmp #$018F
    bne ScummV5_M25_MaybeQueueSentence_Far__done16
    lda.l SAME_SCUMM_C31_POSITIONS+6
    cmp #$0074
    bne ScummV5_M25_MaybeQueueSentence_Far__done16
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    bne ScummV5_M25_MaybeQueueSentence_Far__done
    ; Apply the named pre-Thera engine-state fixture at the semantic-input
    ; boundary, after the bounded room-entry harness has finished its own
    ; initialization.  VAR_EGO is part of ordinary engine state, not a
    ; precomputed branch result or script local.
    rep #$20
    .a16
    lda #$0001
    .if !SAME_BUILD_SCUMM_PHASE6HB
    sta.l $7E2322                    ; legacy window: VAR_EGO
    .endif
    sta.l SAME_SCUMM_M23B_VARIABLES+(1 * 2)
    sep #$20
    .a8
    lda #$0A
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_VERB
    lda #$00
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE
    rep #$20
    .a16
    lda #$0254
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_A
    lda #$0000
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_B
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C20_COUNT
    sta.l SAME_SCUMM_SENTENCE_INJECTED
    lda #$00
    sta.l SAME_SCUMM_M25_START_TRACE_COUNT
    lda #$00
    sta.l SAME_SCUMM_M23C_TRACE_COUNT
    sta.l SAME_SCUMM_M23C_TRACE_OVERFLOW
ScummV5_M25_MaybeQueueSentence_Far__done:
    .a8
    clc
    rtl
ScummV5_M25_MaybeQueueSentence_Far__done16:
    sep #$20
    .a8
    clc
    rtl
.endif
ScummV5_SentenceProcess_Far__restore_count:
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    inc
    sta.l SAME_SCUMM_C20_COUNT
ScummV5_SentenceProcess_Far__done:
    clc
    rtl
ScummV5_SentenceProcess_Far__done16:
    sep #$20
    .a8
    clc
    rtl
ScummV5_SentenceProcess_Far__resource_error:
    .a8
    .if SAME_BUILD_SCUMM_M23B
    lda #$E1
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    .endif
    lda #SCUMM_ERR_RESOURCE
ScummV5_SentenceProcess_Far__error:
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    sec
    rtl

ScummV5_ColdOpcode_FarEntry:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$AE
    bne ScummV5_ColdOpcode_FarEntry__not_wait
    jmp ScummV5_Talk_Wait_FarEntry
ScummV5_ColdOpcode_FarEntry__not_wait:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$4C
    bne ScummV5_ColdOpcode_FarEntry__not_sound_kludge
    jml ScummV5_Op_SoundKludge
ScummV5_ColdOpcode_FarEntry__not_sound_kludge:
    ; DrawBox variants must precede the broad putActor low-bit family:
    ; $FF has low five bits $01 but is canonically drawBox.
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$3F
    bne ScummV5_ColdOpcode_FarEntry__not_draw_box_early
    jmp ScummV5_DrawBox_FarEntry
ScummV5_ColdOpcode_FarEntry__not_draw_box_early:
    ; Phase 6L-A deliberately parks the preliminary loadRoomWithEgo decoder.
    ; The authentic acceptance boundary remains the decoded PC $02DE; no $24
    ; transition may execute until the deferred sound-82 prerequisite passes.
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$1F
    cmp #$1E
    bne ScummV5_ColdOpcode_FarEntry__not_walk_actor
    jmp ScummV5_WalkActorTo_FarEntry
ScummV5_ColdOpcode_FarEntry__not_walk_actor:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$36
    bne ScummV5_ColdOpcode_FarEntry__not_walk_object
    jmp ScummV5_WalkActorToObject_FarEntry
ScummV5_ColdOpcode_FarEntry__not_walk_object:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$0B
    bne ScummV5_ColdOpcode_FarEntry__not_get_verb
    jmp ScummV5_GetVerbEntrypoint_FarEntry
ScummV5_ColdOpcode_FarEntry__not_get_verb:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$10
    bne ScummV5_ColdOpcode_FarEntry__not_get_owner
    jmp ScummV5_GetObjectOwner_FarEntry
ScummV5_ColdOpcode_FarEntry__not_get_owner:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$29
    bne ScummV5_ColdOpcode_FarEntry__not_set_owner
    jml ScummV5_Op_SetOwnerOf
ScummV5_ColdOpcode_FarEntry__not_set_owner:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$25
    bne ScummV5_ColdOpcode_FarEntry__not_pickup
    jml ScummV5_Op_PickupObject
ScummV5_ColdOpcode_FarEntry__not_pickup:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$31
    bne ScummV5_ColdOpcode_FarEntry__not_inventory_count
    jml ScummV5_Op_GetInventoryCount
ScummV5_ColdOpcode_FarEntry__not_inventory_count:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$3D
    bne ScummV5_ColdOpcode_FarEntry__not_find_inventory
    jml ScummV5_Op_FindInventory
ScummV5_ColdOpcode_FarEntry__not_find_inventory:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$7B
    bne ScummV5_ColdOpcode_FarEntry__not_get_walkbox
    jmp ScummV5_GetActorWalkbox_FarEntry
ScummV5_ColdOpcode_FarEntry__not_get_walkbox:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$63
    bne ScummV5_ColdOpcode_FarEntry__not_get_facing
    jmp ScummV5_GetActorFacing_FarEntry
ScummV5_ColdOpcode_FarEntry__not_get_facing:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$07
    bne ScummV5_ColdOpcode_FarEntry__not_set_state
    jmp ScummV5_SetState_FarEntry
ScummV5_ColdOpcode_FarEntry__not_set_state:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$1F
    cmp #$01
    bne ScummV5_ColdOpcode_FarEntry__not_draw_box
    jmp ScummV5_PutActor_FarEntry
ScummV5_ColdOpcode_FarEntry__not_draw_box:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$3F
    bne ScummV5_ColdOpcode_FarEntry__not_put_actor
    jmp ScummV5_DrawBox_FarEntry
ScummV5_ColdOpcode_FarEntry__not_put_actor:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$37
    bne ScummV5_ColdOpcode_FarEntry__not_start_object
    jmp ScummV5_StartObject_FarEntry
ScummV5_ColdOpcode_FarEntry__not_start_object:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$34
    bne ScummV5_ColdOpcode_FarEntry__not_get_dist
    jmp ScummV5_GetDist_FarEntry
ScummV5_ColdOpcode_FarEntry__not_get_dist:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$30
    bne ScummV5_ColdOpcode_FarEntry__unknown
    jmp ScummV5_MatrixOps_FarEntry
ScummV5_ColdOpcode_FarEntry__unknown:
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_GET_WALKBOX_NEXT_PROGRAM
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_GET_WALKBOX_NEXT_OPCODE
    lda #$01
    sta.l SAME_SCUMM_GET_WALKBOX_NEXT_SEEN
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_GET_WALKBOX_NEXT_PC
    sep #$20
    .a8
    lda #SCUMM_ERR_OPCODE
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

; Canonical v5 drawBox variants ($3F/$7F/$BF/$FF).  The visual backend does
; not expose a script-visible box surface here, but decoding must consume the
; exact operands so the enclosing object program remains synchronized.
ScummV5_DrawBox_FarEntry:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_DrawBox_FetchVow
    bcc ScummV5_DrawBox_FarEntry__x1_ok
    brl ScummV5_DrawBox_FarEntry__error
ScummV5_DrawBox_FarEntry__x1_ok:
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_DrawBox_FetchVow
    bcs ScummV5_DrawBox_FarEntry__error
    jsr ScummV5_FetchByte
    bcs ScummV5_DrawBox_FarEntry__error
    ; The auxiliary opcode supplies the masks for x2/y2/color.
    sta.l SAME_SCUMM_LAST_OPCODE
    lda #$80
    jsr ScummV5_DrawBox_FetchVow
    bcs ScummV5_DrawBox_FarEntry__error
    lda #$40
    jsr ScummV5_DrawBox_FetchVow
    bcs ScummV5_DrawBox_FarEntry__error
    lda #$80
    jsr ScummV5_DrawBox_FetchVob
    bcs ScummV5_DrawBox_FarEntry__error
    jml ScummV5_Engine_Frame__next
; Consume a drawBox vow: direct values are p16; variable values carry a p16
; reference and, for indirect references, one additional p16 selector.
ScummV5_DrawBox_FetchVow:
    sta.l SAME_SCUMM_CONDITION
    ; get_vow() selects variable/direct from the opcode flag mask.  A direct
    ; signed word may itself contain bit $2000 (for example #-$100); that
    ; value is not an indirect-variable marker.
    lda.l SAME_SCUMM_LAST_OPCODE
    and.l SAME_SCUMM_CONDITION
    beq ScummV5_DrawBox_FetchVow__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_DrawBox_FetchVow__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    and #$2000
    sep #$20
    .a8
    beq ScummV5_DrawBox_FetchVow__ok
    jsr ScummV5_FetchWord
    bra ScummV5_DrawBox_FetchVow__ok
ScummV5_DrawBox_FetchVow__direct:
    jsr ScummV5_FetchWord
ScummV5_DrawBox_FetchVow__ok:
    clc
ScummV5_DrawBox_FetchVow__done:
    rts
ScummV5_DrawBox_FetchVob:
    sta.l SAME_SCUMM_CONDITION
    ; vob() is byte-valued when the selected flag is clear.  The previous
    ; implementation unconditionally consumed a word here, advancing past
    ; the following opcode for canonical direct colors.
    lda.l SAME_SCUMM_LAST_OPCODE
    and.l SAME_SCUMM_CONDITION
    beq ScummV5_DrawBox_FetchVob__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_DrawBox_FetchVob__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    and #$2000
    sep #$20
    .a8
    beq ScummV5_DrawBox_FetchVob__ok
    jsr ScummV5_FetchWord
    bra ScummV5_DrawBox_FetchVob__ok
ScummV5_DrawBox_FetchVob__direct:
    jsr ScummV5_FetchByte
ScummV5_DrawBox_FetchVob__ok:
    clc
ScummV5_DrawBox_FetchVob__done:
    rts
ScummV5_DrawBox_FarEntry__error:
    sep #$20
    .a8
    lda #SCUMM_ERR_OPCODE
    jsr ScummV5_SetError
    sec
    rts

; Canonical v5 $24/$64/$A4/$E4.  Decode all operands transactionally before
; publishing the asynchronous room request.  The lifecycle owns completion;
; a room-local caller is deliberately allowed to be retired by CommitRoom.
ScummV5_LoadRoomWithEgo_FarEntry:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_LoadRoomWithEgo_FarEntry__object_ok
    brl ScummV5_LoadRoomWithEgo_FarEntry__operand_error
ScummV5_LoadRoomWithEgo_FarEntry__object_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_LOAD_EGO_OBJECT
    sep #$20
    .a8
    lda #$40
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcc ScummV5_LoadRoomWithEgo_FarEntry__room_ok
    brl ScummV5_LoadRoomWithEgo_FarEntry__operand_error
ScummV5_LoadRoomWithEgo_FarEntry__room_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_LOAD_EGO_ROOM
    lda #$00
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_LoadRoomWithEgo_FarEntry__x_ok
    brl ScummV5_LoadRoomWithEgo_FarEntry__operand_error
ScummV5_LoadRoomWithEgo_FarEntry__x_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_LOAD_EGO_X
    sep #$20
    .a8
    lda #$00
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_LoadRoomWithEgo_FarEntry__y_ok
    brl ScummV5_LoadRoomWithEgo_FarEntry__operand_error
ScummV5_LoadRoomWithEgo_FarEntry__y_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_LOAD_EGO_Y
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_LOAD_EGO_PC_AFTER
    ; Resolve VAR_EGO through the one generated dense table.  This profile
    ; binding is canonical v5 variable 1; the opcode never assumes actor 1.
    lda.l SAME_SCUMM_VARIABLES+(1 * 2)
    cmp #$0020
    bcc ScummV5_LoadRoomWithEgo_FarEntry__ego_ok
    brl ScummV5_LoadRoomWithEgo_FarEntry__actor_error
ScummV5_LoadRoomWithEgo_FarEntry__ego_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_LOAD_EGO_EGO
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_LOAD_EGO_CALLER_SLOT
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_LOAD_EGO_CALLER_PROGRAM
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_LOAD_EGO_PREVIOUS_ROOM
    lda #$01
    sta.l SAME_SCUMM_LOAD_EGO_ACTIVE
    lda.l SAME_SCUMM_LOAD_EGO_ROOM
    jsl ScummV5_LoadRoomWithEgo_FarCall_RequestRoom
    bcc ScummV5_LoadRoomWithEgo_FarEntry__queued
    lda #$00
    sta.l SAME_SCUMM_LOAD_EGO_ACTIVE
    brl ScummV5_LoadRoomWithEgo_FarEntry__service_error
ScummV5_LoadRoomWithEgo_FarEntry__queued:
    jml ScummV5_Engine_Frame__complete_success
ScummV5_LoadRoomWithEgo_FarEntry__operand_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_PC_RANGE
    bra ScummV5_LoadRoomWithEgo_FarEntry__fail
ScummV5_LoadRoomWithEgo_FarEntry__actor_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_ACTOR_OPS
    bra ScummV5_LoadRoomWithEgo_FarEntry__fail
ScummV5_LoadRoomWithEgo_FarEntry__service_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SERVICE
ScummV5_LoadRoomWithEgo_FarEntry__fail:
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

; The first new-room ENCD yield is startScene's bounded return point.  This
; helper deliberately reads no caller state because room-local callers have
; already been retired.
ScummV5_LoadRoomWithEgo_Postamble_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LOAD_EGO_ACTIVE
    beq ScummV5_LoadRoomWithEgo_Postamble_Far__done
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$02
    bne ScummV5_LoadRoomWithEgo_Postamble_Far__done
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_VARIABLES+(38 * 2)
    lda.l SAME_SCUMM_LOAD_EGO_EGO
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    sta.l SAME_SCUMM_CAMERA_DEST_X
    sep #$20
    .a8
    lda.l SAME_SCUMM_LOAD_EGO_EGO
    sta.l SAME_SCUMM_C15_CAMERA_FOLLOWS
    lda #$01
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    lda #$00
    sta.l SAME_SCUMM_C15_MOVING_TO_ACTOR
    sta.l SAME_SCUMM_LOAD_EGO_ACTIVE
ScummV5_LoadRoomWithEgo_Postamble_Far__done:
    sep #$20
    .a8
    rtl

ScummV5_GetVerbEntrypoint_FarEntry:
    jsl ScummV5_GetActorFacing_FarCall_ReadResult
    bcc ScummV5_GetVerbEntrypoint_FarEntry__result_ok
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_GetVerbEntrypoint_FarEntry__result_ok:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_GetVerbEntrypoint_FarEntry__object_ok
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_GetVerbEntrypoint_FarEntry__object_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_VERB_OBJECT
    sep #$20
    .a8
    lda #$40
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_GetVerbEntrypoint_FarEntry__verb_ok
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_GetVerbEntrypoint_FarEntry__verb_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_VERB_ID
    jsl ScummV5_Verb_Query_Far
    bcs ScummV5_GetVerbEntrypoint_FarEntry__query_ok
    brl ScummV5_ReadOnlyQuery_Far__resource_error
ScummV5_GetVerbEntrypoint_FarEntry__query_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_VERB_RESULT
    jsl ScummV5_GetActorFacing_FarCall_WriteResult
    jml ScummV5_Engine_Frame__next

ScummV5_GetObjectOwner_FarEntry:
    jsl ScummV5_GetActorFacing_FarCall_ReadResult
    bcc ScummV5_GetObjectOwner_FarEntry__result_ok
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_GetObjectOwner_FarEntry__result_ok:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_GetObjectOwner_FarEntry__object_ok
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_GetObjectOwner_FarEntry__object_ok:
    rep #$20
    .a16
    tax
    jsl ScummV5_ObjectOwner_Query_Far
    bcs ScummV5_GetObjectOwner_FarEntry__query_ok
    brl ScummV5_ReadOnlyQuery_Far__argument_error
ScummV5_GetObjectOwner_FarEntry__query_ok:
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_OWNER_RESULT
    jsl ScummV5_GetActorFacing_FarCall_WriteResult
    jml ScummV5_Engine_Frame__next

ScummV5_GetActorX_FarEntry:
    sep #$20
    .a8
    lda #$00
    bra ScummV5_GetActorPosition_FarEntry
ScummV5_GetActorY_FarEntry:
    sep #$20
    .a8
    lda #$02
ScummV5_GetActorPosition_FarEntry:
    sep #$20
    .a8
    sta.l SAME_SCUMM_MOVE_POSITION_AXIS
    jsl ScummV5_GetActorFacing_FarCall_ReadResult
    bcc ScummV5_GetActorPosition_FarEntry__result_ok
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_GetActorPosition_FarEntry__result_ok:
    ; v5 $43/$C3 getActorX and $23/$A3 getActorY share the result destination
    ; followed by a direct-or-variable word object selector.  The high opcode
    ; bit controls the operand form; it is not an instruction-family split.
    jsl ScummV5_Movement_FarCall_FetchVarOrDirectWord
    bcs ScummV5_ReadOnlyQuery_Far__operand_error
    rep #$30
    .a16
    .i16
    and #$FFFF
    beq ScummV5_GetActorPosition_FarEntry__zero
    cmp #$0020
    bcs ScummV5_GetActorPosition_FarEntry__object
    asl
    asl
    sep #$20
    .a8
    clc
    adc.l SAME_SCUMM_MOVE_POSITION_AXIS
    rep #$20
    .a16
    and #$00FF
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    bra ScummV5_GetActorPosition_FarEntry__write
ScummV5_GetActorPosition_FarEntry__object:
    .a16
    cmp.l SAME_SCUMM_MOVE_OBJECT
    beq ScummV5_GetActorPosition_FarEntry__object_cached
    sta.l SAME_SCUMM_MOVE_OBJECT
    jsl ScummV5_Movement_ObjectWalk_Far
    bcc ScummV5_GetActorPosition_FarEntry__missing
ScummV5_GetActorPosition_FarEntry__object_cached:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_POSITION_AXIS
    and #$00FF
    beq ScummV5_GetActorPosition_FarEntry__object_x
    lda.l SAME_SCUMM_MOVE_REQUEST_Y
    bra ScummV5_GetActorPosition_FarEntry__write
ScummV5_GetActorPosition_FarEntry__object_x:
    .a16
    lda.l SAME_SCUMM_MOVE_REQUEST_X
    bra ScummV5_GetActorPosition_FarEntry__write
ScummV5_GetActorPosition_FarEntry__zero:
    .a16
    lda #$0000
    bra ScummV5_GetActorPosition_FarEntry__write
ScummV5_GetActorPosition_FarEntry__missing:
    .a16
    lda #$FFFF
ScummV5_GetActorPosition_FarEntry__write:
    jsl ScummV5_GetActorFacing_FarCall_WriteResult
    rtl

ScummV5_ReadOnlyQuery_Far__operand_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_PC_RANGE
    bra ScummV5_ReadOnlyQuery_Far__error
ScummV5_ReadOnlyQuery_Far__argument_error:
    .a8
    lda #SCUMM_ERR_ARGUMENTS
    bra ScummV5_ReadOnlyQuery_Far__error
ScummV5_ReadOnlyQuery_Far__resource_error:
    .a8
    .if SAME_BUILD_SCUMM_M23B
    lda #$E2
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    .endif
    ; Preserve the exact query that failed.  These scratch words are already
    ; diagnostic-only and are otherwise overwritten by the normal query scan.
    rep #$20
    .a16
    lda.l SAME_SCUMM_VERB_OBJECT
    sta.l SAME_SCUMM_MOVE_TEMP
    lda.l SAME_SCUMM_VERB_ID
    sta.l SAME_SCUMM_MOVE_TEMP2
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
ScummV5_ReadOnlyQuery_Far__error:
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

; Mark an ordinary global/local allocation so a reused object-script slot can
; never retain executable OBCD ownership. Input A is the selected program.
ScummV5_SlotMarkOrdinaryScript_Far:
    sep #$20
    .a8
    pha
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_OBJECT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_OBJECT_NUMBER+1,x
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda.l SAME_SCUMM_CONDITION
    cmp #SCUMM_V5_NUM_GLOBAL_SCRIPTS
    bcc ScummV5_SlotMarkOrdinaryScript_Far__global
    lda #SCUMM_WIO_LOCAL
    bra ScummV5_SlotMarkOrdinaryScript_Far__store
ScummV5_SlotMarkOrdinaryScript_Far__global:
    .a8
    lda #SCUMM_WIO_GLOBAL
ScummV5_SlotMarkOrdinaryScript_Far__store:
    .a8
    sta.l SAME_SCUMM_C4_SLOT_WHERE,x
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    cmp #$01
    bne ScummV5_SlotMarkOrdinaryScript_Far__done
    lda.l SAME_SCUMM_START_OBJECT_OBJECT_RETIRED
    beq ScummV5_SlotMarkOrdinaryScript_Far__done
    pla
    pha
    sta.l SAME_SCUMM_START_OBJECT_LSCR_PROGRAM
    lda #$01
    sta.l SAME_SCUMM_START_OBJECT_LSCR_ENTRY_SEEN
ScummV5_SlotMarkOrdinaryScript_Far__done:
    pla
    rtl

ScummV5_ChainObjectTrace_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_WHERE,x
    cmp #SCUMM_WIO_ROOM
    bne ScummV5_ChainObjectTrace_Far__done
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_START_OBJECT_CHAIN_TARGET
    lda #$01
    sta.l SAME_SCUMM_START_OBJECT_OBJECT_RETIRED
ScummV5_ChainObjectTrace_Far__done:
    clc
    rtl

; Canonical v5 $37/$77/$B7/$F7 startObject. The complete OBCD remains a
; generated room-owned program; this decoder only selects it and initializes
; an ordinary scheduler slot before entering the existing nested interpreter.
ScummV5_StartObject_FarEntry:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_START_OBJECT_PC_BEFORE
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_StartObject_FarEntry__object_ok
    brl ScummV5_StartObject_FarEntry__operand_error
ScummV5_StartObject_FarEntry__object_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_START_OBJECT_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    sep #$20
    .a8
    lda #$40
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcc ScummV5_StartObject_FarEntry__entry_ok
    brl ScummV5_StartObject_FarEntry__operand_error
ScummV5_StartObject_FarEntry__entry_ok:
    .a8
    sta.l SAME_SCUMM_START_OBJECT_ENTRY
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_VERB_ID
    lda #$0000
    ldx #$0000
ScummV5_StartObject_FarEntry__clear_args:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_ARGS,x
    inx
    inx
    cpx #(SAME_SCUMM_LOCAL_COUNT * 2)
    bcc ScummV5_StartObject_FarEntry__clear_args
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_START_OBJECT_ARG_COUNT
ScummV5_StartObject_FarEntry__next_arg:
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcc ScummV5_StartObject_FarEntry__selector_ok
    brl ScummV5_StartObject_FarEntry__operand_error
ScummV5_StartObject_FarEntry__selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_StartObject_FarEntry__args_done
    sta.l SAME_SCUMM_START_OBJECT_SELECTOR
    lda.l SAME_SCUMM_START_OBJECT_ARG_COUNT
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_StartObject_FarEntry__arg_room
    brl ScummV5_StartObject_FarEntry__argument_error
ScummV5_StartObject_FarEntry__arg_room:
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcc ScummV5_StartObject_FarEntry__arg_low_ok
    brl ScummV5_StartObject_FarEntry__operand_error
ScummV5_StartObject_FarEntry__arg_low_ok:
    sta.l SAME_SCUMM_OPERAND
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcc ScummV5_StartObject_FarEntry__arg_high_ok
    brl ScummV5_StartObject_FarEntry__operand_error
ScummV5_StartObject_FarEntry__arg_high_ok:
    .a8
    sta.l SAME_SCUMM_OPERAND+1
    lda.l SAME_SCUMM_START_OBJECT_SELECTOR
    and #$80
    beq ScummV5_StartObject_FarEntry__arg_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsl ScummV5_StartObject_FarCall_ReadVariable
    bcc ScummV5_StartObject_FarEntry__arg_variable_ok
    brl ScummV5_StartObject_FarEntry__operand_error
ScummV5_StartObject_FarEntry__arg_variable_ok:
    sta.l SAME_SCUMM_OPERAND
ScummV5_StartObject_FarEntry__arg_ready:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_START_OBJECT_ARG_COUNT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_ARGS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_START_OBJECT_ARG_COUNT
    inc
    sta.l SAME_SCUMM_START_OBJECT_ARG_COUNT
    bra ScummV5_StartObject_FarEntry__next_arg
ScummV5_StartObject_FarEntry__args_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_ARGS
    sta.l SAME_SCUMM_START_OBJECT_ARG0
    lda.l SAME_SCUMM_C4_ARGS+2
    sta.l SAME_SCUMM_START_OBJECT_ARG1
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_START_OBJECT_PC_AFTER_ARGS
    lda.l SAME_SCUMM_START_OBJECT_OBJECT
    bne ScummV5_StartObject_FarEntry__has_object
    brl ScummV5_StartObject_FarEntry__no_entry
ScummV5_StartObject_FarEntry__has_object:
    .a16
    .i16

    ; Non-recursive canonical start stops an existing object script first.
    ldx #$0001
ScummV5_StartObject_FarEntry__stop_scan:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_StartObject_FarEntry__stop_next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_StartObject_FarEntry__stop_next
    lda.l SAME_SCUMM_C4_SLOT_WHERE,x
    cmp #SCUMM_WIO_ROOM
    bne ScummV5_StartObject_FarEntry__stop_next
    rep #$20
    .a16
    txa
    and #$00FF
    sta.l SAME_SCUMM_MOVE_TEMP
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_OBJECT_NUMBER,x
    cmp.l SAME_SCUMM_START_OBJECT_OBJECT
    beq ScummV5_StartObject_FarEntry__stop_match
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    bra ScummV5_StartObject_FarEntry__stop_next16
ScummV5_StartObject_FarEntry__stop_match:
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    sep #$20
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_StartObject_FarEntry__stop_next
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    bra ScummV5_StartObject_FarEntry__stop_next
ScummV5_StartObject_FarEntry__stop_next16:
    sep #$20
    .a8
ScummV5_StartObject_FarEntry__stop_next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_StartObject_FarEntry__stop_scan

    jsl ScummV5_ObjectProgram_Resolve_Far
    bcs ScummV5_StartObject_FarEntry__resolved
    brl ScummV5_StartObject_FarEntry__no_entry
ScummV5_StartObject_FarEntry__resolved:
    sta.l SAME_SCUMM_START_OBJECT_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_VERB_RESULT
    sta.l SAME_SCUMM_START_OBJECT_ENTRY_OFFSET
    sep #$20
    .a8
    ldx #$0001
ScummV5_StartObject_FarEntry__slot_scan:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_StartObject_FarEntry__slot_found
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_StartObject_FarEntry__slot_found
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_StartObject_FarEntry__slot_scan
    brl ScummV5_StartObject_FarEntry__capacity_error
ScummV5_StartObject_FarEntry__slot_found:
    .a8
    .i16
    txa
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_START_OBJECT_SLOT
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    lda.l SAME_SCUMM_START_OBJECT_PROGRAM
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda #SCUMM_WIO_ROOM
    sta.l SAME_SCUMM_C4_SLOT_WHERE,x
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    rep #$30
    .a16
    .i16
    txa
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_START_OBJECT_OBJECT
    sta.l SAME_SCUMM_C4_SLOT_OBJECT_NUMBER,x
    lda.l SAME_SCUMM_START_OBJECT_ENTRY_OFFSET
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    xba
    lsr
    lsr
    tax
    lda #$0000
    ldy #$0000
ScummV5_StartObject_FarEntry__clear_locals:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    iny
    cpy #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_StartObject_FarEntry__clear_locals
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    rep #$20
    .a16
    and #$00FF
    xba
    lsr
    lsr
    sta.l SAME_SCUMM_RESULT_OFFSET
    ldy #$0000
ScummV5_StartObject_FarEntry__copy_locals:
    .a16
    .i16
    cpy #(SAME_SCUMM_LOCAL_COUNT * 2)
    bcs ScummV5_StartObject_FarEntry__locals_ready
    tya
    tax
    lda.l SAME_SCUMM_C4_ARGS,x
    sta.l SAME_SCUMM_OPERAND
    tya
    clc
    adc.l SAME_SCUMM_RESULT_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    iny
    iny
    bra ScummV5_StartObject_FarEntry__copy_locals
ScummV5_StartObject_FarEntry__locals_ready:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_START_OBJECT_SLOT
    sta.l SAME_SCUMM_SCENARIO_CHILD_SLOT
    lda.l SAME_SCUMM_START_OBJECT_PROGRAM
    sta.l SAME_SCUMM_SCENARIO_CHILD_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_START_OBJECT_ENTRY_OFFSET
    sta.l SAME_SCUMM_SCENARIO_CHILD_PC
    lda.l SAME_SCUMM_START_OBJECT_OBJECT
    sta.l SAME_SCUMM_SCENARIO_CHILD_NUMBER
    sep #$20
    .a8
    lda #SCUMM_WIO_ROOM
    sta.l SAME_SCUMM_SCENARIO_CHILD_WHERE
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_PARENT_SLOT
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_PARENT_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_PARENT_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    sta.l SAME_SCUMM_SCENARIO_NEST_DEPTH
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_START_OBJECT_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_START_OBJECT_EXEC_COUNT
    jml ScummV5_Op_StartScript__run_nested
ScummV5_StartObject_FarEntry__no_entry:
    jml ScummV5_Engine_Frame__next
ScummV5_StartObject_FarEntry__operand_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_PC_RANGE
    bra ScummV5_StartObject_FarEntry__error
ScummV5_StartObject_FarEntry__argument_error:
    .a8
    lda #SCUMM_ERR_ARGUMENTS
    bra ScummV5_StartObject_FarEntry__error
ScummV5_StartObject_FarEntry__capacity_error:
    .a8
    lda #SCUMM_ERR_SLOT_CAPACITY
ScummV5_StartObject_FarEntry__error:
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

; Canonical ScummEngine_v5::o5_getDist and getObjActToObjActDist.  Numeric
; actor IDs are 0..12 for the v5 engine.  Objects resolve through current-room
; walk points or, when inventory-owned, their current-room owner actor.  Only
; actor -> non-actor applies adjustXYToBeInBox, and that projection is a query.
ScummV5_GetDist_FarEntry:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_GET_DIST_PC_BEFORE
    jsl ScummV5_GetActorFacing_FarCall_ReadResult
    bcc ScummV5_GetDist_FarEntry__result_ok
    jmp ScummV5_GetDist_FarEntry__operand_error
ScummV5_GetDist_FarEntry__result_ok:
    lda.l SAME_SCUMM_RESULT_OFFSET
    sta.l SAME_SCUMM_GET_DIST_RESULT_OFFSET
    jsl ScummV5_GetActorFacing_FarCall_ReadValue
    sta.l SAME_SCUMM_GET_DIST_RESULT_BEFORE
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_GetDist_FarEntry__first_ok
    jmp ScummV5_GetDist_FarEntry__operand_error
ScummV5_GetDist_FarEntry__first_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_GET_DIST_OPERAND1
    sep #$20
    .a8
    lda #$40
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_GetDist_FarEntry__second_ok
    jmp ScummV5_GetDist_FarEntry__operand_error
ScummV5_GetDist_FarEntry__second_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_GET_DIST_OPERAND2
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_GET_DIST_PC_AFTER
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_GET_DIST_ADJUSTED

    ; Canonical remote-actor special case: two actors in the same nonzero room
    ; outside the current room have zero logical distance.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_GET_DIST_OPERAND1
    cmp #$000D
    bcs ScummV5_GetDist_FarEntry__resolve_first
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    beq ScummV5_GetDist_FarEntry__resolve_first
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    beq ScummV5_GetDist_FarEntry__resolve_first
    cmp.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_GetDist_FarEntry__resolve_first
    sta.l SAME_SCUMM_GET_DIST_TYPE1
    rep #$20
    .a16
    lda.l SAME_SCUMM_GET_DIST_OPERAND2
    cmp #$000D
    bcs ScummV5_GetDist_FarEntry__resolve_first
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    beq ScummV5_GetDist_FarEntry__resolve_first
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_GET_DIST_TYPE1
    bne ScummV5_GetDist_FarEntry__resolve_first
    rep #$20
    .a16
    lda #$0000
    brl ScummV5_GetDist_FarEntry__write

ScummV5_GetDist_FarEntry__resolve_first:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_GET_DIST_OPERAND1
    ldx #$0000
    jsl ScummV5_GetDist_Resolve_Far
    bcs ScummV5_GetDist_FarEntry__first_resolved
    brl ScummV5_GetDist_FarEntry__unresolved
ScummV5_GetDist_FarEntry__first_resolved:
    sep #$20
    .a8
    sta.l SAME_SCUMM_GET_DIST_TYPE1
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_GET_DIST_OPERAND2
    ldx #$0001
    jsl ScummV5_GetDist_Resolve_Far
    bcs ScummV5_GetDist_FarEntry__second_resolved
    brl ScummV5_GetDist_FarEntry__unresolved
ScummV5_GetDist_FarEntry__second_resolved:
    sep #$20
    .a8
    sta.l SAME_SCUMM_GET_DIST_TYPE2
    rep #$20
    .a16
    lda.l SAME_SCUMM_GET_DIST_ADJUSTED
    and #$00FF
    cmp #$0002
    beq ScummV5_GetDist_FarEntry__second_position_ready
    lda.l SAME_SCUMM_GET_DIST_X2_RAW
    sta.l SAME_SCUMM_GET_DIST_X2
    lda.l SAME_SCUMM_GET_DIST_Y2_RAW
    sta.l SAME_SCUMM_GET_DIST_Y2
ScummV5_GetDist_FarEntry__second_position_ready:
    rep #$20
    .a16

    ; Projection is asymmetric and only depends on the first numeric operand
    ; being an actor and the second numeric operand not being an actor.
    lda.l SAME_SCUMM_GET_DIST_OPERAND1
    cmp #$000D
    bcs ScummV5_GetDist_FarEntry__distance
    lda.l SAME_SCUMM_GET_DIST_OPERAND2
    cmp #$000D
    bcc ScummV5_GetDist_FarEntry__distance
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_DIST_ADJUSTED
    cmp #$02
    bne ScummV5_GetDist_FarEntry__runtime_projection
    lda #$01
    sta.l SAME_SCUMM_GET_DIST_ADJUSTED
    bra ScummV5_GetDist_FarEntry__distance
ScummV5_GetDist_FarEntry__runtime_projection:
    rep #$20
    .a16
    lda.l SAME_SCUMM_GET_DIST_OPERAND1
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    bne ScummV5_GetDist_FarEntry__distance
    rep #$20
    .a16
    lda.l SAME_SCUMM_GET_DIST_X2_RAW
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    lda.l SAME_SCUMM_GET_DIST_Y2_RAW
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    jsl ScummV5_PutActor_Adjust_Far
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    sta.l SAME_SCUMM_GET_DIST_X2
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sta.l SAME_SCUMM_GET_DIST_Y2
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_GET_DIST_ADJUSTED

ScummV5_GetDist_FarEntry__distance:
    rep #$20
    .a16
    lda.l SAME_SCUMM_GET_DIST_X1
    sec
    sbc.l SAME_SCUMM_GET_DIST_X2
    bpl ScummV5_GetDist_FarEntry__dx_positive
    eor #$FFFF
    inc
ScummV5_GetDist_FarEntry__dx_positive:
    rep #$20
    .a16
    sta.l SAME_SCUMM_GET_DIST_DX
    lda.l SAME_SCUMM_GET_DIST_Y1
    sec
    sbc.l SAME_SCUMM_GET_DIST_Y2
    bpl ScummV5_GetDist_FarEntry__dy_positive
    eor #$FFFF
    inc
ScummV5_GetDist_FarEntry__dy_positive:
    sta.l SAME_SCUMM_GET_DIST_DY
    cmp.l SAME_SCUMM_GET_DIST_DX
    bcs ScummV5_GetDist_FarEntry__write
    lda.l SAME_SCUMM_GET_DIST_DX
    bra ScummV5_GetDist_FarEntry__write
ScummV5_GetDist_FarEntry__unresolved:
    rep #$20
    .a16
    lda #$00FF
ScummV5_GetDist_FarEntry__write:
    .a16
    sta.l SAME_SCUMM_GET_DIST_RESULT
    jsl ScummV5_GetActorFacing_FarCall_WriteResult
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_DIST_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_GET_DIST_EXEC_COUNT
    jml ScummV5_Engine_Frame__next
ScummV5_GetDist_FarEntry__operand_error:
    sep #$20
    .a8
    jmp ScummV5_ReadOnlyQuery_Far__operand_error

; Input A=u16 logical actor/object ID, X=destination pair (0=first, 1=second).
; Output A=u8 type (1 actor, 2 object), carry set on success.
ScummV5_GetDist_Resolve_Far:
    rep #$30
    .a16
    .i16
    pha
    txa
    sta.l SAME_SCUMM_MOVE_POSITION_AXIS
    pla
    cmp #$000D
    bcs ScummV5_GetDist_Resolve_Far__object
    sta.l SAME_SCUMM_MOVE_TEMP
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_GetDist_Resolve_Far__actor_present
    brl ScummV5_GetDist_Resolve_Far__fail
ScummV5_GetDist_Resolve_Far__actor_present:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_GetDist_Resolve_Far__actor_current
    brl ScummV5_GetDist_Resolve_Far__fail
ScummV5_GetDist_Resolve_Far__actor_current:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_TEMP
    asl
    asl
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP1
    jsr ScummV5_GetDist_StoreResolved_Far
    sep #$20
    .a8
    lda #$01
    sec
    rtl
ScummV5_GetDist_Resolve_Far__object:
    .a16
    sta.l SAME_SCUMM_MOVE_OBJECT
    tax
    sep #$20
    .a8
    lda #$10
    sta.l SAME_SCUMM_GET_DIST_STAGE
    jsl ScummV5_ObjectOwner_Query_Far
    bcs ScummV5_GetDist_Resolve_Far__owner_found
    brl ScummV5_GetDist_Resolve_Far__fail
ScummV5_GetDist_Resolve_Far__owner_found:
    sep #$20
    .a8
    pha
    lda #$11
    sta.l SAME_SCUMM_GET_DIST_STAGE
    pla
    cmp #$0F
    beq ScummV5_GetDist_Resolve_Far__room_object
    cmp #$0D
    bcc ScummV5_GetDist_Resolve_Far__owner_actor
    brl ScummV5_GetDist_Resolve_Far__fail
ScummV5_GetDist_Resolve_Far__owner_actor:
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_MOVE_TEMP
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_GetDist_Resolve_Far__owner_present
    brl ScummV5_GetDist_Resolve_Far__fail
ScummV5_GetDist_Resolve_Far__owner_present:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_GetDist_Resolve_Far__owner_current
    brl ScummV5_GetDist_Resolve_Far__fail
ScummV5_GetDist_Resolve_Far__owner_current:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_TEMP
    asl
    asl
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP1
    jsr ScummV5_GetDist_StoreResolved_Far
    sep #$20
    .a8
    lda #$02
    sec
    rtl
ScummV5_GetDist_Resolve_Far__room_object:
    sep #$20
    .a8
    lda #$12
    sta.l SAME_SCUMM_GET_DIST_STAGE
    jsl ScummV5_Movement_ObjectWalk_Far
    bcc ScummV5_GetDist_Resolve_Far__fail
    lda #$13
    sta.l SAME_SCUMM_GET_DIST_STAGE
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_MOVE_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP1
    jsr ScummV5_GetDist_StoreResolved_Far
    sep #$20
    .a8
    lda #$14
    sta.l SAME_SCUMM_GET_DIST_STAGE
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_POSITION_AXIS
    beq ScummV5_GetDist_Resolve_Far__room_object_type
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    sta.l SAME_SCUMM_GET_DIST_X2
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sta.l SAME_SCUMM_GET_DIST_Y2
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_GET_DIST_ADJUSTED
ScummV5_GetDist_Resolve_Far__room_object_type:
    sep #$20
    .a8
    lda #$02
    sec
    rtl
ScummV5_GetDist_Resolve_Far__fail:
    sep #$20
    .a8
    clc
    rtl

ScummV5_GetDist_StoreResolved_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_POSITION_AXIS
    bne ScummV5_GetDist_StoreResolved_Far__second
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP0
    sta.l SAME_SCUMM_GET_DIST_X1
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP1
    sta.l SAME_SCUMM_GET_DIST_Y1
    rts
ScummV5_GetDist_StoreResolved_Far__second:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP0
    sta.l SAME_SCUMM_GET_DIST_X2_RAW
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP1
    sta.l SAME_SCUMM_GET_DIST_Y2_RAW
    rts

; Canonical v5 $1E/$3E/$5E/$7E/$9E/$BE/$DE/$FE walkActorTo.  The
; actor is the byte parameter controlled by bit 7; X and Y are complete word
; parameters controlled by bits 6 and 5.  This decoder only produces the
; source-neutral startWalkActor(actor, x, y, -1) request.  Geometry,
; destination installation, routing, and stepping remain shared below.
ScummV5_WalkActorTo_FarEntry:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcc ScummV5_WalkActorTo_FarEntry__actor_fetched
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_WalkActorTo_FarEntry__actor_fetched:
    sep #$20
    .a8
    cmp #$20
    bcc ScummV5_WalkActorTo_FarEntry__actor_valid
    brl ScummV5_ReadOnlyQuery_Far__argument_error
ScummV5_WalkActorTo_FarEntry__actor_valid:
    .a8
    sta.l SAME_SCUMM_MOVE_ACTOR
    lda #$40
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_WalkActorTo_FarEntry__x_fetched
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_WalkActorTo_FarEntry__x_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sep #$20
    .a8
    lda #$20
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_WalkActorTo_FarEntry__y_fetched
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_WalkActorTo_FarEntry__y_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    ; Canonical v5 walkActorTo preserves the actor's ignore-boxes policy.
    ; Such actors use a direct final leg; routing their request through the
    ; room BOXM graph can leave an authored waitForActor permanently active
    ; when the actor begins on a non-routable presentation box.
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$30
    .a16
    .i16
    and #$00FF
    xba
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    beq ScummV5_WalkActorTo_FarEntry__follow_boxes
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    lda.l SAME_SCUMM_MOVE_ACTOR
    tax
    lda #$FF
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    bra ScummV5_WalkActorTo_FarEntry__normalized
ScummV5_WalkActorTo_FarEntry__follow_boxes:
    jsl ScummV5_PutActor_Adjust_Far
ScummV5_WalkActorTo_FarEntry__normalized:
    sep #$20
    .a8
    lda #$FF                        ; canonical no-final-direction sentinel
    sta.l SAME_SCUMM_MOVE_QUERY_DIR
    jsr ScummV5_Movement_StartNormalized_Far
    jml ScummV5_Engine_Frame__next

ScummV5_WalkActorToObject_FarEntry:
    sep #$20
    .a8
    lda #$01
    sta.l $7E5700
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcc ScummV5_WalkActorToObject_FarEntry__actor_fetched
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_WalkActorToObject_FarEntry__actor_fetched:
    sep #$20
    .a8
    cmp #$20
    bcc ScummV5_WalkActorToObject_FarEntry__actor_valid
    brl ScummV5_ReadOnlyQuery_Far__argument_error
ScummV5_WalkActorToObject_FarEntry__actor_valid:
    sep #$20
    .a8
    sta.l SAME_SCUMM_MOVE_ACTOR
    sta.l $7E5701
    lda #$40
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    bcc ScummV5_WalkActorToObject_FarEntry__object_fetched
    brl ScummV5_ReadOnlyQuery_Far__operand_error
ScummV5_WalkActorToObject_FarEntry__object_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_MOVE_OBJECT
    sta.l $7E5702 ; prelookup object when no movement starts
    lda.l SAME_SCUMM_MOVE_ACTOR
    sta.l $7E5704
    jsl ScummV5_Movement_ObjectWalk_Far
    bcc ScummV5_WalkActorToObject_FarEntry__absent
    lda #$01
    sta.l $7E5705
    bra ScummV5_WalkActorToObject_FarEntry__start
ScummV5_WalkActorToObject_FarEntry__start:
    ; The room cooker derives the canonical normalized object destination from
    ; the complete BOXD geometry and retains it beside the raw walk point. The
    ; bounded route does not touch either mutable box (12/20), so this avoids a
    ; long synchronous geometry scan without changing this source-defined walk.
    jsr ScummV5_Movement_StartNormalized_Far
    jml ScummV5_Engine_Frame__next
ScummV5_WalkActorToObject_FarEntry__absent:
    ; Canonical walkActorToObject is a no-op when the object is not in scope.
    jml ScummV5_Engine_Frame__next

; Install a validated, normalized destination into the one canonical movement
; state machine.  Inputs are MOVE_ACTOR, PUT_ACTOR_RESULT_{X,Y,BOX}, and the
; old-direction byte (or $FF) in MOVE_QUERY_DIR.
ScummV5_Movement_StartNormalized_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M25_MOVE_START_COUNT
    inc
    sta.l SAME_SCUMM_M25_MOVE_START_COUNT
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_M25_MOVE_START_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M25_MOVE_START_PROGRAM
    lda.l SAME_SCUMM_MOVE_ACTOR
    sta.l SAME_SCUMM_M25_MOVE_START_ACTOR
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_QUERY_DIR
    sta.l SAME_SCUMM_MOVE_FINAL_OLD_DIR,x
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x
    lda.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    sta.l SAME_SCUMM_MOVE_CURRENT_BOX,x
    lda #$01
    sta.l SAME_SCUMM_C31_MOVING,x
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    sta.l SAME_SCUMM_PUT_ACTOR_DEST_X,x
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sta.l SAME_SCUMM_MOVE_DEST_Y,x
    rts

; Advance every active actor exactly once after the production scheduler pass.
; The state machine is the bounded v5 BOXM/shared-edge/16.16 walker exercised
; by the authentic room-49 object route; it remains actor/room/object neutral.
ScummV5_Movement_UpdateAll_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_TICK
    inc
    sta.l SAME_SCUMM_MOVE_TICK
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_MOVE_ACTOR
ScummV5_Movement_UpdateAll_Far__loop:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    cpx #$0001
    bne ScummV5_Movement_UpdateAll_Far__eligibility_probe_done
    lda #$20
    jsr ScummV5_Movement_TracePositionEvent
ScummV5_Movement_UpdateAll_Far__eligibility_probe_done:
    lda.l SAME_SCUMM_C31_MOVING,x
    beq ScummV5_Movement_UpdateAll_Far__next
    ; Authentic setup can retain legacy movement bits without a route record.
    ; The canonical startWalkActor path is the sole owner that replaces the
    ; inactive $FFFF destination sentinel.
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_DEST_X,x
    cmp #$FFFF
    sep #$20
    .a8
    beq ScummV5_Movement_UpdateAll_Far__next
ScummV5_Movement_UpdateAll_Far__update:
    jsr ScummV5_Movement_UpdateActor_Far
    bcs ScummV5_Movement_UpdateAll_Far__error
ScummV5_Movement_UpdateAll_Far__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    inc
    sta.l SAME_SCUMM_MOVE_ACTOR
    cmp #$20
    bcc ScummV5_Movement_UpdateAll_Far__loop
    clc
    rtl
ScummV5_Movement_UpdateAll_Far__error:
    sec
    rtl

ScummV5_Movement_UpdateActor_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    phx
    lda.l SAME_SCUMM_MOVE_ACTOR
    cmp #$01
    bne ScummV5_Movement_UpdateActor_Far__entry_probe_done
    lda #$10
    jsr ScummV5_Movement_TracePositionEvent
    lda.l $7E5015
    sta.l $7E502A
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    sta.l $7E502C
    sep #$20
    .a8
    lda.l $7E5016
    inc
    sta.l $7E5016
    lda.l SAME_SCUMM_MOVE_TICK
    sta.l $7E5018
    lda.l SAME_SCUMM_C31_MOVING,x
    sta.l $7E501A
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l $7E501C
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    sta.l $7E501E
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sta.l $7E5020
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sta.l $7E5022
    sep #$20
    .a8
ScummV5_Movement_UpdateActor_Far__entry_probe_done:
    sep #$20
    .a8
    plx
    lda.l SAME_SCUMM_C31_MOVING,x
    and #$01
    bne ScummV5_Movement_UpdateActor_Far__new_leg
    lda.l SAME_SCUMM_C31_MOVING,x
    and #$02
    beq ScummV5_Movement_UpdateActor_Far__after_step
    jsr ScummV5_Movement_WalkStep_Far
    bcc ScummV5_Movement_UpdateActor_Far__after_step
    brl ScummV5_Movement_UpdateActor_Far__done
ScummV5_Movement_UpdateActor_Far__after_step:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    and #$08
    beq ScummV5_Movement_UpdateActor_Far__not_last
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
    lda.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    lda.l SAME_SCUMM_MOVE_FINAL_OLD_DIR,x
    cmp #$FF
    beq ScummV5_Movement_UpdateActor_Far__finish_no_turn
    jsr ScummV5_Movement_OldToNewDir_Far
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_MOVE_TEMP
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_MOVE_TEMP
    sta.l SAME_SCUMM_ACTOR_FACINGS,x
ScummV5_Movement_UpdateActor_Far__finish_no_turn:
    clc
    rts
ScummV5_Movement_UpdateActor_Far__not_last:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_CURRENT_BOX,x
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
    bra ScummV5_Movement_UpdateActor_Far__plan
ScummV5_Movement_UpdateActor_Far__new_leg:
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    and #$FE
    sta.l SAME_SCUMM_C31_MOVING,x
ScummV5_Movement_UpdateActor_Far__plan:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    cmp.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x
    bne ScummV5_Movement_UpdateActor_Far__route_leg
    brl ScummV5_Movement_UpdateActor_Far__final_leg
ScummV5_Movement_UpdateActor_Far__route_leg:
    sta.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    lda.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_MOVE_ROUTE_DEST
    jsl ScummV5_Movement_NextBox_Far
    bcs ScummV5_Movement_UpdateActor_Far__route_found
    brl ScummV5_Movement_UpdateActor_Far__route_error
ScummV5_Movement_UpdateActor_Far__route_found:
    sta.l SAME_SCUMM_MOVE_ROUTE_NEXT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ROUTE_NEXT
    sta.l SAME_SCUMM_MOVE_CURRENT_BOX,x
    jsl ScummV5_Movement_Portal_Far
    bcs ScummV5_Movement_UpdateActor_Far__portal_found
    brl ScummV5_Movement_UpdateActor_Far__route_error
ScummV5_Movement_UpdateActor_Far__portal_found:
    ; Clamp the current coordinate to the source-bound shared portal interval.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    sta.l SAME_SCUMM_MOVE_TEMP
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_PORTAL_TYPE
    cmp #$01
    beq ScummV5_Movement_UpdateActor_Far__vertical
    ; Horizontal portal: fixed Y and clamped current X.
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_PORTAL_FIXED
    sta.l SAME_SCUMM_MOVE_GATE_Y
    lda.l SAME_SCUMM_C31_POSITIONS,x
    bra ScummV5_Movement_UpdateActor_Far__clamp
ScummV5_Movement_UpdateActor_Far__vertical:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_PORTAL_FIXED
    sta.l SAME_SCUMM_MOVE_GATE_X
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
ScummV5_Movement_UpdateActor_Far__clamp:
    .a16
    eor #$8000
    sta.l SAME_SCUMM_MOVE_TEMP2
    lda.l SAME_SCUMM_MOVE_PORTAL_LOW
    eor #$8000
    cmp.l SAME_SCUMM_MOVE_TEMP2
    bcc ScummV5_Movement_UpdateActor_Far__above_low
    beq ScummV5_Movement_UpdateActor_Far__above_low
    lda.l SAME_SCUMM_MOVE_PORTAL_LOW
    bra ScummV5_Movement_UpdateActor_Far__clamped
ScummV5_Movement_UpdateActor_Far__above_low:
    .a16
    lda.l SAME_SCUMM_MOVE_PORTAL_HIGH
    eor #$8000
    cmp.l SAME_SCUMM_MOVE_TEMP2
    bcc ScummV5_Movement_UpdateActor_Far__use_high
    beq ScummV5_Movement_UpdateActor_Far__use_high
    lda.l SAME_SCUMM_MOVE_TEMP2
    eor #$8000
    bra ScummV5_Movement_UpdateActor_Far__clamped
ScummV5_Movement_UpdateActor_Far__use_high:
    lda.l SAME_SCUMM_MOVE_PORTAL_HIGH
ScummV5_Movement_UpdateActor_Far__clamped:
    sta.l SAME_SCUMM_MOVE_TEMP2
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_PORTAL_TYPE
    cmp #$01
    beq ScummV5_Movement_UpdateActor_Far__vertical_value
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_TEMP2
    sta.l SAME_SCUMM_MOVE_GATE_X
    bra ScummV5_Movement_UpdateActor_Far__calc
ScummV5_Movement_UpdateActor_Far__vertical_value:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_TEMP2
    sta.l SAME_SCUMM_MOVE_GATE_Y
ScummV5_Movement_UpdateActor_Far__calc:
    jsr ScummV5_Movement_CalcFactor_Far
    bcs ScummV5_Movement_UpdateActor_Far__done
    ; A zero-length/one-step portal is consumed in this same movement tick.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_CURRENT_BOX,x
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    brl ScummV5_Movement_UpdateActor_Far__plan
ScummV5_Movement_UpdateActor_Far__final_leg:
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    ora #$08
    sta.l SAME_SCUMM_C31_MOVING,x
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    sta.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_DEST_X,x
    sta.l SAME_SCUMM_MOVE_GATE_X
    lda.l SAME_SCUMM_MOVE_DEST_Y,x
    sta.l SAME_SCUMM_MOVE_GATE_Y
    jsr ScummV5_Movement_CalcFactor_Far
ScummV5_Movement_UpdateActor_Far__done:
    clc
    rts
ScummV5_Movement_UpdateActor_Far__route_error:
    sep #$20
    .a8
    ; A route can be invalidated while a script is suspended (room/object
    ; teardown, or a completed final leg).  Retire that stale continuation;
    ; it is not a VM resource failure and must not abort the owning script.
    lda.l SAME_SCUMM_MOVE_ACTOR
    tax
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
    lda #$FF
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x
    clc
    rts

; Establish one canonical 16.16 leg and perform its first actor step.
ScummV5_Movement_CalcFactor_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    sta.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_GATE_X
    sta.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    lda.l SAME_SCUMM_MOVE_GATE_Y
    sta.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    asl
    sta.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l SAME_SCUMM_C18_LHS_LO            ; current X scratch
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    sta.l SAME_SCUMM_C18_LHS_HI            ; current Y scratch
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_MOVE_LEG_ORIGIN_X,x
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sec
    sbc.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_RHS_LO            ; diff X
    lda.l SAME_SCUMM_C18_LHS_HI
    sta.l SAME_SCUMM_MOVE_LEG_ORIGIN_Y,x
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sec
    sbc.l SAME_SCUMM_C18_LHS_HI
    sta.l SAME_SCUMM_C18_REMAINDER_LO      ; diff Y scratch
    lda #$0000
    sta.l SAME_SCUMM_MOVE_FRACTION_X,x
    sta.l SAME_SCUMM_MOVE_FRACTION_Y,x
    ; Equal target: no active leg.
    lda.l SAME_SCUMM_C18_RHS_LO
    ora.l SAME_SCUMM_C18_REMAINDER_LO
    bne ScummV5_Movement_CalcFactor_Far__nonzero
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    and #$FD
    sta.l SAME_SCUMM_C31_MOVING,x
    clc
    rts
ScummV5_Movement_CalcFactor_Far__nonzero:
    ; Fetch actor speed record (actor * 64) and form signed speedY << 16.
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$20
    .a16
    and #$00FF
    xba
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_Y,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C18_LHS_HI
    lda #$0000
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    bpl ScummV5_Movement_CalcFactor_Far__dy_sign_ready
    lda.l SAME_SCUMM_C18_LHS_HI
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_C18_LHS_HI
ScummV5_Movement_CalcFactor_Far__dy_sign_ready:
    .a16
    ; Multiply deltaY by signed diffX.
    lda.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C18_RHS_LO
    bpl ScummV5_Movement_CalcFactor_Far__dx_extend_positive
    lda #$FFFF
    bra ScummV5_Movement_CalcFactor_Far__dx_extended
ScummV5_Movement_CalcFactor_Far__dx_extend_positive:
    .a16
    lda #$0000
ScummV5_Movement_CalcFactor_Far__dx_extended:
    .a16
    sta.l SAME_SCUMM_C18_RHS_HI
    jsl ScummV5_Movement_FarCall_Multiply
    ; Divide by diffY when nonzero; otherwise retain product and zero deltaY.
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    beq ScummV5_Movement_CalcFactor_Far__horizontal
    sta.l SAME_SCUMM_C18_RHS_LO
    bpl ScummV5_Movement_CalcFactor_Far__divisor_positive
    lda #$FFFF
    bra ScummV5_Movement_CalcFactor_Far__divisor_extended
ScummV5_Movement_CalcFactor_Far__divisor_positive:
    .a16
    lda #$0000
ScummV5_Movement_CalcFactor_Far__divisor_extended:
    .a16
    sta.l SAME_SCUMM_C18_RHS_HI
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_LHS_HI
    jsl ScummV5_Movement_FarCall_Divide
    bcc ScummV5_Movement_CalcFactor_Far__divide_ok
    brl ScummV5_Movement_CalcFactor_Far__math_error
ScummV5_Movement_CalcFactor_Far__divide_ok:
    bra ScummV5_Movement_CalcFactor_Far__delta_x_ready
ScummV5_Movement_CalcFactor_Far__horizontal:
    ; The multiply above already produced delta-X for a horizontal leg.
    ; Keep that product; only delta-Y is zeroed below when the signed
    ; direction is reconstructed.  Clearing this scratch here loses the
    ; horizontal velocity and leaves the actor forever active at the portal.
    .a16
ScummV5_Movement_CalcFactor_Far__delta_x_ready:
    ; Preserve candidate deltaX; reconstruct deltaY from signed speedY.
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$20
    .a16
    and #$00FF
    xba
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_X,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_MOVE_TEMP2
    lda.l SAME_SCUMM_C18_RESULT_HI
    bpl ScummV5_Movement_CalcFactor_Far__abs_dx
    eor #$FFFF
    inc
ScummV5_Movement_CalcFactor_Far__abs_dx:
    .a16
    and #$FFFF
    cmp.l SAME_SCUMM_MOVE_TEMP2
    bcs ScummV5_Movement_CalcFactor_Far__check_equal_speed
    brl ScummV5_Movement_CalcFactor_Far__store_delta
ScummV5_Movement_CalcFactor_Far__check_equal_speed:
    bne ScummV5_Movement_CalcFactor_Far__clamp_speed
    brl ScummV5_Movement_CalcFactor_Far__store_delta
ScummV5_Movement_CalcFactor_Far__clamp_speed:
    .a16
    ; Clamp X to speedX and derive Y = deltaX * diffY / diffX.
    lda.l SAME_SCUMM_MOVE_TEMP2
    sta.l SAME_SCUMM_C18_LHS_HI
    lda #$0000
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sec
    sbc.l SAME_SCUMM_MOVE_LEG_ORIGIN_X,x
    bpl ScummV5_Movement_CalcFactor_Far__clamp_sign_ready
    lda.l SAME_SCUMM_C18_LHS_HI
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_C18_LHS_HI
ScummV5_Movement_CalcFactor_Far__clamp_sign_ready:
    lda.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    ; Save clamped X in movement arrays before math scratch is reused.
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_MOVE_DELTA_X_LO,x
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_MOVE_DELTA_X_HI,x
    ; product clamped deltaX * diffY
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sec
    sbc.l SAME_SCUMM_MOVE_LEG_ORIGIN_Y,x
    sta.l SAME_SCUMM_C18_RHS_LO
    bpl ScummV5_Movement_CalcFactor_Far__dy_extend_positive
    lda #$FFFF
    bra ScummV5_Movement_CalcFactor_Far__dy_extended
ScummV5_Movement_CalcFactor_Far__dy_extend_positive:
    .a16
    lda #$0000
ScummV5_Movement_CalcFactor_Far__dy_extended:
    sta.l SAME_SCUMM_C18_RHS_HI
    jsl ScummV5_Movement_FarCall_Multiply
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_LHS_HI
    lda.l SAME_SCUMM_C18_RHS_LO            ; diffX was destroyed: restore below
    ; Original diffX is gateX-originX.
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sec
    sbc.l SAME_SCUMM_MOVE_LEG_ORIGIN_X,x
    sta.l SAME_SCUMM_C18_RHS_LO
    bpl ScummV5_Movement_CalcFactor_Far__dx_div_positive
    lda #$FFFF
    bra ScummV5_Movement_CalcFactor_Far__dx_div_extended
ScummV5_Movement_CalcFactor_Far__dx_div_positive:
    .a16
    lda #$0000
ScummV5_Movement_CalcFactor_Far__dx_div_extended:
    .a16
    sta.l SAME_SCUMM_C18_RHS_HI
    jsl ScummV5_Movement_FarCall_Divide
    bcc ScummV5_Movement_CalcFactor_Far__clamp_divide_ok
    brl ScummV5_Movement_CalcFactor_Far__math_error
ScummV5_Movement_CalcFactor_Far__clamp_divide_ok:
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_MOVE_DELTA_Y_LO,x
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    bra ScummV5_Movement_CalcFactor_Far__facing
ScummV5_Movement_CalcFactor_Far__store_delta:
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_MOVE_DELTA_X_LO,x
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_MOVE_DELTA_X_HI,x
    ; Signed speedY << 16, or zero for a horizontal leg.
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sec
    sbc.l SAME_SCUMM_MOVE_LEG_ORIGIN_Y,x
    beq ScummV5_Movement_CalcFactor_Far__zero_y
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$20
    .a16
    and #$00FF
    xba
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_Y,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    lda #$0000
    sta.l SAME_SCUMM_MOVE_DELTA_Y_LO,x
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    bpl ScummV5_Movement_CalcFactor_Far__facing
    lda.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    bra ScummV5_Movement_CalcFactor_Far__facing
ScummV5_Movement_CalcFactor_Far__zero_y:
    .a16
    lda #$0000
    sta.l SAME_SCUMM_MOVE_DELTA_Y_LO,x
    sta.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
ScummV5_Movement_CalcFactor_Far__facing:
    .a16
    ; Canonical direction test: abs(diffY)*3 > abs(diffX).
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sec
    sbc.l SAME_SCUMM_MOVE_LEG_ORIGIN_X,x
    bpl ScummV5_Movement_CalcFactor_Far__facing_abs_x
    eor #$FFFF
    inc
ScummV5_Movement_CalcFactor_Far__facing_abs_x:
    .a16
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sec
    sbc.l SAME_SCUMM_MOVE_LEG_ORIGIN_Y,x
    bpl ScummV5_Movement_CalcFactor_Far__facing_abs_y
    eor #$FFFF
    inc
ScummV5_Movement_CalcFactor_Far__facing_abs_y:
    .a16
    sta.l SAME_SCUMM_C18_RHS_LO
    asl
    clc
    adc.l SAME_SCUMM_C18_RHS_LO
    cmp.l SAME_SCUMM_C18_LHS_LO
    bcc ScummV5_Movement_CalcFactor_Far__horizontal_facing
    beq ScummV5_Movement_CalcFactor_Far__horizontal_facing
    lda.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    bmi ScummV5_Movement_CalcFactor_Far__face_zero
    lda #$00B4
    bra ScummV5_Movement_CalcFactor_Far__store_facing
ScummV5_Movement_CalcFactor_Far__face_zero:
    .a16
    lda #$0000
    bra ScummV5_Movement_CalcFactor_Far__store_facing
ScummV5_Movement_CalcFactor_Far__horizontal_facing:
    .a16
    lda.l SAME_SCUMM_MOVE_DELTA_X_HI,x
    bmi ScummV5_Movement_CalcFactor_Far__face_270
    lda #$005A
    bra ScummV5_Movement_CalcFactor_Far__store_facing
ScummV5_Movement_CalcFactor_Far__face_270:
    .a16
    lda #$010E
ScummV5_Movement_CalcFactor_Far__store_facing:
    .a16
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_ACTOR_FACINGS,x
    jsr ScummV5_Movement_WalkStep_Far
    rts
ScummV5_Movement_CalcFactor_Far__math_error:
    sec
    rts

; Validator-only post-commit ordering trace. Each record is type,
; PutActor-X count, X, movement tick, update count, pad.
ScummV5_Movement_TracePositionEvent:
    php
    sta.l $7E54FE
    phx
    phy
    rep #$30
    .a16
    .i16
    lda.l $7E54FF
    and #$000F
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l $7E54FE
    sta.l $7E5500,x
    lda.l $7E5015
    sta.l $7E5501,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    sta.l $7E5502,x
    lda.l SAME_SCUMM_MOVE_TICK
    sta.l $7E5504,x
    sep #$20
    .a8
    lda.l $7E5016
    sta.l $7E5506,x
    lda #$00
    sta.l $7E5507,x
    lda.l SAME_SCUMM_C31_MOVING+1
    sta.l $7E5507,x
    lda.l $7E54FF
    inc
    and #$0F
    sta.l $7E54FF
    ply
    plx
    plp
    rts

; One canonical 16.16 step.  Carry set means the leg remains active.
ScummV5_Movement_WalkStep_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M25_MOVE_STEP_COUNT
    inc
    sta.l SAME_SCUMM_M25_MOVE_STEP_COUNT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l SAME_SCUMM_M25_MOVE_STEP_PRE_X
    sta.l $7E500E
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    sta.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    asl
    sta.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C18_RHS_LO
    cmp.l SAME_SCUMM_C31_POSITIONS,x
    bne ScummV5_Movement_WalkStep_Far__move
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    cmp.l SAME_SCUMM_C31_POSITIONS+2,x
    bne ScummV5_Movement_WalkStep_Far__move
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    and #$FD
    sta.l SAME_SCUMM_C31_MOVING,x
    clc
    rts
ScummV5_Movement_WalkStep_Far__move:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    ora #$02
    sta.l SAME_SCUMM_C31_MOVING,x
    ; X: arithmetic (delta >> 8) * scale + position.16 + fraction.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_DELTA_X_LO,x
    xba
    and #$00FF
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_MOVE_DELTA_X_HI,x
    xba
    and #$FF00
    ora.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_MOVE_DELTA_X_HI,x
    bmi ScummV5_Movement_WalkStep_Far__x_shift_negative
    lda #$0000
    bra ScummV5_Movement_WalkStep_Far__x_shift_high
ScummV5_Movement_WalkStep_Far__x_shift_negative:
    .a16
    lda #$FFFF
ScummV5_Movement_WalkStep_Far__x_shift_high:
    sta.l SAME_SCUMM_C18_LHS_HI
    jsr ScummV5_Movement_LoadScaleX_Far
    jsl ScummV5_Movement_FarCall_Multiply
    ; Validator-only arithmetic evidence: retain the X product before the
    ; Y calculation reuses the C18 result registers.
    phx
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    cmp #$01
    bne ScummV5_Movement_WalkStep_Far__product_no_probe
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l $7E5004
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l $7E5006
ScummV5_Movement_WalkStep_Far__product_no_probe:
    plx
    ; The actor probe above is byte-oriented and leaves M=8 on both the
    ; taken and not-taken paths.  Re-establish the word ABI before the
    ; fixed-point fraction/position arithmetic; otherwise a 16-bit X
    ; coordinate crossing $00FF stores only its low byte and never reaches
    ; the authored portal target.
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    clc
    adc.l SAME_SCUMM_MOVE_FRACTION_X,x
    sta.l SAME_SCUMM_MOVE_FRACTION_X,x
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l $7E5010
    adc.l SAME_SCUMM_C31_POSITIONS,x
    sta.l $7E5012
    sta.l SAME_SCUMM_C31_POSITIONS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    cmp #$01
    bne ScummV5_Movement_WalkStep_Far__x_write_probe_done
    lda.l $7E5024
    inc
    sta.l $7E5024
    lda.l SAME_SCUMM_MOVE_TICK
    sta.l $7E5026
    lda #$01
    sta.l $7E5028
ScummV5_Movement_WalkStep_Far__x_write_probe_done:
    rep #$20
    .a16
    sep #$20
    .a8
    lda #$01
    sta.l $7E5014
    lda #$01
    jsr ScummV5_Movement_TracePositionEvent
    rep #$20
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    cmp #$01
    bne ScummV5_Movement_WalkStep_Far__x_probe_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l $7E500C
ScummV5_Movement_WalkStep_Far__x_probe_done:
    rep #$20
    .a16
    ; Y equivalent.
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_DELTA_Y_LO,x
    xba
    and #$00FF
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    xba
    and #$FF00
    ora.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    bmi ScummV5_Movement_WalkStep_Far__y_shift_negative
    lda #$0000
    bra ScummV5_Movement_WalkStep_Far__y_shift_high
ScummV5_Movement_WalkStep_Far__y_shift_negative:
    .a16
    lda #$FFFF
ScummV5_Movement_WalkStep_Far__y_shift_high:
    sta.l SAME_SCUMM_C18_LHS_HI
    jsr ScummV5_Movement_LoadScaleY_Far
    jsl ScummV5_Movement_FarCall_Multiply
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    clc
    adc.l SAME_SCUMM_MOVE_FRACTION_Y,x
    sta.l SAME_SCUMM_MOVE_FRACTION_Y,x
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C18_RESULT_HI
    adc.l SAME_SCUMM_C31_POSITIONS+2,x
    sta.l SAME_SCUMM_C31_POSITIONS+2,x
    ; Clamp each coordinate after passing its signed target.
    jsr ScummV5_Movement_ClampPosition_Far
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C18_RHS_LO
    cmp.l SAME_SCUMM_C31_POSITIONS,x
    bne ScummV5_Movement_WalkStep_Far__active
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    cmp.l SAME_SCUMM_C31_POSITIONS+2,x
    bne ScummV5_Movement_WalkStep_Far__active
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    and #$FD
    sta.l SAME_SCUMM_C31_MOVING,x
    clc
    rts
ScummV5_Movement_WalkStep_Far__active:
    ; Keep the last committed actor-1 coordinate for the movement probe.
    ; This is observation only and does not participate in walking decisions.
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    cmp #$01
    bne ScummV5_Movement_WalkStep_Far__active_no_probe
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l $7E5008
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    sta.l $7E500A
ScummV5_Movement_WalkStep_Far__active_no_probe:
    sec
    rts

ScummV5_Movement_LoadScaleX_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$20
    .a16
    and #$00FF
    xba
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_X,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C18_RHS_LO
    lda #$0000
    sta.l SAME_SCUMM_C18_RHS_HI
    rts
ScummV5_Movement_LoadScaleY_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ACTOR
    rep #$20
    .a16
    and #$00FF
    xba
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_Y,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C18_RHS_LO
    lda #$0000
    sta.l SAME_SCUMM_C18_RHS_HI
    rts

ScummV5_Movement_ClampPosition_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_X,x
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_MOVE_DELTA_X_HI,x
    bmi ScummV5_Movement_ClampPosition_Far__x_negative
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    eor #$8000
    sta.l SAME_SCUMM_MOVE_TEMP2
    lda.l SAME_SCUMM_C18_RHS_LO
    eor #$8000
    cmp.l SAME_SCUMM_MOVE_TEMP2
    bcc ScummV5_Movement_ClampPosition_Far__x_set
    beq ScummV5_Movement_ClampPosition_Far__x_set
    bra ScummV5_Movement_ClampPosition_Far__x_done
ScummV5_Movement_ClampPosition_Far__x_negative:
    .a16
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    eor #$8000
    sta.l SAME_SCUMM_MOVE_TEMP2
    lda.l SAME_SCUMM_C18_RHS_LO
    eor #$8000
    cmp.l SAME_SCUMM_MOVE_TEMP2
    bcs ScummV5_Movement_ClampPosition_Far__x_set
    bra ScummV5_Movement_ClampPosition_Far__x_done
ScummV5_Movement_ClampPosition_Far__x_set:
    .a16
    lda.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C31_POSITIONS,x
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda #$0000
    sta.l SAME_SCUMM_MOVE_FRACTION_X,x
ScummV5_Movement_ClampPosition_Far__x_done:
    .a16
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda.l SAME_SCUMM_MOVE_LEG_TARGET_Y,x
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    lda.l SAME_SCUMM_MOVE_DELTA_Y_HI,x
    bmi ScummV5_Movement_ClampPosition_Far__y_negative
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    eor #$8000
    sta.l SAME_SCUMM_MOVE_TEMP2
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    eor #$8000
    cmp.l SAME_SCUMM_MOVE_TEMP2
    bcc ScummV5_Movement_ClampPosition_Far__y_set
    beq ScummV5_Movement_ClampPosition_Far__y_set
    bra ScummV5_Movement_ClampPosition_Far__done
ScummV5_Movement_ClampPosition_Far__y_negative:
    .a16
    lda.l SAME_SCUMM_MOVE_POSITION_OFFSET
    tax
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    eor #$8000
    sta.l SAME_SCUMM_MOVE_TEMP2
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    eor #$8000
    cmp.l SAME_SCUMM_MOVE_TEMP2
    bcs ScummV5_Movement_ClampPosition_Far__y_set
    bra ScummV5_Movement_ClampPosition_Far__done
ScummV5_Movement_ClampPosition_Far__y_set:
    .a16
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    sta.l SAME_SCUMM_C31_POSITIONS+2,x
    lda.l SAME_SCUMM_MOVE_TEMP
    tax
    lda #$0000
    sta.l SAME_SCUMM_MOVE_FRACTION_Y,x
ScummV5_Movement_ClampPosition_Far__done:
    rts

ScummV5_Movement_OldToNewDir_Far:
    ; ABI: accepts the old direction with either M width and returns its
    ; canonical 16-bit direction in A with M=16.  It deliberately does not
    ; preserve P: callers consume a word result (UpdateActor immediately
    ; establishes REP #$30 before storing it).  Establish the word contract
    ; in the emitted instruction stream before using word immediates;
    ; assembler width annotations alone do not change the 65816 M flag.
    rep #$20
    .a16
    and #$03
    cmp #$00
    beq ScummV5_Movement_OldToNewDir_Far__west
    cmp #$01
    beq ScummV5_Movement_OldToNewDir_Far__east
    cmp #$02
    beq ScummV5_Movement_OldToNewDir_Far__south
    lda #$0000
    rts
ScummV5_Movement_OldToNewDir_Far__west:
    .a16
    lda #$010E
    rts
ScummV5_Movement_OldToNewDir_Far__east:
    .a16
    lda #$005A
    rts
ScummV5_Movement_OldToNewDir_Far__south:
    .a16
    lda #$00B4
    rts

; Canonical ScummEngine_v5::o5_getActorWalkBox: return the actor's existing
; field. No room, geometry, movement, scale, or path state is consulted.
ScummV5_GetActorWalkbox_FarEntry:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_GET_WALKBOX_PC_BEFORE
    jsl ScummV5_GetActorFacing_FarCall_ReadResult
    bcc ScummV5_GetActorWalkbox_FarEntry__result_ok
    jmp ScummV5_GetActorWalkbox_FarEntry__operand_error16
ScummV5_GetActorWalkbox_FarEntry__result_ok:
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    sta.l SAME_SCUMM_GET_WALKBOX_RESULT_OFFSET
    jsl ScummV5_GetActorFacing_FarCall_ReadValue
    sta.l SAME_SCUMM_GET_WALKBOX_RESULT_BEFORE
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcc ScummV5_GetActorWalkbox_FarEntry__actor_fetched
    jmp ScummV5_GetActorWalkbox_FarEntry__operand_error
ScummV5_GetActorWalkbox_FarEntry__actor_fetched:
    .a8
    cmp #$20
    bcc ScummV5_GetActorWalkbox_FarEntry__actor_valid
    jmp ScummV5_GetActorWalkbox_FarEntry__argument_error
ScummV5_GetActorWalkbox_FarEntry__actor_valid:
    .a8
    sta.l SAME_SCUMM_GET_WALKBOX_ACTOR
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    sta.l SAME_SCUMM_GET_WALKBOX_VALUE
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_GET_WALKBOX_PC_AFTER
    lda.l SAME_SCUMM_OPERAND
    jsl ScummV5_GetActorFacing_FarCall_WriteResult
    jsr ScummV5_GetActorWalkbox_Trace_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_WALKBOX_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_GET_WALKBOX_EXEC_COUNT
    jml ScummV5_Engine_Frame__next
ScummV5_GetActorWalkbox_FarEntry__operand_error16:
    sep #$20
    .a8
ScummV5_GetActorWalkbox_FarEntry__operand_error:
    .a8
    lda #SCUMM_ERR_PC_RANGE
    bra ScummV5_GetActorWalkbox_FarEntry__set_error
ScummV5_GetActorWalkbox_FarEntry__argument_error:
    .a8
    lda #SCUMM_ERR_ARGUMENTS
ScummV5_GetActorWalkbox_FarEntry__set_error:
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

ScummV5_GetActorWalkbox_Reset_Far:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_GetActorWalkbox_Reset_Far__clear:
    sep #$20
    .a8
    sta.l SAME_SCUMM_GET_WALKBOX_STATE,x
    inx
    cpx #SAME_SCUMM_GET_WALKBOX_STATE_SIZE
    bcc ScummV5_GetActorWalkbox_Reset_Far__clear
    rtl

ScummV5_GetActorWalkbox_Trace_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_WALKBOX_TRACE_COUNT
    cmp #SAME_SCUMM_GET_WALKBOX_TRACE_CAPACITY
    bcs ScummV5_GetActorWalkbox_Trace_Far__done
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    asl
    asl
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_WALKBOX_ACTOR
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE,x
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE+1,x
    lda.l SAME_SCUMM_GET_WALKBOX_VALUE
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE+2,x
    lda #$00
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE+3,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_GET_WALKBOX_RESULT_OFFSET
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE+4,x
    lda.l SAME_SCUMM_GET_WALKBOX_RESULT_BEFORE
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE+6,x
    lda.l SAME_SCUMM_GET_WALKBOX_PC_BEFORE
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE+8,x
    lda.l SAME_SCUMM_GET_WALKBOX_PC_AFTER
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE+10,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_WALKBOX_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_GET_WALKBOX_TRACE_COUNT
ScummV5_GetActorWalkbox_Trace_Far__done:
    rts

ScummV5_GetActorFacing_FarEntry:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_GET_FACING_STAGE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_GET_FACING_PC_BEFORE
    jsl ScummV5_GetActorFacing_FarCall_ReadResult
    bcc ScummV5_GetActorFacing_FarEntry__result_ok
    jmp ScummV5_GetActorFacing_FarEntry__operand_error16
ScummV5_GetActorFacing_FarEntry__result_ok:
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    sta.l SAME_SCUMM_GET_FACING_RESULT_OFFSET
    jsl ScummV5_GetActorFacing_FarCall_ReadValue
    sta.l SAME_SCUMM_GET_FACING_RESULT_BEFORE
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_GET_FACING_STAGE
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcc ScummV5_GetActorFacing_FarEntry__actor_fetched
    jmp ScummV5_GetActorFacing_FarEntry__operand_error
ScummV5_GetActorFacing_FarEntry__actor_fetched:
    .a8
    cmp #$20
    bcc ScummV5_GetActorFacing_FarEntry__actor_valid
    jmp ScummV5_GetActorFacing_FarEntry__argument_error
ScummV5_GetActorFacing_FarEntry__actor_valid:
    .a8
    sta.l SAME_SCUMM_GET_FACING_ACTOR
    lda #$03
    sta.l SAME_SCUMM_GET_FACING_STAGE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_GET_FACING_ACTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_ACTOR_FACINGS,x
    sta.l SAME_SCUMM_GET_FACING_VALUE
    ; Preserve ScummVM's ordered inclusive tests exactly. The overlaps resolve
    ; as 109 -> 1 and 251 -> 2 because the earlier predicate wins.
    cmp #$0047
    bcc ScummV5_GetActorFacing_FarEntry__second_range
    cmp #$006E
    bcc ScummV5_GetActorFacing_FarEntry__one
ScummV5_GetActorFacing_FarEntry__second_range:
    .a16
    cmp #$006D
    bcc ScummV5_GetActorFacing_FarEntry__third_range
    cmp #$00FC
    bcc ScummV5_GetActorFacing_FarEntry__two
ScummV5_GetActorFacing_FarEntry__third_range:
    .a16
    cmp #$00FB
    bcc ScummV5_GetActorFacing_FarEntry__three
    cmp #$0122
    bcc ScummV5_GetActorFacing_FarEntry__zero
ScummV5_GetActorFacing_FarEntry__three:
    .a16
    lda #$0003
    bra ScummV5_GetActorFacing_FarEntry__converted
ScummV5_GetActorFacing_FarEntry__one:
    .a16
    lda #$0001
    bra ScummV5_GetActorFacing_FarEntry__converted
ScummV5_GetActorFacing_FarEntry__two:
    .a16
    lda #$0002
    bra ScummV5_GetActorFacing_FarEntry__converted
ScummV5_GetActorFacing_FarEntry__zero:
    .a16
    lda #$0000
ScummV5_GetActorFacing_FarEntry__converted:
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    sta.l SAME_SCUMM_GET_FACING_RESULT
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_GET_FACING_PC_AFTER
    lda.l SAME_SCUMM_OPERAND
    jsl ScummV5_GetActorFacing_FarCall_WriteResult
    sep #$20
    .a8
    lda #$04
    sta.l SAME_SCUMM_GET_FACING_STAGE
    jsr ScummV5_GetActorFacing_Trace_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_FACING_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_GET_FACING_EXEC_COUNT
    lda #$05
    sta.l SAME_SCUMM_GET_FACING_STAGE
    jml ScummV5_Engine_Frame__next
ScummV5_GetActorFacing_FarEntry__operand_error16:
    sep #$20
    .a8
ScummV5_GetActorFacing_FarEntry__operand_error:
    .a8
    lda #SCUMM_ERR_PC_RANGE
    bra ScummV5_GetActorFacing_FarEntry__set_error
ScummV5_GetActorFacing_FarEntry__argument_error:
    .a8
    lda #SCUMM_ERR_ARGUMENTS
ScummV5_GetActorFacing_FarEntry__set_error:
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

ScummV5_GetActorFacing_Trace_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_FACING_TRACE_COUNT
    cmp #SAME_SCUMM_GET_FACING_TRACE_CAPACITY
    bcs ScummV5_GetActorFacing_Trace_Far__done
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    asl
    clc
    adc.l SAME_SCUMM_PRODUCT
    asl
    clc
    adc.l SAME_SCUMM_PRODUCT
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_FACING_ACTOR
    sta.l SAME_SCUMM_GET_FACING_TRACE,x
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_GET_FACING_TRACE+1,x
    lda.l SAME_SCUMM_GET_FACING_RESULT
    sta.l SAME_SCUMM_GET_FACING_TRACE+2,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_GET_FACING_VALUE
    sta.l SAME_SCUMM_GET_FACING_TRACE+4,x
    lda.l SAME_SCUMM_GET_FACING_RESULT_OFFSET
    sta.l SAME_SCUMM_GET_FACING_TRACE+6,x
    lda.l SAME_SCUMM_GET_FACING_RESULT_BEFORE
    sta.l SAME_SCUMM_GET_FACING_TRACE+8,x
    lda.l SAME_SCUMM_GET_FACING_PC_BEFORE
    sta.l SAME_SCUMM_GET_FACING_TRACE+10,x
    lda.l SAME_SCUMM_GET_FACING_PC_AFTER
    sta.l SAME_SCUMM_GET_FACING_TRACE+12,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_GET_FACING_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_GET_FACING_TRACE_COUNT
ScummV5_GetActorFacing_Trace_Far__done:
    rts

; Maintain the existing actor-facing state for canonical immediate-direction
; animateActor requests (chore 3/4). This adds no turning or animation engine.
ScummV5_ActorFacing_ObserveAnimate_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    cmp #$F4
    bcc ScummV5_ActorFacing_ObserveAnimate_Far__done
    sec
    sbc #$F4
    cmp #$08
    bcs ScummV5_ActorFacing_ObserveAnimate_Far__done
    and #$03
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l ScummV5_ActorFacing_CardinalAngles,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_ACTOR_FACINGS,x
ScummV5_ActorFacing_ObserveAnimate_Far__done:
    sep #$20
    .a8
    rtl

ScummV5_ActorFacing_CardinalAngles:
    .word $010E,$005A,$00B4,$0000

ScummV5_SetState_FarEntry:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_SETSTATE_PC_BEFORE
    sep #$20
    .a8
    lda #$80
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    rep #$20
    .a16
    bcc ScummV5_SetState_FarEntry__object_fetched
    jmp ScummV5_SetState_FarEntry__operand_error16
ScummV5_SetState_FarEntry__object_fetched:
    cmp.l SAME_SCUMM_OBJECT_COUNT
    bcc ScummV5_SetState_FarEntry__object_valid
    jmp ScummV5_SetState_FarEntry__argument_error16
ScummV5_SetState_FarEntry__object_valid:
    sta.l SAME_SCUMM_SETSTATE_OBJECT
    sep #$20
    .a8
    lda #$40
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcc ScummV5_SetState_FarEntry__value_fetched
    jmp ScummV5_SetState_FarEntry__operand_error
ScummV5_SetState_FarEntry__value_fetched:
    sta.l SAME_SCUMM_SETSTATE_VALUE
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SETSTATE_PC_AFTER
    lda.l SAME_SCUMM_SETSTATE_OBJECT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_SETSTATE_VALUE
    sta.l SAME_SCUMM_OBJECT_STATES,x
    lda #$00
    sta.l SAME_SCUMM_SETSTATE_LOCAL_FOUND
    rep #$30
    .a16
    .i16
    ldx #$0000
ScummV5_SetState_FarEntry__local_scan:
    sep #$20
    .a8
    lda.l SAME_SCUMM_SETSTATE_LOCAL_COUNT
    beq ScummV5_SetState_FarEntry__scan_done
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_SETSTATE_LOCAL_OFFSET
    txa
    ; Divide the byte offset by the fixed 11-byte record stride using a
    ; bounded subtraction loop; active rooms contain at most 200 records.
    ldy #$0000
ScummV5_SetState_FarEntry__index_loop:
    .a16
    .i16
    cmp #SAME_SCUMM_SETSTATE_LOCAL_STRIDE
    bcc ScummV5_SetState_FarEntry__index_ready
    sec
    sbc #SAME_SCUMM_SETSTATE_LOCAL_STRIDE
    iny
    bra ScummV5_SetState_FarEntry__index_loop
ScummV5_SetState_FarEntry__index_ready:
    .a16
    .i16
    tya
    cmp.l SAME_SCUMM_SETSTATE_LOCAL_OFFSET
    bcs ScummV5_SetState_FarEntry__scan_done16
    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+SAME_SCUMM_SETSTATE_L_ID,x
    cmp.l SAME_SCUMM_SETSTATE_OBJECT
    beq ScummV5_SetState_FarEntry__local_found
    txa
    clc
    adc #SAME_SCUMM_SETSTATE_LOCAL_STRIDE
    tax
    bra ScummV5_SetState_FarEntry__local_scan
ScummV5_SetState_FarEntry__local_found:
    txa
    sta.l SAME_SCUMM_SETSTATE_LOCAL_OFFSET
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_SETSTATE_LOCAL_FOUND
    sta.l SAME_SCUMM_SETSTATE_BG_REDRAW
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_SETSTATE_LOCAL_OFFSET
    tax
    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+SAME_SCUMM_SETSTATE_L_X,x
    sta.l SAME_SCUMM_SETSTATE_DIRTY_RECT
    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+SAME_SCUMM_SETSTATE_L_Y,x
    sta.l SAME_SCUMM_SETSTATE_DIRTY_RECT+2
    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+SAME_SCUMM_SETSTATE_L_WIDTH,x
    sta.l SAME_SCUMM_SETSTATE_DIRTY_RECT+4
    lda.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS+SAME_SCUMM_SETSTATE_L_HEIGHT,x
    sta.l SAME_SCUMM_SETSTATE_DIRTY_RECT+6
    sep #$20
    .a8
    lda.l SAME_SCUMM_SETSTATE_DIRTY_COUNT
    inc
    sta.l SAME_SCUMM_SETSTATE_DIRTY_COUNT
ScummV5_SetState_FarEntry__scan_done:
    sep #$20
    .a8
    lda.l SAME_SCUMM_SETSTATE_BG_REDRAW
    beq ScummV5_SetState_FarEntry__success
    lda #$00
    sta.l SAME_SCUMM_SETSTATE_DRAW_QUEUE_COUNT
ScummV5_SetState_FarEntry__success:
    jsr ScummV5_SetState_Trace_Far
    lda.l SAME_SCUMM_SETSTATE_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_SETSTATE_EXEC_COUNT
    jml ScummV5_Engine_Frame__next
ScummV5_SetState_FarEntry__scan_done16:
    sep #$20
    .a8
    bra ScummV5_SetState_FarEntry__scan_done
ScummV5_SetState_FarEntry__operand_error16:
ScummV5_SetState_FarEntry__argument_error16:
    sep #$20
    .a8
ScummV5_SetState_FarEntry__operand_error:
ScummV5_SetState_FarEntry__argument_error:
    lda #SCUMM_ERR_ARGUMENTS
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

ScummV5_SetState_Trace_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_SETSTATE_TRACE_COUNT
    cmp #SAME_SCUMM_SETSTATE_TRACE_CAPACITY
    bcs ScummV5_SetState_Trace_Far__done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    asl
    tax
    lda.l SAME_SCUMM_SETSTATE_OBJECT
    sta.l SAME_SCUMM_SETSTATE_TRACE,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_SETSTATE_VALUE
    sta.l SAME_SCUMM_SETSTATE_TRACE+2,x
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_SETSTATE_TRACE+3,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_SETSTATE_PC_BEFORE
    sta.l SAME_SCUMM_SETSTATE_TRACE+4,x
    lda.l SAME_SCUMM_SETSTATE_PC_AFTER
    sta.l SAME_SCUMM_SETSTATE_TRACE+6,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_SETSTATE_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_SETSTATE_TRACE_COUNT
ScummV5_SetState_Trace_Far__done:
    rts

ScummV5_PutActor_FarEntry:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C10_SUBOP
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_PUT_ACTOR_PC_BEFORE
    sep #$20
    .a8
    lda #$80
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    sep #$20
    .a8
    bcc ScummV5_PutActor_FarEntry__actor_fetched
    jmp ScummV5_PutActor_FarEntry__operand_error
ScummV5_PutActor_FarEntry__actor_fetched:
    .a8
    cmp #$20
    bcc ScummV5_PutActor_FarEntry__actor_valid
    jmp ScummV5_PutActor_FarEntry__actor_error
ScummV5_PutActor_FarEntry__actor_valid:
    .a8
    sta.l SAME_SCUMM_PUT_ACTOR_ACTOR
    lda #$40
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    rep #$20
    .a16
    bcc ScummV5_PutActor_FarEntry__x_fetched
    sep #$20
    .a8
    jmp ScummV5_PutActor_FarEntry__operand_error
ScummV5_PutActor_FarEntry__x_fetched:
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sep #$20
    .a8
    lda #$20
    jsl ScummV5_PutActor_FarCall_FetchWordParam
    rep #$20
    .a16
    bcc ScummV5_PutActor_FarEntry__y_fetched
    sep #$20
    .a8
    jmp ScummV5_PutActor_FarEntry__operand_error
ScummV5_PutActor_FarEntry__y_fetched:
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_PUT_ACTOR_PC_AFTER

    ; Ensure the generic actor record exists, then retain the actor's room.
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_PutActor_FarEntry__present
    jsl ScummV5_PutActor_FarCall_DefaultActor
ScummV5_PutActor_FarEntry__present:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_C31_POSITIONS,x
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    cmp #$0001
    bne ScummV5_PutActor_FarEntry__first_x_probe_done
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l $7E502E
    lda.l SAME_SCUMM_PC
    sta.l $7E5030
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l $7E5032
    lda #$02
    sta.l $7E5034
    rep #$20
    .a16
ScummV5_PutActor_FarEntry__first_x_probe_done:
    sep #$20
    .a8
    lda #$02
    sta.l $7E5014
    lda #$02
    jsr ScummV5_Movement_TracePositionEvent
    lda.l $7E5015
    inc
    sta.l $7E5015
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_C31_POSITIONS+2,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_PUT_ACTOR_REDRAW,x

    ; Actor::putActor(x,y) passes the actor's existing room unchanged.
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_PutActor_FarEntry__current
    jmp ScummV5_PutActor_FarEntry__not_current
ScummV5_PutActor_FarEntry__current:
    lda.l SAME_SCUMM_C22_CURRENT_ROOM
    bne ScummV5_PutActor_FarEntry__nonzero_room
    jmp ScummV5_PutActor_FarEntry__success
ScummV5_PutActor_FarEntry__nonzero_room:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    bne ScummV5_PutActor_FarEntry__ignore_boxes
    jsl ScummV5_PutActor_Adjust_Far
    bra ScummV5_PutActor_FarEntry__placed
ScummV5_PutActor_FarEntry__ignore_boxes:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
ScummV5_PutActor_FarEntry__placed:
    ; setBox retains the raw box scale. A direct scale also updates effective
    ; actor scale; a high-bit scale slot remains at the current effective scale
    ; when that slot has not been initialized by canonical roomOps.
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    cmp #$FF
    beq ScummV5_PutActor_FarEntry__scale_done
    rep #$20
    .a16
    and #$00FF
    tax
    jsl ScummV5_PutActor_LoadGeometry_Far
    bcs ScummV5_PutActor_FarEntry__scale_done
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+16
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP1
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP1
    sta.l SAME_SCUMM_PUT_ACTOR_BOX_SCALE_RAW,x
    bit #$8000
    bne ScummV5_PutActor_FarEntry__scale_done16
    sep #$20
    .a8
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP0
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_BOX_SCALE,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_X,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_Y,x
    bra ScummV5_PutActor_FarEntry__scale_done
ScummV5_PutActor_FarEntry__scale_done16:
    .a16
    sep #$20
    .a8
ScummV5_PutActor_FarEntry__scale_done:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    sta.l SAME_SCUMM_C31_POSITIONS,x
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    cmp #$0001
    bne ScummV5_PutActor_FarEntry__result_x_probe_done
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l $7E502E
    lda.l SAME_SCUMM_PC
    sta.l $7E5030
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l $7E5032
    lda #$03
    sta.l $7E5034
    rep #$20
    .a16
ScummV5_PutActor_FarEntry__result_x_probe_done:
    sep #$20
    .a8
    lda #$02
    sta.l $7E5014
    lda #$03
    jsr ScummV5_Movement_TracePositionEvent
    lda.l $7E5015
    inc
    sta.l $7E5015
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sta.l SAME_SCUMM_C31_POSITIONS+2,x
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    sta.l SAME_SCUMM_PUT_ACTOR_LAST_VALID,x
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sta.l SAME_SCUMM_PUT_ACTOR_LAST_VALID+2,x
    lda #$FFFF
    sta.l SAME_SCUMM_PUT_ACTOR_DEST_X,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
    lda #$01
    sta.l SAME_SCUMM_PUT_ACTOR_REDRAW,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    bra ScummV5_PutActor_FarEntry__success
ScummV5_PutActor_FarEntry__not_current:
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    beq ScummV5_PutActor_FarEntry__success
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
ScummV5_PutActor_FarEntry__success:
    .a8
    jsr ScummV5_PutActor_Trace_Far
    lda.l SAME_SCUMM_PUT_ACTOR_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_PUT_ACTOR_EXEC_COUNT
    jml ScummV5_Engine_Frame__next
ScummV5_PutActor_FarEntry__actor_error:
    .a8
    lda #SCUMM_ERR_ARGUMENTS
    bra ScummV5_PutActor_FarEntry__set_error
ScummV5_PutActor_FarEntry__operand_error:
    .a8
    lda #SCUMM_ERR_PC_RANGE
ScummV5_PutActor_FarEntry__set_error:
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

ScummV5_PutActor_Trace_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_TRACE_COUNT
    cmp #SAME_SCUMM_PUT_ACTOR_TRACE_CAPACITY
    bcs ScummV5_PutActor_Trace_Far__done
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    asl
    asl
    asl
    sec
    sbc.l SAME_SCUMM_PUT_ACTOR_TEMP0 ; count * 7
    asl                              ; count * 14
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_ACTOR
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE,x
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE+1,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE+2,x
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE+4,x
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE+6,x
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE+8,x
    lda.l SAME_SCUMM_PUT_ACTOR_PC_BEFORE
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE+10,x
    lda.l SAME_SCUMM_PUT_ACTOR_PC_AFTER
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE+12,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE_COUNT
ScummV5_PutActor_Trace_Far__done:
    rts

; Source-neutral v5 box adjustment over the active profile's immutable BOXD
; geometry and mutable matrixOps flags.  This does not inspect BOXM routes.
ScummV5_PutActor_Adjust_Far:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    lda.l SAME_SCUMM_MATRIX_BOX_COUNT
    bne ScummV5_PutActor_Adjust_Far__has_boxes
    jmp ScummV5_PutActor_Adjust_Far__no_boxes
ScummV5_PutActor_Adjust_Far__has_boxes:
    dec
    sta.l SAME_SCUMM_PUT_ACTOR_SCAN_BOX
    rep #$20
    .a16
    lda #$FFFF
    sta.l SAME_SCUMM_PUT_ACTOR_BEST_DISTANCE
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
ScummV5_PutActor_Adjust_Far__scan:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_SCAN_BOX
    bne ScummV5_PutActor_Adjust_Far__box_present
    jmp ScummV5_PutActor_Adjust_Far__done
ScummV5_PutActor_Adjust_Far__box_present:
    .a8
    tax
    lda.l SAME_SCUMM_MATRIX_BOX_FLAGS,x
    and #$80
    beq ScummV5_PutActor_Adjust_Far__visible_box
    jmp ScummV5_PutActor_Adjust_Far__next
ScummV5_PutActor_Adjust_Far__visible_box:
    ; Fetch immutable geometry through the active-room accessor.  This keeps
    ; high-numbered authored boxes identical to low-numbered boxes.
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_SCAN_BOX
    and #$00FF
    tax
    jsl ScummV5_PutActor_LoadGeometry_Far
    bcc ScummV5_PutActor_Adjust_Far__geometry_ok
    jmp ScummV5_PutActor_Adjust_Far__next
ScummV5_PutActor_Adjust_Far__geometry_ok:
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_SCAN_BOX
    and #$00FF
    sta.l SAME_SCUMM_PUT_ACTOR_GEOM_OFFSET
    asl
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_GEOM_OFFSET
    asl
    asl
    asl
    tax                         ; box * 24
    sec
    sbc.l SAME_SCUMM_PUT_ACTOR_GEOM_OFFSET ; box * 23 (discard)
    ; Recompute box * 18 = box * 16 + box * 2.
    lda.l SAME_SCUMM_PUT_ACTOR_GEOM_OFFSET
    asl
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_TEMP0
    tax
    txa
    sta.l SAME_SCUMM_PUT_ACTOR_GEOM_OFFSET

    ; Above, below, inside, or side interpolation as checkXYInBoxBounds.
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    eor #$8000
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+2
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__not_above
    beq ScummV5_PutActor_Adjust_Far__not_above
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+2
    sta.l SAME_SCUMM_PUT_ACTOR_POINT_Y
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK
    sta.l SAME_SCUMM_PUT_ACTOR_XMIN
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+4
    sta.l SAME_SCUMM_PUT_ACTOR_XMAX
    jmp ScummV5_PutActor_Adjust_Far__clamp_x
ScummV5_PutActor_Adjust_Far__not_above:
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+14
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__below
    beq ScummV5_PutActor_Adjust_Far__below
    ; Interior requires x >= both lefts and x < both rights.
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    eor #$8000
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__left1_ok
    beq ScummV5_PutActor_Adjust_Far__left1_ok
    bra ScummV5_PutActor_Adjust_Far__side
ScummV5_PutActor_Adjust_Far__left1_ok:
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+12
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__left2_ok
    beq ScummV5_PutActor_Adjust_Far__left2_ok
    bra ScummV5_PutActor_Adjust_Far__side
ScummV5_PutActor_Adjust_Far__left2_ok:
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+4
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__side
    beq ScummV5_PutActor_Adjust_Far__side
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+8
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__side
    beq ScummV5_PutActor_Adjust_Far__side
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_POINT_X
    sta.l SAME_SCUMM_PUT_ACTOR_XMIN
    sta.l SAME_SCUMM_PUT_ACTOR_XMAX
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_POINT_Y
    jmp ScummV5_PutActor_Adjust_Far__distance
ScummV5_PutActor_Adjust_Far__below:
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+14
    sta.l SAME_SCUMM_PUT_ACTOR_POINT_Y
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+12
    sta.l SAME_SCUMM_PUT_ACTOR_XMIN
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+8
    sta.l SAME_SCUMM_PUT_ACTOR_XMAX
    jmp ScummV5_PutActor_Adjust_Far__clamp_x
ScummV5_PutActor_Adjust_Far__side:
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_POINT_Y
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK
    sta.l SAME_SCUMM_PUT_ACTOR_ULX
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+12
    sta.l SAME_SCUMM_PUT_ACTOR_LLX
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+4
    sta.l SAME_SCUMM_PUT_ACTOR_URX
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+8
    sta.l SAME_SCUMM_PUT_ACTOR_LRX
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+2
    sta.l SAME_SCUMM_PUT_ACTOR_TOP
    lda.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+14
    sta.l SAME_SCUMM_PUT_ACTOR_BOTTOM
ScummV5_PutActor_Adjust_Far__binary:
    lda.l SAME_SCUMM_PUT_ACTOR_ULX
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_LLX
    lsr
    sta.l SAME_SCUMM_PUT_ACTOR_XMIN
    lda.l SAME_SCUMM_PUT_ACTOR_URX
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_LRX
    lsr
    sta.l SAME_SCUMM_PUT_ACTOR_XMAX
    lda.l SAME_SCUMM_PUT_ACTOR_TOP
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_BOTTOM
    lsr
    sta.l SAME_SCUMM_PUT_ACTOR_CURRENT_Y
    eor #$8000
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    beq ScummV5_PutActor_Adjust_Far__clamp_x
    bcc ScummV5_PutActor_Adjust_Far__binary_upper
    lda.l SAME_SCUMM_PUT_ACTOR_CURRENT_Y
    sta.l SAME_SCUMM_PUT_ACTOR_TOP
    lda.l SAME_SCUMM_PUT_ACTOR_XMIN
    sta.l SAME_SCUMM_PUT_ACTOR_ULX
    lda.l SAME_SCUMM_PUT_ACTOR_XMAX
    sta.l SAME_SCUMM_PUT_ACTOR_URX
    brl ScummV5_PutActor_Adjust_Far__binary
ScummV5_PutActor_Adjust_Far__binary_upper:
    lda.l SAME_SCUMM_PUT_ACTOR_CURRENT_Y
    sta.l SAME_SCUMM_PUT_ACTOR_BOTTOM
    lda.l SAME_SCUMM_PUT_ACTOR_XMIN
    sta.l SAME_SCUMM_PUT_ACTOR_LLX
    lda.l SAME_SCUMM_PUT_ACTOR_XMAX
    sta.l SAME_SCUMM_PUT_ACTOR_LRX
    brl ScummV5_PutActor_Adjust_Far__binary
ScummV5_PutActor_Adjust_Far__clamp_x:
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    eor #$8000
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_PUT_ACTOR_XMIN
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__check_max
    beq ScummV5_PutActor_Adjust_Far__check_max
    lda.l SAME_SCUMM_PUT_ACTOR_XMIN
    bra ScummV5_PutActor_Adjust_Far__store_x
ScummV5_PutActor_Adjust_Far__check_max:
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_XMAX
    eor #$8000
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__use_max
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    bra ScummV5_PutActor_Adjust_Far__store_x
ScummV5_PutActor_Adjust_Far__use_max:
    lda.l SAME_SCUMM_PUT_ACTOR_XMAX
ScummV5_PutActor_Adjust_Far__store_x:
    sta.l SAME_SCUMM_PUT_ACTOR_POINT_X
ScummV5_PutActor_Adjust_Far__distance:
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sec
    sbc.l SAME_SCUMM_PUT_ACTOR_POINT_X
    bpl ScummV5_PutActor_Adjust_Far__xdist_positive
    eor #$FFFF
    inc
ScummV5_PutActor_Adjust_Far__xdist_positive:
    .a16
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sec
    sbc.l SAME_SCUMM_PUT_ACTOR_POINT_Y
    bpl ScummV5_PutActor_Adjust_Far__ydist_positive
    eor #$FFFF
    inc
ScummV5_PutActor_Adjust_Far__ydist_positive:
    lsr
    lsr
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP1
    cmp.l SAME_SCUMM_PUT_ACTOR_TEMP0
    bcc ScummV5_PutActor_Adjust_Far__x_larger
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP0
    lsr
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_TEMP1
    bra ScummV5_PutActor_Adjust_Far__distance_ready
ScummV5_PutActor_Adjust_Far__x_larger:
    lda.l SAME_SCUMM_PUT_ACTOR_TEMP1
    lsr
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_TEMP0
ScummV5_PutActor_Adjust_Far__distance_ready:
    sta.l SAME_SCUMM_PUT_ACTOR_POINT_DISTANCE
    beq ScummV5_PutActor_Adjust_Far__select
    cmp.l SAME_SCUMM_PUT_ACTOR_BEST_DISTANCE
    bcs ScummV5_PutActor_Adjust_Far__next
ScummV5_PutActor_Adjust_Far__select:
    sta.l SAME_SCUMM_PUT_ACTOR_BEST_DISTANCE
    lda.l SAME_SCUMM_PUT_ACTOR_POINT_X
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    lda.l SAME_SCUMM_PUT_ACTOR_POINT_Y
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_SCAN_BOX
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_BEST_DISTANCE
    beq ScummV5_PutActor_Adjust_Far__done
ScummV5_PutActor_Adjust_Far__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_SCAN_BOX
    dec
    sta.l SAME_SCUMM_PUT_ACTOR_SCAN_BOX
    jmp ScummV5_PutActor_Adjust_Far__scan
ScummV5_PutActor_Adjust_Far__no_boxes:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
ScummV5_PutActor_Adjust_Far__done:
    sep #$20
    .a8
    rtl

ScummV5_MatrixOps_FarEntry:
    sep #$20
    .a8
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcs ScummV5_MatrixOps_FarEntry__error
    sta.l SAME_SCUMM_C10_SUBOP
    sta.l SAME_SCUMM_MATRIX_LAST_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_MatrixOps_FarEntry__unsupported
    lda #$80
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcs ScummV5_MatrixOps_FarEntry__error
    sta.l SAME_SCUMM_MATRIX_LAST_BOX
    lda #$40
    jsl ScummV5_Matrix_FarCall_FetchByteParam
    bcs ScummV5_MatrixOps_FarEntry__error
    sta.l SAME_SCUMM_MATRIX_LAST_FLAGS
    lda.l SAME_SCUMM_MATRIX_LAST_BOX
    cmp #$FF
    beq ScummV5_MatrixOps_FarEntry__success
    lda.l SAME_SCUMM_MATRIX_BOX_COUNT
    beq ScummV5_MatrixOps_FarEntry__success
    lda.l SAME_SCUMM_MATRIX_LAST_BOX
    cmp.l SAME_SCUMM_MATRIX_BOX_COUNT
    bcs ScummV5_MatrixOps_FarEntry__bad_box
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_MATRIX_LAST_FLAGS
    sta.l SAME_SCUMM_MATRIX_BOX_FLAGS,x
    lda.l SAME_SCUMM_MATRIX_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_MATRIX_EXEC_COUNT
    jsr ScummV5_MatrixOps_FarTrace
ScummV5_MatrixOps_FarEntry__success:
    jml ScummV5_Engine_Frame__next
ScummV5_MatrixOps_FarEntry__unsupported:
    .a8
    lda #SCUMM_ERR_OPCODE
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
ScummV5_MatrixOps_FarEntry__error:
    jml ScummV5_Op__error
ScummV5_MatrixOps_FarEntry__bad_box:
    .a8
    lda #SCUMM_ERR_ARGUMENTS
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

; Diagnostic evidence only: record exact decoded instruction boundaries.
ScummV5_MatrixOps_FarTrace:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MATRIX_TRACE_COUNT
    cmp #SAME_SCUMM_MATRIX_TRACE_CAPACITY
    bcs ScummV5_MatrixOps_FarTrace__done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MATRIX_LAST_SUBOP
    sta.l SAME_SCUMM_MATRIX_TRACE,x
    lda.l SAME_SCUMM_MATRIX_LAST_BOX
    sta.l SAME_SCUMM_MATRIX_TRACE+1,x
    lda.l SAME_SCUMM_MATRIX_LAST_FLAGS
    sta.l SAME_SCUMM_MATRIX_TRACE+2,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sec
    sbc #$0004
    sta.l SAME_SCUMM_MATRIX_TRACE+3,x
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_MATRIX_TRACE+5,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_MATRIX_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_MATRIX_TRACE_COUNT
ScummV5_MatrixOps_FarTrace__done:
    rts

; Canonical v5 headless slot-0 actor-talk state. Animation requests are
; recorded as logical events; costume/frame state is deliberately untouched.
ScummV5_Talk_Reset_Far:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Talk_Reset_Far__clear:
    sep #$20
    .a8
    sta.l SAME_SCUMM_TALK_STATE,x
    inx
    cpx #SAME_SCUMM_TALK_STATE_SIZE
    bcc ScummV5_Talk_Reset_Far__clear
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_TALK_CONTROL_COUNT
    sta.l SAME_SCUMM_TALK_CONTROL_FIRST_POS
    sta.l SAME_SCUMM_TALK_CONTROL_FIRST_POS+1
    sta.l SAME_SCUMM_TALK_CONTROL_LAST
    lda #$FF
    sta.l SAME_SCUMM_TALK_ACTOR
    lda #$04
    sta.l SAME_SCUMM_TALK_CHARINC
    .if SAME_BUILD_SCUMM_M23B
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_VARIABLES+(3 * 2)
    sta.l SAME_SCUMM_M23B_VARIABLES+(25 * 2)
    lda #$0004
    sta.l SAME_SCUMM_M23B_VARIABLES+(37 * 2)
    .endif
    sep #$20
    .a8
    rtl

; Input A8 is one encoded byte. Carry reports the declared 32-byte bound.
ScummV5_Talk_StoreTextByte_Far:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C23_SELECTOR
    lda.l SAME_SCUMM_TALK_CONTROL_LAST
    bit #$80
    beq ScummV5_Talk_StoreTextByte_Far__not_pending
    lda.l SAME_SCUMM_C23_SELECTOR
    sta.l SAME_SCUMM_TALK_CONTROL_LAST
    cmp #$03
    bne ScummV5_Talk_StoreTextByte_Far__not_pending
    lda.l SAME_SCUMM_TALK_CONTROL_COUNT
    inc
    sta.l SAME_SCUMM_TALK_CONTROL_COUNT
    cmp #$01
    bne ScummV5_Talk_StoreTextByte_Far__not_pending
    rep #$20
    .a16
    lda.l SAME_SCUMM_C23_RAW_INDEX
    dec
    sta.l SAME_SCUMM_TALK_CONTROL_FIRST_POS
    sep #$20
    .a8
ScummV5_Talk_StoreTextByte_Far__not_pending:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    cmp #$FF
    bne ScummV5_Talk_StoreTextByte_Far__pending_done
    lda #$80
    sta.l SAME_SCUMM_TALK_CONTROL_LAST
ScummV5_Talk_StoreTextByte_Far__pending_done:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_RAW_INDEX
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Headless scenario validation still consumes the complete source string,
    ; but need not retain more than the compact presentation buffer.  Keep
    ; the decoded length/PC contract while discarding bytes beyond storage.
    cmp #$20
    bcc ScummV5_Talk_StoreTextByte_Far__space
    ; Do not classify FF as overflow: it is an encoded control byte and the
    ; caller will fetch/interpret its selector next.  Advance the logical
    ; cursor explicitly; incrementing A here used to leave RAW_INDEX at 32
    ; and made the next continuation look malformed.
    lda.l SAME_SCUMM_C23_RAW_INDEX
    inc
    sta.l SAME_SCUMM_C23_RAW_INDEX
    lda.l SAME_SCUMM_C23_SELECTOR
    clc
    rtl
    .else
    cmp #SAME_SCUMM_TALK_MAX_RAW
    bcc ScummV5_Talk_StoreTextByte_Far__space
    sec
    rtl
    .endif
ScummV5_Talk_StoreTextByte_Far__space:
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    sta.l SAME_SCUMM_TALK_RAW,x
    cpx #$0010
    bcs ScummV5_Talk_StoreTextByte_Far__not_legacy
    sta.l SAME_SCUMM_C23_LAST_RAW,x
ScummV5_Talk_StoreTextByte_Far__not_legacy:
    lda.l SAME_SCUMM_C23_RAW_INDEX
    inc
    sta.l SAME_SCUMM_C23_RAW_INDEX
    lda.l SAME_SCUMM_C23_SELECTOR
    clc
    rtl

ScummV5_Talk_Begin_Far:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_TALK_KEEP_TEXT
    lda.l SAME_SCUMM_C23_RAW_INDEX
    bne ScummV5_Talk_Begin_Far__length_nonzero
    jmp ScummV5_Talk_Begin_Far__error
ScummV5_Talk_Begin_Far__length_nonzero:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; C23 has already consumed the complete encoded stream.  The compact
    ; presentation buffer is intentionally limited to 32 bytes, but headless
    ; logical ownership is not: KEEP_TEXT below carries the decoded lifetime.
    ; The byte cursor is the only remaining bound for this fixture ABI.
    bra ScummV5_Talk_Begin_Far__length_valid
    .endif
    .a8
    cmp #(SAME_SCUMM_TALK_MAX_RAW + 1)
    bcc ScummV5_Talk_Begin_Far__length_valid
    jmp ScummV5_Talk_Begin_Far__error
ScummV5_Talk_Begin_Far__length_valid:
    sta.l SAME_SCUMM_TALK_RAW_LENGTH
    dec
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; A headless fixture may decode a source string larger than the compact
    ; presentation buffer.  C23 has consumed the complete source stream, so
    ; retain its logical length and use the encoded length for the bounded
    ; lifetime calculation instead of validating discarded presentation bytes.
    lda.l SAME_SCUMM_TALK_RAW_LENGTH
    cmp #SAME_SCUMM_TALK_MAX_RAW
    bcc ScummV5_Talk_Begin_Far__stored_terminator
    lda #$01
    sta.l SAME_SCUMM_TALK_KEEP_TEXT
    bra ScummV5_Talk_Begin_Far__actor_check
ScummV5_Talk_Begin_Far__stored_terminator:
    lda.l SAME_SCUMM_TALK_RAW_LENGTH
    dec
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    beq ScummV5_Talk_Begin_Far__terminated
    jmp ScummV5_Talk_Begin_Far__error
ScummV5_Talk_Begin_Far__terminated:
    .endif
ScummV5_Talk_Begin_Far__actor_check:
    .a8
    lda.l SAME_SCUMM_C23_ACTOR
    cmp #$20
    bcc ScummV5_Talk_Begin_Far__actor_valid
    ; Canonical v5 print uses actor $FF for system/status-line speech.  It
    ; has no actor presentation owner, but it remains a real logical message
    ; and must follow the same lifetime/wait contract as actor speech.
    cmp #$FF
    beq ScummV5_Talk_Begin_Far__actor_valid
    jmp ScummV5_Talk_Begin_Far__error
ScummV5_Talk_Begin_Far__actor_valid:
    sta.l SAME_SCUMM_TALK_ACTOR
    ; Preserve exact instruction consumption for evidence and diagnostics.
    ; PC already names the byte following the encoded string terminator.
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_TALK_PC_AFTER
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$94                    ; variable actor: opcode + u16 actor + subop
    beq ScummV5_Talk_Begin_Far__pc_variable_actor
    cmp #$D8                    ; printEgo: opcode + subop
    beq ScummV5_Talk_Begin_Far__pc_ego
    lda #$03                    ; direct actor: opcode + u8 actor + subop
    bra ScummV5_Talk_Begin_Far__pc_prefix_ready
ScummV5_Talk_Begin_Far__pc_variable_actor:
    .a8
    lda #$04
    bra ScummV5_Talk_Begin_Far__pc_prefix_ready
ScummV5_Talk_Begin_Far__pc_ego:
    .a8
    lda #$02
ScummV5_Talk_Begin_Far__pc_prefix_ready:
    clc
    adc.l SAME_SCUMM_TALK_RAW_LENGTH
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    lda.l SAME_SCUMM_TALK_PC_AFTER
    sec
    sbc.l SAME_SCUMM_PRODUCT
    sta.l SAME_SCUMM_TALK_PC_BEFORE
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_TALK_KEEP_TEXT
    bne ScummV5_Talk_Begin_Far__keep_text
    brl ScummV5_Talk_Begin_Far__scan_setup
ScummV5_Talk_Begin_Far__keep_text:
    ; No presentation buffer is exposed in this mode.  The full C23 decode
    ; nevertheless supplies a deterministic logical duration and a complete
    ; message ownership interval for waitForMessage.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_TALK_RAW_LENGTH
    and #$00FF
    dec
    sta.l SAME_SCUMM_LOOP
    sep #$20
    .a8
    sta.l SAME_SCUMM_TALK_CURSOR
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; The controller fixture has a real BG2 presentation owner.  Keep the
    ; complete decoded length for logical ownership, but raster only the
    ; printable glyphs which fit in the bounded encoded-byte buffer.  The
    ; compact buffer may contain FF controls before those glyphs; its display
    ; segment length is therefore a glyph count, not RAW_LENGTH.  Headless
    ; fixtures retain the full logical-only path below.
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_LOOP
    ldx #$0000
ScummV5_Talk_Begin_Far__visible_prefix_scan:
    rep #$20
    .a16
    .i16
    cpx #$0020
    bcs ScummV5_Talk_Begin_Far__visible_prefix_done
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    beq ScummV5_Talk_Begin_Far__visible_prefix_done
    cmp #$FF
    bne ScummV5_Talk_Begin_Far__visible_glyph
    inx
    cpx #$0020
    bcs ScummV5_Talk_Begin_Far__visible_prefix_done
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$01
    beq ScummV5_Talk_Begin_Far__visible_control_no_args
    cmp #$02
    beq ScummV5_Talk_Begin_Far__visible_control_no_args
    cmp #$03
    beq ScummV5_Talk_Begin_Far__visible_control_no_args
    cmp #$08
    beq ScummV5_Talk_Begin_Far__visible_control_no_args
    inx
    inx
    inx
    bra ScummV5_Talk_Begin_Far__visible_prefix_scan
ScummV5_Talk_Begin_Far__visible_control_no_args:
    inx
    bra ScummV5_Talk_Begin_Far__visible_prefix_scan
ScummV5_Talk_Begin_Far__visible_glyph:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LOOP
    inc
    sta.l SAME_SCUMM_LOOP
    sep #$20
    .a8
    inx
    bra ScummV5_Talk_Begin_Far__visible_prefix_scan
ScummV5_Talk_Begin_Far__visible_prefix_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LOOP
    sep #$20
    .a8
    sta.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    sta.l SAME_SCUMM_TALK_SEGMENT_GLYPHS
    lda #$01
    sta.l SAME_SCUMM_TALK_HAVE_MSG
    bra ScummV5_Talk_Begin_Far__scan_done_common
    .else
    lda #$01
    sta.l SAME_SCUMM_TALK_HAVE_MSG
    bra ScummV5_Talk_Begin_Far__scan_done_common
    .endif
    .endif
ScummV5_Talk_Begin_Far__scan_setup:
    ; Parse exactly one display pass. FF 03 is the canonical embedded wait:
    ; retain the complete message and leave CURSOR after the control. Other
    ; controls remain fail-closed until their own semantic milestone.
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_LOOP
    ldx #$0000
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_TALK_SEGMENT_START
    sta.l SAME_SCUMM_TALK_SEGMENT_INDEX
ScummV5_Talk_Begin_Far__scan:
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    beq ScummV5_Talk_Begin_Far__scan_done
    cmp #$FF
    bne ScummV5_Talk_Begin_Far__glyph
    inx
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$03
    beq ScummV5_Talk_Begin_Far__wait_valid
    ; The encoded v5 text stream uses FF followed by a control selector.
    ; Controls 01/02/03/08 have no inline arguments; the remaining
    ; selectors used by the authored Fate messages carry two bytes.  The
    ; display decoder already consumes this canonical form.  Talk scanning
    ; must use the same grammar, while FF 03 remains the embedded wait
    ; boundary handled above.
    cmp #$01
    beq ScummV5_Talk_Begin_Far__control_no_args
    cmp #$02
    beq ScummV5_Talk_Begin_Far__control_no_args
    cmp #$08
    beq ScummV5_Talk_Begin_Far__control_no_args
    inx
    inx
    bra ScummV5_Talk_Begin_Far__scan
ScummV5_Talk_Begin_Far__control_no_args:
    bra ScummV5_Talk_Begin_Far__scan
ScummV5_Talk_Begin_Far__wait_valid:
    inx
    txa
    sta.l SAME_SCUMM_TALK_CURSOR
    bra ScummV5_Talk_Begin_Far__scan_done_wait
ScummV5_Talk_Begin_Far__glyph:
    inx
    rep #$20
    .a16
    lda.l SAME_SCUMM_LOOP
    inc
    sta.l SAME_SCUMM_LOOP
    bra ScummV5_Talk_Begin_Far__scan
ScummV5_Talk_Begin_Far__scan_done:
    sep #$20
    .a8
    txa
    sta.l SAME_SCUMM_TALK_CURSOR
    lda #$01
    sta.l SAME_SCUMM_TALK_HAVE_MSG
    bra ScummV5_Talk_Begin_Far__scan_done_common
ScummV5_Talk_Begin_Far__scan_done_wait:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_TALK_HAVE_MSG
ScummV5_Talk_Begin_Far__scan_done_common:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LOOP
    sep #$20
    .a8
    sta.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    sta.l SAME_SCUMM_TALK_SEGMENT_GLYPHS
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Talk_Begin_Far__no_previous
    lda #$01
    sta.l SAME_SCUMM_TALK_KEEP_TEXT
    jsr ScummV5_Talk_Stop_Far
    lda #$00
    sta.l SAME_SCUMM_TALK_KEEP_TEXT
ScummV5_Talk_Begin_Far__no_previous:
    rep #$30
    .a16
    .i16
    lda #$003C
    sta.l SAME_SCUMM_OPERAND
    .if SAME_BUILD_SCUMM_M23B
    lda.l SAME_SCUMM_M23B_VARIABLES+(37 * 2)
    and #$00FF
    sep #$20
    .a8
    sta.l SAME_SCUMM_TALK_CHARINC
    rep #$20
    .a16
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_CHARINC
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    lda.l SAME_SCUMM_LOOP
    tax
ScummV5_Talk_Begin_Far__delay_loop:
    .a16
    .i16
    cpx #$0000
    beq ScummV5_Talk_Begin_Far__delay_done
    lda.l SAME_SCUMM_OPERAND
    clc
    adc.l SAME_SCUMM_PRODUCT
    sta.l SAME_SCUMM_OPERAND
    dex
    bra ScummV5_Talk_Begin_Far__delay_loop
ScummV5_Talk_Begin_Far__delay_done:
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_TALK_DELAY
    lda.l SAME_SCUMM_TALK_GENERATION
    inc
    sta.l SAME_SCUMM_TALK_GENERATION
    lda.l SAME_SCUMM_FRAME_COUNT
    sta.l SAME_SCUMM_TALK_STARTED_FRAME
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_TALK_ACTIVE
    ; Publish VAR_HAVE_MSG at the same semantic boundary as message ownership.
    ; The frame-begin mirror remains the canonical steady-state publisher, but
    ; a waiter scheduled in the same frame must not observe an uninitialized
    ; zero between Talk_Begin and that mirror.
    .if SAME_BUILD_SCUMM_M23B
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_HAVE_MSG
    and #$00FF
    sta.l SAME_SCUMM_VARIABLES+(3 * 2)
    sep #$20
    .a8
    .endif
    lda #$04
    sta.l SAME_SCUMM_TALK_ACTOR_FRAME
    lda.l SAME_SCUMM_C23_ACTOR
    sta.l SAME_SCUMM_TALK_ACTOR
    lda.l SAME_SCUMM_TALK_START_COUNT
    inc
    sta.l SAME_SCUMM_TALK_START_COUNT
    .if SAME_BUILD_SCUMM_M23B
    rep #$20
    .a16
    lda #$00FF
    sta.l SAME_SCUMM_VARIABLES+(3 * 2)
    lda.l SAME_SCUMM_TALK_ACTOR
    and #$00FF
    sta.l SAME_SCUMM_M23B_VARIABLES+(25 * 2)
    .endif
    sep #$20
    .a8
    lda #$01
    jsr ScummV5_Talk_RecordEvent_Far
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S0
    jsl Same_VideoText_ShowSegment_Far
    .else
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    inc
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    .endif
    clc
    rtl
ScummV5_Talk_Begin_Far__error:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$D8
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    lda.l SAME_SCUMM_C23_ACTOR
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_INDEX2+5
    lda.l SAME_SCUMM_C23_RAW_INDEX
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_INDEX2+6
    lda.l SAME_SCUMM_C23_LAST_SLOT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_INDEX2+7
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_INDEX2+8
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_INDEX2+2
    sep #$20
    .a8
    .endif
    lda #SCUMM_ERR_STRING
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    sec
    rtl

ScummV5_Talk_FrameBegin_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Talk_FrameBegin_Far__publish
    ; A talk segment may be decoded while the prior controller/HUD layer is
    ; still in flight.  Logical ownership is already active in that case;
    ; retry only the presentation publish at the normal frame boundary so
    ; visible dialogue cannot remain stuck on the old HUD prompt.
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    beq ScummV5_Talk_FrameBegin_Far__delay
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S0
    sep #$20
    .a8
    jsl Same_VideoText_ShowSegment_Far
    .endif
ScummV5_Talk_FrameBegin_Far__delay:
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_DELAY
    beq ScummV5_Talk_FrameBegin_Far__publish16
    cmp #$0004
    bcc ScummV5_Talk_FrameBegin_Far__zero
    sec
    sbc #$0004
    bra ScummV5_Talk_FrameBegin_Far__store
ScummV5_Talk_FrameBegin_Far__zero:
    .a16
    lda #$0000
ScummV5_Talk_FrameBegin_Far__store:
    sta.l SAME_SCUMM_TALK_DELAY
ScummV5_Talk_FrameBegin_Far__publish16:
    sep #$20
    .a8
ScummV5_Talk_FrameBegin_Far__publish:
    .if SAME_BUILD_SCUMM_M23B
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_HAVE_MSG
    and #$00FF
    sta.l SAME_SCUMM_VARIABLES+(3 * 2)
    .endif
    sep #$20
    .a8
    rtl

ScummV5_Talk_FrameEnd_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Talk_FrameEnd_Far__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_DELAY
    bne ScummV5_Talk_FrameEnd_Far__done16
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_HAVE_MSG
    cmp #$FF
    bne ScummV5_Talk_FrameEnd_Far__stop
    jsr ScummV5_Talk_Continue_Far
    bra ScummV5_Talk_FrameEnd_Far__done
ScummV5_Talk_FrameEnd_Far__stop:
    jsr ScummV5_Talk_Stop_Far
    rtl
ScummV5_Talk_FrameEnd_Far__done16:
    sep #$20
    .a8
ScummV5_Talk_FrameEnd_Far__done:
    rtl

ScummV5_Talk_ErrorFrameEnd_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Talk_ErrorFrameEnd_Far__advance
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_DELAY
    bne ScummV5_Talk_ErrorFrameEnd_Far__advance16
    sep #$20
    .a8
    jsr ScummV5_Talk_Stop_Far
    bra ScummV5_Talk_ErrorFrameEnd_Far__advance
ScummV5_Talk_ErrorFrameEnd_Far__advance16:
    sep #$20
    .a8
ScummV5_Talk_ErrorFrameEnd_Far__advance:
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_COUNT
    inc
    sta.l SAME_SCUMM_FRAME_COUNT
    sep #$20
    .a8
    rtl

ScummV5_Talk_Stop_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Talk_Stop_Far__done
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S0
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; The controller fixture owns a real BG2 presentation layer.  KEEP_TEXT
    ; still selects the bounded-prefix logical path, but must not retain stale
    ; dialogue pixels after the authored message completes.
    bra ScummV5_Talk_Stop_Far__hide_visual
    .else
    lda.l SAME_SCUMM_TALK_KEEP_TEXT
    bne ScummV5_Talk_Stop_Far__retain_visual
    .endif
ScummV5_Talk_Stop_Far__hide_visual:
    jsl Same_VideoText_Hide_Far
ScummV5_Talk_Stop_Far__retain_visual:
    .a8
    .else
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    inc
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    .endif
    lda #$02
    jsr ScummV5_Talk_RecordEvent_Far
    lda #$00
    sta.l SAME_SCUMM_TALK_ACTIVE
    sta.l SAME_SCUMM_TALK_HAVE_MSG
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_TALK_DELAY
    lda.l SAME_SCUMM_FRAME_COUNT
    sta.l SAME_SCUMM_TALK_COMPLETED_FRAME
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_TALK_ACTOR
    lda #$05
    sta.l SAME_SCUMM_TALK_ACTOR_FRAME
    lda.l SAME_SCUMM_TALK_STOP_COUNT
    inc
    sta.l SAME_SCUMM_TALK_STOP_COUNT
    lda.l SAME_SCUMM_TALK_COMPLETE_COUNT
    inc
    sta.l SAME_SCUMM_TALK_COMPLETE_COUNT
    .if SAME_BUILD_SCUMM_M23B
    rep #$20
    .a16
    lda #$00FF
    sta.l SAME_SCUMM_M23B_VARIABLES+(25 * 2)
    .endif
    sep #$20
    .a8
ScummV5_Talk_Stop_Far__done:
    rts

; Resume a retained v5 message after FF 03. No blank semantic loop is
; introduced: the next segment becomes active in the same frame-end phase.
ScummV5_Talk_Continue_Far:
    ; This helper is called from the frame epilogue, whose caller owns the
    ; processor-width ABI.  The scanner needs a 16-bit X index, but leaving
    ; that width active corrupts the following frame/scheduler tables when the
    ; caller entered with an 8-bit index.  Preserve the complete status word
    ; across the logical continuation, just as a normal leaf helper does.
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_TALK_CURSOR
    and #$00FF
    tax
    lda #$0000
    sta.l SAME_SCUMM_LOOP
    sep #$20
    .a8
    txa
    sta.l SAME_SCUMM_TALK_SEGMENT_START
ScummV5_Talk_Continue_Far__scan:
    .a8
    .i16
    lda.l SAME_SCUMM_TALK_RAW,x
    beq ScummV5_Talk_Continue_Far__end
    cmp #$FF
    beq ScummV5_Talk_Continue_Far__control
    bra ScummV5_Talk_Continue_Far__printable
ScummV5_Talk_Continue_Far__control:
    ; Continue uses the same encoded-text grammar as Talk_Begin.  A
    ; subsequent FF 03 is a logical segment boundary, not malformed text;
    ; controls without arguments are consumed in place and the remaining
    ; control forms carry their canonical two-byte payload.
    sep #$20
    .a8
    .i16
    inx
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$03
    beq ScummV5_Talk_Continue_Far__wait_control
    cmp #$01
    beq ScummV5_Talk_Continue_Far__control_no_args
    cmp #$02
    beq ScummV5_Talk_Continue_Far__control_no_args
    cmp #$08
    beq ScummV5_Talk_Continue_Far__control_no_args
    inx
    inx
    bra ScummV5_Talk_Continue_Far__scan
ScummV5_Talk_Continue_Far__control_no_args:
    inx
    bra ScummV5_Talk_Continue_Far__scan
ScummV5_Talk_Continue_Far__wait_control:
    sep #$20
    .a8
    .i16
    inx
    txa
    sta.l SAME_SCUMM_TALK_CURSOR
    lda #$FF
    bra ScummV5_Talk_Continue_Far__publish
ScummV5_Talk_Continue_Far__printable:
    inx
    rep #$20
    .a16
    lda.l SAME_SCUMM_LOOP
    inc
    sta.l SAME_SCUMM_LOOP
    sep #$20
    .a8
    bra ScummV5_Talk_Continue_Far__scan
ScummV5_Talk_Continue_Far__end:
    .a8
    .i16
    txa
    sta.l SAME_SCUMM_TALK_CURSOR
    lda #$01
ScummV5_Talk_Continue_Far__publish:
    sta.l SAME_SCUMM_TALK_HAVE_MSG
    lda.l SAME_SCUMM_TALK_SEGMENT_INDEX
    inc
    sta.l SAME_SCUMM_TALK_SEGMENT_INDEX
    lda.l SAME_SCUMM_TALK_CONTINUE_COUNT
    inc
    sta.l SAME_SCUMM_TALK_CONTINUE_COUNT
    rep #$20
    .a16
    lda.l SAME_SCUMM_LOOP
    sep #$20
    .a8
    sta.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    sta.l SAME_SCUMM_TALK_SEGMENT_GLYPHS
    lda.l SAME_SCUMM_TALK_CHARINC
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    lda #$003C
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LOOP
    tax
ScummV5_Talk_Continue_Far__delay:
    .a16
    .i16
    cpx #$0000
    beq ScummV5_Talk_Continue_Far__delay_done
    lda.l SAME_SCUMM_OPERAND
    clc
    adc.l SAME_SCUMM_PRODUCT
    sta.l SAME_SCUMM_OPERAND
    dex
    bra ScummV5_Talk_Continue_Far__delay
ScummV5_Talk_Continue_Far__delay_done:
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_TALK_DELAY
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S0
    jsl Same_VideoText_ShowSegment_Far
    .else
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    inc
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    .endif
    sep #$20
    .a8
    plp
    rts
ScummV5_Talk_Continue_Far__error:
    .a8
    lda #SCUMM_ERR_STRING
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    plp
    rts

; A8 kind: 1 start, 2 stop. Each record is kind,actor,chore,u16 generation,
; u16 frame,internal-have-msg.
ScummV5_Talk_RecordEvent_Far:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C23_SELECTOR
    lda.l SAME_SCUMM_TALK_EVENT_COUNT
    cmp #SAME_SCUMM_TALK_EVENT_CAPACITY
    bcs ScummV5_Talk_RecordEvent_Far__done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    asl
    sta.l SAME_SCUMM_PRODUCT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    sta.l SAME_SCUMM_TALK_EVENTS,x
    lda.l SAME_SCUMM_TALK_ACTOR
    sta.l SAME_SCUMM_TALK_EVENTS+1,x
    rep #$20
    .a16
    and #$00FF
    xba
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    cmp #$01
    beq ScummV5_Talk_RecordEvent_Far__start_frame
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_STOP,x
    bra ScummV5_Talk_RecordEvent_Far__frame_ready
ScummV5_Talk_RecordEvent_Far__start_frame:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_START,x
ScummV5_Talk_RecordEvent_Far__frame_ready:
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PRODUCT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_TALK_EVENTS+2,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_GENERATION
    sta.l SAME_SCUMM_TALK_EVENTS+3,x
    lda.l SAME_SCUMM_FRAME_COUNT
    sta.l SAME_SCUMM_TALK_EVENTS+5,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_HAVE_MSG
    sta.l SAME_SCUMM_TALK_EVENTS+7,x
    lda.l SAME_SCUMM_TALK_EVENT_COUNT
    inc
    sta.l SAME_SCUMM_TALK_EVENT_COUNT
ScummV5_Talk_RecordEvent_Far__done:
    rts

ScummV5_Talk_Wait_FarEntry:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_TALK_WAIT_PC
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_LOCAL0
    .endif
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcc ScummV5_Talk_Wait_FarEntry__subop
    brl ScummV5_Talk_Wait_FarEntry__error16
ScummV5_Talk_Wait_FarEntry__subop:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_Talk_Wait_FarEntry__subop_not_actor
    jmp ScummV5_Talk_Wait_FarEntry__actor
ScummV5_Talk_Wait_FarEntry__subop_not_actor:
    sep #$20
    .a8
    cmp #$02
    beq ScummV5_Talk_Wait_FarEntry__message
    brl ScummV5_Talk_Wait_FarEntry__error
ScummV5_Talk_Wait_FarEntry__message:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23B
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$61
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    .endif
    ; VAR_HAVE_MSG is a published compatibility mirror, but the logical
    ; owner is C23's talk service.  A waiter scheduled in the same frame as
    ; Talk_Begin can observe the mirror before its frame-boundary publication;
    ; consult the authoritative active state so headless mode preserves the
    ; real message lifetime instead of running through to its continuation.
    lda.l SAME_SCUMM_TALK_ACTIVE
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    bne ScummV5_Talk_Wait_FarEntry__trace_active
    lda #$63
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    bra ScummV5_Talk_Wait_FarEntry__trace_active_done
ScummV5_Talk_Wait_FarEntry__trace_active:
    sep #$20
    .a8
    lda #$62
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
ScummV5_Talk_Wait_FarEntry__trace_active_done:
    lda.l SAME_SCUMM_TALK_ACTIVE
    .endif
    bne ScummV5_Talk_Wait_FarEntry__block_active
    rep #$20
    .a16
    lda.l SAME_SCUMM_VARIABLES+(3 * 2)
    beq ScummV5_Talk_Wait_FarEntry__resume16
ScummV5_Talk_Wait_FarEntry__block_active:
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_WAIT_PC
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_WAIT_BLOCK_COUNT
    inc
    sta.l SAME_SCUMM_TALK_WAIT_BLOCK_COUNT
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Engine_Frame__complete_success
ScummV5_Talk_Wait_FarEntry__resume16:
    sep #$20
    .a8
    .endif
    lda.l SAME_SCUMM_TALK_WAIT_RESUME_COUNT
    inc
    sta.l SAME_SCUMM_TALK_WAIT_RESUME_COUNT
    jml ScummV5_Engine_Frame__next
ScummV5_Talk_Wait_FarEntry__actor:
    .a8
    lda.l SAME_SCUMM_C10_SUBOP
    bmi ScummV5_Talk_Wait_FarEntry__actor_variable
    jsl ScummV5_Matrix_FarCall_FetchByte
    bra ScummV5_Talk_Wait_FarEntry__actor_fetched
ScummV5_Talk_Wait_FarEntry__actor_variable:
    jsl ScummV5_Movement_FarCall_FetchVariableWord
ScummV5_Talk_Wait_FarEntry__actor_fetched:
    .a8
    bcs ScummV5_Talk_Wait_FarEntry__error
    cmp #$20
    bcs ScummV5_Talk_Wait_FarEntry__error
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    beq ScummV5_Talk_Wait_FarEntry__actor_resume
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_WAIT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_MOVE_WAIT_BLOCKS
    inc
    sta.l SAME_SCUMM_MOVE_WAIT_BLOCKS
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Engine_Frame__complete_success
ScummV5_Talk_Wait_FarEntry__actor_resume:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_WAIT_RELEASES
    inc
    sta.l SAME_SCUMM_MOVE_WAIT_RELEASES
    sep #$20
    .a8
    jml ScummV5_Engine_Frame__next
ScummV5_Talk_Wait_FarEntry__error16:
    sep #$20
    .a8
ScummV5_Talk_Wait_FarEntry__error:
    .a8
    lda #SCUMM_ERR_OPCODE
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Op__error

; Far-call ABI for the production scheduler.  Unlike the historical cold
; tail-dispatch entry, this returns to bank 0 so the scheduler can save the
; yielded slot, run later frame phases, and return to the SNES frame owner.
ScummV5_WaitActor_Call_Far:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_TALK_WAIT_PC
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcc ScummV5_WaitActor_Call_Far__subop_ready
    jmp ScummV5_WaitActor_Call_Far__error16
ScummV5_WaitActor_Call_Far__subop_ready:
    .a16
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_WaitActor_Call_Far__subop_not_actor
    jmp ScummV5_WaitActor_Call_Far__actor
ScummV5_WaitActor_Call_Far__subop_not_actor:
    sep #$20
    .a8
    cmp #$02
    beq ScummV5_WaitActor_Call_Far__message
    jmp ScummV5_WaitActor_Call_Far__error
ScummV5_WaitActor_Call_Far__message:
    .a8
    .if SAME_BUILD_SCUMM_M23B
    ; C23 talk state is authoritative at the same-frame boundary; the
    ; VAR_HAVE_MSG mirror may not yet have been published when this slot is
    ; first revisited.
    lda.l SAME_SCUMM_TALK_ACTIVE
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Observational breadcrumb: record the exact logical owner value seen by
    ; the waiter, without changing the production decision or allocating VM
    ; storage.  This distinguishes a true active-message block from a normal
    ; release at the opcode boundary.
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_COUNT
    .endif
    bne ScummV5_WaitActor_Call_Far__message_block_active
    rep #$20
    .a16
    lda.l SAME_SCUMM_VARIABLES+(3 * 2)
    beq ScummV5_WaitActor_Call_Far__message_release
ScummV5_WaitActor_Call_Far__message_block_active:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; The common dispatcher performs the single canonical rewind below.
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD0
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_WAIT_BLOCK_COUNT
    inc
    sta.l SAME_SCUMM_TALK_WAIT_BLOCK_COUNT
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Engine_Frame__complete_success
ScummV5_WaitActor_Call_Far__message_release:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sep #$20
    .a8
    lda #$42
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_PENDING
    .endif
    sep #$20
    .a8
    .endif
    lda.l SAME_SCUMM_TALK_WAIT_RESUME_COUNT
    inc
    sta.l SAME_SCUMM_TALK_WAIT_RESUME_COUNT
    clc
    rtl
ScummV5_WaitActor_Call_Far__actor:
    .a8
    lda.l SAME_SCUMM_C10_SUBOP
    bmi ScummV5_WaitActor_Call_Far__variable
    jsl ScummV5_Matrix_FarCall_FetchByte
    bra ScummV5_WaitActor_Call_Far__fetched
ScummV5_WaitActor_Call_Far__variable:
    jsl ScummV5_Movement_FarCall_FetchVariableWord
ScummV5_WaitActor_Call_Far__fetched:
    bcs ScummV5_WaitActor_Call_Far__error
    rep #$30
    .a16
    .i16
    and #$00FF
    cmp #$0020
    bcs ScummV5_WaitActor_Call_Far__error16
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    beq ScummV5_WaitActor_Call_Far__release
    rep #$20
    .a16
    lda.l SAME_SCUMM_TALK_WAIT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_MOVE_WAIT_BLOCKS
    inc
    sta.l SAME_SCUMM_MOVE_WAIT_BLOCKS
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    clc
    rtl
ScummV5_WaitActor_Call_Far__release:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_WAIT_RELEASES
    inc
    sta.l SAME_SCUMM_MOVE_WAIT_RELEASES
    sep #$20
    .a8
    clc
    rtl
ScummV5_WaitActor_Call_Far__error16:
    sep #$20
    .a8
ScummV5_WaitActor_Call_Far__error:
    .a8
    lda #SCUMM_ERR_OPCODE
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    sec
    rtl
