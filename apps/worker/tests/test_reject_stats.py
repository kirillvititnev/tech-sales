from apps.worker.reject_stats import note_reject, sync_stats_for_store


def test_note_reject_counts_and_samples() -> None:
    stats: dict = {}
    note_reject(stats, "iphone_missing_color", title="iPhone 16 Pro 256GB")
    note_reject(stats, "iphone_missing_color", title="iPhone 15 128")
    note_reject(stats, "below_min_price")
    note_reject(stats, "iphone_missing_color", title="third")
    note_reject(stats, "iphone_missing_color", title="fourth ignored sample")

    assert stats["rejected"] == 5
    assert stats["reject_reasons"]["iphone_missing_color"] == 4
    assert stats["reject_reasons"]["below_min_price"] == 1
    assert stats["reject_samples"]["iphone_missing_color"] == [
        "iPhone 16 Pro 256GB",
        "iPhone 15 128",
        "third",
    ]


def test_sync_stats_for_store_keeps_nested() -> None:
    flat = sync_stats_for_store(
        {
            "channels": 2,
            "rejected": 3,
            "reject_reasons": {"junk_or_noise": 2},
            "reject_samples": {"junk_or_noise": ["foo"]},
        }
    )
    assert flat["channels"] == 2
    assert flat["reject_reasons"] == {"junk_or_noise": 2}
    assert flat["reject_samples"]["junk_or_noise"] == ["foo"]
