---
name: white-shop-orchestration
description: Routes White Shop work across specialist agents (storefront, API, parser, admin, QA, release). Use when starting a feature, splitting a PR, or deciding which agent/skill owns a task.
---

# White Shop orchestration

You are the managing agent. Humans talk only to you for intake.

## Route

| Signal in the request | Hand to |
|---|---|
| Mini App, catalog cards, cart UI, sheets, HIG | Storefront |
| JWT, `/me`, auth cookies, bonuses, orders API, Pydantic DTOs | API / accounts |
| `classify_offer`, Telethon, PDF/Excel price lists, worker | Catalog / parser |
| Admin orders/channels/catalog/HOT | Admin |
| Failing tests, “prove it”, Playwright | QA |
| CI, Docker, deploy, secrets, Trivy | Release |

## Rules

1. Write a short ticket: goal, paths, definition of done, out-of-scope.
2. Load **at most one** security skill from `.cursor/skills/` allowlist (see skills-first).
3. Start with `graphify query` / `path` before Grep/Read sprawl.
4. Prefer one specialist session over a swarm. Cap: Orchestrator + ≤2 specialists.
5. Prod deploy needs explicit human go — never auto-ship.

## Refuse

Exploit PoCs, browsing `.vendor/cybersecurity-skills/`, loading `exploiting-*` / `abusing-*`.
