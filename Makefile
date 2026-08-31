.PHONY: sync check lint test identity

# Overridable so a platform without this name can supply its own:
#   make test PYTHON=py
PYTHON ?= python3

PROSE_FILES = AGENTS.md README.md CHANGELOG.md DRIFT.md \
	docs/gate-threat-model.md adopters/1a2n-web-visualizer.md \
	plan/HANDOFF.md.example SECURITY.md.example CONTRIBUTING.md.example \
	.github/PULL_REQUEST_TEMPLATE.md .github/ISSUE_TEMPLATE.md

sync:
	$(PYTHON) scripts/sync.py

check:
	$(PYTHON) scripts/sync.py --check

lint:
	$(PYTHON) scripts/lint_style.py
	$(PYTHON) scripts/check_us_spelling.py $(PROSE_FILES)
	$(PYTHON) scripts/check_english_only.py $(PROSE_FILES)
	$(PYTHON) scripts/check_hedging.py $(PROSE_FILES)
	$(PYTHON) scripts/check_conflict_markers.py

test:
	$(PYTHON) scripts/run_tests.py

identity:
	$(PYTHON) scripts/check_git_identity.py --advise
