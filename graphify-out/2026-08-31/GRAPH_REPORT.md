# Graph Report - tech-sales  (2026-08-31)

## Corpus Check
- 164 files · ~74,577 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1422 nodes · 3520 edges · 90 communities (81 shown, 9 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 271 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d62a7be3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- admin.py
- classify_offer
- auth.py
- security.py
- Product
- parse_price_text
- offer_identity.py
- collapse_duplicate_tokens
- useAuth
- devDependencies
- order_notify.py
- product_images.py
- User
- api.ts
- compilerOptions
- sync.py
- test_pricing.py
- extract_color
- customer_notify.py
- get_settings
- get_worker_settings
- adminFetch
- cart.tsx
- favorite_alerts.py
- secure_env.py
- formatPrice
- telegram.ts
- HTTPException
- auth.tsx
- should_prepend_section
- test_security.py
- api/main.py
- settings/page.tsx
- CheckoutForm.tsx
- ProductOut
- Vec3
- [id]/page.tsx
- assert_runtime_secrets
- AppChrome.tsx
- offer_identity module
- require_admin
- users/page.tsx
- api service
- Telethon plus ARQ worker
- Q: Why does classify_offer() connect Offer identity tests to Apple Watch parsing, Parser worker sync, Offer identity core, Offer title cleanup, Device field parsers, Junk section glue rules?
- safeHref.ts
- OrderConfirmation.tsx
- parse_apple_watch
- 16×16 SVG document/file icon
- 16×16 SVG wireframe globe icon
- Next.js horizontal wordmark
- Mini App site parity
- get_folder_channels
- White Shop interlocking WS monogram logo
- Admin MVP
- White Shop WS interlocking monogram brand mark
- 16×16 application window glyph
- route.ts
- ProductSheet
- Apple parser quality
- CartView.tsx
- 0004_admin_users.py
- 0005_markup_rules.py
- 0006_order_bonus_spent.py
- 0007_price_hygiene.py
- eslint.config.mjs
- next.config.ts
- Vercel triangle logo
- proxy.ts
- test_harden_env_replaces_placeholder_secrets
- Xray VLESS Reality
- JWT plus Telegram Login auth
- admin/layout.tsx
- PDF and Excel price-list parsing
- postcss.config.mjs
- White Shop
- Compound Engineering docs_root
- Settings
- Skills-first defensive security
- Flutter mobile
- Three-level referral cashback

## God Nodes (most connected - your core abstractions)
1. `classify_offer()` - 120 edges
2. `User` - 59 edges
3. `get_settings()` - 42 edges
4. `Product` - 36 edges
5. `Order` - 35 edges
6. `sync_folder()` - 34 edges
7. `create_order()` - 31 edges
8. `formatPrice()` - 30 edges
9. `UserNotification` - 28 edges
10. `Base` - 26 edges

## Surprising Connections (you probably didn't know these)
- `offer_identity module` --conceptually_related_to--> `Telethon MTProto worker`  [INFERRED]
  docs/plans/2026-08-20-001-feat-parser-quality-plan.md → README.md
- `Docker Compose infrastructure` --conceptually_related_to--> `api service`  [INFERRED]
  REQUIREMENTS.md → docker-compose.yml
- `Cloudflare tunnel whiteshop.tech` --conceptually_related_to--> `web service`  [INFERRED]
  infra/tunnel/config.example.yml → docker-compose.yml
- `Worker ARQ dependency` --implements--> `Telethon plus ARQ worker`  [INFERRED]
  apps/worker/requirements.txt → REQUIREMENTS.md
- `Worker Telethon dependency` --implements--> `Telethon plus ARQ worker`  [INFERRED]
  apps/worker/requirements.txt → REQUIREMENTS.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Wireframe globe from sphere plus lat/long grid** — apps_web_public_globe_icon, apps_web_public_globe_sphere_outline, apps_web_public_globe_latitude_parallels, apps_web_public_globe_longitude_meridians [EXTRACTED 1.00]
- **Window glyph visual composition** — apps_web_public_window_rounded_frame, apps_web_public_window_control_dots, apps_web_public_window_gray_fill [EXTRACTED 1.00]
- **Telegram access via Xray SOCKS proxy** — docker_compose_worker, docker_compose_xray, infra_vpn_readme_telegram_proxy, infra_vpn_readme_vless_reality [EXTRACTED 1.00]
- **White Shop Docker Compose runtime** — docker_compose_postgres, docker_compose_redis, docker_compose_api, docker_compose_worker, docker_compose_web [EXTRACTED 1.00]
- **offer_identity catalog quality pipeline** — docs_plans_2026_08_20_001_feat_parser_quality_plan_offer_identity, docs_plans_2026_08_20_004_feat_bests_multibrand_parser_plan_bests_parser, docs_plans_2026_08_20_005_feat_unisale_opt_parser_plan_unisale_parser, docs_plans_2026_08_21_001_fix_catalog_title_quality_plan_title_quality [INFERRED 0.85]

## Communities (90 total, 9 thin omitted)

### Community 0 - "admin.py"
Cohesion: 0.16
Nodes (30): admin_list_products(), _admin_product(), create_manual_product(), delete_product_image(), _dump_markup_rules(), get_admin_product(), get_settings(), _parse_markup_rules() (+22 more)

### Community 1 - "classify_offer"
Cohesion: 0.06
Nodes (74): classify_offer(), extract_region(), OfferKind, test_airpods_max_generations(), test_android_huawei_honor_xiaomi_pixel(), test_android_ram_not_iphone_16(), test_android_realme_oneplus_nothing_tecno_colors(), test_asis_category_star_and_deep_blue() (+66 more)

### Community 2 - "auth.py"
Cohesion: 0.06
Nodes (84): AuthRefreshToken, auth_telegram(), auth_telegram_login(), login(), logout(), AsyncSession, post, Request (+76 more)

### Community 3 - "security.py"
Cohesion: 0.17
Nodes (14): check_rate_limit(), public_product_attributes(), Any, rate_limit_headers(), rate_limit_rule(), RateDecision, Auth, rate limits, output filtering — defensive controls used by the API., Optional shared counter store. Failures fall back to in-process memory. (+6 more)

### Community 4 - "Product"
Cohesion: 0.18
Nodes (28): Product, _apply_product_filters(), _attr_text(), catalog_facets(), catalog_media(), _device_category_col(), _device_name_col(), get_product() (+20 more)

### Community 5 - "parse_price_text"
Cohesion: 0.09
Nodes (38): test_parse_spaced_and_dotted_prices(), attachment_filename(), _cell_str(), extract_price_list_text(), is_price_list_attachment(), message_price_texts(), _pdf_text(), Extract supplier price-list text from PDF/Excel attachments. Feeds the same… (+30 more)

### Community 6 - "offer_identity.py"
Cohesion: 0.06
Nodes (40): asis_tier(), build_config(), build_display_title(), category_for_phone(), extract_sim_text(), format_device_name(), _generation(), identity_key() (+32 more)

### Community 7 - "collapse_duplicate_tokens"
Cohesion: 0.11
Nodes (22): _apple_other_device_name(), clean_offer_title(), collapse_duplicate_tokens(), _extract_connectivity(), is_junk_offer(), _nfkc(), parse_audio(), parse_camera() (+14 more)

### Community 8 - "useAuth"
Cohesion: 0.13
Nodes (15): LoginPage(), MiniLoginPage(), MiniRegisterPage(), RegisterPage(), AccountCabinet(), bonusLabel(), PrivacyBlock(), ProfileForm() (+7 more)

### Community 9 - "devDependencies"
Cohesion: 0.06
Nodes (34): dependencies, next, react, react-dom, devDependencies, eslint, eslint-config-next, @eslint/eslintrc (+26 more)

### Community 10 - "order_notify.py"
Cohesion: 0.06
Nodes (75): AdminOrderStatus, CustomerOrderStatus, DeliveryType, str, AdminOrderAction, AdminOrderMessage, AdminOrderOut, AdminOrderStatusUpdate (+67 more)

### Community 11 - "product_images.py"
Cohesion: 0.20
Nodes (19): delete_stored_image(), image_dir(), is_storefront_image_url(), message_photo_eligible(), public_media_url(), Path, Store and serve product photos. Magic bytes only — never trust the filename., Price-list screenshots must not become every SKU's photo. (+11 more)

### Community 12 - "User"
Cohesion: 0.05
Nodes (104): _column_names(), _has_unique_on(), Inspector, upgrade(), _column_names(), Inspector, upgrade(), _column_names() (+96 more)

### Community 13 - "api.ts"
Cohesion: 0.10
Nodes (13): CatalogBrowser(), onSearchKeyDown(), pickSuggest(), Props, SORT_OPTIONS, CatalogFacets, CatalogQuery, CatalogSort (+5 more)

### Community 14 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 15 - "sync.py"
Cohesion: 0.12
Nodes (28): Category, ChannelStatus, ProductOffer, str, Singleton store pricing defaults (row id=1)., Raw supplier price offer with provenance for admin audit., StoreSettings, SupplierChannel (+20 more)

### Community 16 - "test_pricing.py"
Cohesion: 0.12
Nodes (31): apply_markup(), compute_median_cost(), _norm(), Decimal, quarantine_outliers(), quote_storefront(), Storefront pricing: median of supplier offers + markup + rounding., Return (cost_median, storefront_price) after outlier quarantine. (+23 more)

### Community 17 - "extract_color"
Cohesion: 0.10
Nodes (21): extract_color(), extract_ram(), extract_storage(), _format_insta360_body(), parse_airpods_max(), parse_android(), parse_galaxy_buds(), parse_galaxy_watch() (+13 more)

### Community 18 - "customer_notify.py"
Cohesion: 0.22
Nodes (17): UnreadNotificationsOut, CustomerTelegram, deliver_customer_telegrams(), _esc(), format_customer_telegram(), NotificationCopy, UUID, Deliver the same cabinet notices to the customer Telegram bot chat. (+9 more)

### Community 19 - "get_settings"
Cohesion: 0.24
Nodes (12): _database_url(), do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online(), get_settings(), _peer_is_trusted_proxy(), slugify_manual() (+4 more)

### Community 20 - "get_worker_settings"
Cohesion: 0.13
Nodes (17): get_worker_settings(), Any, BaseSettings, field_validator, WorkerSettingsEnv, build_proxy(), main(), Interactive Telegram MTProto login → local session file. Usage (from repo… (+9 more)

### Community 21 - "adminFetch"
Cohesion: 0.12
Nodes (21): AdminCatalogPage(), createManual(), patch(), AdminProduct, AdminProductList, AdminChannelsPage(), load(), patchChannel() (+13 more)

### Community 22 - "cart.tsx"
Cohesion: 0.20
Nodes (15): CartPriceSheet(), CartContext, CartContextValue, CartProvider(), fetchLiveProducts(), loadCart(), saveCart(), acceptCartPending() (+7 more)

### Community 23 - "favorite_alerts.py"
Cohesion: 0.27
Nodes (16): build_favorite_notices(), _clip(), FavoriteWatch, format_rub(), notice_for(), notify_favorite_watchers(), AsyncSession, Decimal (+8 more)

### Community 24 - "secure_env.py"
Cohesion: 0.20
Nodes (18): CompletedProcess, _alter_postgres(), _docker_compose(), _ensure_postgres(), get_key(), harden_env(), _has_key(), is_weak_secret() (+10 more)

### Community 25 - "formatPrice"
Cohesion: 0.26
Nodes (10): MiniProductPage(), ProductPage(), AddToCartButton(), catalogParts(), formatDeviceCategory(), ProductGrid(), api, formatPrice() (+2 more)

### Community 26 - "telegram.ts"
Cohesion: 0.18
Nodes (12): MiniHeader(), MiniTabBar(), TABS, ensureTelegramWebApp(), loadScript(), TelegramWebApp, useTelegramPrefill(), Window (+4 more)

### Community 27 - "HTTPException"
Cohesion: 0.20
Nodes (29): adjust_user_bonus(), create_channel(), _enqueue_customer_telegrams(), get_admin_order(), _get_user(), list_channels(), list_orders(), list_users() (+21 more)

### Community 28 - "auth.tsx"
Cohesion: 0.18
Nodes (15): apiErrorMessage(), AccountNotification, AUTH_CREDS, AuthContext, AuthContextValue, AuthProvider(), captureReferral(), forgetStoredTokens() (+7 more)

### Community 29 - "should_prepend_section"
Cohesion: 0.18
Nodes (14): extract_apple_model_code(), is_junk_section(), normalize_section_header(), Apple order/model codes like MHFJ4 (exactly 5 alnum, mixed letters+digits)., Strip multipart markers and marketing tokens from supplier section headers., Remove Unisale multipart markers like '(часть 1/2)'., should_prepend_section(), strip_part_marker() (+6 more)

### Community 30 - "test_security.py"
Cohesion: 0.20
Nodes (17): admin_csrf_allowed(), client_ip(), is_weak_secret(), Request, Fetch Metadata: browsers send Sec-Fetch-Site; curl/tests omit it., Validate Mini App initData HMAC. Returns parsed fields or None., Socket peer, unless that peer is a local/private reverse proxy., verify_telegram_init_data() (+9 more)

### Community 31 - "api/main.py"
Cohesion: 0.22
Nodes (12): create_app(), lifespan(), _run_schema_migrations(), alembic_config(), Run Alembic to head. Used at API startup instead of create_all., run_migrations(), health(), get (+4 more)

### Community 32 - "settings/page.tsx"
Cohesion: 0.20
Nodes (12): AdminSettingsPage(), addRule(), applySettings(), onSave(), validate(), emptyRule(), formatSyncStats(), isMatch() (+4 more)

### Community 33 - "CheckoutForm.tsx"
Cohesion: 0.29
Nodes (11): CheckoutPage(), MiniCheckoutPage(), bonusBalance(), CheckoutForm(), onSubmit(), DeliveryType, isBonusError(), useCart() (+3 more)

### Community 34 - "ProductOut"
Cohesion: 0.21
Nodes (5): ProductDetailOut, ProductOut, Any, field_validator, _storefront_image()

### Community 35 - "Vec3"
Cohesion: 0.23
Nodes (7): centroid(), dihedral_cos(), main(), Объём |det(P2-P1, P3-P1, P4-P1)| / 6., Cos угла между нормалями к граням (P1,P2,P3) и (P1,P2,P4). n1 = (P2-P1) ×…, tetra_volume(), Vec3

### Community 36 - "[id]/page.tsx"
Cohesion: 0.38
Nodes (6): AdminProduct, AdminProductPage(), onDeletePhoto(), onUpload(), apiDetail(), Offer

### Community 37 - "assert_runtime_secrets"
Cohesion: 0.33
Nodes (6): assert_runtime_secrets(), _password_from_url(), Refuse to boot with placeholder credentials (WS-R1). Tests set…, runtime_secret_problems(), test_runtime_secret_problems_flag_defaults(), startup()

### Community 38 - "AppChrome.tsx"
Cohesion: 0.21
Nodes (7): body, display, metadata, viewport, AppChrome(), CartNavLink(), SiteHeader()

### Community 39 - "offer_identity module"
Cohesion: 0.20
Nodes (12): Apple Support 108898 Dual SIM, Apple Support 118569, KD4 iPhone SIM inference tables, offer_identity module, Storefront SIM SKU identity, Bests re:sale multi-brand parser, publish_kinds android gaming dyson yandex meta, audio and camera OfferKinds (+4 more)

### Community 40 - "require_admin"
Cohesion: 0.40
Nodes (5): admin_credentials_configured(), admin_credentials_valid(), require_admin(), test_admin_rejects_wrong_password(), HTTPBasicCredentials

### Community 41 - "users/page.tsx"
Cohesion: 0.31
Nodes (10): AdminUser, AdminUsersPage(), draftFor(), load(), patchActive(), setDraft(), submitBonus(), apiDetail() (+2 more)

### Community 42 - "api service"
Cohesion: 0.27
Nodes (11): api service, Docker Compose hot-reload overlay, postgres service, redis service, web service, worker service, xray VPN profile service, TELEGRAM_PROXY (+3 more)

### Community 43 - "Telethon plus ARQ worker"
Cohesion: 0.22
Nodes (10): CI Python tests, CI web unit tests, GitHub Actions CI workflow, API FastAPI dependency, Worker ARQ dependency, Worker Telethon dependency, WebApp checkout prefill, Telethon MTProto worker (+2 more)

### Community 44 - "Q: Why does classify_offer() connect Offer identity tests to Apple Watch parsing, Parser worker sync, Offer identity core, Offer title cleanup, Device field parsers, Junk section glue rules?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: Why does classify_offer() connect Offer identity tests to Apple Watch parsing, Parser worker sync, Offer identity core, Offer title cleanup, Device field parsers, Junk section glue rules?, Source Nodes

### Community 46 - "OrderConfirmation.tsx"
Cohesion: 0.28
Nodes (4): DELIVERY_RU, OrderConfirmation(), STATUS_RU, Order

### Community 47 - "parse_apple_watch"
Cohesion: 0.28
Nodes (9): expand_watch_ti(), normalize_milanese_band(), normalize_series_case_color(), parse_apple_watch(), peel_series_case_from_band(), Black Ti → Black Titanium (case & strap wording)., Apple Ultra Milanese is always '* Titanium Milanese Loop' (not bare…, Supplier shorthand: 'S11 46mm Silver Sport Band' → case Silver, band Sport… (+1 more)

### Community 48 - "16×16 SVG document/file icon"
Cohesion: 0.25
Nodes (8): Three horizontal bars suggesting written text, 16×16 SVG document/file icon, Folded top-right dog-ear corner, Generic file-type UI glyph, Monochrome fill #666, Rounded page body with evenodd path, Next.js public-folder static icon, Possible create-next-app default file.svg leftover

### Community 49 - "16×16 SVG wireframe globe icon"
Cohesion: 0.25
Nodes (8): 16×16 SVG wireframe globe icon, Horizontal latitude bands on the sphere, Vertical meridian curves on the sphere, Monochrome fill #666, Next.js public-folder static icon, Possible create-next-app default globe.svg leftover, Circular Earth silhouette (r=8, center 8,8), Generic web/world UI glyph

### Community 50 - "Next.js horizontal wordmark"
Cohesion: 0.29
Nodes (7): Black fill (#000), Next.js framework brand, Lowercase js after circular separator, 394×80 landscape viewBox, Geometric N with diagonal slash, create-next-app default public logo leftover, Next.js horizontal wordmark

### Community 51 - "Mini App site parity"
Cohesion: 0.29
Nodes (8): Next.js web app, Apple HIG storefront UI, Mini App site parity, One Next.js app for site Mini App admin, Cloudflare tunnel whiteshop.tech, Telegram Mini App, Moscow pickup and CDEK regions, Next.js web client

### Community 52 - "get_folder_channels"
Cohesion: 0.43
Nodes (7): _filter_title(), FolderChannel, get_folder_channels(), list_folder_names(), TelegramClient, Resolve Telegram chat folders (dialog filters)., DialogFilter

### Community 53 - "White Shop interlocking WS monogram logo"
Cohesion: 0.36
Nodes (8): White Shop interlocking WS monogram logo, White knockout outline separating overlapping W and S, Rounded curvy capital S in the foreground, Geometric sharp-cornered capital W in the background, Wordmark-free compact monogram brand mark, Solid black marks on a plain white background, PNG brand logo asset under assets/, White Shop brand identity

### Community 54 - "Admin MVP"
Cohesion: 0.25
Nodes (8): Admin MVP, Manual product shelf price, Admin price provenance log, Admin cabinet, Catalog auto-publish, HOT products, LLM product matching, Manual catalog products

### Community 56 - "White Shop WS interlocking monogram brand mark"
Cohesion: 0.38
Nodes (7): Angular letter W with thick sharp strokes and flat tops, High-contrast black letterforms on solid white, White negative-space outlines at W/S intersections, Next.js public-folder PNG served at /logo.png, Rounded letter S weaving through the W, Primary storefront visual identifier for White Shop, White Shop WS interlocking monogram brand mark

### Community 57 - "16×16 application window glyph"
Cohesion: 0.43
Nodes (6): Browser or app window UI metaphor, Three circular title-bar control dots, Monochrome fill #666, 16×16 application window glyph, create-next-app default public icon, Rounded rectangular window chrome

### Community 58 - "route.ts"
Cohesion: 0.52
Nodes (6): DELETE(), GET(), notFound(), PATCH(), POST(), PUT()

### Community 59 - "ProductSheet"
Cohesion: 0.38
Nodes (5): ProductSheet(), focusables(), isDesktop(), onHandlePointerDown(), onKey()

### Community 60 - "Apple parser quality"
Cohesion: 0.33
Nodes (7): Apple parser quality, MIN_OFFER_PRICE_RUB, Precision over recall, StoreSettings singleton, OEM adequacy gate, Median plus markup pricing, Round prices to 100 RUB

### Community 63 - "0004_admin_users.py"
Cohesion: 0.50
Nodes (3): _column_names(), Inspector, upgrade()

### Community 64 - "0005_markup_rules.py"
Cohesion: 0.50
Nodes (3): _column_names(), Inspector, upgrade()

### Community 65 - "0006_order_bonus_spent.py"
Cohesion: 0.50
Nodes (3): _column_names(), Inspector, upgrade()

### Community 66 - "0007_price_hygiene.py"
Cohesion: 0.50
Nodes (3): _column_names(), Inspector, upgrade()

### Community 67 - "eslint.config.mjs"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 68 - "next.config.ts"
Cohesion: 0.40
Nodes (3): apiInternal, nextConfig, securityHeaders

### Community 69 - "Vercel triangle logo"
Cohesion: 0.50
Nodes (4): Vercel brand, Vercel triangle logo, Upward-pointing triangle, White fill (#fff)

### Community 70 - "proxy.ts"
Cohesion: 0.60
Nodes (4): config, proxy(), safeEqual(), unauthorized()

### Community 71 - "test_harden_env_replaces_placeholder_secrets"
Cohesion: 0.67
Nodes (3): _load_secure_env(), Path, test_harden_env_replaces_placeholder_secrets()

### Community 72 - "Xray VLESS Reality"
Cohesion: 0.50
Nodes (4): VLESS Reality Xray client, VLESS Reality VPN, MTProto user-session parsing, Xray VLESS Reality

### Community 73 - "JWT plus Telegram Login auth"
Cohesion: 0.67
Nodes (3): API PyJWT dependency, 152-FZ personal data, JWT plus Telegram Login auth

### Community 75 - "PDF and Excel price-list parsing"
Cohesion: 0.67
Nodes (3): Worker openpyxl dependency, Worker pypdf dependency, PDF and Excel price-list parsing

### Community 81 - "Settings"
Cohesion: 0.22
Nodes (4): Any, BaseSettings, field_validator, Settings

## Ambiguous Edges - Review These
- `16×16 SVG document/file icon` → `Possible create-next-app default file.svg leftover`  [AMBIGUOUS]
  apps/web/public/file.svg · relation: conceptually_related_to
- `16×16 SVG wireframe globe icon` → `Possible create-next-app default globe.svg leftover`  [AMBIGUOUS]
  apps/web/public/globe.svg · relation: conceptually_related_to

## Knowledge Gaps
- **152 isolated node(s):** `__filename`, `__dirname`, `compat`, `eslintConfig`, `apiInternal` (+147 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `16×16 SVG document/file icon` and `Possible create-next-app default file.svg leftover`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `16×16 SVG wireframe globe icon` and `Possible create-next-app default globe.svg leftover`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `classify_offer()` connect `classify_offer` to `offer_identity.py`, `collapse_duplicate_tokens`, `sync.py`, `parse_apple_watch`, `extract_color`, `should_prepend_section`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `sync_folder()` connect `sync.py` to `classify_offer`, `Product`, `parse_price_text`, `order_notify.py`, `product_images.py`, `test_pricing.py`, `customer_notify.py`, `get_worker_settings`, `get_folder_channels`, `favorite_alerts.py`, `HTTPException`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `Product` connect `Product` to `admin.py`, `HTTPException`, `User`, `sync.py`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `User` (e.g. with `get_optional_user()` and `_load_user()`) actually correct?**
  _`User` has 41 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `Product` (e.g. with `add_favorite()` and `list_favorites()`) actually correct?**
  _`Product` has 23 INFERRED edges - model-reasoned connections that need verification._