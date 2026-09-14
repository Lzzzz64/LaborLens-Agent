.PHONY: up down test

up:
	docker compose up -d --build

down:
	docker compose down

test:
	docker compose run --rm backend pytest tests -q
