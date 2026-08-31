---
name: white-shop-storefront-mini
description: White Shop storefront and Telegram Mini App UI invariants (Apple HIG, tab bar, no product-page navigation from cards). Use when editing apps/web customer UI, /mini, cart, checkout chrome, or catalog cards.
---

# Storefront / Mini App

Follow `.cursor/rules/apple-design.mdc` and skills-first UI section.

## Invariants

- Catalog cards must **not** navigate to `/product/[slug]`
- Mini App: bottom tab bar, safe areas, sheets for secondary flows
- Touch targets ≥ 44px; contrast ≥ 4.5:1; light and dark
- Sentence case; errors next to fields (`aria-invalid`, `role="alert"`)
- Never prefill passwords
- Grouped lists for cabinet/settings; confirm destructive actions

## Scope

- Own: `apps/web/src/app/(site)`, `/mini`, shared components used by storefront
- Do not own: `/admin` (Admin agent), API routers (API agent)

## Done

Browser-verify the changed flow on desktop and narrow width when UI changed.
