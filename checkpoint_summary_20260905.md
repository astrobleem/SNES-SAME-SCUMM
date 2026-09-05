# Current checkpoint summary

- Branch: `review/hoist-message-lifetime`.
- Published base: `3476f816fc8766f90f790699da059ba96aee232c`.
- Broad implementation commit `3c88f54516bb04700ce353fb51e1d4f8c0627e6e`
  remains outside this review branch.
- `ATLANTIS.zip` is authoritative full Fate source locally; demo data is
  incomplete. Archives, ROMs, savestates, and generated resources are not
  published here.
- Geometry acceptance evidence is now target-backed: accessor ROM
  `67142583180bee350b07b6632b86a66a6800c15aed3ffe9d6d195be7976ed6de`,
  witness `0xA0`, 64 production calls, exact independent matches for boxes
  1-63 plus target-verified record 0 and index-64 rejection. Standalone
  movement ROM `845abdab907261e26448064861e64d35778a18b4d1a74e8abfa27a8f9feb21aa`
  crosses `4,5,9,16,21,25,31,36,41,47,52,57,62,63` and ends idle at
  `(24,114)`, box 63, with wait released.
- Hoist remains OPEN for fresh same-source confirmation. Preserved prior
  passing ROM/report is `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`.
  Fresh current root-49 acceptance reached room 82 but reported a downstream
  ordinary error; do not label the current hoist gate PASS.
- Headless message behavior retains logical lifetime; old auto-clear wording is
  superseded by the correction above.
