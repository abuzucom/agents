.PHONY: sync check lint test identity

sync:
	python scripts/sync.py

check:
	python scripts/sync.py --check

lint:
	python scripts/lint_style.py
	python scripts/check_us_spelling.py AGENTS.md
	python scripts/check_english_only.py AGENTS.md
	python scripts/check_conflict_markers.py

test:
	python -m unittest discover -s tests -v

identity:
	python scripts/check_git_identity.py --advise
