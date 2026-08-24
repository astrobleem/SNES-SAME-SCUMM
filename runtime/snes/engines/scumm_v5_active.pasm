; Bind the namespaced SCUMM v5 module to the stable active-engine ABI.
SAME_ACTIVE_ENGINE_ID = SAME_ENGINE_SCUMM_V5

Same_ActiveEngine_Boot:
    jsr ScummV5_Engine_Boot
    rts

Same_ActiveEngine_Frame:
    jsr ScummV5_Engine_Frame
    bcs Same_ActiveEngine_Frame__error
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_ENGINE_FRAME_OPS
    clc
    rts
Same_ActiveEngine_Frame__error:
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_ENGINE_FRAME_OPS
    ; Nonzero selectors are debugger-owned conformance cases. Their exact
    ; SCUMM_VM_ERROR state remains observable, but the harness must stay alive
    ; to select the next negative case. Fixture zero is the production path and
    ; still propagates failure into the generic engine lifecycle.
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_REQUEST
    beq Same_ActiveEngine_Frame__production_error
    clc
    rts
Same_ActiveEngine_Frame__production_error:
    sec
    rts

Same_ActiveEngine_Suspend:
    jsr ScummV5_Engine_Suspend
    rts
Same_ActiveEngine_Resume:
    jsr ScummV5_Engine_Resume
    rts
Same_ActiveEngine_Shutdown:
    jsr ScummV5_Engine_Shutdown
    rts
