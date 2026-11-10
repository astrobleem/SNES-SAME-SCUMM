; Engine-defined generic DOS v5 cursor data, derived from cursor.py strokes.
; 4 shapes x 16 rows x LE u16; bit 15 is the leftmost screen pixel.
; Shape IDs: crosshair, hourglass, arrow, hand. Total payload: 140 bytes.
; Caller chooses ROM placement; no bank/org or runtime state is defined here.
; Display shape is 16x16. Project the source anchor through the room grid
; before applying these UNSCALED pixel hotspots. No Loom glyph overrides.
ScummV5_Cursor_Masks:
; Shape 0
    .byte $80,$00,$80,$00,$80,$00,$80,$00,$80,$00,$80,$00,$00,$00,$3F,$7E
    .byte $00,$00,$80,$00,$80,$00,$80,$00,$80,$00,$80,$00,$80,$00,$00,$00
; Shape 1
    .byte $00,$00,$FE,$7F,$06,$60,$0C,$30,$18,$18,$30,$0C,$60,$06,$C0,$03
    .byte $60,$06,$30,$0C,$98,$19,$CC,$33,$E6,$67,$FE,$7F,$00,$00,$00,$00
; Shape 2
    .byte $00,$00,$00,$40,$00,$60,$00,$70,$00,$78,$00,$7C,$00,$7E,$00,$7F
    .byte $80,$7F,$C0,$78,$00,$7C,$00,$46,$00,$06,$00,$03,$00,$03,$80,$01
; Shape 3
    .byte $00,$1E,$00,$12,$00,$12,$00,$12,$00,$12,$FF,$13,$49,$12,$49,$12
    .byte $49,$F2,$01,$90,$01,$90,$01,$90,$01,$80,$01,$80,$01,$80,$FF,$FF
ScummV5_Cursor_Hotspots:
    .byte $08,$07,$08,$07,$01,$01,$05,$00
ScummV5_Cursor_Colors:
    .byte $0F,$0F,$07,$08
