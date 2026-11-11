; Compact controller pages consume original C17 names and mutable ownership.
; No authored verb is enabled here. SELECT opens verbs; START inventory.
; D-pad/Y cycles, A chooses, B returns to the scene. The existing sentence
; mailbox and source scripts remain the only action execution path.
ScummV5_Controller_MenuFrame_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_INPUT_PRESSED
    and #$3000
    beq ScummV5_Controller_MenuFrame__existing
    pha
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    bne ScummV5_Controller_MenuFrame__toggle_close
    lda.l SAME_SCUMM_CONTROLLER_MODE
    and #$00FF
    sta.l SAME_SCUMM_PLAY_UI_SAVED_MODE
    lda #$0001
    sta.l SAME_SCUMM_PLAY_UI_MODE
    lda #$00FF
    sta.l SAME_SCUMM_PLAY_UI_SELECTION
    lda #$0001
    sta.l SAME_SCUMM_PLAY_UI_TEMP
    jsl ScummV5_Controller_MenuNext_Far
    bcs ScummV5_Controller_MenuFrame__verbs_enabled
    pla
    jmp ScummV5_Controller_MenuFrame__close
ScummV5_Controller_MenuFrame__verbs_enabled:
    .a16
    pla
    and #$1000
    bne ScummV5_Controller_MenuFrame__open_inventory
    jmp ScummV5_Controller_MenuFrame__dirty
ScummV5_Controller_MenuFrame__open_inventory:
    .a16
    ; Inventory starts with an authored enabled verb, never an uninitialized
    ; action ID. Opening this page does not submit or change object ownership.
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONTROLLER_VERB
    rep #$20
    .a16
    lda #$0002
    sta.l SAME_SCUMM_PLAY_UI_MODE
    lda #SCUMM_M23A_GLOBAL_OBJECT_COUNT-1
    sta.l SAME_SCUMM_PLAY_UI_SELECTION
    jsl ScummV5_Controller_MenuNext_Far
    jmp ScummV5_Controller_MenuFrame__dirty
ScummV5_Controller_MenuFrame__toggle_close:
    .a16
    pla
    jmp ScummV5_Controller_MenuFrame__close
ScummV5_Controller_MenuFrame__existing:
    .a16
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    bne ScummV5_Controller_MenuFrame__active
    clc
    rtl
ScummV5_Controller_MenuFrame__active:
    .a16
    ; Scripts retain authority while a page is open. A disabled selected verb
    ; closes the page; no cached label can resurrect it or submit it later.
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    cmp #$0001
    bne ScummV5_Controller_MenuFrame__inventory_verb
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    bra ScummV5_Controller_MenuFrame__check_verb
ScummV5_Controller_MenuFrame__inventory_verb:
    .a16
    lda.l SAME_SCUMM_CONTROLLER_VERB
    and #$00FF
ScummV5_Controller_MenuFrame__check_verb:
    .a16
    jsl ScummV5_Controller_MenuVerbEnabled_Far
    bcs ScummV5_Controller_MenuFrame__verb_still_enabled
    jmp ScummV5_Controller_MenuFrame__close
ScummV5_Controller_MenuFrame__verb_still_enabled:
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0040
    beq ScummV5_Controller_MenuFrame__direction
    jmp ScummV5_Controller_MenuFrame__close
ScummV5_Controller_MenuFrame__direction:
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$4F00
    beq ScummV5_Controller_MenuFrame__choose
    lda #$0001
    sta.l SAME_SCUMM_PLAY_UI_TEMP
    lda.l SAME_INPUT_PRESSED
    and #$0A00
    beq ScummV5_Controller_MenuFrame__next
    lda #$FFFF
    sta.l SAME_SCUMM_PLAY_UI_TEMP
ScummV5_Controller_MenuFrame__next:
    .a16
    jsl ScummV5_Controller_MenuNext_Far
    jmp ScummV5_Controller_MenuFrame__dirty
ScummV5_Controller_MenuFrame__choose:
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080
    bne ScummV5_Controller_MenuFrame__accept_pressed
    jmp ScummV5_Controller_MenuFrame__owned
ScummV5_Controller_MenuFrame__accept_pressed:
    .a16
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    cmp #$FFFF
    beq ScummV5_Controller_MenuFrame__owned
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    cmp #$0001
    bne ScummV5_Controller_MenuFrame__inventory
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONTROLLER_VERB
    lda #$05 ; selected original verb, waiting for a source hit
    sta.l SAME_SCUMM_CONTROLLER_MODE
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    beq ScummV5_Controller_MenuFrame__chosen
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_MODE
    bra ScummV5_Controller_MenuFrame__chosen
ScummV5_Controller_MenuFrame__inventory:
    .a16
    ; An owner change while this page was visible invalidates the choice.
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_OWNERS,x
    cmp.l SAME_SCUMM_M23B_VARIABLES+2
    beq ScummV5_Controller_MenuFrame__inventory_owned
    rep #$20
    .a16
    jmp ScummV5_Controller_MenuFrame__close
ScummV5_Controller_MenuFrame__inventory_owned:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_MODE
ScummV5_Controller_MenuFrame__chosen:
    .a8
    sep #$20
    lda #$00
    sta.l SAME_SCUMM_PLAY_UI_MODE
    bra ScummV5_Controller_MenuFrame__dirty
ScummV5_Controller_MenuFrame__close:
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_PLAY_UI_SAVED_MODE
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$00
    sta.l SAME_SCUMM_PLAY_UI_MODE
ScummV5_Controller_MenuFrame__dirty:
    .a8
    sep #$20
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
ScummV5_Controller_MenuFrame__owned:
    .a8
    sec
    rtl

; Find a visible original verb or an Ego-owned inventory identity. The
; existing native inventory query uses ascending object identities; this UI
; follows that contract. Count-limited scans terminate even for empty menus.
ScummV5_Controller_MenuNext_Far:
    rep #$30
    .a16
    .i16
    lda #$0100
    pha
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    cmp #$0001
    beq ScummV5_Controller_MenuNext__limit
    pla
    lda #SCUMM_M23A_GLOBAL_OBJECT_COUNT
    pha
ScummV5_Controller_MenuNext__limit:
    .a16
    lda 1,s
    sta.l SAME_SCUMM_PLAY_UI_COUNT
ScummV5_Controller_MenuNext__scan:
    .a16
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    clc
    adc.l SAME_SCUMM_PLAY_UI_TEMP
    bpl ScummV5_Controller_MenuNext__positive
    lda 1,s
    dec
    bra ScummV5_Controller_MenuNext__bounded
ScummV5_Controller_MenuNext__positive:
    .a16
    cmp 1,s
    bcc ScummV5_Controller_MenuNext__bounded
    lda #$0000
ScummV5_Controller_MenuNext__bounded:
    .a16
    sta.l SAME_SCUMM_PLAY_UI_SELECTION
    tax
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    cmp #$0001
    bne ScummV5_Controller_MenuNext__object
    txa
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_PLAY_UI_OFFSET
    asl
    clc
    adc.l SAME_SCUMM_PLAY_UI_OFFSET
    sta.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    beq ScummV5_Controller_MenuNext__skip
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_MODE,x
    cmp #$01
    bne ScummV5_Controller_MenuNext__skip
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    cmp #$02
    bcs ScummV5_Controller_MenuNext__found
    bra ScummV5_Controller_MenuNext__skip
ScummV5_Controller_MenuNext__object:
    .a16
    txa
    beq ScummV5_Controller_MenuNext__skip
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_OWNERS,x
    cmp.l SAME_SCUMM_M23B_VARIABLES+2
    beq ScummV5_Controller_MenuNext__found
ScummV5_Controller_MenuNext__skip:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_PLAY_UI_COUNT
    dec
    sta.l SAME_SCUMM_PLAY_UI_COUNT
    bne ScummV5_Controller_MenuNext__scan
    pla
    lda #$FFFF
    sta.l SAME_SCUMM_PLAY_UI_SELECTION
    clc
    rtl
ScummV5_Controller_MenuNext__found:
    .a8
    rep #$20
    .a16
    pla
    sec
    rtl

.if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
ScummV5_Controller_MenuText_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    pha
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    pha
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    cmp #$FFFF
    bne ScummV5_Controller_MenuText__have_entry
    ; Empty is explicit interface state, not fabricated source object text.
    ldx #$0000
ScummV5_Controller_MenuText__empty_copy:
    .a16
    sep #$20
    .a8
    lda.l ScummV5_Controller_MenuEmpty,x
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    rep #$20
    .a16
    inx
    cpx #$0010
    bcc ScummV5_Controller_MenuText__empty_copy
    lda #$000F
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    jmp ScummV5_Controller_MenuText__finish
ScummV5_Controller_MenuText__have_entry:
    .a16
    sep #$20
    .a8
    lda #$3E
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    jsl ScummV5_Controller_MenuName_Far
    lda #$0001
    sta.l SAME_SCUMM_PLAY_UI_TEMP
    jsl ScummV5_Controller_MenuNext_Far
    bcc ScummV5_Controller_MenuText__finish
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    cmp 3,s
    beq ScummV5_Controller_MenuText__finish
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    tax
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    inx
    lda #$01 ; SCUMM encoded newline
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    inx
    lda #$20
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    inx
    rep #$20
    .a16
    txa
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    jsl ScummV5_Controller_MenuName_Far
ScummV5_Controller_MenuText__finish:
    .a16
    rep #$20
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    tax
    sep #$20
    .a8
    sta.l SAME_VIDEO_TEXT_CONTROLLER_LENGTH
    sta.l SAME_SCUMM_TALK_RAW_LENGTH
    lda #$00
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    lda #$01
    sta.l SAME_VIDEO_TEXT_CONTROLLER_VALID
    rep #$20
    .a16
    pla
    sta.l SAME_SCUMM_C17_RECORD_OFFSET
    pla
    sta.l SAME_SCUMM_PLAY_UI_SELECTION
    rtl

; At most13 original encoded bytes per menu line; the existing text decoder
; owns charset controls and rejects a malformed/truncated control sequence.
ScummV5_Controller_MenuName_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    cmp #$0001
    bne ScummV5_Controller_MenuName__object
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_PLAY_UI_OFFSET
    asl
    clc
    adc.l SAME_SCUMM_PLAY_UI_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_PLAY_UI_COUNT
    txa
    clc
    adc #SAME_SCUMM_C17_V_NAME
    tax
    bra ScummV5_Controller_MenuName__bound
ScummV5_Controller_MenuName__object:
    .a16
    lda.l SAME_SCUMM_PLAY_UI_SELECTION
    cmp #SAME_SCUMM_OBJECT_NAME_COUNT
    bcs ScummV5_Controller_MenuName__done
    tax
    lda.l SAME_SCUMM_OBJECT_NAME_LENGTH,x
    and #$00FF
    sta.l SAME_SCUMM_PLAY_UI_COUNT
    txa
    asl
    asl
    asl
    asl
    asl
    tax
ScummV5_Controller_MenuName__bound:
    .a16
    lda.l SAME_SCUMM_PLAY_UI_COUNT
    beq ScummV5_Controller_MenuName__done
    dec ; source cache length includes NUL
    cmp #$000D
    bcc ScummV5_Controller_MenuName__count
    lda #$000D
ScummV5_Controller_MenuName__count:
    .a16
    sta.l SAME_SCUMM_PLAY_UI_COUNT
ScummV5_Controller_MenuName__copy:
    .a16
    lda.l SAME_SCUMM_PLAY_UI_COUNT
    beq ScummV5_Controller_MenuName__done
    lda.l SAME_SCUMM_PLAY_UI_MODE
    and #$00FF
    cmp #$0001
    sep #$20
    .a8
    bne ScummV5_Controller_MenuName__object_byte
    lda.l SAME_SCUMM_C17_VERBS,x
    bra ScummV5_Controller_MenuName__byte
ScummV5_Controller_MenuName__object_byte:
    .a8
    lda.l SAME_SCUMM_OBJECT_NAMES,x
ScummV5_Controller_MenuName__byte:
    .a8
    pha
    phx
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    tax
    sep #$20
    .a8
    lda 3,s
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    plx
    pla
    inx
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    inc
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    lda.l SAME_SCUMM_PLAY_UI_COUNT
    dec
    sta.l SAME_SCUMM_PLAY_UI_COUNT
    bra ScummV5_Controller_MenuName__copy
ScummV5_Controller_MenuName__done:
    .a16
    rtl
ScummV5_Controller_MenuEmpty:
    .byte $49,$6E,$76,$65,$6E,$74,$6F,$72,$79,$20,$65,$6D,$70,$74,$79,$00
.endif

; A=verb ID. Return A16, C=present, enabled and named. Does not mutate C17.
ScummV5_Controller_MenuVerbEnabled_Far:
    rep #$30
    .a16
    .i16
    cmp #$0100
    bcs ScummV5_Controller_MenuVerbEnabled__no
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_PLAY_UI_OFFSET
    asl
    clc
    adc.l SAME_SCUMM_PLAY_UI_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    beq ScummV5_Controller_MenuVerbEnabled__no
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_MODE,x
    cmp #$01
    bne ScummV5_Controller_MenuVerbEnabled__no
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    cmp #$02
    bcc ScummV5_Controller_MenuVerbEnabled__no
    rep #$20
    .a16
    sec
    rtl
ScummV5_Controller_MenuVerbEnabled__no:
    rep #$20
    .a16
    clc
    rtl
