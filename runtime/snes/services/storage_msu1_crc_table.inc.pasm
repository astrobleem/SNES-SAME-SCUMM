; Immutable service data, included once beside the checked package directory.
; 256 split 16-bit words, 1024 ROM bytes, no additional mutable state.
; For entry i: repeat c=(c>>1) ^ (0xEDB88320 if c&1 else 0) eight times.
Same_Msu1_CrcTableLow:
    .word $0000, $3096, $612C, $51BA, $C419, $F48F, $A535, $95A3
    .word $8832, $B8A4, $E91E, $D988, $4C2B, $7CBD, $2D07, $1D91
    .word $1064, $20F2, $7148, $41DE, $D47D, $E4EB, $B551, $85C7
    .word $9856, $A8C0, $F97A, $C9EC, $5C4F, $6CD9, $3D63, $0DF5
    .word $20C8, $105E, $41E4, $7172, $E4D1, $D447, $85FD, $B56B
    .word $A8FA, $986C, $C9D6, $F940, $6CE3, $5C75, $0DCF, $3D59
    .word $30AC, $003A, $5180, $6116, $F4B5, $C423, $9599, $A50F
    .word $B89E, $8808, $D9B2, $E924, $7C87, $4C11, $1DAB, $2D3D
    .word $4190, $7106, $20BC, $102A, $8589, $B51F, $E4A5, $D433
    .word $C9A2, $F934, $A88E, $9818, $0DBB, $3D2D, $6C97, $5C01
    .word $51F4, $6162, $30D8, $004E, $95ED, $A57B, $F4C1, $C457
    .word $D9C6, $E950, $B8EA, $887C, $1DDF, $2D49, $7CF3, $4C65
    .word $6158, $51CE, $0074, $30E2, $A541, $95D7, $C46D, $F4FB
    .word $E96A, $D9FC, $8846, $B8D0, $2D73, $1DE5, $4C5F, $7CC9
    .word $713C, $41AA, $1010, $2086, $B525, $85B3, $D409, $E49F
    .word $F90E, $C998, $9822, $A8B4, $3D17, $0D81, $5C3B, $6CAD
    .word $8320, $B3B6, $E20C, $D29A, $4739, $77AF, $2615, $1683
    .word $0B12, $3B84, $6A3E, $5AA8, $CF0B, $FF9D, $AE27, $9EB1
    .word $9344, $A3D2, $F268, $C2FE, $575D, $67CB, $3671, $06E7
    .word $1B76, $2BE0, $7A5A, $4ACC, $DF6F, $EFF9, $BE43, $8ED5
    .word $A3E8, $937E, $C2C4, $F252, $67F1, $5767, $06DD, $364B
    .word $2BDA, $1B4C, $4AF6, $7A60, $EFC3, $DF55, $8EEF, $BE79
    .word $B38C, $831A, $D2A0, $E236, $7795, $4703, $16B9, $262F
    .word $3BBE, $0B28, $5A92, $6A04, $FFA7, $CF31, $9E8B, $AE1D
    .word $C2B0, $F226, $A39C, $930A, $06A9, $363F, $6785, $5713
    .word $4A82, $7A14, $2BAE, $1B38, $8E9B, $BE0D, $EFB7, $DF21
    .word $D2D4, $E242, $B3F8, $836E, $16CD, $265B, $77E1, $4777
    .word $5AE6, $6A70, $3BCA, $0B5C, $9EFF, $AE69, $FFD3, $CF45
    .word $E278, $D2EE, $8354, $B3C2, $2661, $16F7, $474D, $77DB
    .word $6A4A, $5ADC, $0B66, $3BF0, $AE53, $9EC5, $CF7F, $FFE9
    .word $F21C, $C28A, $9330, $A3A6, $3605, $0693, $5729, $67BF
    .word $7A2E, $4AB8, $1B02, $2B94, $BE37, $8EA1, $DF1B, $EF8D

Same_Msu1_CrcTableHigh:
    .word $0000, $7707, $EE0E, $9909, $076D, $706A, $E963, $9E64
    .word $0EDB, $79DC, $E0D5, $97D2, $09B6, $7EB1, $E7B8, $90BF
    .word $1DB7, $6AB0, $F3B9, $84BE, $1ADA, $6DDD, $F4D4, $83D3
    .word $136C, $646B, $FD62, $8A65, $1401, $6306, $FA0F, $8D08
    .word $3B6E, $4C69, $D560, $A267, $3C03, $4B04, $D20D, $A50A
    .word $35B5, $42B2, $DBBB, $ACBC, $32D8, $45DF, $DCD6, $ABD1
    .word $26D9, $51DE, $C8D7, $BFD0, $21B4, $56B3, $CFBA, $B8BD
    .word $2802, $5F05, $C60C, $B10B, $2F6F, $5868, $C161, $B666
    .word $76DC, $01DB, $98D2, $EFD5, $71B1, $06B6, $9FBF, $E8B8
    .word $7807, $0F00, $9609, $E10E, $7F6A, $086D, $9164, $E663
    .word $6B6B, $1C6C, $8565, $F262, $6C06, $1B01, $8208, $F50F
    .word $65B0, $12B7, $8BBE, $FCB9, $62DD, $15DA, $8CD3, $FBD4
    .word $4DB2, $3AB5, $A3BC, $D4BB, $4ADF, $3DD8, $A4D1, $D3D6
    .word $4369, $346E, $AD67, $DA60, $4404, $3303, $AA0A, $DD0D
    .word $5005, $2702, $BE0B, $C90C, $5768, $206F, $B966, $CE61
    .word $5EDE, $29D9, $B0D0, $C7D7, $59B3, $2EB4, $B7BD, $C0BA
    .word $EDB8, $9ABF, $03B6, $74B1, $EAD5, $9DD2, $04DB, $73DC
    .word $E363, $9464, $0D6D, $7A6A, $E40E, $9309, $0A00, $7D07
    .word $F00F, $8708, $1E01, $6906, $F762, $8065, $196C, $6E6B
    .word $FED4, $89D3, $10DA, $67DD, $F9B9, $8EBE, $17B7, $60B0
    .word $D6D6, $A1D1, $38D8, $4FDF, $D1BB, $A6BC, $3FB5, $48B2
    .word $D80D, $AF0A, $3603, $4104, $DF60, $A867, $316E, $4669
    .word $CB61, $BC66, $256F, $5268, $CC0C, $BB0B, $2202, $5505
    .word $C5BA, $B2BD, $2BB4, $5CB3, $C2D7, $B5D0, $2CD9, $5BDE
    .word $9B64, $EC63, $756A, $026D, $9C09, $EB0E, $7207, $0500
    .word $95BF, $E2B8, $7BB1, $0CB6, $92D2, $E5D5, $7CDC, $0BDB
    .word $86D3, $F1D4, $68DD, $1FDA, $81BE, $F6B9, $6FB0, $18B7
    .word $8808, $FF0F, $6606, $1101, $8F65, $F862, $616B, $166C
    .word $A00A, $D70D, $4E04, $3903, $A767, $D060, $4969, $3E6E
    .word $AED1, $D9D6, $40DF, $37D8, $A9BC, $DEBB, $47B2, $30B5
    .word $BDBD, $CABA, $53B3, $24B4, $BAD0, $CDD7, $54DE, $23D9
    .word $B366, $C461, $5D68, $2A6F, $B40B, $C30C, $5A05, $2D02

