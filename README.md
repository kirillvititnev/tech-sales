# White Shop

Автоматизированная B2C-витрина техники: парсинг Telegram-каналов поставщиков → медиана цен + наценка → магазин (Mini App / сайт / Flutter) + админка.

Требования: см. [REQUIREMENTS.md](./REQUIREMENTS.md).

## Стек

- **API:** Python / FastAPI / PostgreSQL / Redis
- **Worker:** Telethon (MTProto) + ARQ (каждые 15 мин)
- **Web:** Next.js (витрина + Mini App + админка)
- **Mobile:** Flutter (позже)

## Быстрый старт (локально)

```bash
make env
make up          # postgres на :5433 (+ redis в docker, если образ скачан)
make install     # venv + npm
make api         # http://localhost:8000/docs  (создаёт таблицы)
make seed        # демо-категории и товар
make web         # http://localhost:3000
make worker      # фоновый парсер (нужны TELEGRAM_API_ID/HASH)
make test
```

> Postgres в docker слушает **5433** (чтобы не конфликтовать с другими локальными БД).
> Redis можно поднять через docker или `brew services start redis` / `redis-server`.

Или всё через Docker:

```bash
make env
make up-all
```

## Telegram

1. Получи `api_id` / `api_hash` на https://my.telegram.org и пропиши в `.env`
2. Логин локальной сессии (за границей прокси не нужен):

```bash
make tg-login
```

Сессия сохранится в `data/telegram.session` (в git не попадает).

### VPN на VPS (VLESS Reality)

Когда сервер будет в зоне, где Telegram режется:

```bash
cp infra/vpn/xray.config.example.json infra/vpn/xray.config.json
# заполни UUID / host / Reality keys
docker compose --profile vpn up -d xray
```

В `.env` на сервере: `TELEGRAM_PROXY=socks5://xray:1080`  
Подробности: `infra/vpn/README.md`.

Сейчас `TELEGRAM_PROXY` оставь пустым.

## Структура

```
apps/api      # FastAPI
apps/worker   # Telethon + ARQ
apps/web      # Next.js
assets/       # логотип
```
