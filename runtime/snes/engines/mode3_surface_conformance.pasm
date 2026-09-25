; Copyright-free production Mode-3 backend fixture. The engine-facing entry
; points remain in bank zero; all implementation lives with the selected far
; backend and communicates through the production event queue.
SAME_ACTIVE_ENGINE_ID = SAME_ENGINE_DEMO

Same_ActiveEngine_Boot:
    jsl Same_Mode3_Fixture_Boot_Far
    clc
    rts

Same_ActiveEngine_Frame:
    jsl Same_Mode3_Fixture_Frame_Far
    clc
    rts

Same_ActiveEngine_Suspend:
    clc
    rts
Same_ActiveEngine_Resume:
    clc
    rts
Same_ActiveEngine_Shutdown:
    clc
    rts
