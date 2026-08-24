# SAME package version 1

The package format is a direct-seek container for ROM, MSU-1, and host fixtures.
It avoids a dynamic filesystem on the SNES.

## Header: 32 bytes

```text
magic[8]       "SAMEPKG\0"
version u16    1
header_size    32
entry_count
entry_size     32
directory_offset
data_offset
flags
crc32          CRC of every byte after the header
```

## Directory entry: 32 bytes

```text
name[8]        ASCII section identifier
kind[4]        CODE, VDAT, ADAT, etc.
flags u16
alignment_log2 u8
reserved u8    must be zero
offset u32
size u32
unpacked_size u32   equals size in v1
crc32 u32
```

Version 1 has no compression. This is deliberate: predictable seeks and bounded
reads matter more than saving host disk space.

## Build

```bash
same package build examples/packages/demo-package.json out/demo.samepkg \
  --poppy-include out/demo-package.inc.pasm
same package inspect out/demo.samepkg
same package extract out/demo.samepkg /tmp/same-package
```

The generated Poppy include is useful during bootstrap. The long-term storage
backend should read the directory at runtime so adding an earlier section does not
require hand-synchronizing every later offset.
