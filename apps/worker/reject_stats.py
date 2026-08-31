"""Helpers for sync reject accounting."""

from __future__ import annotations


def note_reject(
    stats: dict,
    reason: str,
    *,
    title: str | None = None,
    sample_limit: int = 3,
) -> None:
    """Increment rejected counters and optionally keep short title samples."""
    stats["rejected"] = int(stats.get("rejected", 0)) + 1
    reasons = stats.setdefault("reject_reasons", {})
    reasons[reason] = int(reasons.get(reason, 0)) + 1
    if not title:
        return
    samples = stats.setdefault("reject_samples", {})
    bucket = samples.setdefault(reason, [])
    if len(bucket) < sample_limit:
        bucket.append(title[:160])


def sync_stats_for_store(stats: dict) -> dict:
    """Flatten sync stats for StoreSettings.last_sync_stats JSON."""
    out: dict = {}
    for key, val in stats.items():
        if key in {"reject_reasons", "reject_samples", "skip_group_reasons"}:
            out[key] = val
        elif isinstance(val, bool):
            out[key] = val
        else:
            out[key] = int(val)
    return out
