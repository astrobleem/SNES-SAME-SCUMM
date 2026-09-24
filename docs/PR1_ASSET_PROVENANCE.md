# PR #1 audio asset provenance inventory

This is a source/provenance inventory, not a license opinion. The PR history
adds 68 audio-related assets: 28 WAV samples, 2 BRR samples, and 38 MML files.
The original Fate archive is not committed.

## WAV and BRR samples

The files under `audio/fate_s6/samples/` fall into these source groups:

| Files | Count | Observed provenance / modification | Rights and attribution evidence |
|---|---:|---|---|
| `mt32_*.wav` | 21 | Local hash comparison against the `SNES-SuperMonkeyIsland` checkout identifies 12 exact copies from its instrument sample tree and 9 loop-safe derivatives. `loop_safe_manifest.json` records the derived source hashes and loop/resampling parameters. | No asset-specific redistribution grant or attribution terms were found in that checkout. The driver license does not cover these samples. |
| `fate154_ch*.wav` | 7 | Generated from the Fate sound-154 ADLIB extraction described by `ADLIB_ORACLE.md` and `fate154_adlib_manifest.json`; these are transformations of game-derived material. | The archive is user-supplied; no redistribution permission or attribution grant for the source audio was found. |
| `Phantasia_Flute.brr`, `Phantasia_Soft_Bass.brr` | 2 | Exact hash matches to the correspondingly named BRR files in the local `SNES-SuperMonkeyIsland/audio/samples/phantasia/` tree. | No sample-specific license or permission artifact was found in the source checkout. |

The matching source files were present locally during this audit. That establishes
where the bytes came from, not who owns them or whether they may be redistributed.

## MML music data

The 38 added `.mml` files are in `audio/fate_s6/`, its `m21_sound80/` and
`m22_sound80/` subdirectories, `audio/m24ra/`, and `audio/fate_s6/auditions/`.
The committed audit/oracle documents describe the source-derived cue analysis,
channel/program selections, and transformations. The M24R-A fixture material
is separately identified as synthetic where its catalog says so. These facts do
not establish permission to redistribute source-derived musical compositions.

## License and attribution boundary

`audio/fate_s6/TAD-LICENSE.txt` is the TAD driver's zlib license; it is not a
license for the WAV/BRR sample content or MML compositions. The source checkout
has licenses for some bundled tools but no repository-wide audio-content grant
covering the matched sample paths. `audio/fate_s6/auditions/README.md` records
an authorization assertion, but the reviewed tree contains no accompanying
permission record identifying the grantor, scope, attribution, or terms.

Accordingly, provenance is partially identified but redistribution rights and
required attribution remain unresolved. Do not describe this PR as source-only
or infer permission from the absence of an original game archive. A maintainer
must obtain and record applicable permission/attribution evidence or decide on
a history-level asset-removal/replacement plan before merge. Because these blobs
are present in already-published commits, deleting them only from a later tree
would not remove them from the PR history.
