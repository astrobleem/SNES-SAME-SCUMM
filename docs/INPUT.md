# SAME input

The input service separates physical hardware from guest actions.

## Physical snapshot

The SNES bootstrap polls automatic joypad reads after `$4212` reports completion.
It maintains:

```text
held
pressed  = current & ~previous
released = previous & ~current
```

The host SDK implements the same edge semantics.

## Bundled profiles

- `snes`
- `genesis_3button`
- `arcade_2button`
- `openbor`
- `scumm`
- `agi`

Profiles are target policy. The kernel only transports the physical snapshot.
A Genesis target can later add six-button multiplexing without changing the event
record.

## Initial Genesis mapping

| Genesis | SNES |
|---|---|
| A | Y |
| B | B |
| C | A |
| Start | Start |
| D-pad | D-pad |

This is a starting mapping, not a compatibility requirement.
