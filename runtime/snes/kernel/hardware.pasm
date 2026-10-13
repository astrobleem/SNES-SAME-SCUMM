; SAME SNES hardware register subset
INIDISP          = $2100
BGMODE           = $2105
MOSAIC           = $2106
BG1SC            = $2107
BG2SC            = $2108
BG12NBA          = $210B
BG1HOFS          = $210D
BG1VOFS          = $210E
BG2HOFS          = $210F
BG2VOFS          = $2110
OAMADDL          = $2102
OAMADDH          = $2103
OAMDATA          = $2104
VMAIN            = $2115
VMADDL           = $2116
VMDATAL          = $2118
CGADD            = $2121
CGDATA           = $2122
TM               = $212C
TS               = $212D
CGWSEL           = $2130
CGADSUB          = $2131
SETINI           = $2133
NMITIMEN         = $4200
MDMAEN           = $420B
HDMAEN           = $420C
HVBJOY           = $4212
JOY1L            = $4218
RDNMI            = $4210
MEMSEL           = $420D
APUIO0           = $2140
APUIO1           = $2141
APUIO2           = $2142
APUIO3           = $2143

; MSU-1 is accessed only by SAME's storage/audio services. Engine, SCUMM and
; video consumers use service calls and never name these registers directly.
MSU1_STATUS       = $2000 ; bit 7=data busy; bit 6=audio busy; bit 3=track error
MSU1_DATA         = $2001 ; serialized auto-incrementing data port
MSU1_ID0          = $2002 ; read-only "S-MSU1" identity bytes
MSU1_ID1          = $2003
MSU1_ID2          = $2004
MSU1_ID3          = $2005
MSU1_ID4          = $2006
MSU1_ID5          = $2007
MSU1_SEEK0        = $2000 ; writes: offset byte 0..3; byte 3 commits seek
MSU1_SEEK1        = $2001
MSU1_SEEK2        = $2002
MSU1_SEEK3        = $2003
MSU1_TRACK_LO     = $2004 ; writes: low then high commits track selection
MSU1_TRACK_HI     = $2005
MSU1_VOLUME       = $2006
MSU1_CONTROL      = $2007 ; bit 0 play; bit 1 repeat

; DMA channel 7 is reserved by the kernel commit queue.  Clients describe a
; transfer; only runtime/snes/kernel/dma.pasm programs these registers.
DMAP7            = $4370
BBAD7            = $4371
A1T7L            = $4372
A1B7             = $4374
DAS7L            = $4375
