from __future__ import annotations

import pytest

from apps.worker.offer_identity import (
    OfferKind,
    classify_offer,
    clean_offer_title,
    identity_key,
    is_junk_section,
    should_prepend_section,
)


@pytest.mark.parametrize(
    ("title", "expected_sim"),
    [
        ("iPhone 17 Pro Max 256GB Blue 🇯🇵 (E-Sim)", "eSIM"),
        ("iPhone 17 Pro Max 256GB Blue 🇺🇸 (eSIM)", "eSIM"),
        ("🇺🇸 16 Pro 256GB Black", "eSIM"),
        ("🇪🇺 16 Pro 256GB Black", "Sim+eSIM"),
        ("🇯🇵 17 Pro 256GB Blue", "eSIM"),
        ("🇩🇪 17 Pro 256GB Blue", "Sim+eSIM"),
        ("🇨🇳 17 Pro Max 256GB Blue", "2Sim"),
        ("CN 16 Pro 256GB Black", "2Sim"),
        ("iPhone Air 256GB Cloud White 🇨🇳", "eSIM"),
        ("iPhone Air 256GB White", "eSIM"),
        ("🇺🇸 eSim 17 Air 1TB White", "eSIM"),
    ],
)
def test_sim_inference_matrix(title: str, expected_sim: str) -> None:
    ident = classify_offer(title)
    assert ident.publish is True
    assert ident.sim == expected_sim
    assert "🇯🇵" not in ident.display_title
    assert "🇺🇸" not in ident.display_title
    assert "🇨🇳" not in ident.display_title


def test_iphone_17_pro_black_rejected() -> None:
    ident = classify_offer("🇨🇳 17 Pro Max 256GB Black")
    assert ident.publish is False
    assert ident.reject_reason == "iphone_missing_color"


def test_iphone_air_shorthand_and_colors() -> None:
    cases = [
        ("🇺🇸 eSim 17 Air 1TB White", "1TB · Cloud White · eSIM"),
        ("🇯🇵 eSim 17 Air 1TB Gold", "1TB · Light Gold · eSIM"),
        ("🇯🇵 eSim 17 Air 1TB Blue", "1TB · Sky Blue · eSIM"),
        ("🇯🇵 eSim 17 Air 1TB Black", "1TB · Space Black · eSIM"),
        ("iPhone Air 256GB Cloud White", "256GB · Cloud White · eSIM"),
    ]
    for title, config in cases:
        ident = classify_offer(title)
        assert ident.publish is True, title
        assert ident.device_name == "iPhone Air"
        assert ident.config == config, (title, ident.config)


def test_iphone_17e_name_and_soft_pink() -> None:
    ident = classify_offer("🇺🇸 eSim 17e 512GB Pink")
    assert ident.publish is True
    assert ident.device_name == "iPhone 17e"
    assert ident.config == "512GB · Soft Pink · eSIM"
    assert classify_offer("🇺🇸 eSim 16e 128GB Black").device_name == "iPhone 16e"


def test_iphone_17_base_mist_blue() -> None:
    ident = classify_offer("🇺🇸 eSim 17 512GB Blue")
    assert ident.publish is True
    assert ident.device_name == "iPhone 17"
    assert ident.config == "512GB · Mist Blue · eSIM"


def test_jp_us_esim_collapse() -> None:
    a = classify_offer("iPhone 17 Pro Max 256GB Blue 🇯🇵 (E-Sim)")
    b = classify_offer("iPhone 17 Pro Max 256GB Blue 🇺🇸 (eSIM)")
    assert a.identity_key == b.identity_key
    assert a.identity_key == identity_key(a.model, a.storage, a.color, a.sim)


def test_iphone_missing_sim_and_region_rejected() -> None:
    ident = classify_offer("17e 256GB Black")
    assert ident.publish is False
    assert ident.reject_reason == "iphone_missing_sim"


def test_explicit_sim_overrides_region() -> None:
    ident = classify_offer("🇩🇪 17 Pro 256GB Blue (E-Sim)")
    assert ident.sim == "eSIM"


def test_section_glue_skips_when_model_present() -> None:
    assert should_prepend_section("iPhone 17 Pro Max", "17e 256GB Black") is False


def test_section_glue_allows_continuation() -> None:
    assert should_prepend_section("iPhone 17 Pro Max", "256GB Blue (E-Sim)") is True


def test_junk_sections_never_glue() -> None:
    assert is_junk_section("Выдача в день заказа или на следующий день до 14:00‼️")
    assert is_junk_section("Прайс Galaxy S")
    assert is_junk_section("Asis+ Non Active без коробки")
    assert should_prepend_section("Прайс Galaxy S", "S25 Ultra 12/256 Black") is False
    assert (
        should_prepend_section(
            "Выдача в день заказа или на следующий день до 14:00‼️",
            '24" LG 24LB70006LA',
        )
        is False
    )


def test_top_resale_model_section_still_glues_continuation() -> None:
    assert should_prepend_section("IPhone 16:", "256GB Black") is True
    assert should_prepend_section("IPhone 16:", "🇺🇸 16 128GB Black") is False


def test_marketing_noise_rejected() -> None:
    ident = classify_offer("АКЦИЯ только сегодня iPhone")
    assert ident.publish is False


@pytest.mark.parametrize(
    "title",
    [
        "Стайлер Dyson 🆕 Цена",
        "Гарантия Б/У 30 дней на техническую составляющую устройства* Цена",
        "Аккумуляторы Dyson V11 и V15 Цена",
        "Мини - лот ⚠️ Цена",
        "Лот 4️⃣ Цена",
        "Муляжи 🆕 iPhone 18 Pro Max Black/White/Cherry",
        "Муляж iPhone 15 128GB Black 🇺🇸",
        "AirPods Pro лот",
        "Vision Pro муляж",
    ],
)
def test_junk_titles_rejected(title: str) -> None:
    ident = classify_offer(title)
    assert ident.publish is False
    assert ident.reject_reason in {"junk_or_noise", "noise_or_unrecognized"}


def test_cena_suffix_stripped_from_apple_other() -> None:
    ident = classify_offer("Mac Mini M2 512GB Цена")
    assert ident.publish is True
    assert "цена" not in ident.display_title.lower()
    assert "Цена" not in ident.display_title


def test_clean_strips_vydacha_and_duplicate_brand() -> None:
    cleaned = clean_offer_title(
        "Выдача в день заказа или на следующий день до 14:00!! Saeco Saeco Magic M1"
    )
    assert "выдача" not in cleaned.lower()
    assert "заказа" not in cleaned.lower()
    assert cleaned == "Saeco Magic M1"


def test_clean_strips_prais_prefix() -> None:
    cleaned = clean_offer_title("Прайс Galaxy S S25 12/256Gb (SM-S931B) Icyblue")
    assert not cleaned.lower().startswith("прайс")
    assert "Galaxy S25" in cleaned
    assert "Прайс" not in cleaned


def test_asis_section_stripped_still_publishes_iphone() -> None:
    ident = classify_offer(
        "Asis+ Non Active без коробки iPhone 16 Pro 256Gb Natural 🇭🇰 (Asis+)"
    )
    assert ident.publish is True
    assert "asis" not in ident.display_title.lower()
    assert "коробк" not in ident.display_title.lower()
    assert "iPhone 16 Pro" in ident.display_title


def test_structured_iphone_catalog_card() -> None:
    ident = classify_offer("🇺🇸 16 Pro 256GB Black")
    assert ident.publish is True
    assert ident.brand == "Apple"
    assert ident.device_category == "Смартфоны"
    assert ident.device_name == "iPhone 16 Pro"
    assert ident.config == "256GB · Black Titanium · eSIM"
    assert ident.display_title == "iPhone 16 Pro · 256GB · Black Titanium · eSIM"


def test_structured_samsung_top_resale_line() -> None:
    ident = classify_offer("S25 Ultra 12/256 Black S938B 🇪🇺")
    assert ident.publish is True
    assert ident.brand == "Samsung"
    assert ident.device_category == "Смартфоны"
    assert ident.device_name == "Galaxy S25 Ultra"
    assert "12/256GB" in ident.config or "256GB" in ident.config
    assert "Black" in ident.config
    assert "прайс" not in ident.display_title.lower()


def test_galaxy_s_plus_displays_as_plus() -> None:
    for title in (
        "S26+ 12/256 Violet S947B 🇦🇪",
        "S26 plus 12/512 White S947B 🇰🇿",
        "S23+ 8/256 Black",
    ):
        ident = classify_offer(title)
        assert ident.publish is True, title
        assert "+" not in ident.device_name, (title, ident.device_name)
        assert "Plus" in ident.device_name, (title, ident.device_name)
        assert ident.device_name.startswith("Galaxy S"), ident.device_name


def test_galaxy_a_series_top_resale() -> None:
    cases = [
        ("A07 6/128 Black  🇷🇺", "Galaxy A07", "6/128GB · Black"),
        ("A16 8/256 Black  🇪🇺", "Galaxy A16", "8/256GB · Black"),
        ("A17 6/128 Blue  🇷🇺", "Galaxy A17", "6/128GB · Blue"),
        ("A17 6/128 Gray  🇷🇺", "Galaxy A17", "6/128GB · Gray"),
        ("A26 6/128 Pink  🇷🇺", "Galaxy A26", "6/128GB · Peach Pink"),
        ("A56 8/256 Graphite  🇦🇪", "Galaxy A56", "8/256GB · Awesome Graphite"),
        ("A56 8/256 Gray  🇦🇪", "Galaxy A56", "8/256GB · Awesome Lightgray"),
        ("A56 12/256 Olive  🇲🇾", "Galaxy A56", "12/256GB · Awesome Olive"),
        ("A57 8/256 Pink", "Galaxy A57", "8/256GB · Awesome Pink"),
        ("A57 8/256GB Icy Blue", "Galaxy A57", "8/256GB · Awesome Icyblue"),
        ("A57 8/256GB Navy", "Galaxy A57", "8/256GB · Awesome Navy"),
        ("A57 8/256GB Lilac", "Galaxy A57", "8/256GB · Awesome Lilac"),
        ("A37 8/128GB Charcoal", "Galaxy A37", "8/128GB · Awesome Charcoal"),
    ]
    for title, name, config in cases:
        ident = classify_offer(title)
        assert ident.publish is True, title
        assert ident.brand == "Samsung"
        assert ident.device_name == name, (title, ident.device_name)
        assert ident.config == config, (title, ident.config)
    # iPad A16 must not become Galaxy A16
    assert classify_offer("iPad A16 128GB Wi-Fi Blue").kind != OfferKind.samsung or not classify_offer(
        "iPad A16 128GB Wi-Fi Blue"
    ).device_name.startswith("Galaxy A")
    ipad = classify_offer("iPad A16 128GB Blue")
    assert "Galaxy A16" not in ipad.device_name
    assert classify_offer("A17 Black").publish is False  # no RAM/storage


def test_structured_airpods() -> None:
    ident = classify_offer("AirPods 4 ANC")
    assert ident.publish is True
    assert ident.brand == "Apple"
    assert ident.device_category == "Наушники"
    assert "AirPods" in ident.device_name


def test_airpods_max_generations() -> None:
    cases = [
        # Bests: "Max 2 USB-C" = 2024 refresh, not gen2
        ("AirPods Max 2 USB-C Midnight", "AirPods Max USB-C", "Midnight"),
        ("AirPods Max 2 USB-C Purple", "AirPods Max USB-C", "Purple"),
        ("AirPods Max USB-C (2024) Orange", "AirPods Max USB-C", "Orange"),
        # Bests: explicit 2026 = real Max 2
        ("AirPods Max 2 2026 Midnight", "AirPods Max 2", "Midnight"),
        ("AirPods Max 2 2026 Blue", "AirPods Max 2", "Blue"),
        ("AirPods Max gen2 Orange", "AirPods Max 2", "Orange"),
        # Explicit connectors
        ("AirPods Max Type-C Midnight", "AirPods Max USB-C", "Midnight"),
        ("AirPods Max тайпси Black", "AirPods Max USB-C", "Midnight"),
        ("AirPods Max Lightning Silver", "AirPods Max Lightning", "Silver"),
        ("AirPods Max Space Gray 2020", "AirPods Max Lightning", "Space Gray"),
        ("AirPods Max Pink", "AirPods Max Lightning", "Pink"),
    ]
    for title, name, color in cases:
        ident = classify_offer(title)
        assert ident.publish is True, title
        assert ident.device_name == name, (title, ident.device_name)
        assert ident.color == color, (title, ident.color)
        assert ident.config == color
    # Top re:sale — no year/connector → reject
    for title in ("AirPods Max Black", "AirPods Max Blue", "AirPods Max Starlight"):
        ident = classify_offer(title)
        assert ident.publish is False, title
        assert ident.reject_reason == "airpods_max_missing_generation"



def test_iphone_air_requires_iphone_word() -> None:
    assert classify_offer("Google Fitbit Air Obsidian").publish is False
    assert classify_offer("Dreame Ultra Slim Magnetic Power Bank Air Power 17").publish is False
    # Insta360 Mic Air is a real mic — not an iPhone
    mic = classify_offer("Insta360 Mic Air")
    assert mic.publish is True
    assert mic.brand == "Insta360"
    assert mic.kind == OfferKind.insta360
    assert "iPhone" not in mic.device_name


def test_insta360_x5_and_variants() -> None:
    cases = [
        ("insta 360x5", "Insta360 X5", "Экшн-камеры"),
        ("В наличии insta 360x5", "Insta360 X5", "Экшн-камеры"),
        ("Insta360 X4 Black", "Insta360 X4", "Экшн-камеры"),
        ("Insta360 Ace Pro 2", "Insta360 Ace Pro 2", "Экшн-камеры"),
        ("insta360 go 3s", "Insta360 GO 3S", "Экшн-камеры"),
        ("Insta360 Link 2", "Insta360 Link 2", "Аксессуары"),
    ]
    for title, name, category in cases:
        ident = classify_offer(title)
        assert ident.publish is True, title
        assert ident.brand == "Insta360"
        assert ident.device_name == name, (title, ident.device_name)
        assert ident.device_category == category, title
        assert ident.kind == OfferKind.insta360


def test_junk_section_v_nalichii() -> None:
    assert is_junk_section("В наличии") is True
    assert should_prepend_section("В наличии", "insta 360x5") is False


def test_clock_time_not_iphone_14() -> None:
    title = "Выдача в день заказа или на следующий день до 14:00!! Xiaomi Desktop Heater"
    ident = classify_offer(title)
    assert ident.publish is False
    assert ident.kind != OfferKind.iphone or not ident.publish


def test_iphone_requires_storage() -> None:
    ident = classify_offer("iPhone 14 Black 🇺🇸")
    assert ident.publish is False
    assert ident.reject_reason == "iphone_missing_storage"


def test_android_ram_not_iphone_16() -> None:
    cases = [
        "Прайс Oneplus/Honor/Huawei OnePlus 13s 16/512Gb Black Velvet 🇮🇳",
        "Прайс Galaxy S S26 Ultra 16/1Tb (SM-S948B) Sky Blue 🇪🇺",
        "Samsung Z Fold 8 16/1TB Cream 🇦🇪",
        "Прайс Poco Poco F8 Ultra 16/512Gb Black 🇪🇺",
    ]
    for title in cases:
        ident = classify_offer(title)
        assert ident.kind != OfferKind.iphone or not ident.publish, title
        assert "iPhone 16" not in ident.display_title, title


def test_iphone_16_rejects_1tb() -> None:
    ident = classify_offer("iPhone 16 1TB Blue 🇺🇸")
    assert ident.publish is False
    assert ident.reject_reason == "iphone_invalid_storage"


def test_iphone_16_teal_color() -> None:
    ident = classify_offer("iPhone 16 128GB Teal 1Sim+eSim 🇮🇳")
    assert ident.publish is True
    assert ident.color == "Teal"
    assert "Teal" in ident.config
    assert ident.sim == "Sim+eSIM"


def test_asis_category_star_and_deep_blue() -> None:
    ident = classify_offer(
        "Asis Active iPhone без коробки iPhone 17 Pro 512Gb Deep Blue 🇰🇷 (Asis)"
    )
    assert ident.publish is True
    assert ident.device_category == "Asis*"
    assert ident.color == "Deep Blue"
    assert "Deep Blue" in ident.config
    assert ident.config.startswith("512GB")


def test_mist_blue_full_name() -> None:
    ident = classify_offer("iPhone 17 512Gb Mist Blue 🇭🇰 (Asis+)")
    assert ident.publish is True
    assert ident.color == "Mist Blue"
    assert ident.device_category == "Asis+*"
    assert ident.sim == "Sim+eSIM"


def test_hk_is_sim_plus_esim() -> None:
    ident = classify_offer("iPhone 16 Pro 256Gb Desert 🇭🇰")
    assert ident.publish is True
    assert ident.sim == "Sim+eSIM"
    assert ident.device_category == "Смартфоны"


def test_ultra_white_ocean_band_rejects_missing_case() -> None:
    # White is band color only; Ultra 2/3 cases are Natural/Black Titanium.
    ident = classify_offer("Ultra 2 White Ocean Band")
    assert ident.publish is False
    assert ident.reject_reason == "watch_missing_case_color"
    assert "White Ocean Band" in ident.display_title
    assert "White Titanium" not in ident.display_title


def test_ultra_black_ti_with_band_ok() -> None:
    ident = classify_offer("Ultra 3 Black Ti Black Alpine Loop (M)")
    assert ident.publish is True
    assert ident.color == "Black Titanium"
    assert ident.band == "Black Alpine Loop (M)"


def test_series_silver_sport_band_case_not_band_color() -> None:
    ident = classify_offer("S11 46mm Silver Sport Band (L/M)")
    assert ident.publish is True
    assert ident.device_name == "Apple Watch S11 46mm"
    assert ident.color == "Silver"
    assert ident.band == "Sport Band (L/M)"


def test_series_gray_means_space_gray() -> None:
    ident = classify_offer("S11 46mm Gray Sport Band (L/M)")
    assert ident.publish is True
    assert ident.color == "Space Gray"
    assert ident.band == "Sport Band (L/M)"
    assert classify_offer("S11 46mm Space Grey Sport Band (S/M)").color == "Space Gray"


def test_series_black_means_jet_black() -> None:
    ident = classify_offer("S11 46mm Black Sport Band (L/M)")
    assert ident.publish is True
    assert ident.color == "Jet Black"
    assert ident.band == "Sport Band (L/M)"


def test_se3_black_means_midnight() -> None:
    ident = classify_offer("SE3 44mm Black Sport Band (L/M)")
    assert ident.publish is True
    assert ident.device_name == "Apple Watch SE 3 44mm"
    assert ident.color == "Midnight"
    assert ident.band == "Sport Band (L/M)"


def test_ipad_color_not_in_device_name() -> None:
    ident = classify_offer("IPad Mini 7 256GB Gray Wi-Fi")
    assert ident.publish is True
    assert ident.device_name == "iPad Mini 7 Wi-Fi"
    assert ident.color == "Gray"
    assert "Gray" not in ident.device_name


def test_ipad_a16_is_ipad_11() -> None:
    a = classify_offer("IPad A16 256GB Silver Wi-Fi")
    b = classify_offer("IPad 11 256GB Silver Wi-Fi")
    assert a.publish and b.publish
    assert a.device_name == "iPad 11 Wi-Fi"
    assert a.identity_key == b.identity_key


def test_macbook_model_code_in_config_not_name() -> None:
    ident = classify_offer("MacBook NEO A18 MHFJ4 – 8/512 Blush")
    assert ident.publish is True
    assert ident.device_name == "MacBook NEO A18"
    assert ident.color == "Blush"
    assert ident.model_code == "MHFJ4"
    assert ident.config == "8/512GB · Blush · MHFJ4"
    assert "MHFJ4" not in ident.device_name
    assert "Blush" not in ident.device_name


def test_macbook_m4_max_chip_order() -> None:
    ident = classify_offer("MacBook Pro 16 Max M4 MX303 – 36/1tb Space Black")
    assert ident.publish is True
    assert ident.device_name == "MacBook Pro 16 M4 Max"
    assert "Max M4" not in ident.device_name
    assert ident.config == "36/1TB · Space Black · MX303"


def test_iphone_17_pro_official_colors() -> None:
    white = classify_offer("🇺🇸 eSim 17 Pro Max 2TB White")
    assert white.publish is True
    assert white.color == "Silver"
    orange = classify_offer("🇺🇸 eSim 17 Pro Max 2TB Orange")
    assert orange.publish is True
    assert orange.color == "Cosmic Orange"
    blue = classify_offer("🇯🇵 17 Pro 256GB Blue")
    assert blue.publish is True
    assert blue.color == "Deep Blue"
    # no Black Titanium on 17 Pro
    bad = classify_offer("🇺🇸 17 Pro Max 256GB Black")
    assert bad.publish is False
    assert bad.reject_reason == "iphone_missing_color"


def test_ps5_dualsense_from_section() -> None:
    ident = classify_offer("Purple", section="DualSense PS5:")
    assert ident.publish is True
    assert ident.brand == "Sony"
    assert ident.device_category == "Геймпады"
    assert ident.device_name == "PS5 DualSense"
    assert ident.color == "Purple"
    assert ":" not in ident.device_name
    assert ":" not in ident.display_title


def test_ps5_console_revision_naming() -> None:
    ident = classify_offer("PS5 Pro Digital 2TB(2я рев)")
    assert ident.publish is True
    assert ident.device_name == "PS5 Pro Digital 2Tb 2 ревизия"
    assert ident.device_category == "Игровые консоли"


def test_ps5_no_glue_onto_full_line() -> None:
    from apps.worker.offer_identity import should_prepend_section

    assert (
        should_prepend_section(
            "PS5 Pro Digital 2TB(1я рев)  -",
            "PS5 Slim Disk(1я рев)",
        )
        is False
    )


def test_android_huawei_honor_xiaomi_pixel() -> None:
    cases = [
        ("Huawei Nova 15 8/256GB Black 🇷🇺", "Huawei", "Huawei Nova 15", "8/256GB · Black"),
        ("Honor X9D 8/256GB Gold", "Honor", "Honor X9D", "8/256GB · Gold"),
        ("Xiaomi 17T 12/512GB Black", "Xiaomi", "Xiaomi 17T", "12/512GB · Black"),
        ("Redmi Note 15 Pro Plus 5G 8/256GB Black", "Redmi", "Redmi Note 15 Pro Plus 5G", "8/256GB · Black"),
        ("Poco X7 Pro 12/256GB Black", "Poco", "Poco X7 Pro", "12/256GB · Black"),
        ("Pixel 10 Pro XL 256GB Porcelain", "Google", "Pixel 10 Pro XL", "256GB · Porcelain"),
        ("Redmi Pad 2 Pro 8/256GB Gray Wi-Fi", "Redmi", "Redmi Pad 2 Pro", "8/256GB · Gray · Wi-Fi"),
        ("Xiaomi Pad 8 Pro 12/512GB Blue Wi-Fi", "Xiaomi", "Xiaomi Pad 8 Pro", "12/512GB · Blue · Wi-Fi"),
    ]
    for title, brand, name, config in cases:
        ident = classify_offer(title)
        assert ident.publish is True, title
        assert ident.kind == OfferKind.android, title
        assert ident.brand == brand, (title, ident.brand)
        assert ident.device_name == name, (title, ident.device_name)
        assert ident.config == config, (title, ident.config)


def test_gaming_xbox_nintendo_oculus() -> None:
    xbox = classify_offer("XBOX Series X 1TB Black")
    assert xbox.publish and xbox.brand == "Microsoft"
    assert xbox.device_name == "Xbox Series X"
    assert "1TB" in xbox.config and "Black" in xbox.config

    ctrl = classify_offer("XBOX Controller Pulse Cipher")
    assert ctrl.publish and ctrl.device_category == "Геймпады"

    nsw = classify_offer("Nintendo Switch 2")
    assert nsw.publish and nsw.brand == "Nintendo"

    quest = classify_offer("Oculus Quest 3 512GB")
    assert quest.publish and quest.brand == "Meta"
    assert "512GB" in quest.config

    g29 = classify_offer("Logitech G29")
    assert g29.publish and g29.brand == "Logitech"


def test_dyson_airwrap_supersonic_vacuum() -> None:
    air = classify_offer("Airwrap HS05 Long Blue/Copper 🇭🇰")
    assert air.publish and air.kind == OfferKind.dyson
    assert air.device_name == "Dyson Airwrap HS05 Long"
    assert air.color == "Blue/Copper"
    assert air.device_category == "Стайлеры"

    super_ = classify_offer("Supersonic HD16 Pink/Rose Gold")
    assert super_.publish and "HD16" in super_.device_name
    assert super_.color == "Pink/Rose Gold"

    vac = classify_offer("V15 Detect Absolute SV47 Yellow/Nickel")
    assert vac.publish and vac.device_category == "Пылесосы"

    ph = classify_offer("PH05 White/Gold")
    assert ph.publish and ph.device_category == "Воздухоочистители"


def test_yandex_station_and_meta_rayban() -> None:
    ya = classify_offer("Яндекс Станция Лайт 2 (Зелёный)")
    assert ya.publish and ya.kind == OfferKind.yandex
    assert ya.brand == "Яндекс"
    assert ya.color == "Green"
    assert ya.device_category == "Умный дом"

    rb = classify_offer("Ray Ban Meta Wayfarer RW4012 (Matte Black/Clear) L")
    assert rb.publish and rb.kind == OfferKind.meta
    assert rb.brand == "Meta"
    assert rb.device_name == "Ray-Ban Meta Wayfarer"
    assert "RW4012" in rb.config and "L" in rb.config


def test_sony_portal_pulse_vr2_horizon() -> None:
    portal = classify_offer("PlayStation Sony Portal White")
    assert portal.publish and portal.device_name == "Sony Portal"
    assert portal.color == "White"

    pulse = classify_offer("PlayStation Pulse Elite Black")
    assert pulse.publish and pulse.device_name == "Pulse Elite"

    vr = classify_offer("PlayStation VR2 Horizon")
    assert vr.publish and "VR2" in vr.device_name and "Horizon" in vr.device_name


def test_galaxy_buds_and_watch_8() -> None:
    buds = classify_offer("Galaxy Buds 4 Pro Black")
    assert buds.publish and buds.device_name == "Galaxy Buds 4 Pro"
    assert buds.color == "Black"

    watch = classify_offer("Galaxy Watch 8 Ultra 47mm LTE Gray")
    assert watch.publish and "Watch 8 Ultra" in watch.device_name
    assert "LTE" in watch.config
    assert watch.color == "Gray"


def test_galaxy_ring_unisale() -> None:
    # Samsung OEM: Titanium Gold; sizes 5–13
    ring = classify_offer("Galaxy Ring Titanium Gold 10 Q500")
    assert ring.publish is True
    assert ring.brand == "Samsung"
    assert ring.device_name == "Galaxy Ring 10"
    assert ring.color == "Titanium Gold"
    assert ring.model_code == "Q500"
    assert "Size 10" in ring.config


def test_review_fixes_precision_gates() -> None:
    # MacBook Neo year must not be stripped as a price token
    neo = classify_offer("MacBook Neo 2025 16/512GB Silver")
    assert neo.publish is True
    assert "2025" in neo.device_name

    # Pixel-only finishes must not leak onto iPhone
    iphone = classify_offer("iPhone 16 128GB Snow")
    assert iphone.publish is False or iphone.color != "Snow"

    # Bare model tokens without brand must not invent OEM brands
    assert classify_offer("Aura Studio 3 Black").publish is False
    assert classify_offer("Hero 12 Black").publish is False

    # Region paren is not a color — reject rather than invent "Eu"
    jbl = classify_offer("JBL Flip 7 (EU)")
    assert jbl.publish is False
    assert jbl.reject_reason == "audio_missing_color"

    # PowerShot keeps space before color
    cam = classify_offer("PowerShot G7X Mark III Black")
    assert cam.publish is True
    assert "G7XBlack" not in cam.device_name
    assert cam.color == "Black"


def test_macbook_bare_and_apple_accessories() -> None:
    mb = classify_offer("Pro 14 M1 Pro 2021 16/1TB Space Gray MKGQ3")
    assert mb.publish and mb.device_name.startswith("MacBook Pro 14")
    assert "MKGQ3" in mb.config

    air = classify_offer("Air 13 M4 2025 16/512GB Starlight MW103")
    assert air.publish and air.device_name.startswith("MacBook Air 13")

    mag = classify_offer("MagSafe 2m MX6Y3")
    assert mag.publish and mag.device_category == "Аксессуары"

    tv = classify_offer("Apple TV 4K 64GB MN873")
    assert tv.publish and tv.device_category == "ТВ"

    cable = classify_offer("USB-C Cable 60W 1m MQKJ3")
    assert cable.publish and "USB-C Cable" in cable.device_name

    adapter = classify_offer("Power Adapter 20W")
    assert adapter.publish and "Power Adapter" in adapter.device_name


def test_indonesia_flag_region() -> None:
    from apps.worker.offer_identity import extract_region

    assert extract_region("Air 13 M5 16/1TB 🇮🇩") == "id"


def test_audio_jbl_marshall_beats_bose() -> None:
    jbl = classify_offer("JBL Flip 7 (Purple) - 8800")
    assert jbl.publish and jbl.kind == OfferKind.audio
    assert jbl.brand == "JBL"
    assert jbl.device_category == "Колонки"
    assert jbl.device_name == "JBL Flip 7"
    assert jbl.color == "Purple"

    marshall = classify_offer("Marshall Willen II (Black)")
    assert marshall.publish and marshall.brand == "Marshall"
    assert marshall.device_category == "Колонки"
    assert "Willen II" in marshall.device_name

    motif = classify_offer("Marshall Motif II ANC (Black)")
    assert motif.publish and motif.device_category == "Наушники"

    beats = classify_offer("Beats Pill (Champagne Gold)")
    assert beats.publish and beats.brand == "Beats"
    assert beats.device_category == "Колонки"

    bose = classify_offer("Bose Ultra Open Earbuds (White Smoke)")
    assert bose.publish and bose.brand == "Bose"
    assert bose.device_category == "Наушники"

    senn = classify_offer("Sennheiser Momentum True Wireless 4 (Black)")
    assert senn.publish and senn.brand == "Sennheiser"

    hk = classify_offer("Harman Kardon Onyx Studio 9 (Black)")
    assert hk.publish and hk.brand == "Harman Kardon"
    assert hk.device_category == "Колонки"

    bw = classify_offer("Bowers & Wilkins Px7 S2e (Black)")
    assert bw.publish and bw.brand == "Bowers & Wilkins"
    assert bw.device_category == "Наушники"

    beo = classify_offer("Beoplay HX (Black Anthracite)")
    assert beo.publish and beo.brand == "Beoplay"
    assert "HX" in beo.device_name

    # OnePlus Buds Pro 3 OEM finish — must not steal Galaxy Buds path
    buds = classify_offer("OnePlus Buds 3 Pro Lunar Radiance 🇪🇺")
    assert buds.publish and buds.kind == OfferKind.audio
    assert buds.brand == "OnePlus"
    assert buds.color == "Lunar Radiance"
    assert "Galaxy" not in buds.device_name


def test_macbook_leading_order_code_unisale() -> None:
    air = classify_offer("MC654 Air 13 Silver M4 24/512GB")
    assert air.publish is True
    assert air.device_name == "MacBook Air 13 M4"
    assert air.color == "Silver"
    assert air.model_code == "MC654"
    assert "24/512GB" in air.config
    assert "MC654" in air.config

    pro = classify_offer("MPHH3 Pro 14 Silver M2 Pro 16/512GB")
    assert pro.publish is True
    assert pro.device_name == "MacBook Pro 14 M2 Pro"
    assert pro.model_code == "MPHH3"
    assert pro.color == "Silver"

    # Top re:sale: order-code line under MacBook section (16/1tb must not block glue as iPhone 16)
    top = classify_offer("🇷🇺 MKGQ3 – 16/1tb Space Gray — 123000₽", section="MacBook Pro 14 (M1)")
    assert top.publish is True
    assert top.device_name == "MacBook Pro 14 M1"
    assert top.model_code == "MKGQ3"
    assert "123000" not in top.device_name


def test_android_realme_oneplus_nothing_tecno_colors() -> None:
    # OEM Pixel 7 finishes: Lemongrass, Snow (Google)
    pixel = classify_offer("Pixel 7 8/128GB Lemongrass")
    assert pixel.publish and pixel.color == "Lemongrass"
    assert pixel.device_name == "Pixel 7"

    snow = classify_offer("Pixel 7 8/128GB Snow")
    assert snow.publish and snow.color == "Snow"

    # Huawei OEM: Lake Cyan (Nova 15 Max), Guava Soda (Pura 90s Pro)
    lake = classify_offer("Huawei Nova 15 Max 8/256GB Lake Cyan")
    assert lake.publish and lake.color == "Lake Cyan"

    guava = classify_offer("Huawei Pura 90s Pro 12/512GB Guava Soda")
    assert guava.publish and guava.color == "Guava Soda"

    realme = classify_offer("Realme c85 8/256GB Blue 🇷🇺")
    assert realme.publish and realme.brand == "Realme"
    assert realme.device_name == "Realme C85"

    p3 = classify_offer("Realme p3 Lite 8/256GB Black")
    assert p3.publish and "P3" in p3.device_name and "Lite" in p3.device_name

    op = classify_offer("OnePlus 13s 12/256GB Black")
    assert op.publish and op.brand == "OnePlus"
    assert "13s" in op.device_name or "13S" in op.device_name

    op15 = classify_offer("OnePlus 15 16/512GB Black")
    assert op15.publish and op15.brand == "OnePlus"

    nothing = classify_offer("Nothing Phone 3 12/256GB Black")
    assert nothing.publish and nothing.brand == "Nothing"
    assert "Phone 3" in nothing.device_name

    tecno = classify_offer("Tecno 40 Camon 8/256GB Black")
    assert tecno.publish and tecno.brand == "Tecno"
    assert tecno.device_name == "Tecno Camon 40"


def test_samsung_fold_flip_fe_finishes() -> None:
    fold = classify_offer("Galaxy z fold8 12/512GB Pistachio 🇹🇭")
    assert fold.publish is True
    assert fold.device_name == "Galaxy Z Fold8"
    assert fold.color == "Pistachio"

    flip = classify_offer("Galaxy z flip7 8/256GB Jetblack")
    assert flip.publish is True
    assert flip.device_name == "Galaxy Z Flip7"
    assert flip.color == "Jet Black"

    fe = classify_offer("S25 FE 8/256GB Jetblack")
    assert fe.publish is True
    assert fe.device_name == "Galaxy S25 FE"
    assert fe.color == "Jet Black"


def test_meta_rayban_without_meta_token() -> None:
    rb = classify_offer("Ray-Ban Wayfarer RW4012 (Matte Black/Clear) L")
    assert rb.publish and rb.kind == OfferKind.meta
    assert rb.device_name == "Ray-Ban Meta Wayfarer"
    assert "RW4012" in rb.config


def test_dyson_am07_and_v16s_submarine() -> None:
    fan = classify_offer("Dyson AM07 White/Silver")
    assert fan.publish and fan.kind == OfferKind.dyson
    assert "AM07" in fan.device_name
    assert fan.device_category == "Вентиляторы"

    vac = classify_offer("Dyson V16s Piston Animal Submarine")
    assert vac.publish and "V16s" in vac.device_name
    assert "Submarine" in vac.device_name
    assert vac.device_category == "Пылесосы"


def test_camera_instax_dji_gopro_powershot() -> None:
    # Fujifilm Instax ≠ Insta360
    instax = classify_offer("Instax sq1 Square Chalk White")
    assert instax.publish and instax.kind == OfferKind.camera
    assert instax.brand == "Fujifilm"
    assert instax.device_category == "Фото"
    assert "SQ1" in instax.device_name
    assert instax.color == "Chalk White"

    link = classify_offer("Instax LINK Wide Black")
    assert link.publish and link.brand == "Fujifilm"
    assert "Link Wide" in link.device_name

    # Must not route Instax into Insta360
    assert instax.kind != OfferKind.insta360

    dji = classify_offer("DJI Osmo 6 Action (Adventure Combo) Black")
    assert dji.publish and dji.brand == "DJI"
    assert dji.device_name == "DJI Osmo Action 6"
    assert "Adventure Combo" in dji.config
    assert dji.color == "Black"

    gopro = classify_offer("GoPro Hero 12 Black")
    assert gopro.publish and gopro.brand == "GoPro"
    assert "Hero 12" in gopro.device_name

    canon = classify_offer("Canon PowerShot G7X Black")
    assert canon.publish and canon.brand == "Canon"
    assert "G7X" in canon.device_name or "PowerShot" in canon.device_name

