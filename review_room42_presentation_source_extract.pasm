; Exact screened excerpts from the current working tree.  ROMs, captures, and
; game-derived payloads are intentionally excluded from this review branch.

; tools/generate_snes_video_overlay.py emits this service hook for bg2_index4:
    jsl Same_Overlay_Bg2_Handle_Far
    bcc Same_Video_Handle__overlay_not_handled
    plp
    rts
Same_Video_Handle__overlay_not_handled:

; runtime/snes/kernel/frame.pasm: only SET_LAYER owns the preparation stop.
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_VIDEO_OP_SET_LAYER
    bne Same_Kernel_DrainEvents__next
    ; The backend/storage FIFO remains drainable while overlay preparation is pending.

; tools/validate_scumm_room42_controller_nexen.py captures the active message,
; rather than treating post-completion output as dialogue evidence:
        if message_seen and not dialogue_captured:
            session.take_screenshot(format="base64")
            dialogue_captured = True
