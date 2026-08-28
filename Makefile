.PHONY: help env up up-all up-dev down logs api worker web install migrate tunnel

help:
	@echo "White Shop — common commands"
	@echo "  make env       generate unique secrets in .env (chmod 600)"
	@echo "  make up        start postgres + redis"
	@echo "  make up-all    production-like stack (baked images, next start)"
	@echo "  make up-dev    docker with bind-mounts + next dev"
	@echo "  make down      stop containers"
	@echo "  make logs      tail compose logs"
	@echo "  make install   create venv + install api/worker + web deps"
	@echo "  make api       run FastAPI locally"
	@echo "  make worker    run ARQ worker locally"
	@echo "  make tg-login  interactive Telegram session login"
	@echo "  make web       run Next.js locally"
	@echo "  make tunnel    publish local :3000 via Cloudflare (needs login)"
	@echo "  make migrate    alembic upgrade head"
	@echo "  make seed      seed demo categories/products"
	@echo "  make test      run unit tests"

env:
	@mkdir -p data uploads
	@python3 scripts/secure_env.py

up:
	docker compose up -d postgres redis

up-all:
	docker compose up -d --build

up-dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

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
	.venv/bin/uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

worker:
	.venv/bin/arq apps.worker.main.WorkerSettings

tg-login:
	PYTHONPATH=. .venv/bin/python -m apps.worker.login

sync-apple:
	PYTHONPATH=. .venv/bin/python -m apps.worker.run_sync --folder Apple

web:
	@python3 scripts/secure_env.py >/dev/null
	cd apps/web && npm run dev

tunnel:
	cloudflared tunnel --config infra/tunnel/config.yml run

seed:
	PYTHONPATH=. .venv/bin/python -m apps.api.seed

migrate:
	PYTHONPATH=. .venv/bin/alembic -c apps/api/alembic.ini upgrade head

test:
	PYTHONPATH=. .venv/bin/pytest apps/worker/tests apps/api/tests -q
	node --experimental-strip-types --test apps/web/src/lib/telegramUser.test.ts apps/web/src/lib/apiBase.test.ts
	cd apps/web && npm run build
