; Exact screened excerpts from the current SAME source.  These are source
; extracts for review; the game ROM and generated resource payloads remain
; excluded from this branch.

; runtime/snes/kernel/frame.pasm
.if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; Sample fixture input after the generic SCUMM pass and room lifecycle;
    ; the sentence API is consumed by the next engine pass.
    jsl ScummV5_Controller_Frame_Far
.endif

; runtime/snes/engines/scumm_v5_m24rb_far.pasm, source actor initialization
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_SOURCE_ACTOR_INIT
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT+64
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE+64
    rep #$30
    .a16
    .i16
    lda #$0040
    sta.l SAME_SCUMM_C14_BASE
    jsl ScummV5_PutActor_FarCall_DefaultActor
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_COSTUME+64
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT+64
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE+64
    lda #$07
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX+1
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX+1
    rep #$20
    .a16
    lda #$0091
    sta.l SAME_SCUMM_C31_POSITIONS+4
    lda #$0070
    sta.l SAME_SCUMM_C31_POSITIONS+6

; runtime/snes/engines/scumm_v5_controller_far.pasm, Open mailbox tuple
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_SENTENCE_API_VERB
    lda #$EA
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1+1
    lda #$00
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2+1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_PENDING

; runtime/snes/engines/scumm_v5_controller_far.pasm, authored Inspect tuple
    lda #$09
    sta.l SAME_SCUMM_SENTENCE_API_VERB
    lda #$EA
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1+1
    lda #$00
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2+1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_PENDING
