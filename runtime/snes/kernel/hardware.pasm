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

; DMA channel 7 is reserved by the kernel commit queue.  Clients describe a
; transfer; only runtime/snes/kernel/dma.pasm programs these registers.
DMAP7            = $4370
BBAD7            = $4371
A1T7L            = $4372
A1B7             = $4374
DAS7L            = $4375
