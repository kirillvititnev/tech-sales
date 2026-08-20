---
title: "ЮНИСЕЙЛ ОПТ — multi-brand adequacy + parser coverage"
date: 2026-08-20
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

## Goal Capsule

- Objective: Qualify ЮНИСЕЙЛ ОПТ (`opt_uniseil` / telegram `2621999285`) so live unique price lines classify into adequate storefront SKUs; close the current ~368 rejects with manufacturer-backed names/colors; deepen sync so the channel’s multi-part price posts are ingested.
- Product authority: Worker parser/identity/sync for this supplier channel. Cart/UI out of scope.
- Open blockers: None (adequacy rules settled below; disputed colors resolved via manufacturer sources during implementation).

## Product Contract

### Summary

Unisale posts a large multi-brand catalog (Apple, Samsung, Xiaomi, Huawei, Dyson, Yandex, gaming, headphones/speakers, cameras). Live pull yields ~1833 unique lines; current classifier publishes ~1465 and rejects ~368 (`noise_or_unrecognized`, sparse `*_missing_color`). Expand parsers with **precision**: every new SKU must map to a real manufacturer model/finish; when unsure, look up the OEM page and reject rather than invent.

### Requirements

- R1. Adequacy gate: publish only when brand + device family + storage/config (or equivalent) + color/finish (when the line states one) resolve to a coherent OEM SKU; reject ambiguous or counterfeit-looking lines.
- R2. On disputed color/model names, consult manufacturer specs (Samsung/Google/Huawei/JBL/Marshall/Dyson/DJI/etc.) and normalize to official-ish finishes; if no mapping, reject with a clear reason.
- R3. Cover Unisale reject clusters from live inventory (2026-08-20):
  - Audio: JBL, Marshall, Beats, Bose, Sennheiser, Harman Kardon, Bowers & Wilkins, Beoplay
  - MacBook lines with leading Apple order codes (`MC654 Air 13 …`, `MPHH3 Pro 14 …`)
  - Android: Realme, OnePlus, Nothing Phone, Tecno; Pixel colors (Lemongrass/Snow); Huawei finishes (Lake Cyan, Guava Soda)
  - Samsung Z Fold8 / Z Flip7 / S25 FE color tokens (Jetblack, Pistachio, …)
  - Cameras/action: Fujifilm Instax (not Insta360), DJI Osmo Pocket/Action, GoPro Hero, Canon PowerShot
  - Meta Ray-Ban lines that omit the word “Meta” but carry RW401x
  - Dyson AM07 + V16s Piston Animal Submarine
- R4. Preserve existing Top/Bests rules (iPhone SIM, AirPods Max gen reject, Galaxy Plus naming, trailing flags).
- R5. Sync: ensure Unisale multi-part posts are fetched (raise messages-per-channel for Apple folder sync or channel-specific depth) so DB matches live Telegram coverage, not the stale 415-offer subset.
- R6. Tests: fixtures for each new brand family + Unisale-shaped MacBook/order-code lines; Top smoke must stay ≥406/412 publish.

### Scope Boundaries

**In scope:** `apps/worker/offer_identity.py`, `parser.py` (only if Unisale line shapes need it), `sync.py` / `run_sync` message depth, worker tests, optional Unisale audit script under tests or docs note in plan appendix.

**Out of scope:** Storefront redesign, cart PR, PDF/Excel, inventing brands not present in Unisale live pull.

### Key Decisions

- KD1. New kind `audio` for headphone/speaker brands (JBL/Marshall/Beats/Bose/Sennheiser/HK/B&W/Beoplay); cameras under kind `camera` (Instax/DJI/GoPro/Canon) — session-settled: user-directed multi-brand expansion; rejected stuffing everything into `android`/`gaming`.
- KD2. Precision over recall on Unisale — session-settled: user-directed (“проверяй каждый товар… при сомнениях гугли”); rejected auto-publish unknown colors as raw tokens without OEM check.
- KD3. MacBook: leading 5-char Apple order code is `model_code`, body parsed as Air/Pro — session-settled: pattern from Unisale lines; rejected treating order code as device name.
- KD4. Fujifilm Instax ≠ Insta360 — session-settled: research/adequacy; rejected routing Instax into `insta360`.
- KD5. Keep separate kinds from Bests plan (`android`, `gaming`, `dyson`, `yandex`, `meta`) and extend them rather than rewrite — session-settled: user-approved prior work.

### Acceptance Examples

| Supplier | Expected |
|---|---|
| `JBL Flip 7 (Purple) - 8800` | JBL \| Колонки \| Flip 7 \| Purple |
| `MC654 Air 13 Silver M4 24/512GB - 127300` | Apple \| Ноутбуки \| MacBook Air 13 M4 \| 24/512GB · Silver · MC654 |
| `Realme c85 8/256GB Blue 🇷🇺` | Realme \| Смартфоны \| Realme C85 \| 8/256GB · Blue |
| `Galaxy z fold8 12/512GB Pistachio 🇹🇭` | Samsung \| Galaxy Z Fold8 \| 12/512GB · Pistachio |
| `Instax sq1 Square Chalk White` | Fujifilm \| Фото \| Instax Square SQ1 \| Chalk White |
| `DJI Osmo 6 Action (Adventure Combo) Black` | DJI \| Экшн-камеры \| Osmo Action 6 \| Adventure Combo · Black |

## Planning Contract

### Technical Approach

1. Live-audit Unisale (Telethon) → reject buckets (done for planning); re-run after implementation as DoD gate (target: reject only deliberate adequacy rejects + known Apple Max/watch gaps if any appear).
2. Extend `OfferKind` with `audio`, `camera`; wire `publish_kinds` + floors (~2000 audio accessories, ~8000 cameras/phones).
3. Parsers:
   - `parse_audio` — brand lexicons + parenthetical colors; title-case model
   - `parse_camera` — Instax / DJI Osmo / GoPro Hero / PowerShot
   - Extend `parse_android` for Realme/OnePlus/Nothing/Tecno + color alias table (OEM-checked)
   - Extend `parse_macbook_bare` for leading `[A-Z0-9]{5}` order codes
   - Samsung Fold/Flip casing + FE/Jetblack/Pistachio aliases
   - `parse_meta_rayban` tolerate `Ray-Ban` + `RW401x` without Meta token
   - Dyson AM07 / V16s submarine naming
4. Sync: default `messages_per_channel` high enough for Unisale multi-part lists (e.g. ≥80–120) or document `--messages` in run_sync; verify Unisale offer count rises after sync.
5. Adequacy: for each new color alias, cite OEM in test docstring or comment when non-obvious; reject unknown android colors via existing `android_missing_color` rather than empty publish.

### Files

- `apps/worker/offer_identity.py`
- `apps/worker/sync.py` (and/or `run_sync.py` default messages)
- `apps/worker/tests/test_offer_identity.py`
- `docs/plans/2026-08-20-005-feat-unisale-opt-parser-plan.md` (this file)

### Implementation Units

- **U1** Audio brand parser + tests (JBL/Marshall/Beats/Bose/Sennheiser/HK/B&W/Beoplay)
- **U2** MacBook leading order-code + Neo/Air Unisale shapes
- **U3** Android: Realme/OnePlus/Nothing/Tecno + Pixel/Huawei color adequacy
- **U4** Samsung Z Fold/Flip/FE finishes; Ray-Ban RW*; Dyson AM07/V16s
- **U5** Camera kind: Instax / DJI / GoPro / PowerShot
- **U6** Sync depth + live Unisale audit gate + Top regression smoke

### Verification Contract

- `pytest apps/worker/tests/test_parser.py apps/worker/tests/test_offer_identity.py`
- Live Unisale: unique lines; publish/reject; reject buckets must not include JBL/Marshall/MacBook-order-code/Realme/Beats as bulk `noise_or_unrecognized`
- Top re:sale DB smoke: publish ≥406 / unique ~412 with only expected rejects

### Definition of Done

- Units implemented with OEM-checked aliases where needed
- Live Unisale reject rate for previously listed brand buckets near zero (adequacy rejects only)
- Local commit on feature branch (no remote in this checkout)
- User-facing readiness to review Unisale line-by-line if desired
