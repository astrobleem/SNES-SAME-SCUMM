# Poppy rules enforced by SAME

SAME uses Chad's `astrobleem/poppy` fork only.

## Required fork fix

`ec005c196eedabf7d0c25ff6336398c427dd43ac` must be an ancestor of the build
checkout. It fixes resumed-bank label and byte placement.

## Source rules

1. Included files use fully qualified global labels. `@` local labels can
   mis-resolve when reached through `.include`.
2. Every branch target that reaches a width-dependent immediate re-establishes
   width and includes `.a8` or `.a16`; index-sensitive code includes `.i16`.
3. There is no `stz.l` instruction on 65816.
4. Absolute-long indexed addressing exists with X, not Y.
5. Standalone `^(Label)` bank-byte expressions are forbidden; use a generated or
   literal bank constant until the fork fixes that operator.
6. WLA-DX memory-map and ROM-bank directives do not belong in Poppy source.
7. Any `$7E:xxxxxx`/far WRAM symbol requires an explicit `.l`-capable access. Bare or `.w` access is DBR-relative and can hit hardware instead of WRAM. For opcodes without a long form, load/store through an accumulator sequence or a proven low-WRAM mirror.
8. A conditional branch is still limited to ±127 bytes. Use inverted condition +
   `brl`, or a leaf routine, when the assembler reports a range error.

Run:

```bash
python tools/lint_poppy.py runtime/snes/main.pasm
```

This check does not prove assembly or hardware behavior. It catches the known
silent/misleading source shapes before invoking Poppy.
