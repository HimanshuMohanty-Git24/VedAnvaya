.PHONY: install format lint typecheck test check schemas pilot rigveda lineage knowledge lexical semantic-config semantic-dry-run

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
	uv run pytest -m "not live and not api"

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

lexical:
	uv run python scripts/build_vedaweb_morphology_index.py
	uv run python scripts/build_rigveda_lexical.py
	uv run python scripts/generate_lexical_reports.py

semantic-config:
	uv run python scripts/build_semantic_pilot_config.py

# Builds every pilot packet and prices the run without contacting anyone. Free.
semantic-dry-run:
	uv run python scripts/run_semantic_pilot.py --dry-run
