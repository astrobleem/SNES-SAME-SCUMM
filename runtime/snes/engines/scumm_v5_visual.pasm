; SCUMM room lifecycle integration for target-neutral cooked room visuals.
.bank 21
.org $8000

ScummV5_InitialVisual_Bootstrap_Far:
    php
    sep #$20
    .a8
    lda #SCUMM_V5_INITIAL_VISUAL_ROOM
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_RequestRoom_FarEntry
    .else
    jsl ScummV5_Visual_RequestRoom_Far
    .endif
    bcs ScummV5_InitialVisual_Bootstrap__done
    jsl Same_Mode3_Kernel_DrainEvents_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$05
    bne ScummV5_InitialVisual_Bootstrap__done
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_ResourceReady_FarEntry
    .else
    jsl ScummV5_Visual_ResourceReady_Far
    .endif
    ; Resource installation publishes the three presentation packets. Drain
    ; them before the forced-blank realization loop begins; no SCUMM logical
    ; frame is run here.
    jsl Same_Mode3_Kernel_DrainEvents_Far
ScummV5_InitialVisual_Bootstrap__done:
    plp
    rtl

; Called only after the normal room installer has established the active room.
ScummV5_RoomVisual_Installed_Far:
    php
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    inc
    bne ScummV5_RoomVisual_Installed__generation_ok
    inc
ScummV5_RoomVisual_Installed__generation_ok:
    sta.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    jsl Same_VideoSurface_ComposeRoom_Far
    ; Room installation can overlap the previous room's conversion.  Publish
    ; the new room through the normal pending-visual path as well, so the
    ; frame service retries after the backend unlocks even when the camera
    ; coordinate itself did not change.
    jsl Same_VideoSurface_CameraPublished_Far
    plp
    rtl

; Camera publication is an engine lifecycle signal.  The generic display
; facade owns availability, deferred latest-request storage, and composition.
ScummV5_Visual_CameraPublished_Far:
    jsl Same_VideoSurface_CameraPublished_Far
    rtl

ScummV5_Visual_Frame_Far:
    ; BG1 displays the indexed SCUMM surface from VRAM $0000.  The optional
    ; BG2 controller overlay uses character-base nibble 7; retain that overlay
    ; base while leaving BG1 on the tile-shadow destination.
    php
    sep #$20
    .a8
    lda #$70
    sta BG12NBA
    plp
    ; Room/camera publication can enqueue video packets during the SCUMM
    ; engine pass after the kernel's earlier drain. Consume that production
    ; queue at the visual-frame boundary before servicing the pending room;
    ; otherwise the surface may be valid while the Mode-3 tile/CGRAM commit
    ; remains stranded behind the event FIFO.
    jsl Same_Mode3_Kernel_DrainEvents_Far
    jsl Same_VideoSurface_ServicePending_Far
    ; ServicePending publishes the room's dirty/palette/present packets.
    ; Consume that publication in this same visual-frame boundary so the
    ; backend starts conversion immediately instead of leaving the first
    ; room batch stranded behind the next scheduler phase.
    jsl Same_Mode3_Kernel_DrainEvents_Far
    rtl
