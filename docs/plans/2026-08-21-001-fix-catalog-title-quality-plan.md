---
title: "Catalog title quality — MacBook RAM, strip часть, drop iMac, re-verify"
date: 2026-08-21
artifact_contract: ce-unified-plan/v1
artifact_readiness: implementation-ready
product_contract_source: ce-plan-bootstrap
execution: code
---

## Goal Capsule

- Objective: Audit storefront product titles, fix `offer_identity` so names are clean OEM-style SKUs, remove iMacs from the catalog, and re-verify published inventory no longer shows RAM leaks, «часть», Galaxy-as-Apple Watch mashups, or marketing junk in device names.
- Product authority: Worker classifier + one-shot catalog cleanup. Cart/UI/pricing out of scope.
- Open blockers: None.

## Product Contract

### Summary

Live catalog (~925 published) has systematic title defects from section glue and `_apple_other_device_name` leftovers. User reviewed screenshots: MacBook titles end with `16/`; iPad Air/Pro carry Unisale «часть N/N»; iMacs should be removed entirely; Watch/accessories mashups and «Новые»/cable misclassifications must go.

### Requirements

- R1. MacBook `device_name` must not contain RAM fragments (`16/`, `24/`), GPU tuples leftovers (`10/10/…`), or bare trailing `/`.
- R2. Strip Unisale multipart markers `(часть N/N)` / `часть N/N` from section headers and titles before naming; iPad Air/Pro titles must look like `iPad Air 11`, never `iPad Air часть Air 11`.
- R3. Reject all iMac offers (`reject_reason=imac_excluded`); unpublish existing iMac / Mac-mini-iMac mashup products.
- R4. Samsung Galaxy Watch Ultra must classify as Samsung, never Apple Watch Ultra (even when `watch ultra` token matches).
- R5. Reject or clean marketing/noise glued into Apple names: section/title tokens `Новые`, cables/аксессуары mis-hit as MacBook, duplicate Ultra 3 / Neo when caused by section glue.
- R6. After classifier fixes, refresh or unpublish existing bad published rows so the storefront matches current classifier (not stale titles).
- R7. Regression tests for each failure class above; existing Top/Unisale smoke must not regress materially.

### Scope Boundaries

**In scope:** `apps/worker/offer_identity.py`, `apps/worker/tests/test_offer_identity.py`, one-shot cleanup (script or admin SQL via Python) against local DB published products.

**Out of scope:** Cart UI, catalog search UI, markup=0 pricing (already applied), inventing new product families, Telegram re-fetch (reclassify existing offers is enough for DoD).

### Key Decisions

- KD1. Remove iMacs entirely from storefront — session-settled: user-directed («аймаки давай лучше нахрен уберем»); rejected: polish iMac titles and keep them.
- KD2. Fix titles at classifier root (`offer_identity`), then cleanup DB — session-settled: user-directed audit; rejected: display-only frontend stripping.
- KD3. Strip `(часть N/N)` globally for Apple section/title glue — session-settled: root cause of iPad «часть»; rejected: per-product hardcodes.
- KD4. Prefer Galaxy Watch parser before Apple `watch ultra` token — session-settled: observed mashups; rejected: keep Apple match with post-hoc rename.
- KD5. MacBook Neo stays when the line is a real Neo SKU; strip duplicate Neo/Air tails and «Новые» marketing — session-settled: adequacy; rejected: ban all Neo.

### Acceptance Examples

| Input | Expected |
|---|---|
| section `MACBOOK PRO 14` + `MKGQ3 · 16/1TB · Space Gray` | `MacBook Pro 14` · `16/1TB · Space Gray · MKGQ3` (no `16/` in device_name) |
| section `iPad Air (часть 1/2)` + `iPad Air 11 (M2) 2024 256GB Wi‑Fi Blue` | `iPad Air 11` (no «часть») |
| `iMac M4 (10/10/16/1TB) Orange` | reject `imac_excluded` |
| `Galaxy Watch Ultra SM-L705F … Blue` | Samsung \| Galaxy Watch Ultra … \| Blue |
| section `MacBook Новые` + `Air13 M5 16/1TB Starlight (2026)` | clean MacBook Air 13 M5 (no «Новые»/trailing `16/`) |

## Planning Contract

### Technical Approach

1. Pre-clean: `strip_multipart_part_marker(text)` removes `(часть\s*\d+\s*/\s*\d+)` and bare `часть\s*\d+\s*/\s*\d+` from section + working title before prepend/name.
2. Expand junk/noise: treat sections containing only marketing (`Новые`, `обменки`) as non-glue; strip those tokens from MacBook tails; reject cable/lightning accessory lines that match `macbook` falsely.
3. RAM/GPU scrub in `_apple_other_device_name` (and shared helpers): after `RAM_STORAGE_RE` / `STORAGE_RE`, also remove `\b\d{1,2}\s*/\s*` orphans, `(?:\d+\s*/\s*){2,}\d+` GPU/CPU tuples, and trailing `/`.
4. iMac: early reject when `\bimac\b` in working/title/section (unless we later re-open — out of scope).
5. Ordering: ensure `galaxy_watch` path runs before Apple watch / `watch ultra` apple_other; harden `APPLE_OTHER_RE` so `watch ultra` does not win on `Galaxy Watch Ultra`.
6. Cleanup job: for each published product with offers, re-run `classify_offer` on latest active offer; if reject or identity changed, update title/attrs or set `is_published=False` (especially all iMac).
7. Tests covering R1–R5 acceptance table.

### Files

- `apps/worker/offer_identity.py`
- `apps/worker/tests/test_offer_identity.py`
- optional one-shot: `apps/worker/cleanup_titles.py` (or inline under `python -m`)

### Key Technical Decisions

- KTD1. Strip «часть» before `should_prepend_section` so Unisale multipart headers become `iPad Air` / `iMac Mac mini` (then iMac still rejected).
- KTD2. iMac reject is hard-fail publish gate, not category hide on the web.
- KTD3. DB cleanup rewrites `Product.title` / `attributes` from classifier when publish=True; unpublish when publish=False.

### Assumptions

- Local Postgres has current published catalog; no git remote → LFG ships local commits only.
- MacBook Neo is a valid product family when present on supplier lines.

### Open Questions

- None blocking. Deferred: whether Mac mini alone (non-iMac) stays — yes, keep Mac mini if cleanly classified.

## Implementation Units

### U1. Classifier hygiene (MacBook RAM, часть, iMac reject, Galaxy Watch)

**Files:** `apps/worker/offer_identity.py`, `apps/worker/tests/test_offer_identity.py`

**Approach:** Implement strip helpers + reject/order fixes; add focused tests from acceptance table and live DB failure samples.

**Test scenarios:**
- MacBook order-code line: no `16/` in `device_name`
- iPad Air section with «часть»: no «часть» in `device_name`
- iMac line: `publish is False`, reason `imac_excluded`
- Galaxy Watch Ultra: brand Samsung, not Apple
- MacBook Новые section: no «Новые» in `device_name`

### U2. Catalog cleanup + storefront re-verify

**Files:** cleanup script or one-shot module; verify via DB counts

**Approach:** Reclassify active offers → update/unpublish products; report before/after counts for `часть`, trailing `16/`, iMac published, Galaxy-as-Apple.

**Test scenarios:**
- Script dry-runnable / idempotent
- After run: published iMac count = 0; published titles matching `часть` / `\d+/` in MacBook device_name ≈ 0

## Verification Contract

- `PYTHONPATH=. .venv/bin/pytest apps/worker/tests/test_offer_identity.py -q`
- Cleanup report: zero published iMac; spot-check MacBook/iPad facets
- Optional: curl `/api/v1/catalog/products?device_category=…` smoke

## Definition of Done

- [ ] U1 tests green
- [ ] U2 cleanup applied on local DB
- [ ] Published catalog free of iMac, «часть» in iPad names, MacBook `16/` device_name leaks (spot-audit)
- [ ] Local commit of title-quality changes (no remote → no PR)
