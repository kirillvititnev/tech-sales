---
title: "Admin MVP — channels, catalog, HOT, price log, markup, orders"
date: 2026-08-20
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

## Goal Capsule

- Objective: Deliver the first usable White Shop admin surface covering REQUIREMENTS §8.1 essentials operators need daily: channels, catalog/HOT/manual products, price provenance, default markup, and orders — without analytics, auth hardening, or referral tooling yet.
- Product authority: This plan owns `/admin` IA and `/api/v1/admin/*` expansions listed below. Matching moderation queue UX, Telegram admin alerts, users/bonuses, and analytics are out of scope.
- Open blockers: None. Admin remains unauthenticated in this slice (same as current `/admin`); JWT/admin login is a follow-up.

## Product Contract

### Summary

Today admin only lists orders. Operators need to see supplier channels and errors, manage storefront cards (HOT / publish / manual), inspect where a price came from, and adjust the default markup. Orders stay in the same shell with clearer navigation.

### Requirements

- R1. Admin shell with navigation: Заказы | Каналы | Каталог | Наценка | (home).
- R2. Channels page: list title, folder, status, last_parsed_at, last_error; allow pause/activate status toggle.
- R3. Catalog page: list products (published and unpublished), search by title; toggle `is_hot` and `is_published`; create a manual product (title, price, optional brand, HOT).
- R4. Product price log: for a product, show active supplier offers with channel title, raw_title, raw_price, parsed_at, message id — provenance for admin audit (§2.7).
- R5. Markup page: view/edit store default `markup_percent` and `price_round_to` persisted in DB (fallback to env defaults); changing settings does not require mass reprice in this slice (document that re-sync / future reprice applies).
- R6. Orders page remains available under admin nav with existing status actions.
- R7. Russian UI labels; no analytics dashboards.
- R8. No admin password gate in this slice (explicit deferral).

### Scope Boundaries

**In scope:** Admin Next.js multi-page shell; admin API for channels status, products CRUD-lite, offers log, store settings; wire existing orders.

**Out of scope:** Matching moderation queue UI; Telegram notify admin; users/referrals/bonuses; category tree editor; PDF upload; role system; analytics; forcing global reprice job.

### Key Decisions

- KD1. Admin MVP = §8.1 must-haves minus users/referrals and matching queue — session-settled: user-directed (`/lfg админка` after ordered TZ); rejected waiting for full auth first.
- KD2. Auto-publish remains; admin intervenes via publish/HOT toggles — session-settled: user-directed (§8.2).
- KD3. Single default markup strategy editable now; per-category strategies later — session-settled: user-directed (§3.1 “базово фикс %, заложить гибко”).
- KD4. Admin auth deferred — session-settled: user-approved for this slice.

### Actors

- A1. Store admin / operator

### Key Flows

- F1. Open /admin → navigate to Каналы → pause failing channel.
- F2. Каталог → find product → open price log → toggle HOT.
- F3. Каталог → add manual product → appears on storefront when published.
- F4. Наценка → set 12% → saved for subsequent pricing reads.

### Acceptance Examples

- AE1. Channel with `status=error` can be set to `paused` then `active` via admin API/UI.
- AE2. Manual product with price 99900 appears in public catalog when `is_published=true`.
- AE3. Product with linked offers returns non-empty price log entries with channel title.
- AE4. PATCH settings markup 12 persists and GET returns 12.

### Success Criteria

- Admin nav covers R1 sections; API tests for settings, manual product, channel status, offers list; `make test` / web build green.

## Planning Contract

### Key Technical Decisions

- KTD1. `StoreSettings` singleton row (`id=1`) for markup_percent + price_round_to; seed on first GET.
- KTD2. Admin product list includes unpublished; public catalog unchanged.
- KTD3. Manual product: `is_manual=True`, slug from title+hash, `cost_median=price` before markup or set price directly as storefront price with markup_percent=0 for simplicity — **use entered price as final storefront price** for manual items (operator sets shelf price).
- KTD4. Offers endpoint joins channel; limit 100 active offers by product_id.
- KTD5. Next.js `/admin` layout + subroutes; client components for mutations.

### Implementation Units

### U1. StoreSettings + admin settings API

- Files: `apps/api/models/catalog.py` or `settings.py`, schemas, `admin.py`, tests
- Verify: pytest settings GET/PATCH

### U2. Admin channels + catalog + offers APIs

- Files: `apps/api/routers/admin.py`, schemas
- Endpoints: PATCH channel status; GET products admin; PATCH product flags; POST manual product; GET product offers
- Verify: pytest

### U3. Admin Next.js shell + pages

- Files: `apps/web/src/app/admin/layout.tsx`, `page.tsx` (orders), `channels/`, `catalog/`, `catalog/[id]/`, `settings/`, `lib/api.ts`
- Verify: `npm run build`

### Verification Contract

- `PYTHONPATH=. .venv/bin/pytest apps/api/tests apps/worker/tests -q`
- `node --experimental-strip-types --test apps/web/src/lib/telegramUser.test.ts`
- `cd apps/web && npm run build`

### Definition of Done

- U1–U3 complete; R1–R7 met; R8 documented in plan/README note.
- Local commit (no remote).

### How This Work Fits Together

<!-- ce-section: work-relationships -->

Next TZ slices after this admin MVP: auth/ЛК, matching queue, multi-folder sync, PDF/Excel, referrals, Flutter.
