---
title: "Telegram Mini App — store parity with site checkout"
date: 2026-08-20
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

## Goal Capsule

- Objective: Ship a Telegram Mini App shell that exposes the same catalog → product → checkout → order confirmation flow as the White Shop website, using Telegram WebApp context where available.
- Product authority: This plan owns Mini App UX/shell and initData-aware checkout prefills. Full JWT auth, ЛК, referrals, multi-brand folders, PDF/Excel, Flutter, and deep admin remain separate TZ areas.
- Open blockers: None for coding. Bot token / HTTPS public URL are ops prerequisites for production BotFather setup; local/dev works with WebApp stub when outside Telegram.

## Product Contract

### Summary

REQUIREMENTS §7 prioritizes Mini App with full site parity. The site already has catalog, product, checkout (Moscow pickup / CDEK), and order pages. This work wraps that experience for Telegram: detect WebApp, theme/viewport, prefill buyer fields from Telegram user, and keep one Next.js codebase.

### Requirements

- R1. Mini App entry route (e.g. `/mini` or root with Mini App detection) shows catalog equivalent to the site catalog.
- R2. Product detail and checkout are reachable from Mini App with the same delivery rules (pickup Moscow / CDEK + address) and manager-only payment copy.
- R3. When `Telegram.WebApp.initDataUnsafe.user` is present, prefill name and telegram username on checkout; phone remains manual if Telegram does not provide it.
- R4. Outside Telegram (browser), Mini App routes still work as a normal store (graceful degradation) for local QA.
- R5. Call `WebApp.ready()` and `WebApp.expand()` when the script is available; respect dark/light theme variables when practical without a full redesign.
- R6. Order success page remains reachable and shows order number/status; MainButton optional enhancement may open checkout but is not required if in-page CTA works.
- R7. Document BotFather / env knobs (`NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` optional, `TELEGRAM_BOT_TOKEN` for future server validate) in `.env.example` without requiring token for unit tests.
- R8. Do not block Mini App on full JWT auth; initData server verification may be stubbed/logged for a follow-up auth plan.

### Scope Boundaries

**In scope:** Next.js Mini App shell, WebApp script loader, checkout prefill, catalog/product/checkout/order parity paths, light styling hooks, env docs.

**Out of scope:** Flutter; email/password + JWT ЛК; referral bonuses; admin Telegram notifications; PDF/Excel; non-Apple folders; validating initData HMAC in production-hardening depth (note as follow-up).

### Key Decisions

- KD1. Mini App = full site functional parity — session-settled: user-directed (REQUIREMENTS 7.2); rejected “урезанный Mini App”.
- KD2. One Next.js app for site + Mini App + admin — session-settled: user-directed (stack §11); rejected separate mini SPA.
- KD3. Checkout delivery + manager payment already on site are reused — session-settled: user-approved.
- KD4. Full auth deferred; soft prefill from WebApp user only — session-settled: user-approved for this slice.

### Actors

- A1. Buyer in Telegram Mini App
- A2. Buyer testing Mini App routes in desktop browser
- A3. Operator configuring BotFather URL (ops)

### Key Flows

- F1. Open Mini App → catalog → product → checkout (prefilled) → order confirmation. (R1–R4)
- F2. Open `/mini` in browser without Telegram → same flow without prefill. (R4)

### Acceptance Examples

- AE1. In WebApp mock with user `{first_name, username}`, checkout shows name + @username prefilled.
- AE2. CDEK without address still rejected by existing API.
- AE3. `/mini` without Telegram script still lists products when API is up.

### Success Criteria

- Mini App routes usable for catalog and checkout end-to-end against local API.
- Prefill works when WebApp user present.
- Tests cover WebApp helper + checkout prefill behavior; `make test` / web unit or lightweight tests green.

## Planning Contract

### Key Technical Decisions

- KTD1. Add `/mini` route group (or `apps/web/src/app/mini/...`) reusing catalog/product/checkout/order components — avoid duplicating business logic.
- KTD2. Client helper `lib/telegram.ts`: load `telegram-web-app.js`, expose `getTelegramUser()`, `isTelegramWebApp()`, `readyMiniApp()`.
- KTD3. Extend `CheckoutForm` with optional `defaults` prop for name/telegram; Mini checkout page passes Telegram user.
- KTD4. Keep admin outside Mini App primary nav; Mini header links catalog/HOT/orders lookup only.
- KTD5. Server-side initData HMAC validation is a stub TODO behind env `TELEGRAM_BOT_TOKEN` — not blocking publish of shell.

### Implementation Units

### U1. Telegram WebApp client helper

- Goal: Detect WebApp, ready/expand, read user.
- Files: `apps/web/src/lib/telegram.ts`, `apps/web/src/components/TelegramProvider.tsx`
- Test: unit-testable pure parsing of unsafe user shape (mock window).
- Verify: vitest or node test if present; else small TS-safe helpers tested via jest-free node assert script — prefer adding `apps/web` vitest only if already configured; otherwise test helper logic in a tiny `apps/web/src/lib/telegram.test.ts` with vitest from Next, or skip to Python-free — **use a minimal Node test file run by Makefile** OR document browser QA. Prefer: extract pure functions and test with pytest-incompatible — actually use `node --test` on compiled/plain JS. Simplest: put pure functions in telegram.ts and add `apps/web/scripts/telegram-helper.test.mjs` OR use existing pattern. **Decision: add vitest only if package.json easy; else test via documented manual + TypeScript compile.** Better: add pure functions tests with `node --import tsx --test` if tsx available. Simplest path for monorepo: create `apps/api` doesn't fit. I'll add a small `apps/web/src/lib/telegramUser.ts` pure module and test it from a node script in Makefile.

Actually Next.js project may not have vitest. I'll add pure `parseTelegramUser` and test with a simple node assert in `apps/web/src/lib/__tests__` using node:test on a .mjs re-export. Or just rely on TypeScript and one integration. Plan says tests — implement pure helper + node:test.

### U2. Mini App pages + shell

- Goal: `/mini`, `/mini/product/[slug]`, `/mini/checkout`, `/mini/order/[number]` with Mini shell header.
- Files: `apps/web/src/app/mini/**`, `apps/web/src/components/MiniHeader.tsx`
- Reuse: ProductGrid, CheckoutForm, api.ts
- Verify: `npm run build` in apps/web (typecheck)

### U3. Checkout prefill + env docs

- Goal: Wire defaults; `.env.example` bot notes; README Mini App section.
- Files: `CheckoutForm.tsx`, `.env.example`, `README.md`
- Verify: existing pytest still green; build green

### Verification Contract

- `PYTHONPATH=. .venv/bin/pytest apps/api/tests apps/worker/tests -q`
- `cd apps/web && npm run build`
- Manual: open `/mini` with API up

### Definition of Done

- U1–U3 done; R1–R7 satisfied for local/dev; R8 documented as follow-up.
- Checkout uncommitted site work included in the same ship (prerequisite).
- No Flutter/auth/referrals scope creep.

### How This Work Fits Together

<!-- ce-section: work-relationships -->

This is the next client surface after site checkout. Remaining TZ: auth/ЛК, admin depth, multi-folder sync, PDF/Excel, referrals, Flutter — separate plans/LFG runs.
