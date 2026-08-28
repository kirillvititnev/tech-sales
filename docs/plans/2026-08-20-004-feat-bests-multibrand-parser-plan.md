---
title: "Bests re:sale multi-brand parser coverage"
date: 2026-08-20
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

## Goal Capsule

- Objective: Make Bests re:sale (~855 unique price lines) classify into structured storefront offers for Huawei/Honor/Xiaomi/Redmi/Poco/Pixel, Xbox/Nintendo/Oculus, Dyson, Yandex Station, Meta Ray-Ban, Sony Portal/Pulse/VR2, Samsung A37/A57 colors + Buds/Watch, plus Bests trailing-flag price lines and MacBook “Pro 14 …” continuations.
- Product authority: Extends worker identity/parser/sync publish rules; cart/UI work on the tree is out of scope.
- Open blockers: None (disputed color names resolved via Samsung Newsroom / product pages at planning time).

## Product Contract

### Summary

Bests re:sale posts multi-brand price lists. After fixing trailing region flags after price, ~345 lines still reject as `noise_or_unrecognized` / `samsung_missing_color`. Extend `offer_identity` + `publish_kinds` so recognizable Bests products publish with brand · category · device · config.

### Requirements

- R1. Parse Bests trailing `— price 🏳️` lines (flag attached to title for region).
- R2. Publish Android phones/tablets: Huawei, Honor, Xiaomi, Redmi, Poco, Google Pixel with RAM/storage · color · connectivity when present.
- R3. Publish Xbox / Nintendo / Meta Quest (Oculus) / Logitech wheel / Steam Deck dock as gaming SKUs.
- R4. Publish Dyson hair + vacuum/purifier lines (section glue for HD## / Airwrap / V## / PH##).
- R5. Publish Яндекс Станция family with color.
- R6. Publish Ray-Ban Meta glasses (model + lens + size).
- R7. Extend Sony: Portal, Pulse Elite/3D, PlayStation VR2 Horizon.
- R8. Samsung: A37/A57 official Awesome-* colors; Galaxy Buds; Galaxy Watch 8 / Classic / Ultra.
- R9. Apple: MacBook Pro continuation titles (`Pro 14 M…`); common accessories (MagSafe cable, USB-C cable, Power Adapter, Apple TV).
- R10. Precision still wins: keep rejecting truly unparseable noise; do not invent generations for ambiguous AirPods Max.
- R11. Wire new kinds into `sync.publish_kinds` and `min_price_for_kind`.

### Scope Boundaries

**In scope:** `apps/worker/parser.py`, `offer_identity.py`, `sync.py`, worker tests; live Bests audit.

**Out of scope:** Cart UI, republish all channels in prod, PDF/Excel, Flutter.

### Key Decisions

- KD1. New kinds: `android`, `gaming`, `dyson`, `yandex`, `meta` — session-settled: user-directed (cover “и прочее”); rejected single mega-`other` blob.
- KD2. A57 colors → Awesome Navy / Gray / Icyblue / Lilac; A37 → Awesome Charcoal / Lavender / Graygreen / White (Samsung Global Newsroom) — session-settled: research-backed.
- KD3. Android phones do not require SIM inference (unlike iPhone); region flag optional metadata only — session-settled: user-approved pattern from Samsung lines.
- KD4. Keep existing Apple/Samsung/Sony/Insta360 rules intact (Top re:sale regression) — session-settled: user-directed.

### Acceptance Examples

- `Huawei Nova 15 8/256GB Black — 22.200 🇷🇺` → Huawei | Смартфоны | Nova 15 | 8/256GB · Black
- `XBOX Series X 1TB Black — 66.800` → Microsoft | Игровые консоли | Xbox Series X | 1TB · Black
- `Airwrap HS05 Long Blue/Copper — 39.500 🇭🇰` → Dyson | Стайлеры | Airwrap HS05 Long | Blue/Copper
- `A57 8/256GB Icy Blue — 33.500` → Samsung | Galaxy A57 | 8/256GB · Awesome Icyblue

## Planning Contract

### Technical Approach

1. Keep trailing-flag `PRICE_LINE_RE` (already landed in working tree).
2. Add kind parsers beside `parse_sony_ps5` / `parse_insta360`; call from `classify_offer` before unknown reject.
3. Expand `MODEL_SECTION_RE` / `should_prepend_section` so Dyson HD##, Buds, Watch, MacBook Pro, Яндекс sections glue correctly without poisoning phone lines.
4. Expand `normalize_galaxy_a_color` for a37/a57; add Galaxy Buds + Watch parsers under samsung or apple_other-adjacent samsung path.
5. Expand `APPLE_OTHER_RE` / accessory tokens for MagSafe, Power Adapter, Apple TV, USB-C Cable; MacBook body match for `Pro 14 M\d` / `Air 13 M\d`.
6. Sync: add kinds to `publish_kinds` + floors (~3000–5000 for accessories/stations, ~8000 phones, ~15000 consoles).

### Files

- `apps/worker/parser.py`
- `apps/worker/offer_identity.py`
- `apps/worker/sync.py`
- `apps/worker/tests/test_offer_identity.py`
- `apps/worker/tests/test_parser.py`

### Implementation Units

- **U1** Parser trailing-flag + section glue for Bests headers — done (trailing flag pre-landed; MODEL_SECTION_RE / should_prepend_section expanded)
- **U2** Android phone/tablet classifier (`android` kind) — done
- **U3** Gaming (Xbox/Nintendo/Quest/Logitech/Steam) + Sony Portal/Pulse/VR2 — done
- **U4** Dyson + Yandex + Meta Ray-Ban — done
- **U5** Samsung A37/A57 colors + Buds + Watch; Apple MacBook/accessory gaps — done
- **U6** Sync publish_kinds + floors; Bests live audit gate; Top smoke regression tests — done (live Bests text currently wiped; baseline reject replay 199/199 + Top smoke)

### Verification Contract

- `pytest apps/worker/tests/test_parser.py apps/worker/tests/test_offer_identity.py`
- Live Bests: unique lines publish rate for named brand buckets ≥95%; Top re:sale smoke still publishes iPhone/Samsung core fixtures.

### Definition of Done

- Plan units implemented with tests
- Bests channel inventory shows only residual rejects that are genuinely out-of-scope noise or missing attrs
- User-facing: say «готово» when Bests parses quality-wise
- PR opened via LFG shipping steps
