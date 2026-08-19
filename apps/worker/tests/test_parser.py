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
