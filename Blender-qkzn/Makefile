PYTHON ?= python3

.PHONY: lint test zip dev

lint:
$(PYTHON) -m ruff check Blender-qkzn/addons/blender_qkzn
$(PYTHON) -m black --check Blender-qkzn/addons/blender_qkzn
$(PYTHON) -m mypy Blender-qkzn/addons/blender_qkzn

test:
$(PYTHON) -m pytest -q Blender-qkzn/addons/blender_qkzn/tests

zip:
$(PYTHON) tools/make_zip.py

dev:
$(PYTHON) -m pip install -e .[dev]
