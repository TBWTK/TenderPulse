.PHONY: sync test lint dbt-test verify docker-up docker-down

sync:
	uv sync --all-extras

test:
	.venv/bin/pytest --cov=tenderpulse --cov-branch --cov-report=term-missing -q

lint:
	.venv/bin/ruff check src tests migrations
	.venv/bin/ruff format --check src tests migrations
	.venv/bin/mypy src/tenderpulse

dbt-test:
	.venv/bin/dbt build --project-dir analytics --profiles-dir analytics

verify: test lint
	docker compose config --quiet
	python3 /Users/tbwtk/.codex/skills/project-control/scripts/project_control.py check .

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
