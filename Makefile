.PHONY: help env up down logs api worker web install migrate

help:
	@echo "White Shop — common commands"
	@echo "  make env       copy .env.example -> .env"
	@echo "  make up        start postgres + redis (+ optional full stack)"
	@echo "  make down      stop containers"
	@echo "  make logs      tail compose logs"
	@echo "  make install   create venv + install api/worker + web deps"
	@echo "  make api       run FastAPI locally"
	@echo "  make worker    run ARQ worker locally"
	@echo "  make tg-login  interactive Telegram session login"
	@echo "  make web       run Next.js locally"
	@echo "  make seed      seed demo categories/products"
	@echo "  make test      run unit tests"

env:
	@test -f .env || cp .env.example .env
	@mkdir -p data uploads
	@echo ".env ready"

up:
	docker compose up -d postgres redis

up-all:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

install: env
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -r apps/api/requirements.txt -r apps/worker/requirements.txt
	cd apps/web && npm install

api:
	.venv/bin/uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

worker:
	.venv/bin/arq apps.worker.main.WorkerSettings

tg-login:
	PYTHONPATH=. .venv/bin/python -m apps.worker.login

sync-apple:
	PYTHONPATH=. .venv/bin/python -m apps.worker.run_sync --folder Apple

web:
	cd apps/web && npm run dev

seed:
	PYTHONPATH=. .venv/bin/python -m apps.api.seed

test:
	PYTHONPATH=. .venv/bin/pytest apps/worker/tests apps/api/tests -q
