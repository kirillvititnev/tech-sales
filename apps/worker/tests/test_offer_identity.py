from __future__ import annotations

import pytest

from apps.worker.offer_identity import classify_offer, identity_key, should_prepend_section


@pytest.mark.parametrize(
    ("title", "expected_sim"),
    [
        ("iPhone 17 Pro Max 256GB Blue 🇯🇵 (E-Sim)", "eSIM"),
        ("iPhone 17 Pro Max 256GB Blue 🇺🇸 (eSIM)", "eSIM"),
        ("🇺🇸 16 Pro 256GB Black", "eSIM"),
        ("🇪🇺 16 Pro 256GB Black", "Sim+eSIM"),
        ("🇯🇵 17 Pro 256GB Blue", "eSIM"),
        ("🇩🇪 17 Pro 256GB Blue", "Sim+eSIM"),
        ("🇨🇳 17 Pro Max 256GB Black", "2Sim"),
        ("CN 16 Pro 256GB Black", "2Sim"),
        ("iPhone Air 256GB Cloud White 🇨🇳", "eSIM"),
        ("iPhone Air 256GB White", "eSIM"),
    ],
)
def test_sim_inference_matrix(title: str, expected_sim: str) -> None:
    ident = classify_offer(title)
    assert ident.publish is True
    assert ident.sim == expected_sim
    assert "🇯🇵" not in ident.display_title
    assert "🇺🇸" not in ident.display_title
    assert "🇨🇳" not in ident.display_title


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


def test_marketing_noise_rejected() -> None:
    ident = classify_offer("АКЦИЯ только сегодня iPhone")
    assert ident.publish is False
