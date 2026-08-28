.PHONY: sync check lint test identity

# Overridable so a platform without this name can supply its own:
#   make test PYTHON=py
PYTHON ?= python3

sync:
	$(PYTHON) scripts/sync.py

check:
	$(PYTHON) scripts/sync.py --check

lint:
	$(PYTHON) scripts/lint_style.py
	$(PYTHON) scripts/check_us_spelling.py AGENTS.md
	$(PYTHON) scripts/check_english_only.py AGENTS.md
	$(PYTHON) scripts/check_conflict_markers.py

test:
	$(PYTHON) -m unittest discover -s tests -v

identity:
	$(PYTHON) scripts/check_git_identity.py --advise
