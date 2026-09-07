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
    jsl Same_VideoSurface_ServiceEvents_Far
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
    jsl Same_VideoSurface_ServiceEvents_Far
ScummV5_InitialVisual_Bootstrap__done:
    plp
    rtl

; Called only after the normal room installer has established the active room.
ScummV5_RoomVisual_Installed_Far:
    php
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_ROOM_INSTALLS
    inc
    sta.l SAME_VIDEO_DIAG_ROOM_INSTALLS
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_VIDEO_DIAG_INSTALL_NEXTGEN
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    inc
    bne ScummV5_RoomVisual_Installed__generation_ok
    inc
ScummV5_RoomVisual_Installed__generation_ok:
    sta.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    ; NEXT_GENERATION is a global presentation sequence, not a per-room
    ; installation marker.  Earlier room/camera traffic may legitimately
    ; leave it nonzero before this room is installed.  Every room install must
    ; compose its own descriptor once; otherwise the first present packet for
    ; the new room is silently skipped.
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    jsl Same_VideoSurface_ComposeRoom_Far
    ; Room installation may publish its first presentation after the frame's
    ; ordinary pre-engine drain.  Consume that target-neutral publication at
    ; the room lifecycle boundary so the selected backend receives the room
    ; generation without requiring SCUMM to know its implementation.
    jsl Same_VideoSurface_ServiceEvents_Far
    plp
    rtl

; Camera publication is an engine lifecycle signal.  The generic display
; facade owns availability, deferred latest-request storage, and composition.
ScummV5_Visual_CameraPublished_Far:
    jsl Same_VideoSurface_CameraPublished_Far
    rtl

ScummV5_Visual_Frame_Far:
    ; Resolve any room/camera presentation request before the actor pass.
    ; Actor composition must be the final indexed-surface mutation for this
    ; frame; otherwise a pending background blit can erase the actor before
    ; the native presentation service consumes the surface.
    jsl Same_VideoSurface_ServiceEvents_Far
    jsl Same_VideoSurface_ServicePending_Far
    jsl Same_VideoSurface_ServiceEvents_Far
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
      jsl ScummV5_Controller_RenderActor_Far
    .endif
    jsl Same_VideoSurface_ServiceEvents_Far
    rtl
