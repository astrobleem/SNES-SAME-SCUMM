Same_Kernel_Init:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_FRAME_COUNTER
    jsr Same_Dma_Reset
    jsr Same_Event_Reset
    jsr Same_Input_Reset
    jsr Same_Video_Reset
    jsr Same_Storage_Reset
    jsr Same_Engine_Reset
    plp
    rts

; Deterministic S-CPU frame phases.  Foreign CPU execution is a target hook;
; video hardware writes remain NMI-owned.
Same_Frame_Run:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_RESET_DIAG_ENGINE_PHASE
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_RESET_DIAG_ROOM
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_RESET_DIAG_PROGRAM
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_RESET_DIAG_SLOT
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_RESET_DIAG_SCRIPT_PC
    jsr Same_Input_Poll
    sep #$20
    .a8
    lda #$02
    sta.l SAME_RESET_DIAG_ENGINE_PHASE
    rep #$20
    .a16
    ; A SCUMM opcode may publish a required storage/audio request at the end
    ; of the previous engine phase.  Drain that packet before entering the
    ; next engine phase so a resource-wait state cannot strand its own event
    ; behind the scheduler gate.  The later drain remains necessary for
    ; requests generated during this frame.
    jsr Same_Kernel_DrainEvents
    jsr Same_Engine_Frame
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; Sample fixture input after the generic SCUMM pass and room lifecycle;
    ; the sentence API is consumed by the next engine pass.
    jsl ScummV5_Controller_Frame_Far
    .endif
    sep #$20
    .a8
    lda #$03
    sta.l SAME_RESET_DIAG_ENGINE_PHASE
    rep #$20
    .a16
    .if SAME_VIDEO_OVERLAY_BG2
    ; A script opcode may publish a completed target-neutral overlay during
    ; Same_Engine_Frame.  Consume and prepare that bounded request before the
    ; independent talk frame-end and camera lifecycle phases spend the rest
    ; of this host frame.
    jsr Same_Kernel_DrainEvents
    jsl Same_Overlay_Bg2_Step_Far
    .endif
    .if SAME_BUILD_SCUMM_M23A
    ; Talk expiration and FF 03 continuation are a normal once-per-logical-
    ; frame lifecycle phase, independent of which scheduler slot yielded.
    jsl ScummV5_Talk_FrameEnd_Far
    .endif
    .if SAME_BUILD_SCUMM_M23A
    ; Camera publication is a normal logical-frame phase after script/actor
    ; execution.  Same_Engine_Frame reports failure but returns here, so later
    ; lifecycle phases still run for the terminal frame.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_FRAME_PHASE_COUNT
    inc
    sta.l SAME_SCUMM_CAMERA_FRAME_PHASE_COUNT
    jsr ScummV5_Camera_Update
    .endif
    jsr Same_Kernel_DrainEvents
.include "../generated/video_overlay_frame.inc.pasm"
.include "../generated/video_backend_frame.inc.pasm"
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    jsl ScummV5_Visual_Frame_Far
    .endif
    jsr Same_Audio_Process
    plp
    rts

Same_Kernel_DrainEvents:
    php
Same_Kernel_DrainEvents__next:
    rep #$30
    .a16
    .i16
    jsr Same_Event_Pop
    bcs Same_Kernel_DrainEvents__done
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    cmp #SAME_SERVICE_VIDEO
    beq Same_Kernel_DrainEvents__video
    cmp #SAME_SERVICE_AUDIO
    beq Same_Kernel_DrainEvents__audio
    cmp #SAME_SERVICE_STORAGE
    beq Same_Kernel_DrainEvents__storage
    cmp #SAME_SERVICE_DEBUG
    beq Same_Kernel_DrainEvents__debug
    cmp #SAME_SERVICE_ENGINE
    beq Same_Kernel_DrainEvents__engine
    cmp #SAME_SERVICE_SAVE
    beq Same_Kernel_DrainEvents__save
    cmp #SAME_SERVICE_JOBS
    beq Same_Kernel_DrainEvents__jobs
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__video:
    sep #$20
    .a8
    jsr Same_Video_Handle
    .if SAME_VIDEO_OVERLAY_BG2
    ; Only the overlay's SET_LAYER packet owns the one-frame preparation
    ; boundary.  Non-overlay video packets must continue through the selected
    ; backend even while that preparation is pending; otherwise a stale
    ; PREPARING state strands storage/room events behind the video FIFO.
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_VIDEO_OP_SET_LAYER
    bne Same_Kernel_DrainEvents__next
    ; Do not stop the FIFO here.  The overlay step is independently bounded
    ; and the backend/storage packets remain valid while it is preparing.
    .endif
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__audio:
    sep #$20
    .a8
    jsr Same_Audio_Handle
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__storage:
    sep #$20
    .a8
    jsr Same_Storage_Handle
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__debug:
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    sta.l SAME_DEBUG_LAST_OPCODE
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__engine:
    sep #$20
    .a8
    jsr Same_Engine_Handle
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__save:
    sep #$20
    .a8
    jsr Same_Save_Handle
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__jobs:
    sep #$20
    .a8
    jsr Same_Jobs_Handle
    bra Same_Kernel_DrainEvents__next
Same_Kernel_DrainEvents__done:
    plp
    rts
