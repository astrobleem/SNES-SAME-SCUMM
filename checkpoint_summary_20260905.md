# Current checkpoint summary

- Branch: `review/hoist-message-lifetime`.
- Published base: `3476f816fc8766f90f790699da059ba96aee232c`.
- Broad implementation commit `3c88f54516bb04700ce353fb51e1d4f8c0627e6e`
  remains outside this review branch.
- `ATLANTIS.zip` is authoritative full Fate source locally; demo data is
  incomplete. Archives, ROMs, savestates, and generated resources are not
  published here.
- Accepted path: startup42 -> room 1 -> room 42 -> compressor -> LSCR 207 ->
  authored room 82, with `error=0` and observed object/bit effects.
- ROM SHA-256:
  `75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`.
- Local evidence: `build/startup42-hoist-debug38-effects/report.json`.
- Headless message behavior retains logical lifetime; old auto-clear wording is
  superseded by the correction above.
