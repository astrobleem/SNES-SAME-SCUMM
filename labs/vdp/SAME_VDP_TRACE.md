# SAME-VDP Trace Format v1

A trace is UTF-8 JSON Lines. Blank lines and lines beginning with `#` are ignored.
The first JSON object is the header; every following object is an event.

## Header

```json
{"format":"same-vdp-trace","version":1,"name":"01_solid_palette","video":{"width":256,"height":224,"timing":"ntsc","mode":"h32"},"scope":"frame-static-mode5"}
```

Version 1 accepts 256/320 widths and 224/240 heights. The SNES milestone-0 backend
currently rejects everything except 256x224 H32.

## Events

`ctrl` writes one 16-bit word to the Genesis VDP control port.

```json
{"op":"ctrl","value":"0x8f02"}
```

`data` writes one 16-bit word to the VDP data port.

```json
{"op":"data","value":"0x0e0e"}
```

`data_words` is a lossless compact form for consecutive data-port writes.

```json
{"op":"data_words","values":["0x0123","0x4567"]}
```

`frame` marks a frame boundary. Milestone 0 renders the final state at the final
frame marker.

```json
{"op":"frame","label":"frame0000"}
```

`comment` carries human-readable context and has no machine effect.

## Deliberately absent from v1 milestone 0

Status/HV reads, FIFO timing, DMA timing, interrupts, scanline timestamps, sprites,
window, Plane B compositing, raster changes and shadow/highlight are not silently
approximated. A backend rejects unsupported state instead of claiming success.
