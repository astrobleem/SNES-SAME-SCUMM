; Source-reviewed opaque INDEX8 run copy, included in video_surface.pasm's
; existing bank. Source bytes are already palette-mapped; zero is opaque.
; Inputs: A16=(y<<8)|x, X16=count (1..256), Y16=verified source offset.
; SAME_VIDEO_SURFACE_DP_SOURCE points at a checked, currently-owned buffer.
; No event is published here; caller publishes one completed pose.
Same_VideoSurface_BlitCheckedOpaqueRun_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_BlitCheckedOpaqueRun__writable
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl
Same_VideoSurface_BlitCheckedOpaqueRun__writable:
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    tya
    sta.l SAME_MODE3_WORK_INDEX
    txa
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    bne Same_VideoSurface_BlitCheckedOpaqueRun__count_nonzero
    jmp Same_VideoSurface_BlitCheckedOpaqueRun__bad
Same_VideoSurface_BlitCheckedOpaqueRun__count_nonzero:
    .a16
    cmp #$0101
    bcc Same_VideoSurface_BlitCheckedOpaqueRun__count_ok
    jmp Same_VideoSurface_BlitCheckedOpaqueRun__bad
Same_VideoSurface_BlitCheckedOpaqueRun__count_ok:
    .a16
    clc
    adc.l SAME_MODE3_WORK_INDEX
    bcc Same_VideoSurface_BlitCheckedOpaqueRun__source_no_wrap
    jmp Same_VideoSurface_BlitCheckedOpaqueRun__bad
Same_VideoSurface_BlitCheckedOpaqueRun__source_no_wrap:
    .a16
    cmp #$0801
    bcc Same_VideoSurface_BlitCheckedOpaqueRun__source_ok
    jmp Same_VideoSurface_BlitCheckedOpaqueRun__bad
Same_VideoSurface_BlitCheckedOpaqueRun__source_ok:
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    xba
    and #$00FF
    cmp #$00E0
    bcc Same_VideoSurface_BlitCheckedOpaqueRun__y_ok
    jmp Same_VideoSurface_BlitCheckedOpaqueRun__bad
Same_VideoSurface_BlitCheckedOpaqueRun__y_ok:
    .a16
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    cmp #$0101
    bcc Same_VideoSurface_BlitCheckedOpaqueRun__right_ok
    jmp Same_VideoSurface_BlitCheckedOpaqueRun__bad
Same_VideoSurface_BlitCheckedOpaqueRun__right_ok:
    .a16
    lda #$0001
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    tax
    lda.l SAME_MODE3_WORK_INDEX
    tay
Same_VideoSurface_BlitCheckedOpaqueRun__copy:
    sep #$20
    .a8
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    iny
    rep #$20
    .a16
    dec SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    bne Same_VideoSurface_BlitCheckedOpaqueRun__copy
    plp
    clc
    rtl
Same_VideoSurface_BlitCheckedOpaqueRun__bad:
    plp
    sec
    rtl
