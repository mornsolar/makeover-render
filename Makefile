.PHONY: install fmt lint type test test-fast check run clean

install:
	uv sync

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff format --check .
	uv run ruff check .

type:
	uv run mypy src

test:
	uv run pytest

test-fast:
	uv run pytest -m "not blender"

check: lint type test

run:
	uv run uvicorn makeover_render.interfaces.api.app:app --reload --port 8081

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov dist build
