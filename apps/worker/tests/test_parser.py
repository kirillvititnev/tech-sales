from __future__ import annotations

from decimal import Decimal

from apps.worker.parser import parse_price_text, parse_price_token


def test_section_does_not_glue_onto_other_model() -> None:
    text = """
📦 iPhone 17 Pro Max
17e 256GB Black - 56800
"""
    lines = parse_price_text(text)
    assert len(lines) == 1
    assert "17 Pro Max" not in lines[0].title
    assert "17e" in lines[0].title.lower()


def test_section_glues_onto_continuation() -> None:
    text = """
📦 iPhone 17 Pro Max
256GB Blue (E-Sim) - 102800
"""
    lines = parse_price_text(text)
    assert len(lines) == 1
    assert "iPhone 17 Pro Max" in lines[0].title
    assert "256GB" in lines[0].title


def test_header_alone_not_parsed() -> None:
    assert parse_price_text("📦 iPhone 17 Pro Max") == []


def test_phone_number_not_price() -> None:
    assert parse_price_token("79001234567") is None


def test_price_above_legacy_min() -> None:
    assert parse_price_token("6500") == Decimal("6500")


def test_top_resale_style_clean_lines() -> None:
    text = """
IPhone 16:
🇺🇸 16 128GB Black — 61200₽
🇺🇸 16 128GB White — 62500₽
AirPods 4 ANC  — 13800₽
"""
    lines = parse_price_text(text)
    titles = [line.title for line in lines]
    assert any("16 128GB Black" in t for t in titles)
    assert all("Прайс" not in t and "Выдача" not in t for t in titles)
    black = next(line for line in lines if "128GB Black" in line.title)
    assert not black.title.lower().startswith("iphone 16:")


def test_bests_trailing_region_flag_after_price() -> None:
    text = """
Galaxy S23 Plus
S23 Plus 8/512GB Black — 42.800 🇦🇪
Mac Mini M4 16/512GB MU9E3 — 76.300 🇭🇰
DualSense White — 5.800
"""
    lines = parse_price_text(text)
    assert len(lines) == 3
    assert lines[0].price == Decimal("42800")
    assert "S23 Plus" in lines[0].title
    assert "🇦🇪" in lines[0].title  # trailing flag moved onto title for region/SIM
    assert lines[1].price == Decimal("76300")
    assert "🇭🇰" in lines[1].title
    assert lines[2].price == Decimal("5800")


def test_junk_banner_not_used_as_section() -> None:
    text = """
Выдача в день заказа или на следующий день до 14:00‼️
Saeco Magic M1 — 218900
Прайс Galaxy S
• S25 Ultra 12/256Gb Titanium Black — 65900₽
"""
    lines = parse_price_text(text)
    assert len(lines) == 2
    assert lines[0].title == "Saeco Magic M1"
    assert "Выдача" not in lines[0].title
    assert lines[1].title.startswith("S25 Ultra")
    assert "Прайс" not in lines[1].title


def test_trailing_qty_suffix_still_parses() -> None:
    lines = parse_price_text("17 Air 256GB Blue 🇦🇪 (E-Sim) - 71600 х1")
    assert len(lines) == 1
    assert "17 Air" in lines[0].title
    assert lines[0].price == Decimal("71600")


def test_global_market_ipad_and_macbook_neo_continuations() -> None:
    text = """
📲 iPad

iPad 11 2025 Wi-Fi:

128GB Yellow - 37000
128GB Pink - 38500

iPad Air 11 M4 Wi-Fi:

128GB Gray - 61000

MacBook

Neo:

8/256GB Citrus - 61500
8/512GB Blush - 72000
"""
    lines = parse_price_text(text)
    titles = [line.title for line in lines]
    yellow = next(line for line in lines if "Yellow" in line.title)
    assert "iPad 11" in yellow.title
    assert "128GB" in yellow.title
    assert yellow.price == Decimal("37000")
    gray = next(line for line in lines if "Gray" in line.title)
    assert "iPad Air 11" in gray.title
    citrus = next(line for line in lines if "Citrus" in line.title)
    assert "MacBook Neo" in citrus.title
    assert "8/256GB" in citrus.title
    assert any("Blush" in t and "MacBook Neo" in t for t in titles)


def test_global_market_price_after_flag_without_dash() -> None:
    lines = parse_price_text("17 Pro Max 1TB Blue🇭🇰 148000")
    assert len(lines) == 1
    assert lines[0].price == Decimal("148000")
    assert "17 Pro Max" in lines[0].title
    assert "🇭🇰" in lines[0].title


def test_global_market_accessories_do_not_glue_onto_fitbit() -> None:
    text = """
🎧AirPods
AirPods 4 ANC - 13200
✨Accessories
Fitbit Air Berry - 10300
Pencil 2 - 5900
"""
    lines = parse_price_text(text)
    air = next(line for line in lines if "AirPods 4" in line.title)
    assert air.section and "AirPods" in air.section
    fitbit = next(line for line in lines if "Fitbit" in line.title)
    assert "AirPods" not in fitbit.title
    pencil = next(line for line in lines if "Pencil" in line.title)
    assert "AirPods" not in pencil.title
