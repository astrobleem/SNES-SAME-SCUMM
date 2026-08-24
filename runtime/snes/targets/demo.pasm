; SAME 0.1 target-lifecycle compatibility shim.
; New code calls Same_Engine_* directly; legacy experiments may retain these
; labels while migrating to the engine host.
Same_Target_Boot:
    jsr Same_Engine_Boot
    rts
Same_Target_Frame:
    jsr Same_Engine_Frame
    rts
Same_Target_Shutdown:
    jsr Same_Engine_Shutdown
    rts
