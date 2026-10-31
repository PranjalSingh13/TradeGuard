.PHONY: up down test lint
up:
	docker compose -f infra/docker-compose.yml up -d
down:
	docker compose -f infra/docker-compose.yml down
test:
	python -m pytest
lint:
	ruff check src tests
