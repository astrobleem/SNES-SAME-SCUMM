# Room-55 target evidence

Screened review evidence only. ROMs, savestates, archives, and generated game
payloads remain local.

## Accessor

- ROM SHA-256: `67142583180bee350b07b6632b86a66a6800c15aed3ffe9d6d195be7976ed6de`.
- Build: `SAME_FATE_DEMO_ARCHIVE=/home/chad/SAME-0.2.0/ATLANTIS.zip SAME_SNES_ENGINE=scumm_v5 SAME_BUILD_M24RB=1 SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 SAME_BUILD_SCUMM_M25_MOVEMENT=1 SAME_BUILD_SCUMM_M25A_VALIDATOR=1 SAME_M25A_VALIDATOR_CASE=room55-accessor SAME_BUILD_SCUMM_SCENARIO_FIXTURE=1 bash tools/build_snes.sh`.
- Target validation: `PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py ... --capture-put-actor-sequence` (full command and local output path are retained in the acceptance report).
- The fixture executes the real generated ROM accessor through production
  `putActor` calls for indices 0-63. The target-only marker is `0xA0`: record 0
  sentinel matched and index 64 rejected.
- Independent local decode matched every latest target work-record capture for
  boxes 1-63 (63/63). The first count-0 observation is a pre-yield sampling
  artifact; it is not counted as an independent record-0 capture.
- Effective offsets: 1=`$0012`, 31=`$022E`, 32=`$0240`, 43=`$0306`,
  63=`$046E`; index 64 is rejected.

## Multi-leg movement

- ROM SHA-256: `845abdab907261e26448064861e64d35778a18b4d1a74e8abfa27a8f9feb21aa`.
- Build/validation use the same production compiler and `SAME_M25A_VALIDATOR_CASE=room55-movement`; the local command includes `--frames 5000 --expected-room 49 --light --minimal-observation`.
- Copyright-free target fixture uses normal room install, accessor, BOXM route,
  movement scheduler, and `$AE` wait. Observed route:
  `4,5,9,16,21,25,31,36,41,47,52,57,62,63`.
- Final actor `(24,114)`, walkbox 63, moving 0; wait released; error 0.

## Open gate

The same-source compressor-to-hoist regression is separate. The preserved old
passing ROM is `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`.
The current fresh run reaches room 82 but has not yet reproduced the complete
error-free return lifecycle, so geometry acceptance is not represented as a
hoist PASS here.
