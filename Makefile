.PHONY: install format lint typecheck test check schemas pilot rigveda lineage knowledge

install:
	uv sync --extra dev

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run mypy

test:
	uv run pytest -m "not live"

check: lint typecheck test

schemas:
	uv run vedagraph schema export

pilot:
	uv run vedagraph corpus build-pilot


rigveda:
	uv run python scripts/build_rigveda_full.py

lineage:
	uv run python scripts/verify_lineage.py --per-mandala 5

knowledge:
	uv run python scripts/build_anukramani_registries.py
	uv run python scripts/build_rigveda_knowledge.py
	uv run python scripts/generate_knowledge_reports.py
