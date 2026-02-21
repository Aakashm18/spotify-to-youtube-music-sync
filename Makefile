.PHONY: help install install-dev fmt lint test sync dedup clean

# ── Default target ──────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  🎵 Spotify → YouTube Sync — Developer Commands"
	@echo ""
	@echo "  make install      Install production dependencies"
	@echo "  make install-dev  Install all dependencies (incl. dev tools)"
	@echo "  make fmt          Auto-format code with black + isort"
	@echo "  make lint         Run black, isort, flake8 checks"
	@echo "  make test         Run unit tests with coverage"
	@echo "  make sync         Run the sync locally (requires env vars)"
	@echo "  make dry-run      Preview sync without making changes"
	@echo "  make dedup        Remove duplicate videos from YouTube playlist"
	@echo "  make clean        Remove __pycache__, .pytest_cache, logs"
	@echo ""

# ── Setup ───────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

# ── Code quality ─────────────────────────────────────────────────────────────
fmt:
	black --line-length 100 .
	isort --profile black --line-length 100 .

lint:
	black --check --line-length 100 .
	isort --check-only --profile black --line-length 100 .
	flake8 . --max-line-length 100 --extend-ignore=E203,W503

# ── Testing ──────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

# ── Run scripts ──────────────────────────────────────────────────────────────
sync:
	python youtube.py

dry-run:
	python youtube.py --dry-run --verbose

since:
	@echo "Usage: make since DATE=2025-01-01"
	python youtube.py --since $(DATE)

dedup:
	python remove_duplicates.py --dry-run

tokens:
	python scripts/get_tokens.py

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f processed_tracks.tmp
