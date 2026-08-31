# Graph Report - tech-sales  (2026-08-29)

## Corpus Check
- 156 files · ~61,683 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1172 nodes · 2765 edges · 71 communities (65 shown, 6 thin omitted)
- Extraction: 91% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 235 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Customer accounts and JWT
- Orders and Telegram notify
- Admin catalog API
- Offer identity tests
- Parser worker sync
- Bonus ledger models
- Admin Next.js pages
- Offer identity core
- Catalog browser types
- Price parser and markup
- Cabinet login UI
- Next.js package.json
- TypeScript compiler config
- Offer title cleanup
- Cart and checkout
- Device field parsers
- Secure env bootstrap
- API boot and migrations
- Auth rate limiting
- Frontend auth session
- Admin secret checks
- Product and cart pages
- Telegram Mini App SDK
- Junk section glue rules
- Tetrahedron math script
- App chrome and layout
- Multi-brand parser plans
- Compose stack services
- CI and worker deps
- Manual catalog slugs
- DB session dependencies
- Mini App and delivery
- Order confirmation pages
- Apple Watch parsing
- API settings object
- Default file.svg icon
- Default globe.svg icon
- Next.js leftover wordmark
- White Shop brand mark
- Admin MVP requirements
- Storefront logo PNG
- Default window.svg icon
- Product sheet gestures
- Median markup pricing
- Alembic env runner
- Admin users migration
- Demo catalog seed
- ESLint config
- Next.js config headers
- Vercel leftover logo
- Admin HTTP Basic proxy
- Secure env tests
- VLESS Reality VPN
- JWT and 152-FZ
- Admin nav layout
- PDF Excel price lists
- White Shop product
- PostCSS config
- Compound Engineering config
- Cursor skills-first rules
- Flutter mobile later
- Three-level referral cashback

## God Nodes (most connected - your core abstractions)
1. `classify_offer()` - 120 edges
2. `User` - 53 edges
3. `get_settings()` - 33 edges
4. `Product` - 33 edges
5. `Order` - 28 edges
6. `formatPrice()` - 28 edges
7. `Base` - 26 edges
8. `create_order()` - 24 edges
9. `useAuth()` - 24 edges
10. `sync_folder()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `offer_identity module` --conceptually_related_to--> `Telethon MTProto worker`  [INFERRED]
  docs/plans/2026-08-20-001-feat-parser-quality-plan.md → README.md
- `Worker ARQ dependency` --implements--> `Telethon plus ARQ worker`  [INFERRED]
  apps/worker/requirements.txt → REQUIREMENTS.md
- `Worker Telethon dependency` --implements--> `Telethon plus ARQ worker`  [INFERRED]
  apps/worker/requirements.txt → REQUIREMENTS.md
- `Docker Compose infrastructure` --conceptually_related_to--> `api service`  [INFERRED]
  REQUIREMENTS.md → docker-compose.yml
- `Cloudflare tunnel whiteshop.tech` --conceptually_related_to--> `web service`  [INFERRED]
  infra/tunnel/config.example.yml → docker-compose.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **White Shop Docker Compose runtime** — docker_compose_postgres, docker_compose_redis, docker_compose_api, docker_compose_worker, docker_compose_web [EXTRACTED 1.00]
- **offer_identity catalog quality pipeline** — docs_plans_2026_08_20_001_feat_parser_quality_plan_offer_identity, docs_plans_2026_08_20_004_feat_bests_multibrand_parser_plan_bests_parser, docs_plans_2026_08_20_005_feat_unisale_opt_parser_plan_unisale_parser, docs_plans_2026_08_21_001_fix_catalog_title_quality_plan_title_quality [INFERRED 0.85]
- **Telegram access via Xray SOCKS proxy** — docker_compose_worker, docker_compose_xray, infra_vpn_readme_telegram_proxy, infra_vpn_readme_vless_reality [EXTRACTED 1.00]
- **Wireframe globe from sphere plus lat/long grid** — apps_web_public_globe_icon, apps_web_public_globe_sphere_outline, apps_web_public_globe_latitude_parallels, apps_web_public_globe_longitude_meridians [EXTRACTED 1.00]
- **Window glyph visual composition** — apps_web_public_window_rounded_frame, apps_web_public_window_control_dots, apps_web_public_window_gray_fill [EXTRACTED 1.00]

## Communities (71 total, 6 thin omitted)

### Community 0 - "Customer accounts and JWT"
Cohesion: 0.06
Nodes (97): require_user(), _unauthorized(), AuthRefreshToken, User, add_favorite(), delete_me(), export_me(), list_favorites() (+89 more)

### Community 1 - "Orders and Telegram notify"
Cohesion: 0.07
Nodes (74): AdminOrderStatus, CustomerOrderStatus, DeliveryType, Order, OrderItem, str, create_order(), get_order_by_number() (+66 more)

### Community 2 - "Admin catalog API"
Cohesion: 0.07
Nodes (74): Product, adjust_user_bonus(), admin_list_products(), create_channel(), create_manual_product(), get_admin_order(), get_settings(), _get_user() (+66 more)

### Community 3 - "Offer identity tests"
Cohesion: 0.06
Nodes (74): classify_offer(), extract_region(), OfferKind, test_airpods_max_generations(), test_android_huawei_honor_xiaomi_pixel(), test_android_ram_not_iphone_16(), test_android_realme_oneplus_nothing_tecno_colors(), test_asis_category_star_and_deep_blue() (+66 more)

### Community 4 - "Parser worker sync"
Cohesion: 0.06
Nodes (53): Category, ChannelStatus, ProductOffer, str, Raw supplier price offer with provenance for admin audit., SupplierChannel, _esc(), format_ops_alert() (+45 more)

### Community 5 - "Bonus ledger models"
Cohesion: 0.09
Nodes (36): _column_names(), _has_unique_on(), Inspector, upgrade(), _column_names(), Inspector, upgrade(), _column_names() (+28 more)

### Community 6 - "Admin Next.js pages"
Cohesion: 0.09
Nodes (33): AdminProductOffersPage(), Offer, AdminCatalogPage(), createManual(), load(), patch(), AdminProduct, AdminChannelsPage() (+25 more)

### Community 7 - "Offer identity core"
Cohesion: 0.06
Nodes (40): asis_tier(), build_config(), build_display_title(), category_for_phone(), extract_sim_text(), format_device_name(), _generation(), identity_key() (+32 more)

### Community 8 - "Catalog browser types"
Cohesion: 0.09
Nodes (17): CatalogBrowser(), onSearchKeyDown(), pickSuggest(), Props, SORT_OPTIONS, catalogParts(), formatDeviceCategory(), ProductGrid() (+9 more)

### Community 9 - "Price parser and markup"
Cohesion: 0.11
Nodes (33): apply_markup(), compute_median_cost(), Decimal, Storefront pricing: median of supplier offers + markup + rounding., Return (cost_median, storefront_price)., round_price(), storefront_price(), test_markup_and_round() (+25 more)

### Community 10 - "Cabinet login UI"
Cohesion: 0.11
Nodes (17): LoginPage(), MiniLoginPage(), MiniRegisterPage(), RegisterPage(), AccountCabinet(), bonusLabel(), PrivacyBlock(), ProfileForm() (+9 more)

### Community 11 - "Next.js package.json"
Cohesion: 0.06
Nodes (34): dependencies, next, react, react-dom, devDependencies, eslint, eslint-config-next, @eslint/eslintrc (+26 more)

### Community 12 - "TypeScript compiler config"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 13 - "Offer title cleanup"
Cohesion: 0.11
Nodes (22): _apple_other_device_name(), clean_offer_title(), collapse_duplicate_tokens(), _extract_connectivity(), is_junk_offer(), _nfkc(), parse_audio(), parse_camera() (+14 more)

### Community 14 - "Cart and checkout"
Cohesion: 0.17
Nodes (13): CheckoutPage(), MiniCheckoutPage(), CheckoutForm(), DeliveryType, MiniTabBar(), TABS, CartContext, CartContextValue (+5 more)

### Community 15 - "Device field parsers"
Cohesion: 0.10
Nodes (21): extract_color(), extract_ram(), extract_storage(), _format_insta360_body(), parse_airpods_max(), parse_android(), parse_galaxy_buds(), parse_galaxy_watch() (+13 more)

### Community 16 - "Secure env bootstrap"
Cohesion: 0.20
Nodes (18): CompletedProcess, _alter_postgres(), _docker_compose(), _ensure_postgres(), get_key(), harden_env(), _has_key(), is_weak_secret() (+10 more)

### Community 17 - "API boot and migrations"
Cohesion: 0.19
Nodes (14): create_app(), lifespan(), _run_schema_migrations(), alembic_config(), Run Alembic to head. Used at API startup instead of create_all., run_migrations(), health(), get (+6 more)

### Community 18 - "Auth rate limiting"
Cohesion: 0.16
Nodes (14): admin_credentials_configured(), _auth_date_fresh(), check_rate_limit(), client_ip(), Request, rate_limit_headers(), RateDecision, Auth, rate limits, output filtering — defensive controls used by the API. (+6 more)

### Community 19 - "Frontend auth session"
Cohesion: 0.18
Nodes (15): apiErrorMessage(), AccountNotification, AuthContext, AuthContextValue, AuthProvider(), captureReferral(), clearStored(), Me (+7 more)

### Community 20 - "Admin secret checks"
Cohesion: 0.19
Nodes (14): admin_credentials_valid(), is_weak_secret(), _password_from_url(), rate_limit_rule(), Validate Mini App initData HMAC. Returns parsed fields or None., Return (bucket_suffix, limit, window_sec) or None to skip., runtime_secret_problems(), verify_telegram_init_data() (+6 more)

### Community 21 - "Product and cart pages"
Cohesion: 0.25
Nodes (6): MiniProductPage(), ProductPage(), AddToCartButton(), CartView(), formatPrice(), Product

### Community 22 - "Telegram Mini App SDK"
Cohesion: 0.26
Nodes (10): MiniHeader(), ensureTelegramWebApp(), loadScript(), TelegramWebApp, useTelegramPrefill(), Window, CheckoutPrefill, isTelegramUser() (+2 more)

### Community 23 - "Junk section glue rules"
Cohesion: 0.18
Nodes (14): extract_apple_model_code(), is_junk_section(), normalize_section_header(), Apple order/model codes like MHFJ4 (exactly 5 alnum, mixed letters+digits)., Strip multipart markers and marketing tokens from supplier section headers., Remove Unisale multipart markers like '(часть 1/2)'., should_prepend_section(), strip_part_marker() (+6 more)

### Community 24 - "Tetrahedron math script"
Cohesion: 0.23
Nodes (7): centroid(), dihedral_cos(), main(), Объём |det(P2-P1, P3-P1, P4-P1)| / 6., Cos угла между нормалями к граням (P1,P2,P3) и (P1,P2,P4). n1 = (P2-P1) ×…, tetra_volume(), Vec3

### Community 25 - "App chrome and layout"
Cohesion: 0.21
Nodes (7): body, display, metadata, viewport, AppChrome(), CartNavLink(), SiteHeader()

### Community 26 - "Multi-brand parser plans"
Cohesion: 0.20
Nodes (12): Apple Support 108898 Dual SIM, Apple Support 118569, KD4 iPhone SIM inference tables, offer_identity module, Storefront SIM SKU identity, Bests re:sale multi-brand parser, publish_kinds android gaming dyson yandex meta, audio and camera OfferKinds (+4 more)

### Community 27 - "Compose stack services"
Cohesion: 0.27
Nodes (11): api service, Docker Compose hot-reload overlay, postgres service, redis service, web service, worker service, xray VPN profile service, TELEGRAM_PROXY (+3 more)

### Community 28 - "CI and worker deps"
Cohesion: 0.22
Nodes (10): CI Python tests, CI web unit tests, GitHub Actions CI workflow, API FastAPI dependency, Worker ARQ dependency, Worker Telethon dependency, WebApp checkout prefill, Telethon MTProto worker (+2 more)

### Community 29 - "Manual catalog slugs"
Cohesion: 0.38
Nodes (7): get_settings(), Admin helpers: store settings singleton and slug for manual products., slugify_manual(), test_bot_token_strips_inline_env_comments(), test_env_markup_defaults(), test_slugify_manual_differs_by_title(), test_slugify_manual_stable()

### Community 30 - "DB session dependencies"
Cohesion: 0.40
Nodes (8): get_db(), AsyncSession, _bearer_token(), get_optional_user(), _load_user(), peek_user(), AsyncSession, Request

### Community 31 - "Mini App and delivery"
Cohesion: 0.28
Nodes (9): Next.js web app, Apple HIG storefront UI, Mini App site parity, One Next.js app for site Mini App admin, Cloudflare tunnel whiteshop.tech, Telegram Mini App, Moscow pickup and CDEK regions, Next.js web client (+1 more)

### Community 32 - "Order confirmation pages"
Cohesion: 0.28
Nodes (4): DELIVERY_RU, OrderConfirmation(), STATUS_RU, Order

### Community 33 - "Apple Watch parsing"
Cohesion: 0.28
Nodes (9): expand_watch_ti(), normalize_milanese_band(), normalize_series_case_color(), parse_apple_watch(), peel_series_case_from_band(), Black Ti → Black Titanium (case & strap wording)., Apple Ultra Milanese is always '* Titanium Milanese Loop' (not bare…, Supplier shorthand: 'S11 46mm Silver Sport Band' → case Silver, band Sport… (+1 more)

### Community 34 - "API settings object"
Cohesion: 0.25
Nodes (4): Any, BaseSettings, field_validator, Settings

### Community 35 - "Default file.svg icon"
Cohesion: 0.25
Nodes (8): Three horizontal bars suggesting written text, 16×16 SVG document/file icon, Folded top-right dog-ear corner, Generic file-type UI glyph, Monochrome fill #666, Rounded page body with evenodd path, Next.js public-folder static icon, Possible create-next-app default file.svg leftover

### Community 36 - "Default globe.svg icon"
Cohesion: 0.25
Nodes (8): 16×16 SVG wireframe globe icon, Horizontal latitude bands on the sphere, Vertical meridian curves on the sphere, Monochrome fill #666, Next.js public-folder static icon, Possible create-next-app default globe.svg leftover, Circular Earth silhouette (r=8, center 8,8), Generic web/world UI glyph

### Community 37 - "Next.js leftover wordmark"
Cohesion: 0.29
Nodes (7): Black fill (#000), Next.js framework brand, Lowercase js after circular separator, 394×80 landscape viewBox, Geometric N with diagonal slash, create-next-app default public logo leftover, Next.js horizontal wordmark

### Community 38 - "White Shop brand mark"
Cohesion: 0.36
Nodes (8): White Shop interlocking WS monogram logo, White knockout outline separating overlapping W and S, Rounded curvy capital S in the foreground, Geometric sharp-cornered capital W in the background, Wordmark-free compact monogram brand mark, Solid black marks on a plain white background, PNG brand logo asset under assets/, White Shop brand identity

### Community 39 - "Admin MVP requirements"
Cohesion: 0.25
Nodes (8): Admin MVP, Manual product shelf price, Admin price provenance log, Admin cabinet, Catalog auto-publish, HOT products, LLM product matching, Manual catalog products

### Community 40 - "Storefront logo PNG"
Cohesion: 0.38
Nodes (7): Angular letter W with thick sharp strokes and flat tops, High-contrast black letterforms on solid white, White negative-space outlines at W/S intersections, Next.js public-folder PNG served at /logo.png, Rounded letter S weaving through the W, Primary storefront visual identifier for White Shop, White Shop WS interlocking monogram brand mark

### Community 41 - "Default window.svg icon"
Cohesion: 0.43
Nodes (6): Browser or app window UI metaphor, Three circular title-bar control dots, Monochrome fill #666, 16×16 application window glyph, create-next-app default public icon, Rounded rectangular window chrome

### Community 42 - "Product sheet gestures"
Cohesion: 0.38
Nodes (5): ProductSheet(), focusables(), isDesktop(), onHandlePointerDown(), onKey()

### Community 43 - "Median markup pricing"
Cohesion: 0.33
Nodes (7): Apple parser quality, MIN_OFFER_PRICE_RUB, Precision over recall, StoreSettings singleton, OEM adequacy gate, Median plus markup pricing, Round prices to 100 RUB

### Community 44 - "Alembic env runner"
Cohesion: 0.60
Nodes (5): _database_url(), do_run_migrations(), run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 45 - "Admin users migration"
Cohesion: 0.50
Nodes (3): _column_names(), Inspector, upgrade()

### Community 46 - "Demo catalog seed"
Cohesion: 0.50
Nodes (4): str, UserRole, Seed demo categories and HOT product for local development., seed()

### Community 47 - "ESLint config"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 48 - "Next.js config headers"
Cohesion: 0.40
Nodes (3): apiInternal, nextConfig, securityHeaders

### Community 49 - "Vercel leftover logo"
Cohesion: 0.50
Nodes (4): Vercel brand, Vercel triangle logo, Upward-pointing triangle, White fill (#fff)

### Community 50 - "Admin HTTP Basic proxy"
Cohesion: 0.60
Nodes (4): config, proxy(), safeEqual(), unauthorized()

### Community 51 - "Secure env tests"
Cohesion: 0.67
Nodes (3): _load_secure_env(), Path, test_harden_env_replaces_placeholder_secrets()

### Community 52 - "VLESS Reality VPN"
Cohesion: 0.50
Nodes (4): VLESS Reality Xray client, VLESS Reality VPN, MTProto user-session parsing, Xray VLESS Reality

### Community 53 - "JWT and 152-FZ"
Cohesion: 0.67
Nodes (3): API PyJWT dependency, 152-FZ personal data, JWT plus Telegram Login auth

### Community 55 - "PDF Excel price lists"
Cohesion: 0.67
Nodes (3): Worker openpyxl dependency, Worker pypdf dependency, PDF and Excel price-list parsing

### Community 56 - "White Shop product"
Cohesion: 0.67
Nodes (3): White Shop, B2C reseller with storefront, White Shop

## Ambiguous Edges - Review These
- `16×16 SVG document/file icon` → `Possible create-next-app default file.svg leftover`  [AMBIGUOUS]
  apps/web/public/file.svg · relation: conceptually_related_to
- `16×16 SVG wireframe globe icon` → `Possible create-next-app default globe.svg leftover`  [AMBIGUOUS]
  apps/web/public/globe.svg · relation: conceptually_related_to

## Knowledge Gaps
- **142 isolated node(s):** `__filename`, `__dirname`, `compat`, `eslintConfig`, `apiInternal` (+137 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `16×16 SVG document/file icon` and `Possible create-next-app default file.svg leftover`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `16×16 SVG wireframe globe icon` and `Possible create-next-app default globe.svg leftover`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `classify_offer()` connect `Offer identity tests` to `Apple Watch parsing`, `Parser worker sync`, `Offer identity core`, `Offer title cleanup`, `Device field parsers`, `Junk section glue rules`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `Product` connect `Admin catalog API` to `Customer accounts and JWT`, `Orders and Telegram notify`, `Parser worker sync`, `Bonus ledger models`, `Demo catalog seed`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `sync_folder()` connect `Parser worker sync` to `Price parser and markup`, `Admin catalog API`, `Offer identity tests`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 37 inferred relationships involving `User` (e.g. with `get_optional_user()` and `_load_user()`) actually correct?**
  _`User` has 37 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Product` (e.g. with `add_favorite()` and `list_favorites()`) actually correct?**
  _`Product` has 21 INFERRED edges - model-reasoned connections that need verification._