PYTHON ?= python3
PYTHONPATH := $(CURDIR)/src
TAD_COMPILER ?= $(or $(wildcard $(CURDIR)/../terrific-audio-driver/target/release/tad-compiler),tad-compiler)

.PHONY: all fixtures generate fate-audio test validate demo package adventure-package \
	engine-demo audio simulate snes s5-snes h0 k1 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c28 c29 c30 c31 c32 c33 c34 c35 c36 c37 c38 c39 c40 c41 c42 s1 s2 s3 s4 s5 s6-preflight s6-tad s6-auditions \
	m4 m5-build m5 m6 m7-build m7 m8-build m8 m9-build m9 m10-build m10 m11-build m11 m12-build m12 m13-build m13 m14-build m14 m15-build m15 m16-build m16 m17-build m17 m18-build m18 m19-build m19 m20-build m20 m21-build m21 m22-build m22 m23a-build m23a m23b-build m23b m23c-build m23c m24ra-build m24ra m24rb-build m24rb m25a-validator-build m25a-validator clean

all: fixtures generate test validate demo

fixtures:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_engine_fixtures.py

generate: fixtures
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli abi generate runtime/snes/generated/abi.inc.pasm
	$(PYTHON) tools/generate_snes_engine_selection.py --engine demo
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_snes_carrier.py \
		--carrier lorom --rom-size-code 0x07 \
		--manifest runtime/snes/generated/carrier_manifest.json
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_snes_video_backend.py \
		--backend legacy_backdrop --carrier lorom \
		--manifest runtime/snes/generated/video_backend_manifest.json

fate-audio:
	mkdir -p build/fate-audio
	$(PYTHON) tools/generate_fate_tad_tone.py build/fate-audio/fate-tone.wav
	$(PYTHON) tools/build_fate_loop_safe_samples.py
	$(TAD_COMPILER) asar-export --lorom \
		--output-asm build/fate-audio/fate-tad.asm \
		--output-bin build/fate-audio/fate-tad.bin \
		--output-inc build/fate-audio/fate-tad.inc \
		audio/fate_s6/fate.terrificaudio
	$(PYTHON) tools/generate_fate_tad_layout.py \
		build/fate-audio/fate-tad.bin build/fate-audio/fate-tad.inc \
		audio/fate_s6/fate_tad_layout.inc.pasm

# Run every SAME and inherited SAME-VDP unit test.
test: generate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m unittest discover -s tests -v

validate: generate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/lint_poppy.py runtime/snes/main.pasm
	@for f in examples/targets/*.json; do PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli target validate "$$f" >/dev/null; done
	@for f in examples/profiles/*.json; do PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli engine validate "$$f" >/dev/null; done

package:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli package build \
		examples/packages/demo-package.json out/demo.samepkg \
		--poppy-include out/demo-package.inc.pasm

adventure-package: fixtures
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli package build \
		examples/packages/adventure-demo-package.json out/adventure-demo.samepkg \
		--poppy-include out/adventure-demo.inc.pasm

simulate:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli simulate \
		examples/targets/genesis.json --frames 120 \
		--input-script examples/input/genesis-demo.json \
		--output out/genesis-simulation.json

engine-demo: fixtures
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli engine run \
		examples/profiles/scumm_v5_conformance.json --frames 120 \
		--output out/scumm-v5-report.json \
		--framebuffer out/scumm-v5-frame.png \
		--save-file out/scumm-v5-slot0.same-save
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli engine run \
		examples/profiles/agi_v2_conformance.json --frames 120 \
		--output out/agi-v2-report.json \
		--framebuffer out/agi-v2-frame.png \
		--save-file out/agi-v2-slot0.same-save

audio:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli audio demo \
		--trace examples/audio/sn76489-demo.jsonl \
		--wav out/sn76489-demo.wav --duration 1.25

demo: package adventure-package engine-demo simulate audio
	cd labs/vdp && PYTHONPATH=../../src $(PYTHON) -m same_vdp.cli verify --root .

snes: generate validate fate-audio
	tools/build_snes.sh

s5-snes: generate validate fate-audio
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5.sfc tools/build_snes.sh

h0: snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_h0_nexen.py

k1: h0
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_k1_nexen.py

# Independent SCUMM semantic gate: five VM ticks, normally six video frames.
c1: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_core_nexen.py --rom build/same-scumm-v5.sfc

c2: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c2_nexen.py --rom build/same-scumm-v5.sfc

c3: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c3_nexen.py --rom build/same-scumm-v5.sfc

c4: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c4_nexen.py --rom build/same-scumm-v5.sfc

c5: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c5_nexen.py --rom build/same-scumm-v5.sfc

c6: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c6_nexen.py --rom build/same-scumm-v5.sfc

c7: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c7_nexen.py --rom build/same-scumm-v5.sfc

c8: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c8_nexen.py --rom build/same-scumm-v5.sfc

c9: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c9_nexen.py --rom build/same-scumm-v5.sfc

c10: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c10_nexen.py --rom build/same-scumm-v5.sfc

c11: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c11_nexen.py --rom build/same-scumm-v5.sfc

c12: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c12_nexen.py --rom build/same-scumm-v5.sfc

c13: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c13_nexen.py --rom build/same-scumm-v5.sfc

c14: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c14_nexen.py --rom build/same-scumm-v5.sfc

c15: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c15_nexen.py --rom build/same-scumm-v5.sfc

c16: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c16_nexen.py --rom build/same-scumm-v5.sfc

c17: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c17_nexen.py --rom build/same-scumm-v5.sfc

c18: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c18_nexen.py --rom build/same-scumm-v5.sfc

c19: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c19_nexen.py --rom build/same-scumm-v5.sfc

c20: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c20_nexen.py --rom build/same-scumm-v5.sfc

c21: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c21_nexen.py --rom build/same-scumm-v5.sfc

c22: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c22_nexen.py --rom build/same-scumm-v5.sfc

c23: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c23_nexen.py --rom build/same-scumm-v5.sfc

c24: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c24_nexen.py --rom build/same-scumm-v5.sfc

c25: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c25_nexen.py --rom build/same-scumm-v5.sfc

c26: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c26_nexen.py --rom build/same-scumm-v5.sfc

c28: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c28_nexen.py --rom build/same-scumm-v5.sfc

c29: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c29_nexen.py --rom build/same-scumm-v5.sfc

c30: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c30_nexen.py --rom build/same-scumm-v5.sfc

c31: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c31_nexen.py --rom build/same-scumm-v5.sfc

c32: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_c32_nexen.py --rom build/same-scumm-v5.sfc

c33: s6-preflight

c34: s6-preflight

c35: s6-preflight

c36: s6-preflight

c37: s6-preflight

c38: s6-preflight

c39: s6-preflight

c40: s6-preflight

c41: s6-tad

c42: s6-auditions

s1: test validate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_scumm_s1_profile.py

s2: test validate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_scumm_s2_adapters.py

s3: test validate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_scumm_s3_video.py

s4: test validate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_scumm_s4_audio_save.py

s5: test validate s5-snes
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_scumm_s5_binding.py \
		--rom build/same-scumm-v5.sfc

s6-preflight: test validate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_scumm_s6_fate_preflight.py

s6-tad: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5.sfc

s6-auditions: s5-snes
	PYTHONPATH=/home/chad/Mesen2/python $(PYTHON) tools/capture_fate_instrument_auditions.py \
		--rom build/same-scumm-v5.sfc

m4: test validate
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_monkey_v5_music.py \
		--archive /home/chad/_monkeypacks_backup.zip \
		--output build/monkey-v5-music-m4

m5-build:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/build_monkey_v5_tad.py \
		--archive /home/chad/_monkeypacks_backup.zip \
		--output build/monkey-v5-tad-m5
	SAME_TAD_PREBUILT_DIR=build/monkey-v5-tad-m5 \
		SAME_MUSIC_CATALOG=examples/resources/music/monkey_v5_compiled.json \
		SAME_SNES_ENGINE=scumm_v5 \
		SAME_SNES_OUTPUT=build/same-scumm-v5-monkey-m5.sfc tools/build_snes.sh

m5: m5-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_monkey_v5_tad_nexen.py \
		--rom build/same-scumm-v5-monkey-m5.sfc \
		--build-report build/monkey-v5-tad-m5/report.json

m6: test validate m5
	$(MAKE) fate-audio
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/validate_music_catalog_m6.py \
		--fate-enums build/fate-audio/fate-tad.inc \
		--monkey-enums build/monkey-v5-tad-m5/tad.inc \
		--output build/music-catalog-m6/report.json
	$(MAKE) s5-snes

m7-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_scumm_v5_music_graph.py \
		--graph examples/resources/music/fate_s6_build_graph.json \
		--archive /home/chad/fatedemo-box.zip --output build/music-m7-fate
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_scumm_v5_music_graph.py \
		--graph examples/resources/music/monkey_v5_build_graph.json \
		--archive /home/chad/_monkeypacks_backup.zip --output build/music-m7-monkey
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_scumm_v5_music_graph.py \
		--graph examples/resources/music/fate_s6_build_graph.json \
		--archive /home/chad/fatedemo-box.zip --output build/music-m7-fate --verify
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_scumm_v5_music_graph.py \
		--graph examples/resources/music/monkey_v5_build_graph.json \
		--archive /home/chad/_monkeypacks_backup.zip --output build/music-m7-monkey --verify
	SAME_TAD_PREBUILT_DIR=build/music-m7-fate \
		SAME_MUSIC_CATALOG=build/music-m7-fate/catalog.json \
		SAME_SNES_ENGINE=scumm_v5 \
		SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m7.sfc tools/build_snes.sh
	SAME_TAD_PREBUILT_DIR=build/music-m7-monkey \
		SAME_MUSIC_CATALOG=build/music-m7-monkey/catalog.json \
		SAME_SNES_ENGINE=scumm_v5 \
		SAME_SNES_OUTPUT=build/same-scumm-v5-monkey-m7.sfc tools/build_snes.sh

m7: test validate m7-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m7.sfc --sound 83
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m7.sfc --sound 154
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_monkey_v5_tad_nexen.py \
		--rom build/same-scumm-v5-monkey-m7.sfc \
		--build-report build/music-m7-monkey/report.json

m8-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_scumm_v5_music_graph.py \
		--graph examples/resources/music/fate_s6_build_graph.json \
		--archive /home/chad/fatedemo-box.zip --output build/music-m8-fate
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_scumm_v5_music_graph.py \
		--graph examples/resources/music/fate_s6_build_graph.json \
		--archive /home/chad/fatedemo-box.zip --output build/music-m8-fate --verify
	SAME_TAD_PREBUILT_DIR=build/music-m8-fate \
		SAME_MUSIC_CATALOG=build/music-m8-fate/catalog.json \
		SAME_SNES_ENGINE=scumm_v5 \
		SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m8.sfc tools/build_snes.sh

m8: test validate m8-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m8.sfc --sound 172
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m8.sfc --sound 18
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m8.sfc --sound 153
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m8.sfc --sound 150

m9-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/fate_of_atlantis_demo.json \
		--source-archive /home/chad/fatedemo-box.zip \
		--music-output build/profile-music/fate-m9 \
		--rom build/same-scumm-v5-fate-m9.sfc
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/monkey1_ultimate_talkie.json \
		--source-archive /home/chad/_monkeypacks_backup.zip \
		--music-output build/profile-music/monkey-m9 \
		--rom build/same-scumm-v5-monkey-m9.sfc

m9: test validate m9-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m9.sfc --sound 154
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_monkey_v5_tad_nexen.py \
		--rom build/same-scumm-v5-monkey-m9.sfc \
		--build-report build/profile-music/monkey-m9/report.json

m10-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_conformance.json \
		--music-output build/profile-music/qtma-m10 \
		--rom build/same-qtma-m10.sfc
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_conformance.json \
		--music-output build/profile-music/qtma-m10 \
		--rom build/same-qtma-m10-reuse.sfc --reuse
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/fate_of_atlantis_demo.json \
		--source-archive /home/chad/fatedemo-box.zip \
		--music-output build/profile-music/fate-m10 \
		--rom build/same-scumm-v5-fate-m10.sfc
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/monkey1_ultimate_talkie.json \
		--source-archive /home/chad/_monkeypacks_backup.zip \
		--music-output build/profile-music/monkey-m10 \
		--rom build/same-scumm-v5-monkey-m10.sfc

m10: test validate m10-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_scumm_s6_tad_nexen.py \
		--rom build/same-scumm-v5-fate-m10.sfc --sound 154
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH) $(PYTHON) \
		tools/validate_monkey_v5_tad_nexen.py \
		--rom build/same-scumm-v5-monkey-m10.sfc \
		--build-report build/profile-music/monkey-m10/report.json

m11-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_runtime_conformance.json \
		--music-output build/profile-music/qtma-m11 \
		--rom build/same-qtma-m11.sfc
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_runtime_conformance.json \
		--music-output build/profile-music/qtma-m11 \
		--rom build/same-qtma-m11-reuse.sfc --reuse

m11: test validate m11-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_qtma_music_runtime_nexen.py \
		--rom build/same-qtma-m11.sfc

m12-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_runtime_conformance.json \
		--music-output build/profile-music/qtma-m12 \
		--rom build/same-qtma-m12.sfc
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_runtime_conformance.json \
		--music-output build/profile-music/qtma-m12 \
		--rom build/same-qtma-m12-reuse.sfc --reuse

m12: test validate m12-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m12.sfc

m13-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_mov_runtime_conformance.json \
		--music-output build/profile-music/qtma-m13 \
		--rom build/same-qtma-m13.sfc
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_mov_runtime_conformance.json \
		--music-output build/profile-music/qtma-m13 \
		--rom build/same-qtma-m13-reuse.sfc --reuse

m13: test validate m13-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m13.sfc --gate M13-QTMA-MOV-runtime \
		--output build/qtma-m13-mov-runtime

m14-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_time_runtime_conformance.json \
		--music-output build/profile-music/qtma-m14 \
		--rom build/same-qtma-m14.sfc
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/qtma_music_time_runtime_conformance.json \
		--music-output build/profile-music/qtma-m14 \
		--rom build/same-qtma-m14-reuse.sfc --reuse

m14: test validate m14-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m14.sfc --gate M14-rational-time-runtime \
		--duration-frames 60 --lifecycle-complete-frame 195 \
		--engine-complete-frame 196 --last-audible-min 3.10 \
		--last-audible-max 3.70 --output build/qtma-m14-time-runtime

m15-build: m13-build m14-build

m15: test validate m15-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m13.sfc --gate M15-segmented-M13-runtime \
		--output build/qtma-m15-segmented-m13-runtime
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m14.sfc --gate M15-segmented-M14-runtime \
		--duration-frames 60 --lifecycle-complete-frame 195 \
		--engine-complete-frame 196 --last-audible-min 3.10 \
		--last-audible-max 3.70 \
		--output build/qtma-m15-segmented-m14-runtime

m16-build: m15-build

m16: test validate m16-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m13.sfc --gate M16-audit-M13-runtime \
		--output build/qtma-m16-audit-m13-runtime
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m14.sfc --gate M16-audit-M14-runtime \
		--duration-frames 60 --lifecycle-complete-frame 195 \
		--engine-complete-frame 196 --last-audible-min 3.10 \
		--last-audible-max 3.70 --output build/qtma-m16-audit-m14-runtime

m17-build: m16-build

m17: test validate m17-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m13.sfc --gate M17-IR-replay-M13-runtime \
		--output build/qtma-m17-ir-replay-m13-runtime
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m14.sfc --gate M17-IR-replay-M14-runtime \
		--duration-frames 60 --lifecycle-complete-frame 195 \
		--engine-complete-frame 196 --last-audible-min 3.10 \
		--last-audible-max 3.70 --output build/qtma-m17-ir-replay-m14-runtime

m18-build: m17-build

m18: test validate m18-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m13.sfc --gate M18-checkpoint-M13-runtime \
		--output build/qtma-m18-checkpoint-m13-runtime
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_music_lifecycle_nexen.py \
		--rom build/same-qtma-m14.sfc --gate M18-checkpoint-M14-runtime \
		--duration-frames 60 --lifecycle-complete-frame 195 \
		--engine-complete-frame 196 --last-audible-min 3.10 \
		--last-audible-max 3.70 --output build/qtma-m18-checkpoint-m14-runtime

m19-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/monkey1_ultimate_talkie.json \
		--source-archive /home/chad/_monkeypacks_backup.zip \
		--music-output build/profile-music/monkey-m19 \
		--rom build/same-scumm-v5-monkey-m19.sfc

m19: test validate m19-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_scumm_m19_monkey_music_nexen.py \
		--rom build/same-scumm-v5-monkey-m19.sfc

m20-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/monkey1_ultimate_talkie.json \
		--source-archive /home/chad/_monkeypacks_backup.zip \
		--music-output build/profile-music/monkey-m20 \
		--rom build/same-scumm-v5-monkey-m20.sfc --scumm-m20

m20: test validate m20-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_scumm_m20_save_nexen.py \
		--rom build/same-scumm-v5-monkey-m20.sfc

m21-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_fate_sound80_routes.py \
		--archive /home/chad/fatedemo-box.zip \
		--output audio/fate_s6/m21_sound80
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/fate_of_atlantis_demo.json \
		--source-archive /home/chad/fatedemo-box.zip \
		--music-output build/profile-music/fate-m21-final \
		--rom build/same-scumm-v5-fate-m21.sfc --scumm-m21

m21: test validate m21-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_scumm_m21_fate_route_nexen.py \
		--rom build/same-scumm-v5-fate-m21.sfc
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/capture_fate_m21_auditions.py \
		--rom build/same-scumm-v5-fate-m21.sfc

m22-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_fate_sound80_m22_sections.py \
		--archive /home/chad/fatedemo-box.zip \
		--output audio/fate_s6/m22_sound80
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_m22_tad_toolchain.py \
		--output build/toolchain/tad-m22
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_profile_music_rom.py \
		--profile examples/profiles/templates/fate_of_atlantis_demo.json \
		--source-archive /home/chad/fatedemo-box.zip \
		--music-output build/profile-music/indy4-fate-demo-m22 \
		--compiler build/toolchain/tad-m22/target/release/tad-compiler \
		--rom build/same-scumm-v5-fate-m22.sfc --scumm-m22

m22: test validate m22-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_scumm_m22_fate_hook8_nexen.py \
		--rom build/same-scumm-v5-fate-m22.sfc
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_scumm_m22_save_nexen.py \
		--rom build/same-scumm-v5-fate-m22.sfc
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_scumm_m22_lifetime_nexen.py \
		--rom build/same-scumm-v5-fate-m22.sfc
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/capture_fate_m22_auditions.py \
		--rom build/same-scumm-v5-fate-m22.sfc

m23a-build:
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/indy4-fate-demo-m22 \
	SAME_MUSIC_CATALOG=$(CURDIR)/build/profile-music/indy4-fate-demo-m22/catalog.json \
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m23a.sfc \
	SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/templates/fate_of_atlantis_demo.json \
	SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 \
	SAME_BUILD_SCUMM_M23A=1 SAME_SCUMM_SAVE_LOGICAL_ID=80 \
	SAME_FATE_DEMO_ARCHIVE=/home/chad/fatedemo-box.zip tools/build_snes.sh
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/inspect_fate_m23a_rooms.py \
		--manifest build/m23a-rooms/authentic/manifest.json \
		--output build/m23a-rooms/inspection.json
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/validate_scumm_m23a_host.py \
		--manifest build/m23a-rooms/authentic/manifest.json \
		--output build/m23a-rooms/host-report.json

m23a: test validate m23a-build
	PYTHONPATH=/home/chad/Mesen2/python:$(PYTHONPATH):tools $(PYTHON) \
		tools/validate_scumm_m23a_rooms_nexen.py \
		--rom build/same-scumm-v5-fate-m23a.sfc

m23b-build:
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/indy4-fate-demo-m22 \
	SAME_MUSIC_CATALOG=$(CURDIR)/build/profile-music/indy4-fate-demo-m22/catalog.json \
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m23b.sfc \
	SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/templates/fate_of_atlantis_demo.json \
	SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 \
	SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 \
	SAME_SCUMM_SAVE_LOGICAL_ID=80 SAME_FATE_DEMO_ARCHIVE=/home/chad/fatedemo-box.zip \
	tools/build_snes.sh
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/indy4-fate-demo-m22 \
	SAME_MUSIC_CATALOG=$(CURDIR)/build/profile-music/indy4-fate-demo-m22/catalog.json \
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m23b-negative.sfc \
	SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/templates/fate_of_atlantis_demo.json \
	SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 \
	SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23B_NEGATIVE=1 \
	SAME_SCUMM_SAVE_LOGICAL_ID=80 SAME_FATE_DEMO_ARCHIVE=/home/chad/fatedemo-box.zip \
	tools/build_snes.sh
	PYTHONPATH=src $(PYTHON) tools/validate_scumm_m23b_host.py \
		--manifest build/m23a-rooms/authentic/manifest.json \
		--output build/m23b-host-report.json

m23b: test validate m23b-build
	PYTHONPATH=/home/chad/Mesen2/python:src:tools $(PYTHON) \
		tools/validate_scumm_m23b_nexen.py \
		--rom build/same-scumm-v5-fate-m23b.sfc \
		--negative-rom build/same-scumm-v5-fate-m23b-negative.sfc \
		--manifest build/m23a-rooms/authentic/manifest.json

m23c-build:
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/indy4-fate-demo-m22 \
	SAME_MUSIC_CATALOG=$(CURDIR)/build/profile-music/indy4-fate-demo-m22/catalog.json \
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m23c.sfc \
	SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/templates/fate_of_atlantis_demo.json \
	SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 \
	SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 \
	SAME_SCUMM_SAVE_LOGICAL_ID=80 SAME_FATE_DEMO_ARCHIVE=/home/chad/fatedemo-box.zip \
	tools/build_snes.sh
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/indy4-fate-demo-m22 \
	SAME_MUSIC_CATALOG=$(CURDIR)/build/profile-music/indy4-fate-demo-m22/catalog.json \
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m23c-class-control.sfc \
	SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/templates/fate_of_atlantis_demo.json \
	SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 \
	SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 \
	SAME_BUILD_SCUMM_M23C_CLASS_CONTROL=1 SAME_SCUMM_SAVE_LOGICAL_ID=80 \
	SAME_FATE_DEMO_ARCHIVE=/home/chad/fatedemo-box.zip tools/build_snes.sh
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/indy4-fate-demo-m22 \
	SAME_MUSIC_CATALOG=$(CURDIR)/build/profile-music/indy4-fate-demo-m22/catalog.json \
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5-fate-m23c-sound-control.sfc \
	SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/templates/fate_of_atlantis_demo.json \
	SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 \
	SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 \
	SAME_BUILD_SCUMM_M23C_SOUND_CONTROL=1 SAME_SCUMM_SAVE_LOGICAL_ID=80 \
	SAME_FATE_DEMO_ARCHIVE=/home/chad/fatedemo-box.zip tools/build_snes.sh
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/indy4-fate-demo-m22 \
	SAME_MUSIC_CATALOG=$(CURDIR)/build/profile-music/indy4-fate-demo-m22/catalog.json \
	SAME_SNES_ENGINE=scumm_v5 SAME_SNES_OUTPUT=build/same-scumm-v5-m23c-if-class.sfc \
	SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/templates/fate_of_atlantis_demo.json \
	SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE=1 \
	SAME_SCUMM_SAVE_LOGICAL_ID=80 \
	SAME_FATE_DEMO_ARCHIVE=/home/chad/fatedemo-box.zip tools/build_snes.sh
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/cook_scumm_v5_rooms.py --archive /home/chad/fatedemo-box.zip \
		--profile examples/profiles/templates/fate_of_atlantis_demo.json --rooms 49 \
		--global-scripts 144 145 --executable --output-dir build/m23a-rooms/authentic
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/cook_scumm_v5_rooms.py --archive /home/chad/fatedemo-box.zip \
		--profile examples/profiles/templates/fate_of_atlantis_demo.json --rooms 63 \
		--global-scripts 151 --executable --output-dir build/m23a-rooms/authentic-room63
	PYTHONPATH=src $(PYTHON) tools/validate_scumm_m23c_host.py \
		--manifest build/m23a-rooms/authentic/manifest.json \
		--manifest build/m23a-rooms/authentic-room63/manifest.json \
		--output build/m23c-host-report.json

m23c: test validate m23c-build
	PYTHONPATH=/home/chad/Mesen2/python:src:tools $(PYTHON) \
		tools/validate_scumm_m23c_if_class_nexen.py --rom build/same-scumm-v5-m23c-if-class.sfc
	PYTHONPATH=/home/chad/Mesen2/python:src:tools $(PYTHON) \
		tools/validate_scumm_m23c_nexen.py \
		--rom build/same-scumm-v5-fate-m23c.sfc \
		--class-control-rom build/same-scumm-v5-fate-m23c-class-control.sfc \
		--sound-control-rom build/same-scumm-v5-fate-m23c-sound-control.sfc
	PYTHONPATH=/home/chad/Mesen2/python:src:tools $(PYTHON) \
		tools/validate_scumm_m22_save_nexen.py \
		--rom build/same-scumm-v5-fate-m22.sfc

m24ra-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_m24ra_tad_toolchain.py \
		--output build/toolchain/tad-m24ra
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_m24ra_fixture.py \
		--compiler build/toolchain/tad-m24ra/target/release/tad-compiler \
		--output build/profile-music/m24ra
	SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/profile-music/m24ra \
	SAME_MUSIC_CATALOG=$(CURDIR)/audio/m24ra/catalog.json \
	SAME_TAD_LAYOUT_OUTPUT=runtime/snes/generated/m24ra_tad_layout.inc.pasm \
	SAME_SNES_ENGINE=m24ra_conformance SAME_BUILD_M24RA=1 \
	SAME_SNES_OUTPUT=build/same-m24ra.sfc tools/build_snes.sh

m24ra: test validate m24ra-build
	PYTHONPATH=/home/chad/Mesen2/python:src:tools $(PYTHON) \
		tools/validate_m24ra_nexen.py --rom build/same-m24ra.sfc

m24rb-build:
	PYTHONPATH=$(PYTHONPATH):tools $(PYTHON) tools/build_fate_m24rb_composite.py \
		--archive /home/chad/fatedemo-box.zip --output build/m24rb-content
	$(PYTHON) tools/build_m24rb_tad_toolchain.py --output build/toolchain/tad-m24rb
	build/toolchain/tad-m24rb/target/release/tad-compiler asar-export --lorom \
		--output-asm build/m24rb-content/tad.asm \
		--output-bin build/m24rb-content/tad-unlinked.bin \
		--output-inc build/m24rb-content/tad.inc build/m24rb-content/m24rb.terrificaudio
	$(PYTHON) tools/postlink_m24rb_tad.py --input build/m24rb-content/tad-unlinked.bin \
		--output build/m24rb-content/tad.bin --report build/m24rb-content/postlink.json
	@for spec in low:300 high:900 sustain:1800 loop:0; do \
		label=$${spec%%:*}; delay=$${spec##*:}; \
		SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/m24rb-content \
		SAME_MUSIC_CATALOG=$(CURDIR)/audio/m24rb/catalog.json \
		SAME_TAD_LAYOUT_OUTPUT=runtime/snes/generated/m24ra_tad_layout.inc.pasm \
		SAME_SNES_ENGINE=m24rb_conformance SAME_BUILD_M24RA=1 SAME_BUILD_M24RB=1 \
		SAME_M24RB_PHASE_DELAY=$$delay SAME_SNES_OUTPUT=build/same-m24rb-$$label.sfc \
		tools/build_snes.sh || exit 1; \
	done

m24rb: test validate m24rb-build
	PYTHONPATH=src:tools $(PYTHON) tools/validate_scumm_m24rb_host.py \
		--manifest build/m23a-rooms/authentic/manifest.json \
		--manifest build/m23a-rooms/authentic-room63/manifest.json \
		--output build/m24rb-host-report.json
	PYTHONPATH=/home/chad/Mesen2/python:src:tools $(PYTHON) tools/validate_scumm_m24rb_nexen.py \
		--low-rom build/same-m24rb-low.sfc --high-rom build/same-m24rb-high.sfc \
		--sustain-rom build/same-m24rb-sustain.sfc --loop-rom build/same-m24rb-loop.sfc \
		--output build/m24rb-nexen

m25a-validator-build:
	@for case in normal depth missing outer; do \
		SAME_TAD_PREBUILT_DIR=$(CURDIR)/build/m24rb-content \
		SAME_MUSIC_CATALOG=$(CURDIR)/audio/m24rb/catalog.json \
		SAME_TAD_LAYOUT_OUTPUT=runtime/snes/generated/m24ra_tad_layout.inc.pasm \
		SAME_SNES_ENGINE=scumm_v5 SAME_BUILD_M24RA=1 SAME_BUILD_M24RB=1 \
		SAME_BUILD_SCUMM_M20=1 SAME_BUILD_SCUMM_M21=1 SAME_BUILD_SCUMM_M22=1 \
		SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 SAME_BUILD_SCUMM_M23C=1 \
		SAME_BUILD_SCUMM_M25A_VALIDATOR=1 SAME_M25A_VALIDATOR_CASE=$$case \
		SAME_SCUMM_SAVE_LOGICAL_ID=80 \
		SAME_SNES_PROFILE=$(CURDIR)/examples/profiles/m25a_nested_conformance.json \
		SAME_SNES_OUTPUT=$(CURDIR)/build/m25a-validator/$$case/m25a-$$case.sfc \
		tools/build_snes.sh || exit 1; \
	done

m25a-validator: m25a-validator-build
	PYTHONPATH=/home/chad/Mesen2/python:src:tools $(PYTHON) \
		tools/validate_scumm_m25a_nested_nexen.py \
		--normal-rom build/m25a-validator/normal/m25a-normal.sfc \
		--depth-rom build/m25a-validator/depth/m25a-depth.sfc \
		--missing-rom build/m25a-validator/missing/m25a-missing.sfc \
		--outer-rom build/m25a-validator/outer/m25a-outer.sfc \
		--normal-manifest build/m25a-validator/normal/manifest.json \
		--depth-manifest build/m25a-validator/depth/manifest.json \
		--missing-manifest build/m25a-validator/missing/manifest.json \
		--outer-manifest build/m25a-validator/outer/manifest.json

clean:
	rm -rf build out/* runtime/snes/generated/*
