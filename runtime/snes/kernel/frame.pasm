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
    jsr Same_Audio_Reset
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
    jsr Same_Input_Poll
    jsr Same_Engine_Frame
    jsr Same_Kernel_DrainEvents
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
