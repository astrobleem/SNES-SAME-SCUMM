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
    .if SAME_BUILD_SCUMM_CONTROLLER
    ; Room installation is the generic interaction-state lifetime boundary.
    ; The fixture's room-68 -> room-42 request remains elsewhere; this reset
    ; deliberately depends only on the established room-installed callback.
    jsl ScummV5_Controller_ResetInteractionOnRoomInstall_Far
    .endif
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE && (SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $01)
    ; A room install begins a new actor-surface cache lifetime.  This is a
    ; lifecycle reset, not an actor draw and not a backend operation.
    jsl ScummV5_Controller_ResetVisualCache_Far
    .endif
    ; NEXT_GENERATION is a global presentation sequence, not a per-room
    ; installation marker.  Earlier room/camera traffic may legitimately
    ; leave it nonzero before this room is installed.  Every room install must
    ; compose its own descriptor once; otherwise the first present packet for
    ; the new room is silently skipped.
    ; The surface service owns deferred initial publication if the previous
    ; room still has an in-flight presentation.
    jsl Same_VideoSurface_RoomInstalled_Far
    .if SAME_BUILD_SCUMM_CONTROLLER
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_ROOM_READY
    .endif
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
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE && (SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $04)
      ; Semantic actor composition runs after the movement pass.  This later
      ; visual phase only services pending surface work and retries, rather
      ; than taking a second snapshot from a different semantic phase.
      ; Keep the expensive initial actor composition out of hover/verb input
      ; frames.  The semantic publisher remains active in those modes, while
      ; the actor compositor begins when the authored walk presentation mode
      ; owns the scene; this prevents a full surface preparation from
      ; starving the normal input poll.
      sep #$20
      .a8
      lda.l SAME_SCUMM_CONTROLLER_MODE
      cmp #$02
      bcc ScummV5_Visual_Frame__prewalk_actor
      ; A controller sentence is published after the engine pass and is
      ; consumed by the next normal SCUMM frame.  Do not publish the old
      ; standing cache during that mailbox-pending boundary; it would occupy
      ; the surface before the sentence's first coherent moving snapshot.
      lda.l SAME_SCUMM_SENTENCE_API_PENDING
      bne ScummV5_Visual_Frame__skip_actor
ScummV5_Visual_Frame__render_actor:
      jsl ScummV5_Controller_RenderActor_Far
      bra ScummV5_Visual_Frame__skip_actor
ScummV5_Visual_Frame__prewalk_actor:
      ; A stable room may need one initial actor composition.  It is safe to
      ; attempt only after the room's own visual transaction has completed.
      ; With rejected PRESENTs, RENDER_VALID intentionally remains clear; do
      ; not turn that into an eager full-room compose loop while the room
      ; request is still pending.  The surface service owns this lifecycle
      ; gate; the engine does not inspect backend state or carrier details.
      lda.l SAME_VIDEO_SURFACE_PENDING_VISUAL
      bne ScummV5_Visual_Frame__skip_actor
      ; STATUS is a historical result code and may remain LOCKED after a
      ; rejected/deferred attempt.  Ask the neutral service whether the
      ; surface is writable now; do not make a stale status byte the actor
      ; cache gate.
      jsl Same_VideoSurface_CanWrite_Far
      bcs ScummV5_Visual_Frame__skip_actor
      lda.l SAME_SCUMM_CONTROLLER_RENDER_VALID
      bne ScummV5_Visual_Frame__skip_actor
      jsl ScummV5_Controller_RenderActor_Far
ScummV5_Visual_Frame__skip_actor:
    .endif
    jsl Same_VideoSurface_ServiceEvents_Far
    rtl
