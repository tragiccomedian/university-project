.PHONY: help up down logs shell migrate migrate-auto migrate-undo \
        test test-cov lint format typecheck install dev-install \
        seed openapi clean

# ─── Helpers ──────────────────────────────────────────────────────────────────
APP_SERVICE ?= app

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker ───────────────────────────────────────────────────────────────────
up: ## Start all services (dev mode with hot-reload)
	docker compose up --build -d

down: ## Stop all services
	docker compose down

restart: ## Restart app + worker
	docker compose restart app worker

logs: ## Follow app logs
	docker compose logs -f app worker

shell: ## Open a bash shell in the app container
	docker compose exec $(APP_SERVICE) bash

# ─── Database ─────────────────────────────────────────────────────────────────
migrate: ## Apply all pending Alembic migrations
	docker compose exec $(APP_SERVICE) alembic upgrade head

migrate-auto: ## Auto-generate a new migration (MSG="description")
	docker compose exec $(APP_SERVICE) alembic revision --autogenerate -m "$(MSG)"

migrate-undo: ## Roll back the last migration
	docker compose exec $(APP_SERVICE) alembic downgrade -1

migrate-history: ## Show migration history
	docker compose exec $(APP_SERVICE) alembic history --verbose

seed: ## Populate DB with demo data
	docker compose exec $(APP_SERVICE) python -m app.db.seed

# ─── Testing ──────────────────────────────────────────────────────────────────
test: ## Run tests (requires local .env with TEST_DATABASE_URL)
	pytest -v

test-cov: ## Run tests with coverage report
	pytest --cov=app --cov-report=term-missing --cov-report=html -v

test-ci: ## Run tests as CI would (no coverage HTML)
	pytest --cov=app --cov-report=xml -v

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Run ruff linter
	ruff check app tests

format: ## Auto-format with ruff
	ruff format app tests
	ruff check --fix app tests

typecheck: ## Run mypy
	mypy app

check: lint typecheck ## Run all static checks

# ─── Local Dev Setup ─────────────────────────────────────────────────────────
install: ## Install project dependencies
	pip install -e ".[dev]"

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

dev: install pre-commit-install ## Full local dev setup

# ─── API Contract ─────────────────────────────────────────────────────────────
openapi: ## Export openapi.json (app must be running)
	curl -s http://localhost:8000/openapi.json | python -m json.tool > openapi.json
	@echo "✅ openapi.json exported"

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
