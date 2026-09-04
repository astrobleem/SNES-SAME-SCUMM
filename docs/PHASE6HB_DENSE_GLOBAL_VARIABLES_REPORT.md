# Phase 6H-B dense SCUMM v5 globals

The Fate profile now derives its ordinary-global contract from the decoded
`MAXS` chunk in `FATEDEMO/PLAYFATE.000`.  The chunk begins at decoded offset
979 (`$03D3`), is 26 bytes, and has SHA-256
`004c043e2371f1f75f81df26184eda89fef95c7d6886b84deeffa07ac1c0f98f`.
Its little-endian fields are 800 ordinary globals, ignored v5 word 16, 2048
bit variables, 200 local objects, 50 arrays, 5 charsets, 100 verbs, 20 new
names, and 80 inventory objects.

The generated dense table is 800 two-byte entries (`$0640` bytes) at
`$7E0800-$7E0E3F`, with half-open end `$7E0E40`.  The declared stack floor is
`$7E1800`, leaving `$09C0` bytes.  The native stack initializes at `$1FFF`;
fresh authentic gates ended at `$1FFF` (LoROM and SA-1 legacy) and `$1FEE`
(Mode-3/BG2).  The accepted preflight owns the deeper-path stack/guard audit.
The historical `$7E2320-$7E233F` bootstrap window remains reserved and zero.

Ordinary reads, result decoding, result reads, and result writes use the one
generated base.  Result offsets remain byte offsets, so Var[799] is `$063E`;
local (`$8000`) and bit (`$4000`) result tags remain disjoint.  Indexed
addition now rejects carry and namespace overflow before final range checking.
`setVarRange` continues advancing by two bytes and rejects the generated end.
Cold engine boot separately clears the complete generated table; room, script,
camera, message, and video lifecycles do not clear it.

Fresh-emulator evidence on all three carriers observed Var[1]=1, Var[33]=2,
Var[119]=0, Var[120]=`$FFFF`, and Var[121]=0.  Thus the authentic `$1A`
instruction at global script 2 `$046B` resolves logical index `$0078`, byte
offset `$00F0`, and physical address `$7E08F0`, then advances to `$0470`.
The verified `$A0` is `stopObjectCode`; it retires global script 2.  The
remaining LSCR 211 subsequently stops at the next genuine unsupported
script-resource start at PC `$029B` (last opcode `$0A`, `SCUMM_ERR_SCRIPT`),
which Phase 6H-B does not implement.

Deterministic ROM SHA-256 identities:

- LoROM legacy: `b9be4afd8673fbf1a372d4ec3ac9c7a674df4a95fc42676ecaec5b0e4352a78e`
- SA-1 legacy: `1de73a28fde61776fef3b0dda5db69015dfa1d4ac60685d7353aa17f4f27991c`
- SA-1 Mode-3/BG2: `8b9223bb49388d687cb8318421e6f95fc3e71d78f96a4461a539a68f71692f01`

Each artifact was built twice with byte-identical output.  Both SA-1 gates
reported unchanged architectural state.  Phase 6G-B video code was not
modified.  The pre/post `make m25a-validator` signature remained the same:
`storage.pasm:36:9: Undefined symbol ScummV5_M23A_ValidateRecord_FarEntry`;
the failure still occurs in the known umbrella M24R-B configuration.
