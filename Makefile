.PHONY: sync check lint test identity

sync:
	python scripts/sync.py

check:
	python scripts/sync.py --check

lint:
	python scripts/lint_style.py
	python scripts/check_us_spelling.py AGENTS.md
	python scripts/check_english_only.py AGENTS.md
	python scripts/check_conflict_markers.py AGENTS.md CHANGELOG.md README.md plan/HANDOFF.md.example SECURITY.md.example CONTRIBUTING.md.example .github/PULL_REQUEST_TEMPLATE.md .github/ISSUE_TEMPLATE.md

test:
	python -m unittest discover -s tests -v

identity:
	python scripts/check_git_identity.py --advise
