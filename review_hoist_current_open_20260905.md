# Current same-source hoist regression

This screened note records the remaining open gate. It contains no ROM,
savestate, ATLANTIS bytes, or generated game payload.

## Geometry gates

- Production room-55 source/cooked geometry is 64/64 identical.
- The target accessor uses the corrected 18-byte (`$12`) stride.
- ROM-driven target witness: 64 production `putActor` calls; record 0 is
  checked by the fixture verifier, records 1–63 are independently compared
  from target observations, and index 64 is rejected. Witness offsets are
  1=`$0012`, 31=`$022E`, 32=`$0240`, 43=`$0306`, 63=`$046E`.
- The copyright-free production movement fixture traversed
  `4,5,9,16,21,25,31,36,41,47,52,57,62,63`, ended at `(24,114)` in box 63,
  became idle, and released `$AE waitForActor`.

## Hoist evidence

The preserved earlier passing ROM is identified by SHA-256
`b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`.

The fresh current root-49 ROM is
`b6a9f823d91b67b09e7f0eec3fe343e7fa85e87142646882ff912c609626ef73`.
It consumed `(8,492,0)` and `(8,500,497)`, observed compressor state,
`setState(500,0)`, bit 444, and entered room 82. Its first ordinary failure
was `SCUMM_ERR_VARIABLE` (12), room82 program 245 / LSCR 201, PC `$0003`,
opcode `$00`; no room82 return/settle with error 0 was observed.

A fresh current build with the same controlled root now diverges earlier at
frame 34 in room49 program 208, PC `$0006`, opcode `$26`, error 2, before
either sentence. Removing the additional cooked rooms did not remove that
divergence; the experiment ROM SHA-256 is
`51fda4577129381fc16abc822dacaa76af100ba7f95053a80ecc05ed78cb7804`.
This is a configuration/runtime regression requiring follow-up; it is not
claimed as a geometry failure.

## Reproduction identities

Target commands and full build environments are recorded in the project
checkpoint. The focused source/test publication intentionally excludes the
ROMs and all game-derived resources.
