PYTHON ?= python3
CASE ?= 01_solid_palette

.PHONY: all goldens test verify rom rom-all clean

all: goldens test

goldens:
	PYTHONPATH=src $(PYTHON) -m same_vdp.cli build-all --root .

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

verify:
	PYTHONPATH=src $(PYTHON) -m same_vdp.cli verify --root .

rom:
	CASE=$(CASE) tools/build_rom.sh

rom-all:
	tools/build_all_roms.sh

clean:
	rm -rf build/* snes/generated/*
