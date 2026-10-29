from __future__ import annotations

from typing import Iterable, Any

import pandas as pd


def _to_utc(ts: Any) -> pd.Timestamp | None:
    if ts is None or pd.isna(ts):
        return None
    if isinstance(ts, pd.Timestamp):
        value = ts
    else:
        value = pd.Timestamp(ts)
    if value.tzinfo is None:
        return value.tz_localize("UTC")
    return value.tz_convert("UTC")


def select_eligible_forecast(forecasts: Iterable[dict[str, Any]], target_period: Any, cutoff: Any) -> dict[str, Any] | None:
    target_time = _to_utc(target_period)
    cutoff_time = _to_utc(cutoff)
    if target_time is None or cutoff_time is None:
        return None

    eligible: list[dict[str, Any]] = []
    for record in forecasts:
        if not isinstance(record, dict):
            continue
        publish_time = _to_utc(record.get("publishTime"))
        start_time = _to_utc(record.get("startTime"))
        if publish_time is None or start_time is None:
            continue
        if start_time == target_time and publish_time <= cutoff_time:
            eligible.append(record)

    if not eligible:
        return None

    return sorted(
        eligible,
        key=lambda item: _to_utc(item.get("publishTime")) or pd.Timestamp.min.tz_localize("UTC"),
    )[-1]
