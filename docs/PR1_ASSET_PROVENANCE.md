# PR #1 audio/media provenance and disposition

This is a factual provenance inventory, not a legal opinion. It compares
`3476f816fc8766f90f790699da059ba96aee232c` with reviewed PR head
`a983e49edf1ce947efff68dd362ea076538f3d36`. The table lists every added
`.wav`, `.brr`, and `.mml` asset (28 WAV, 2 BRR, 38 MML). All 68 were added by
`3c88f54`.

## Group findings

The table's common fields are recorded here so a disposition is not mistaken
for a file-by-file rights finding.

| Group | Files / purpose and consumers | Observed source and author | Rights / derivation / reproducibility | Required and disposition |
|---|---|---|---|---|
| W1 | 21 `mt32_*.wav` instrument, loop, and zone samples. Historical Fate/Monkey sampled-audio profile builders, audition captures, and music-graph tools referenced them. | Twelve were exact byte matches to samples in a local `SNES-SuperMonkeyIsland` checkout; nine were derived loop/resample variants. Source identity is established; sample author/rights holder is not. | The local source checkout yielded no sample-specific redistribution grant or attribution terms. The nine derivatives remain derived from those source samples. No reproducible, cleared source package was present. | Not required by `make test`, `make validate`, default `make snes`/`make s5-snes`, or current M24R-A fixture. **REMOVE** all; historical title-audio targets are fail-closed. |
| W2 | Seven `fate154_ch*.wav` sound-zone samples, used by the historical Fate sound-154 TAD conversion. | Generated from an extracted Fate demo sound-154 ADLIB/OPL capture and patch data using `build_fate_adlib_samples.py`; the captured sound is game-derived. | Conversion changes representation, not source provenance. No separate redistribution grant for the sound data was found. The generator is retained only as an explicit external-input research tool and writes outside tracked source by default. | No ordinary tests or current default build need these. **REMOVE** all. |
| B1 | Two `Phantasia_*.brr` sample assets, used by a historical Fate sound-80 route. | Exact byte matches to BRR files in the same local `SNES-SuperMonkeyIsland` tree; no author attribution was established. | No sample-specific redistribution license/permission was found. BRR encoding does not change the source identity. | Not required by current tests or builds. **REMOVE** both. |
| M1 | Six audition MML files: scales/ranges and instrument-zone listening fixtures. | Project-authored test patterns, but coupled by names/instrument references to the W1 unlicensed sample bank and historical review workflow. | Their short scale patterns are not copied melodies, but the committed package did not provide a self-contained, cleared instrument bank and the files were not required by current tests. Conservatively removed with that asset-dependent workflow. | Not required by current tests/builds. **REMOVE** all six. |
| M2 | Eight M21 sound-80 MML files: six used-range programs plus default and hook-14 arrangements. | Converted/selected from Fate sound-80 data and the W1 sample bank; generated/maintained by the historical Fate route builder. | Source-derived cue data and sample references; no applicable music/sample redistribution evidence was found. | Only historical Fate profile builds used them; those builds are guarded. **REMOVE** all eight. |
| M3 | Four M22 sound-80 MML files: three used-range programs plus hook/section arrangement. | Derived from Fate sound-80 branch/section data and the W1 bank; generated/maintained by the historical section builder. | Transformation does not remove source-derived composition/sample identity. No redistribution basis was found. | Only historical Fate profile builds used them; those builds are guarded. **REMOVE** all four. |
| M4 | Nineteen root `audio/fate_s6/sound_*.mml` cue arrangements. | Derived from Fate sound resources, their event/timing structure, or the W1/W2 sample identities. | The arrangements and source-linked musical content have no separate grant documented here. MML is not made original merely by being a text conversion. | Not required by current default builds/tests. **REMOVE** all nineteen. |
| M5 | `audio/m24ra/m24ra_async_layer_transition.mml`, one synthetic asynchronous-layer conformance composition. | Original SAME fixture, authored in the repository and reproducibly compiled by the M24R-A build scripts; its own header identifies the fixture and author. | It is not derived from a game cue or sample. The root `LICENSE` dedicates original project material to the public domain. Its generated waveform is produced deterministically by `tools/build_m24ra_fixture.py`; no WAV/BRR output is committed. | Required by the supported M24R-A diagnostic build. **CLEAR — RETAIN**. |

## Added media identities

Each row is the exact path, byte size, SHA-256, introducing commit, and
disposition at reviewed head. Group codes refer to the full purpose/source/
consumer/rights/required findings above. The W1/W2/B1/M1–M4 assets are absent
from the resulting asset-clearance tree; their historical Git objects remain
in ancestors because published history was not rewritten.

| Path | Bytes | SHA-256 | Introduced | Group / disposition |
|---|---:|---|---|---|
| `audio/fate_s6/auditions/bass_range.mml` | 271 | `188df9c7e73efce10b8080f8e3c818b2412359514d9947e9d33462f3af975d16` | `3c88f54` | M1 / REMOVE |
| `audio/fate_s6/auditions/flute_zones.mml` | 495 | `6d141d525611603158172540444545213510a53851f467387863603e096eb334` | `3c88f54` | M1 / REMOVE |
| `audio/fate_s6/auditions/marimba_zones.mml` | 439 | `d9ff90895106a17928d6328e731a11afa20007d2f8de19de483a168684f2d58f` | `3c88f54` | M1 / REMOVE |
| `audio/fate_s6/auditions/organ_zones.mml` | 319 | `b19a070ef20915c6613b2a65ff4afbd79651a405b649ed04d13dc0984cdd80b8` | `3c88f54` | M1 / REMOVE |
| `audio/fate_s6/auditions/pad_zones.mml` | 421 | `d05b64d72755455cf759185dee2e70ead3617a1a5b6925d0a9ed2c94356cf2de` | `3c88f54` | M1 / REMOVE |
| `audio/fate_s6/auditions/percussion.mml` | 376 | `ad2f477076ebfe5a0027c680b490b8b10827d029c2156851ebabc448f8d3e723` | `3c88f54` | M1 / REMOVE |
| `audio/fate_s6/m21_sound80/program_32_used_range.mml` | 384 | `157ff9edb2631f75db2f5d81eb6e20cf7de99f7387a392569c5d70651705d4a5` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m21_sound80/program_33_used_range.mml` | 506 | `6e45a9834d05dbb4e05f970207fe538e9b23b41342c611994d81d82b280dbd81` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m21_sound80/program_50_used_range.mml` | 424 | `a5ffc57083fa371d43bf19a0a5f44c3d57757713c7c4f57b0c8f9e1c33eee4e7` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m21_sound80/program_57_used_range.mml` | 487 | `bdd804dafce718e178b36b87db1b4a362a490e37d20b4576120f030a6042a0e8` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m21_sound80/program_77_used_range.mml` | 468 | `8d5e523317029818048427d62013d9735af734e47584b5dc58c3afe9bcd7e236` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m21_sound80/program_82_used_range.mml` | 424 | `88f10016362d8472c50d9e97e01799531062f43b7b440a9464823abed80e46dd` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m21_sound80/sound80_default.mml` | 6941 | `113efa85ec5f6b07758d1df2172690893d1d83a4be1d7293f6029831ef339b39` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m21_sound80/sound80_hook14.mml` | 2941 | `d3e30d970f2a500cfd51e8154dde5f640a374cbd10df310f944de5775edb1c31` | `3c88f54` | M2 / REMOVE |
| `audio/fate_s6/m22_sound80/program_107_used_range.mml` | 470 | `fab0b8118d9e072f81c5be5da4d8f68ac5198d99386298e273c2ed25a9e4c278` | `3c88f54` | M3 / REMOVE |
| `audio/fate_s6/m22_sound80/program_50_used_range.mml` | 424 | `457ad4201280df67b52a4c1bf7bebc8693e4a88dbee263b29ee38f7cb92c4fd7` | `3c88f54` | M3 / REMOVE |
| `audio/fate_s6/m22_sound80/program_97_used_range.mml` | 386 | `ce9e8bccaa2483cff6ee2069fddcace40e333fa72c465d20cd4f8d38f284f080` | `3c88f54` | M3 / REMOVE |
| `audio/fate_s6/m22_sound80/sound80_hook14_hook8_sections.mml` | 9615 | `3b95889950ecf14afcf4dd04231f5b7dad3a6a10939495d948ff891242adc89b` | `3c88f54` | M3 / REMOVE |
| `audio/fate_s6/samples/Phantasia_Flute.brr` | 2531 | `cfc130314b6860d12c9144b8d856ce2b192f26cc94f1f9abc3b3525df931943b` | `3c88f54` | B1 / REMOVE |
| `audio/fate_s6/samples/Phantasia_Soft_Bass.brr` | 812 | `8a200226b881a267425460a5ca09781f6ed5cb9c880c5842f19d6a798a866e89` | `3c88f54` | B1 / REMOVE |
| `audio/fate_s6/samples/fate154_ch1_high.wav` | 6476 | `c46d0020077ff8803477a97284edc6a09c8e64a484a3d493a6b557425a4baa7e` | `3c88f54` | W2 / REMOVE |
| `audio/fate_s6/samples/fate154_ch1_low.wav` | 7788 | `49f2c6f9dcd7624798cd1598cae37d9986f39543739ea17068027c9206594bfb` | `3c88f54` | W2 / REMOVE |
| `audio/fate_s6/samples/fate154_ch2_mid.wav` | 4748 | `77c99efdfe384219d00ca303ef8ecb7e947fbf2b156e830baa883659195e71ed` | `3c88f54` | W2 / REMOVE |
| `audio/fate_s6/samples/fate154_ch4_mid.wav` | 5740 | `3204140f7ec4574a7e6162f4daff871da09c214d67b3dbc2b285d8efa49aa93b` | `3c88f54` | W2 / REMOVE |
| `audio/fate_s6/samples/fate154_ch5_high.wav` | 4748 | `a9d3ce073f1f59afce93eba2f37a7b08eed3f63bb727cd28543ef42ff8279fb3` | `3c88f54` | W2 / REMOVE |
| `audio/fate_s6/samples/fate154_ch6_high.wav` | 8204 | `3b895ca9a2d724d3bf8312871ead22e5a1719fa195ea1ab528e4fd537f030bfa` | `3c88f54` | W2 / REMOVE |
| `audio/fate_s6/samples/fate154_ch6_low.wav` | 8492 | `03ee835e35a9ee2327e9e5ca894fefeb9fa9036eb8d23925668dddc72e985a16` | `3c88f54` | W2 / REMOVE |
| `audio/fate_s6/samples/mt32_drum_kick.wav` | 6444 | `2f947a4a8794ed616c8376caea2ba45a36fbce266fae73a32d387464cef28691` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_drum_n38.wav` | 14764 | `b8c4128bab40873c78a17ab63d91a0ab274690ceb552ec7de785cdb27b8876e8` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_lead_flute.wav` | 15404 | `123d578c976d86c8faba6df669078f3b672572b2fd4cbf1753d34d3e2c4af7da` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_marimba.wav` | 5804 | `2bfb2b7df66ed53e5569eb28544d76bf8679c062376f46f17007408419495c3f` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_marimba_low.wav` | 5644 | `3e3409265ff44ccd426b5e4bf3747685e5a5eff774e31881c0a2fea7136ce1a9` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_organ.wav` | 23596 | `f3da09a70ea6eb4adf7aaa85d7bc376445c484619204c775fac408ac5e5f84da` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_organ_cycle.wav` | 236 | `611925f99b15a6ab5f957d76b57a696d21d2d19b188f2cb62799e19377d08e7d` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p13.wav` | 25836 | `101b8549d1b5cba8f503a8bdecc630c825eee44edc4497465415275690e5030e` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p13_low.wav` | 12268 | `b07c086a484f91e488ce5dedd4f118a54d83b60c652ed0c377d8b69fd940e4d7` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p74.wav` | 14380 | `37629d1ee508d9d1d17a4ebe02619a22e9301fdd2d7f4d31bcfbcd34a5ded596` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p74_cycle.wav` | 428 | `6300ac1f74b88259e9f7a45e909d543f28f0193084917d4ee8dd6a40bd48b883` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p74_cycle_x2.wav` | 236 | `fc7d29783acea7a6298e110b92c6c017735ec6ff7fe8f8716316f5cbf8c5f109` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p74_cycle_x4.wav` | 140 | `3b264692dccd3da63bb03bc4de06a04cd601925190edad8d8364460c2f1958d4` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p74_low.wav` | 9548 | `d3e2ae8c9603960d081e9a7faa16680193a899a32f451d22cd8f1f71388dccbf` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p74_low_x2.wav` | 4846 | `dec735bf37825046c1e9fae33df2ba4d3f1fb1c2277952905c6b35d2696d3ffa` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p74_low_x4.wav` | 2478 | `bb72dc540d38f8031dd1a56a1cbefb8d804201f7db7c91f9a076d42e2d924942` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p88.wav` | 12492 | `26d24605e1848483e3d8cccaf3320836b3c06fe15b25f273ab1d2edad6d013eb` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p88_cycle.wav` | 172 | `46f9898214a712228ed046e230bce8b2d5b67d34007857ed83e80b8a88261920` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p88_cycle_x2.wav` | 108 | `2fb5861e6b6b182fe2e39a55c223c4827c2dab37d2a6db61644039ec25429483` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p88_low.wav` | 17516 | `21149b493b595484fca1eab8625d5691cb41cad04b616cce218abcf635e1b8f3` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/samples/mt32_p88_x2.wav` | 6318 | `d17ad545704c8c1f8585c01a0fea88615062a2e4a3a63b57bf42bf8aa50363ce` | `3c88f54` | W1 / REMOVE |
| `audio/fate_s6/sound_117.mml` | 777 | `b8979d8d58bc6c0c9e27bfb6e7dc7ffa55e7855a6c45505197c5f44aca043e87` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_141.mml` | 473 | `a74e8d9377d13598a64bf5fe381174d6586102ed187f414ccee6498052d6db72` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_150.mml` | 2789 | `497c75ba164a0aff6f1277afc1744385b4dbf2f1aa5fc12006696e0645158248` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_153.mml` | 4441 | `d746d526a6b491f708d1a1f78bda3800e8bf5a680a16e38fe00a721c4bd15933` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_154.mml` | 2185 | `45110f50f2b4d4ff31a922f8eb2c43d886dbba5940dea8dae5ea0b3f035a5a18` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_17.mml` | 837 | `34ce37144471ac422c69a5aed7f3bd3f39fe75ba4fc9fdd7a5f4413355d95015` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_172.mml` | 402 | `c7aeae47472546f7e33a5b6219d900703a5a791d3be717246e230fac5d362542` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_18.mml` | 2810 | `efa3af32ff425c12f9c93a35c4723c0768697ba95dbbca387c92d6a36cd196fe` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_183.mml` | 3136 | `0fdfde339a39461a8b2d8224b02b9a959c91fa1653576d068fb2a4da247ab9a5` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_185.mml` | 618 | `c7333414a5d6a810b035e020481d93694eecb1ea1afd726eb16e275da542aeb8` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_190.mml` | 497 | `f0c14e1fc60e2fb8dbb93d793dc72ffbe96fc876a63ed7c60e659aae15e36368` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_192.mml` | 666 | `0f4b0b030d7354e4785ba9fb3ff303192b88304158254f4cdd9f5f39ddfba63c` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_201.mml` | 469 | `d2c0fbbe223b1e6b4ce02b79bfc80d59ba9ade23dcc6652fa5ca3e6553a94332` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_202.mml` | 469 | `60e16cfed5526c8cc572a599f15fdecd8f0d81f99e809b93a380ac1c8fe3b394` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_207.mml` | 469 | `80fa286a32b25292575bab9c35d67d417c0db32c26265fc115eda9ec833cd3f7` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_78.mml` | 1975 | `bdfcea9e6d80db94d6d91a87c00c9d593342a0475afeb362c967eeb84c86f44f` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_81.mml` | 2057 | `6d73656df952aaf004513b61fc30b8061856e2b5d9919c185ba90865fed3165b` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_83.mml` | 2128 | `553a79f64cd171c74f8931c5adade7b7f3070334669a7981f66ef27f13d2a942` | `3c88f54` | M4 / REMOVE |
| `audio/fate_s6/sound_91.mml` | 674 | `3e7780b60e7cea451f0324c7a3e7e55afa094a9e0b8d42ee111196e06a435765` | `3c88f54` | M4 / REMOVE |
| `audio/m24ra/m24ra_async_layer_transition.mml` | 970 | `67810cb05458ec6fcceec12b5f98cde5a8ac3ee303bee51761c3231b42c5e410` | `3c88f54` | M5 / CLEAR — RETAIN |

## Other embedded media and generated inputs

The retained QTMA fixtures are short, project-authored synthetic score/container
test inputs, not game captures. They are consumed by `tests/test_music_*`,
`tests/test_qtma_mov.py`, and the corresponding QTMA build graphs; they are
required for the generic music import/timing/segmentation coverage. The root
`LICENSE` public-domain dedication covers original project material.

| Retained input | Bytes | SHA-256 | Introduced | Purpose / basis |
|---|---:|---|---|---|
| `examples/resources/music/qtma_m2_fixture.hex` | 465 | `650af33ab40519e3efe1513f8f38f22e49ff4cc0c2abad0c027112d893fd019d` | `3c88f54` | Synthetic M2 score fixture; parser/timing/playback tests. |
| `examples/resources/music/qtma_m13_movie.hex` | 1073 | `113dcd7865dee9c0cdd22a51ef57df537b1a49ed7c0e44b348218de3e3568250` | `3c88f54` | Synthetic M13 movie/MUSI fixture; MOV importer tests. |
| `examples/resources/music/qtma_m14_movie_600.hex` | 1073 | `ed6ea9d0bbf10b95d7d6cd284a420d7b291c2f45e4e0dc0d3e9fbb7a2cc4e111` | `3c88f54` | Synthetic 600 Hz timing fixture; rational timebase tests. |
| `examples/resources/music/qtma_m10_bank.json` | 323 | `faa1ec06857c9f67347f01fe1be6f91b6ab1e93f9081019cf9884155f0f5bbbf` | `3c88f54` | Integer-generated triangle/noise test-bank recipe, no waveform payload. |
| `audio/m24ra/m24ra.terrificaudio` | 835 | `27bbeb2cf4e670dc179a0a621d3f8ee9c3ab74abe4267c42e57e0ad14a705896` | `3c88f54` | Original TAD project wrapper for the M24R-A fixture; root project license. |
| `audio/m24ra/catalog.json` | 474 | `e38e9ebc4458d8b17f8d549a59d0442d6b85bfcc4c2fa7c8f72f3c1075b28b10` | `3c88f54` | Catalog metadata for the synthetic M24R-A song, not audio. |

The M24R-A project is compiled with `tools/build_m24ra_fixture.py`. That script
generates a 3,200-frame, 32 kHz mono signed-16 waveform from a deterministic
440 Hz additive harmonic formula (harmonics 1–8, amplitude scale 0.22) into
ignored `build/` output. Its SHA is recorded in the generated fixture report;
no generated WAV, BRR, or other audio binary is committed.

The remaining `qtma_m10/m13/m14` build graphs/catalogs and `qtma_m2_trace.json`
and `qtma_m3_reference.json` are authored fixture metadata/expected results,
not captured performances. The `fate_s6_compiled.json` and
`monkey_v5_compiled.json` files are metadata-only identity/duration/route
catalogs, not embedded media; they are used only by explicitly selected
external-data profiles and the bounded profile preflight, not default builds.

The two added `.bin` paths in that commit are generated tilemaps for the SA-1
surface/video labs, not audio/sample payloads. There are no added SPC/MOD audio
payloads hidden elsewhere in the tree, and no original resource archive is
tracked.

The following generated/source inputs were also removed with the uncertain
media. The hashes identify the exact reviewed-head files; all were introduced
by `3c88f54`. These are not additional WAV/BRR/MML counts, but they contain
reproduction instructions, sample identities, composition data, or routes to
the same unresolved material.

| Path | Bytes | SHA-256 | Purpose / finding | Disposition |
|---|---:|---|---|---|
| `audio/fate_s6/fate.terrificaudio` | 9362 | `0052a3cde3d835c56e5c5d964c3d7b1e7723c81c6685e03b86fe4f2489910dd8` | TAD project embedding Fate-derived MML and references to the W1/W2 bank. | REMOVE |
| `audio/fate_s6/fate_tad_layout.inc.pasm` | 1328 | `36bee1c542d060cd75ad75346561f7debf8a79a26c6478d0ac32390ede8860fc` | Generated offsets/layout for the removed Fate TAD image; not independently needed. | REMOVE |
| `audio/fate_s6/samples/fate154_adlib_manifest.json` | 4832 | `90b0eaca9fa29afdf6c4f8650a1898af25364b4039a8962c01e3a514e25ef255` | Bank metadata and hashes for W2 sound-154-derived samples. | REMOVE |
| `audio/fate_s6/samples/loop_safe_manifest.json` | 2207 | `56f17e53e38f1bad05f259e3a87da8b8af67a64041a63a9740150c65b62118e4` | Source/output identities and derivation parameters for W1 loop assets. | REMOVE |
| `audio/fate_s6/m21_sound80/manifest.json` | 9524 | `494e03389d2395c58158ad34ada9a29e2cc73b74313facbf890fafc0d0c20231` | Fate sound-80 route and output audit metadata. | REMOVE |
| `audio/fate_s6/m21_sound80/sound80_default.audit.json` | 1208 | `bf180e6ebb482e685f580b2c69e39bc3c9db956776cffa92a22a67ab876c8b28` | Source-derived default-cue audit. | REMOVE |
| `audio/fate_s6/m21_sound80/sound80_hook14.audit.json` | 1280 | `8c40f9b70c91df334c921987d90884da4abd2e8bd2c0cff696a4898993d42033` | Source-derived hook-cue audit. | REMOVE |
| `audio/fate_s6/m22_sound80/audit.json` | 35499 | `0011262743113e35b3c1be72482eac62bf6311ca773d78ffd76f3be9d5f013ff` | Detailed Fate branch/section and music audit. | REMOVE |
| `audio/fate_s6/m22_sound80/instrument_bank.json` | 4727 | `677b60a89dbb3637ed15192a58b8aa2b4891bfe241cc4941815baf2ebfbc26f9` | M22 bank map referencing W1 samples and patch identities. | REMOVE |
| `audio/monkey_v5/monkey154_church_bank.json` | 1133 | `f09963eda43734b174d77241489a62a53b181a5b5e4a0f853b046518edcda8a5` | Monkey cue-to-sample mapping for W1. | REMOVE |
| `examples/resources/music/fate_s6_build_graph.json` | 18062 | `cb5fb5e174a290ea5fb673ffa5a2fa8d565b86100cb131f730a2eea98d6e837a` | Dependency graph that rebuilds the removed Fate compositions and sampled output. | REMOVE |
| `examples/resources/music/monkey_v5_build_graph.json` | 2053 | `7b529f7d1f6c374b1c7ad0ac63c0a5787d09a99728790a0d9b8214f7f39e85a3` | Dependency graph that rebuilds Monkey output using W1. | REMOVE |

The `audio/fate_s6/m22_sound80/terrific_audio_driver_m22.patch` file is driver
code, not audio or a sample payload; it remains under the applicable TAD zlib
license now located at `audio/TAD-LICENSE.txt`. The generic M24R-A TAD
patch/toolchain also remains under that driver license, which does not cover
any audio assets.

The retained M24R-A fixture and QTMA fixture rights basis is the repository's
root `LICENSE` public-domain dedication for original project material. No
third-party WAV/BRR/music composition is retained in the current tree. Default
tests and builds do not require the deleted media. The old title-specific
audio profile targets fail closed with an explicit explanation; restoring
them requires a separately cleared external input package.

## History and publication boundary

The removable assets were introduced in already-published commit `3c88f54`.
This branch does not rewrite that published history: ancestor Git objects can
still contain their old blob data. The additive change removes all 67
unresolved Fate/Monkey WAV, BRR, and MML assets from the branch's resulting
tree and removes/guards their build selections. The one added MML retained is
the independently authored M24R-A fixture. A normal PR tree diff against its
base therefore no longer distributes the deleted paths, but this cleanup is
not a history purge. No ZIP, original game resource, ROM, savestate, or raw
archive is added by this clearance change.
