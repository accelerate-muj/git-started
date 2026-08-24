# Rabbit Holes handbook.
#
#   make           build every phase into pdf/
#   make clean     remove LaTeX build artefacts
#   make P=5       build only phase 5
#
# Thin wrapper over build.py, which does the real work and is cross platform.

PYTHON ?= python

all:
	$(PYTHON) build.py $(P)

clean:
	$(PYTHON) build.py --clean

.PHONY: all clean
