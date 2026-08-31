---
name: white-shop-parser-identity
description: White Shop worker parser and offer-identity contract (classify_offer, section glue, PDF/Excel lists, sync). Use when editing apps/worker, offer_identity, price parsing, or catalog sync from Telegram channels.
---

# Parser / offer identity

God node in the graph: `classify_offer()` — touch carefully; run worker tests.

## Contract

- One storefront product identity across suppliers via `identity_key` / classify pipeline
- Section headers and junk glue must not wipe a whole folder on sync
- Price lists: text posts + PDF/Excel attachments; no OCR in MVP
- Storefront price = median supplier prices + markup (API pricing owns the math)
- Disappeared offers leave the storefront promptly (sync policy)

## Scope

- Own: `apps/worker/**`, especially `offer_identity.py`, `parser.py`, `sync.py`, `attachments.py`
- Do not rewrite JWT/PII or Mini App chrome here

## Done

`pytest apps/worker/tests -q` (or targeted test module) green after changes.
Run `graphify update .` if hooks did not refresh (AST-only).
