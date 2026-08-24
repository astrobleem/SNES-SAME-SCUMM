# First emulator gate: SAME engine host

Do not import SCUMM, AGI, TAD, storage, or SA-1 donor code before this gate
passes.

## 1. Build identity

Build:

```text
build/same-engine-host.sfc
```

Record SHA-256 and load that exact path in Nexen or Mesen2 from a fresh power-on.
Confirm no stale state or older `same-kernel-demo.sfc` is loaded.

## 2. Engine lifecycle after boot

After at most two VBlanks, the screen should be solid dark red. Read:

| Address | Expected |
|---|---:|
| `$7E2220` | `$01` — conformance demo engine |
| `$7E2221` | `$02` — running |
| `$7E2222` | `$0A` — last engine status `READY` |
| `$7E2224` | `$0001` after a normal engine frame |
| `$7E2226` | increasing total operation count |
| `$7E2210` | frame counter increasing once per VBlank |
| `$7E2212` | backdrop shadow `$0010` |

The lifecycle byte is especially important: an earlier source audit caught a
DBR-relative clear that would have written to `$00:2222` rather than WRAM. Verify
real execution, not only the symbol value.

## 3. Event-ring health

| Address | Expected |
|---|---:|
| `$7E2004` | returns to zero each frame |
| `$7E2006` | zero dropped packets |
| `$7E2008` | zero rejected required packets |
| `$7E200A` | sequence advances |

Observe through at least frame 180 so two heartbeat packets have crossed the
queue. Stop if either loss counter changes or the queue remains nonzero.

## 4. Input and video service

Press and release one control at a time:

| Control | `$7E2212` | Visible color |
|---|---:|---|
| Left | `$7C00` | blue |
| Right | `$03E0` | green |
| B | `$001F` | red |
| A | `$7FFF` | white |

Edge state:

```text
$7E2200 held
$7E2202 previous
$7E2204 pressed
$7E2206 released
```

A held control appears in `pressed` for exactly one poll. Release appears in
`released` for exactly one poll. Holding a control for hundreds of frames must
not create new press edges or packet loss.

## 5. Audio service route

Press Start once. This gate intentionally produces no sound. It proves an engine
can submit a normalized request without touching SPC ports:

| Address | Expected |
|---|---:|
| `$7E2214` | `$00` — `MUSIC_PLAY` |
| `$7E2216` | `$0001` — track 1 |

The request must be consumed in the same frame and must not change video state.

## 6. Acceptance record

Preserve:

- ROM SHA-256;
- Poppy HEAD;
- emulator/version;
- fresh-power-on statement;
- frame and operation-counter ranges;
- lifecycle/status bytes;
- event loss counters;
- screenshot for boot and each color;
- Start request WRAM values.

Only after this evidence exists should the first service extraction gate in
`docs/NEXT_GATES.md` begin.

## Accepted workstation result — 2026-08-22

H0 passed from fresh power-on in the MCP-enabled Nexen build for:

```text
ROM SHA-256 d452760a3089a271eb4cdb7be181e39d4ecdf760e089ae0f306cdec95afc0a0b
ROM size 32768 bytes
reset=$8000 nmi=$8047 irq=$8069
report build/h0-nexen-d452760a3089a271/report.json
report SHA-256 bacaa052cc99c6d11ec28f68e2c38405aa8ac03e421decc00d0ad52d0a88bda7
```

The report retains fresh-power identity, exact WRAM checkpoints, controller-scan
timelines, queue counters, boot/color screenshots, the 240-frame held-input test,
and Start audio routing. The black rows below the 224-line active display in the
239-line Nexen captures are overscan, not an uncommitted backdrop region.
