PYTHON ?= python3
PYTHONPATH := $(CURDIR)/src

.PHONY: all fixtures generate test validate demo package adventure-package \
		engine-demo audio simulate snes s5-snes h0 k1 c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11 c12 c13 c14 c15 c16 c17 c18 c19 c20 c21 c22 c23 c24 c25 c26 c28 s1 s2 s3 s4 s5 s6-preflight clean

all: fixtures generate test validate demo

fixtures:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) tools/generate_engine_fixtures.py

generate: fixtures
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m same.cli abi generate runtime/snes/generated/abi.inc.pasm
	$(PYTHON) tools/generate_snes_engine_selection.py --engine demo

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

snes: generate validate
	tools/build_snes.sh

s5-snes: generate validate
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

clean:
	rm -rf build out/* runtime/snes/generated/*
