#!/usr/bin/env python3
"""Generate a fail-closed profile table for bounded compiled sections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if audit.get("schema") != "same_fate_sound80_m22_sections_v1":
        raise RuntimeError("compiled-section audit schema differs")
    logical = int(audit["logical_sound_id"])
    route = audit["cue_route_history"]
    token = int(audit["boundary"]["token"])
    text = f"""; Generated from a source-bound compiled-section audit. Do not hand-edit.
; Input staging: arg0 low=logical cue, high=pending hook;
; arg1 low=current route kind, high=current route value.
; Output staging: arg0 low=selector, high=boundary token;
; arg1 low=current section, high=selected continuation.
Same_Music_MapSectionPlan:
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp #${logical:02X}
    bne Same_Music_MapSectionPlan__reject
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+1
    cmp #$08
    bne Same_Music_MapSectionPlan__reject
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    cmp #$01
    bne Same_Music_MapSectionPlan__reject
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+1
    cmp #${int(route['value']):02X}
    bne Same_Music_MapSectionPlan__reject
    lda #$01
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #${token:02X}
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+1
    lda #$01
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda #$02
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+1
    clc
    rts
Same_Music_MapSectionPlan__reject:
    sec
    rts
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"{args.output}: cue={logical} route={route['kind']}:{route['value']} hook=8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
