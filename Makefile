.PHONY: sync check lint

sync:
	python scripts/sync.py

check:
	python scripts/sync.py --check

lint:
	python scripts/lint_style.py
	python scripts/check_us_spelling.py AGENTS.md
	python scripts/check_english_only.py AGENTS.md
