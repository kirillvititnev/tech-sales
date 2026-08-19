---
title: "Parser quality: Apple offers → clean storefront SKUs"
date: 2026-08-20
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-brainstorm
execution: code
---

## Goal Capsule

- Objective: Raise Apple-folder parse quality so the storefront shows precise, deduplicated product cards (model + storage/attrs + color + SIM), with region used only to infer SIM and retained for admin — not as a storefront differentiator.
- Product authority: This contract owns parser/matching/publish rules for Telegram Apple-folder offers into the existing White Shop catalog. Surrounding work (other folders, PDF/Excel, Mini App, Flutter) is not active scope.
- Open blockers: None.

## Product Contract

### Summary

White Shop syncs Apple Telegram channels into offers and products, but marketing noise, section-header glue, weak spelling normalization, and region/SIM inconsistency pollute the storefront. This work hardens parsing toward precision: reject garbage and ambiguous iPhone lines, normalize at medium aggressiveness, infer SIM from text and region using Apple regional rules, and publish one card per configuration without region in the title.

### Problem Frame

Buyers and the operator need trustworthy cards. Today products include junk and near-duplicate titles because match keys keep SIM wording inconsistently and strip flags without applying region→SIM rules. Missing a rare line is acceptable; publishing phones, promo banners, or glued section titles is not.

### Requirements

- R1. Prefer precision over recall: when a line is ambiguous or fails hard filters, do not publish it to the storefront.
- R2. Storefront product identity for matching and display is model + storage (or equivalent attrs) + color + SIM type — never region/country/flag.
- R3. Region (flag emoji, USA/US, HK, JP, CN, etc.) may be stored in admin-facing attributes / raw offer metadata; it must not appear in the storefront title or split cards.
- R4. Canonical storefront SIM types are exactly three: `eSIM`, `Sim+eSIM`, `2Sim` (dual physical / nano-only).
- R5. Explicit SIM text in the offer wins over region inference when present (after synonym normalization). Synonyms for `2Sim` include dual nano, 2×SIM, physical-only, «только физ. SIM».
- R6. When SIM text is absent, infer SIM from model + region using KD4 tables. If both SIM and region are absent for an iPhone, do not publish.
- R7. China mainland iPhones that are dual-nano / no-eSIM at the hardware level publish as `2Sim` — not as `Sim+eSIM`.
- R8. Hong Kong / Macao dual-nano hardware and supplier lines that explicitly say dual physical / no eSIM also publish as `2Sim`.
- R9. Publish all recognized Apple products (iPhone, iPad, Mac, Watch, AirPods, accessories) when model + price parse successfully and filters pass.
- R10. Hard-reject explicit noise: supplier phone numbers as prices, marketing/banner lines, section headers without a price.
- R11. Hard-reject offers below a configurable minimum price; default floor is 6000 RUB.
- R12. Matching aggressiveness is medium: normalize SIM/storage synonyms, strip flags for identity, normalize model/color spelling, and prevent section-header prepend glue — no fuzzy title merging.
- R13. After a successful Apple-folder re-sync under these rules, storefront must not show marketing/phone junk, must collapse JP/US eSIM equivalents into one card when SIM matches, and must apply 14–16 / 17 / Air SIM inference correctly when region is known.

### Scope Boundaries

**In scope**
- Parse, normalize, match, SIM inference, publish/hide rules for Telegram folder “Apple”.
- Admin retention of region/raw variants as attributes.
- Configurable price floor (default 6000).

**Out of scope**
- Other Telegram folders, PDF/Excel supplier files.
- Storefront visual redesign, Mini App, Flutter.
- Aggressive fuzzy matching.
- Changing median + markup + round-to-100 pricing math.

### Key Decisions

- KD1. Precision + hard garbage over max recall — session-settled: user-directed; rejected max recall.
- KD2. Three SIM SKUs (`eSIM` / `Sim+eSIM` / `2Sim`); China dual-nano → `2Sim` — session-settled: user-directed (corrected from earlier Sim+eSIM map).
- KD3. Region for SIM inference + admin attrs; one storefront card without region — session-settled: user-directed.
- KD4. iPhone SIM inference (authority: [Apple Support 118569](https://support.apple.com/en-us/118569), Dual SIM [108898](https://support.apple.com/en-us/108898)):

  **iPhone 14 / 15 / 16 (+ Plus/Pro/Pro Max / 16e)**
  - US → `eSIM`
  - China mainland → `2Sim`
  - Other non-US → `Sim+eSIM`
  - HK/Macao dual-nano → `2Sim`

  **iPhone 17e / 17 / 17 Pro / 17 Pro Max**
  - eSIM-only markets → `eSIM`: US, USVI, Canada, Mexico, Japan, Guam, UAE, Saudi Arabia, Bahrain, Kuwait, Qatar, Oman
  - China mainland 17/Pro/Max → `2Sim`; CN 17e → `eSIM` when Apple’s China eSIM note applies
  - HK/Macao dual-nano → `2Sim`
  - Other markets outside eSIM-only list → `Sim+eSIM`

  **iPhone Air** → always `eSIM` (including China)

- KD5. Catalog coverage: all recognized Apple with model+price — session-settled: user-directed.
- KD6. iPhone with neither SIM nor region → do not publish — session-settled: user-directed.
- KD7. Garbage = explicit noise + configurable price floor (start 6000) — session-settled: user-directed.
- KD8. Medium matching, not fuzzy — session-settled: user-directed.

### Actors

- A1. Catalog operator / admin
- A2. Storefront buyer
- A3. Sync worker (system)

### Key Flows

- F1. Offer line → parse → noise & price-floor → normalize → resolve SIM → iPhone missing SIM+region? drop → match key without region → median price upsert. (R1–R13)
- F2. Admin sees region variants in attributes; storefront title omits region. (R2–R3)

### Acceptance Examples

- AE1. Covers R2–R4, R12. JP + US eSIM same model/storage/color → one card `… · eSIM`.
- AE2. Covers R6, KD4. `🇺🇸 16 Pro 256GB Black` → `eSIM`.
- AE3. Covers R6, KD4. `🇪🇺 16 Pro 256GB Black` → `Sim+eSIM`.
- AE4. Covers R6, KD4. `🇯🇵 17 Pro 256GB` → `eSIM`.
- AE5. Covers R6, KD4. `🇩🇪 17 Pro 256GB` → `Sim+eSIM`.
- AE5b. Covers R7, KD4. `🇨🇳 17 Pro Max 256GB` / `CN 16 Pro 256GB` → `2Sim`.
- AE6. Covers KD4. Any iPhone Air (incl. CN) → `eSIM`.
- AE7. Covers R6, R1. `17e 256GB Black` no region/SIM → not published.
- AE8. Covers R10, R11. Marketing; phone number; accessory 2500 RUB → rejected.
- AE9. Covers R12. Section `iPhone 17 Pro Max` glued onto `17e 256GB` → no glued duplicate; parse as 17e or drop.

### Success Criteria

- Re-sync yields no marketing/phone-number products on public catalog.
- eSIM-only region pairs collapse when SIM matches.
- Spot-check 14–16 US vs EU and 17 JP vs EU / CN matches KD4.
- Price floor remains configurable; default 6000.

### Assumptions

- Median + markup + round-to-100 pricing unchanged.
- Air is eSIM-only globally despite ambiguous dual listing on Apple 118569.
- “Recognized Apple” = classifier finds a usable Apple model/token.

### Outstanding Questions

- Deferred to Planning: exact synonym tables; admin attribute JSON shape; whether rejected offers are retained for audit — settled below as KTDs / unit details.

### How This Work Fits Together

<!-- ce-section: work-relationships -->

Quality pass on the existing Apple Telegram → catalog pipeline. Enables a trustworthy storefront and later folders/parsers; those expansions are not in this plan.

## Planning Contract

### Key Technical Decisions

- KTD1. Split offer structuring into a dedicated pure module `apps/worker/offer_identity.py` (parse fields, normalize, SIM infer, match key, display title) called from `parser.py` / `sync.py` — session-settled: user-approved; rejected growing only `parser.py` into a kitchen sink. Reason: unit-testable without Telethon/DB.
- KTD2. Match key = SHA1 of canonical identity string `model|storage|color|sim` (lowercased, no region) — replaces today’s `normalize_title(full_title)` as the product grouping key. `external_key` for offers may keep raw-line hash for channel offer upserts, but product grouping must use identity key. Reason: R2/R3.
- KTD3. Encode Apple region→SIM tables as data constants in `offer_identity.py` with a single `infer_sim(model, region, sim_text) -> SimType | None` — session-settled: user-approved. Source: Apple Support 118569 / 108898.
- KTD4. Price floor via `MIN_OFFER_PRICE_RUB` (env, default `6000`) on `WorkerSettingsEnv` — session-settled: user-directed (KD7).
- KTD5. Section glue: only prepend section when the line title looks like a continuation (starts with storage/color/SIM tokens, or lacks a model family token that the section provides) — never prepend when the line already contains an iPhone/model token. Covers AE9.
- KTD6. Non-iPhone Apple lines: no SIM required; match key uses model+attrs+color with `sim=""`. iPhone-only gates for R6/R7.
- KTD7. Product `attributes` store at least `{folder, sim, region_samples, norm_key, model, storage, color}`; storefront `title` built without region. Unpublished products stay unpublished when identity fails filters (`is_published=False`); do not delete offers (audit retained).

### High-Level Technical Design

```text
Telegram message
  → parse_price_text (line/price + careful section)
  → classify_offer (fields + noise?)
  → price < MIN_OFFER_PRICE? drop
  → resolve_sim (text > region tables)
  → iPhone && !sim → drop
  → identity_key / display_title
  → ProductOffer upsert (raw retained)
  → group by identity_key → median price → Product title/attrs
```

Follow existing patterns in `apps/worker/sync.py` (`storefront_price`, `APPLEISH`, folder attributes) and `apps/worker/parser.py` (`PRICE_LINE_RE`, `parse_price_token`).

### Implementation Units

### U1. Offer identity + SIM inference (pure)

- Goal: Structured identity and SIM resolution without I/O.
- Requirements: R2–R8, R12 (normalization), KD4
- Files: `apps/worker/offer_identity.py` (new), optionally thin re-exports from `apps/worker/parser.py`
- Approach: Extract region (flags + tokens US/USA/CN/JP/HK/…); normalize SIM synonyms to `eSIM`|`Sim+eSIM`|`2Sim`; infer per KD4; build `identity_key` and `display_title` without region; medium model/color/storage normalization.
- Test scenarios:
  - AE1–AE7, AE5b, AE6 as unit cases
  - Explicit SIM text overrides wrong region
  - Air always eSIM
  - Missing SIM+region on iPhone → None / reject signal
- Verify: `pytest apps/worker/tests/test_offer_identity.py -q`

### U2. Parser section glue + noise helpers

- Goal: Fix section prepend; expose helpers for marketing/noise detection used by sync.
- Requirements: R10, R12, AE9
- Files: `apps/worker/parser.py`, `apps/worker/tests/test_parser.py` (new)
- Approach: Apply KTD5 glue rule; keep price-line regex; treat banner-like titles (АКЦИЯ, прайс, только сегодня, WhatsApp, etc.) as noise; phone-as-price already partly in `parse_price_token`.
- Test scenarios:
  - AE9 glue
  - Section header alone yields no ParsedLine
  - Marketing title flagged / skipped
- Verify: `pytest apps/worker/tests/test_parser.py -q`

### U3. Config floor + sync publish path

- Goal: Wire identity into sync; enforce floor; publish clean titles/attrs.
- Requirements: R1, R9–R11, R13, F1–F2
- Files: `apps/worker/config.py`, `apps/worker/sync.py`, `.env.example`, `Makefile` (extend `make test` to worker tests)
- Approach: Read `min_offer_price_rub`; after parse, run identity pipeline; group products by `identity_key`; set `title`/`attributes` per KTD7; skip publish when identity rejects; keep median pricing.
- Test scenarios:
  - Unit test sync grouping helpers if extracted; otherwise cover via identity+parser and a small pure `group_key` helper test
  - Floor rejects 2500 (AE8)
- Verify: `pytest apps/worker/tests apps/api/tests -q` (or `make test` after Makefile update)

### U4. Characterization / regression fixtures

- Goal: Lock AE matrix so future edits cannot silently regress SIM tables.
- Requirements: R13, all AEs
- Files: `apps/worker/tests/fixtures/sim_cases.json` (optional) or parameterized tests in `test_offer_identity.py`
- Approach: Table-driven tests mirroring AE1–AE9; CN→2Sim asserted explicitly.
- Verify: same pytest command as U1

### Verification Contract

- Command: `PYTHONPATH=. .venv/bin/pytest apps/worker/tests apps/api/tests -q`
- Also update `Makefile` `test` target to include `apps/worker/tests`.
- Manual (optional, not blocking DoD): `make sync-apple` then spot-check catalog API for CN/JP/US samples — only when Telegram session is available.

### Definition of Done

- All units U1–U4 complete; AE1–AE9 covered by automated tests.
- `make test` green including worker tests.
- Product Contract R1–R13 addressed; no fuzzy matcher introduced.
- Abandoned experimental code removed from the diff.
- Session-settled KTDs/KDs preserved (China = `2Sim`, floor configurable default 6000, medium match).
