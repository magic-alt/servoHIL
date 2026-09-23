.PHONY: test validate schematic release
PYTHON ?= python3
test:
	$(PYTHON) -m unittest discover -s tests -v
validate:
	$(PYTHON) tools/revb.py validate --carrier axu2cgb
	$(PYTHON) tools/revb.py validate --carrier zu2cg_som
schematic:
	$(PYTHON) tools/revb.py generate --carrier axu2cgb --output build/revB
release:
	$(PYTHON) tools/revb.py release --carrier axu2cgb
