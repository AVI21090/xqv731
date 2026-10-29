from __future__ import annotations

import asyncio
import json
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
import pandas as pd

from app.cache import read_cache, write_cache
from app.config import (
    DEFAULT_END_DATE,
    DEFAULT_START_DATE,
    ELEXON_BASE_URL,
    FORECAST_CUTOFF_UTC_HOUR,
)
from app.forecast_selection import select_eligible_forecast
from app.metrics import compute_accuracy_metrics

SOURCE = "Elexon BMRS Insights API"
SOURCE_URL = "https://developer.data.elexon.co.uk/"
CACHE_TTL_SECONDS = 3600
CUTOFF_ASSUMPTION = (
    f"Latest WINDFOR publication at or before {FORECAST_CUTOFF_UTC_HOUR:02d}:00 UTC "
    "on the day before delivery. This is the assignment's configurable day-ahead "
    "cutoff assumption, not a claim about an official market purchasing deadline."
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _iso_utc(value: Any) -> pd.Timestamp | None:
    if value is None or pd.isna(value):
        return None
    try:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            return timestamp.tz_localize("UTC")
        return timestamp.tz_convert("UTC")
    except (TypeError, ValueError, OverflowError):
        return None


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _cutoff_for_delivery(target: pd.Timestamp) -> pd.Timestamp:
    delivery_date = target.tz_convert("UTC").date()
    cutoff_date = delivery_date - timedelta(days=1)
    return pd.Timestamp(datetime.combine(
        cutoff_date,
        time(hour=FORECAST_CUTOFF_UTC_HOUR),
        tzinfo=timezone.utc,
    ))


async def _fetch_dataset(dataset: str, params: dict[str, str]) -> tuple[list[dict[str, Any]], str]:
    query = urlencode(params)
    cache_key = f"insights:{dataset}:{query}"
    try:
        cached = read_cache(cache_key)
    except OSError:
        cached = None
    if isinstance(cached, dict) and isinstance(cached.get("records"), list):
        cached_at = _iso_utc(cached.get("retrieved_at"))
        age_seconds = (pd.Timestamp.now(tz="UTC") - cached_at).total_seconds() if cached_at is not None else None
        if age_seconds is not None and 0 <= age_seconds < CACHE_TTL_SECONDS:
            return cached["records"], cached["retrieved_at"]

    url = f"{ELEXON_BASE_URL}/datasets/{dataset}/stream?{query}"
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        response = await client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        payload = response.json()

    # Stream endpoints return a JSON array; accept the documented metadata wrapper too.
    records = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError(f"Elexon {dataset} response did not contain a record list")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError(f"Elexon {dataset} response contained a malformed record")
    retrieved_at = utc_now_iso()
    try:
        write_cache(cache_key, {"retrieved_at": retrieved_at, "records": records})
    except OSError:
        pass
    return records, retrieved_at


async def load_elexon_data(start_date: str, end_date: str) -> dict[str, Any]:
    start = _date(start_date)
    end = _date(end_date)
    if start > end:
        raise ValueError("start date must be before end date")

    # Keep earlier publications in the forecast horizon so a missed update does
    # not cause an older but still eligible vintage to be discarded.
    forecast_start = datetime.combine(start - timedelta(days=3), time.min, tzinfo=timezone.utc)
    forecast_end = datetime.combine(
        end - timedelta(days=1),
        time(hour=FORECAST_CUTOFF_UTC_HOUR),
        tzinfo=timezone.utc,
    )
    actual_params = {
        "settlementDateFrom": start.isoformat(),
        "settlementDateTo": end.isoformat(),
        "fuelType": "WIND",
    }
    forecast_params = {
        "publishDateTimeFrom": forecast_start.isoformat().replace("+00:00", "Z"),
        "publishDateTimeTo": forecast_end.isoformat().replace("+00:00", "Z"),
    }
    metadata: dict[str, Any] = {
        "status": "unavailable",
        "message": "Elexon data could not be retrieved for this range.",
        "source": SOURCE,
        "source_url": SOURCE_URL,
        "retrieval_time": utc_now_iso(),
        "coverage_start": start_date,
        "coverage_end": end_date,
        "records_returned": 0,
        "valid_records": 0,
        "duplicate_records": 0,
        "invalid_records": 0,
        "missing_actual_records": 0,
        "missing_forecast_records": 0,
        "upstream_available": False,
        "upstream_error": None,
        "selected_cutoff_assumption": CUTOFF_ASSUMPTION,
        "actual_endpoint": f"{ELEXON_BASE_URL}/datasets/FUELHH/stream?{urlencode(actual_params)}",
        "forecast_endpoint": f"{ELEXON_BASE_URL}/datasets/WINDFOR/stream?{urlencode(forecast_params)}",
    }

    try:
        (actual_records, actual_retrieved), (forecast_records, forecast_retrieved) = await asyncio.gather(
            _fetch_dataset("FUELHH", actual_params),
            _fetch_dataset("WINDFOR", forecast_params),
        )
        metadata.update({
            "status": "ok",
            "message": None,
            "upstream_available": True,
            "records_returned": len(actual_records) + len(forecast_records),
            "retrieval_time": max(actual_retrieved, forecast_retrieved),
        })
        return {
            **metadata,
            "actual_records": actual_records,
            "forecast_records": forecast_records,
        }
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, OSError) as exc:
        metadata["upstream_error"] = f"{type(exc).__name__}: {exc}"
        metadata["message"] = (
            "The public Elexon Insights API request failed. No values were invented. "
            f"Reason: {metadata['upstream_error']}"
        )
        return metadata


def _normalise_actuals(records: list[dict[str, Any]]) -> tuple[dict[pd.Timestamp, float], int, int, int]:
    by_period: dict[pd.Timestamp, tuple[float, pd.Timestamp | None]] = {}
    duplicates = 0
    invalid = 0
    for record in records:
        if str(record.get("fuelType", "")).upper() != "WIND":
            continue
        target = _iso_utc(record.get("startTime"))
        generation = _number(record.get("generation"))
        if target is None or generation is None:
            invalid += 1
            continue
        if target in by_period:
            duplicates += 1
            published = _iso_utc(record.get("publishTime"))
            previous_publish = by_period[target][1]
            if published is not None and (previous_publish is None or published > previous_publish):
                by_period[target] = (generation, published)
        else:
            by_period[target] = (generation, _iso_utc(record.get("publishTime")))

    values = {target: value[0] for target, value in by_period.items()}
    return values, duplicates, invalid, len(values)


def _normalise_forecasts(
    records: list[dict[str, Any]],
) -> tuple[dict[pd.Timestamp, list[dict[str, Any]]], int, int, int]:
    by_period: dict[pd.Timestamp, dict[pd.Timestamp, dict[str, Any]]] = {}
    duplicates = 0
    invalid = 0
    for record in records:
        target = _iso_utc(record.get("startTime"))
        published = _iso_utc(record.get("publishTime"))
        generation = _number(record.get("generation"))
        if target is None or published is None or generation is None:
            invalid += 1
            continue
        # WINDFOR is hourly. The forecast for each hourly block is used for its
        # two half-hour FUELHH settlement periods (a constant-within-hour rule).
        if target.minute != 0 or target.second != 0 or target.microsecond != 0:
            invalid += 1
            continue
        target = target.floor("h")
        versions = by_period.setdefault(target, {})
        if published in versions:
            duplicates += 1
        versions[published] = {
            "startTime": target,
            "publishTime": published,
            "generation": generation,
        }

    forecasts = {
        target: sorted(versions.values(), key=lambda item: item["publishTime"])
        for target, versions in by_period.items()
    }
    return forecasts, duplicates, invalid, sum(len(items) for items in forecasts.values())


def _empty_metrics(total_records: int = 0) -> dict[str, Any]:
    return {
        "mae_mw": None,
        "rmse_mw": None,
        "bias_mw": None,
        "mape_pct": None,
        "matched_periods": 0,
        "missing_actual_records": 0,
        "missing_forecast_records": 0,
        "zero_actual_count": 0,
        "total_records": total_records,
        "coverage_pct": 0.0,
    }


def _select_forecast_history(
    forecast_map: dict[pd.Timestamp, list[dict[str, Any]]], target: pd.Timestamp,
) -> list[dict[str, Any]]:
    hourly_target = target.floor("h")
    cutoff = _cutoff_for_delivery(target)
    eligible = [
        item for item in forecast_map.get(hourly_target, [])
        if item["publishTime"] <= cutoff
    ]
    selected = select_eligible_forecast(eligible, hourly_target, cutoff)
    return [
        {
            "startTime": item["startTime"].isoformat().replace("+00:00", "Z"),
            "publishTime": item["publishTime"].isoformat().replace("+00:00", "Z"),
            "generation": item["generation"],
            "selected": selected is not None and item["publishTime"] == selected["publishTime"],
        }
        for item in eligible
    ]


async def _analysis_for_range(start_date: str, end_date: str) -> dict[str, Any]:
    metadata = await load_elexon_data(start_date, end_date)
    if metadata["status"] != "ok":
        return {"metadata": metadata, "periods": [], "history_target": None}

    actual_map, actual_duplicates, actual_invalid, _ = _normalise_actuals(metadata["actual_records"])
    forecast_map, forecast_duplicates, forecast_invalid, _ = _normalise_forecasts(metadata["forecast_records"])
    start = pd.Timestamp(start_date, tz="UTC")
    end_exclusive = pd.Timestamp(end_date, tz="UTC") + timedelta(days=1)
    periods = pd.date_range(start, end_exclusive, freq="30min", inclusive="left")
    rows: list[dict[str, Any]] = []
    series: list[dict[str, Any]] = []

    for target in periods:
        hourly_forecasts = forecast_map.get(target.floor("h"), [])
        cutoff = _cutoff_for_delivery(target)
        selected = select_eligible_forecast(hourly_forecasts, target.floor("h"), cutoff)
        forecast = selected["generation"] if selected else None
        actual = actual_map.get(target)
        error = forecast - actual if forecast is not None and actual is not None else None
        rows.append({
            "target_time": target,
            "forecast_generation": forecast,
            "actual_generation": actual,
            "publish_time": selected["publishTime"] if selected else None,
        })
        series.append({
            "time": target.isoformat().replace("+00:00", "Z"),
            "forecast": forecast,
            "actual": actual,
            "error": error,
        })

    accuracy = compute_accuracy_metrics(rows)
    metadata.update({
        "valid_records": accuracy["matched_periods"],
        "duplicate_records": actual_duplicates + forecast_duplicates,
        "invalid_records": actual_invalid + forecast_invalid,
        "missing_actual_records": sum(1 for row in rows if row["actual_generation"] is None),
        "missing_forecast_records": sum(1 for row in rows if row["forecast_generation"] is None),
    })
    accuracy["missing_actual_records"] = metadata["missing_actual_records"]
    accuracy["missing_forecast_records"] = metadata["missing_forecast_records"]
    accuracy["coverage_pct"] = (accuracy["matched_periods"] / len(periods) * 100) if len(periods) else 0.0

    history_target = next(
        (row["target_time"] for row in reversed(rows) if _select_forecast_history(forecast_map, row["target_time"])),
        None,
    )
    return {
        "metadata": metadata,
        "periods": periods,
        "rows": rows,
        "series": series,
        "accuracy": accuracy,
        "forecast_map": forecast_map,
        "history_target": history_target,
    }


def _unavailable_dashboard(start_date: str, end_date: str, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "message": metadata["message"],
        "source": metadata["source"],
        "retrieval_time": metadata["retrieval_time"],
        "selected_range": f"{start_date} to {end_date}",
        "metadata": metadata,
        "kpis": {
            "average_forecast_generation_mw": None,
            "average_actual_generation_mw": None,
            "mae_mw": None,
            "rmse_mw": None,
            "matched_periods": 0,
        },
        "series": [],
        "accuracy": _empty_metrics(),
        "largest_errors": [],
        "forecast_history": [],
    }


async def build_dashboard(date_start: str, date_end: str) -> dict[str, Any]:
    analysis = await _analysis_for_range(date_start, date_end)
    metadata = analysis["metadata"]
    if metadata["status"] != "ok":
        return _unavailable_dashboard(date_start, date_end, metadata)

    rows = analysis["rows"]
    matched = [
        row for row in rows
        if row["forecast_generation"] is not None and row["actual_generation"] is not None
    ]
    accuracy = analysis["accuracy"]
    largest_errors = sorted(
        (
            {
                "target_time": row["target_time"].isoformat().replace("+00:00", "Z"),
                "forecast_generation": row["forecast_generation"],
                "actual_generation": row["actual_generation"],
                "signed_error": row["forecast_generation"] - row["actual_generation"],
                "absolute_error": abs(row["forecast_generation"] - row["actual_generation"]),
                "publish_time": row["publish_time"].isoformat().replace("+00:00", "Z"),
            }
            for row in matched
        ),
        key=lambda row: row["absolute_error"],
        reverse=True,
    )[:10]
    forecast_history = (
        _select_forecast_history(analysis["forecast_map"], analysis["history_target"])
        if analysis["history_target"] is not None
        else []
    )
    averages = {
        "average_forecast_generation_mw": (
            sum(row["forecast_generation"] for row in matched) / len(matched) if matched else None
        ),
        "average_actual_generation_mw": (
            sum(row["actual_generation"] for row in matched) / len(matched) if matched else None
        ),
    }
    empty = not matched
    return {
        "status": "empty" if empty else "ok",
        "message": "No eligible matched forecast and actual periods were found for this range." if empty else None,
        "source": metadata["source"],
        "retrieval_time": metadata["retrieval_time"],
        "selected_range": f"{date_start} to {date_end}",
        "metadata": metadata,
        "kpis": {
            **averages,
            "mae_mw": accuracy["mae_mw"],
            "rmse_mw": accuracy["rmse_mw"],
            "matched_periods": accuracy["matched_periods"],
        },
        "series": analysis["series"],
        "accuracy": accuracy,
        "largest_errors": largest_errors,
        "forecast_history": forecast_history,
    }


async def accuracy_for_range(start_date: str, end_date: str) -> dict[str, Any]:
    dashboard = await build_dashboard(start_date, end_date)
    return {
        "status": dashboard["status"],
        "message": dashboard["message"],
        "source": dashboard["source"],
        "retrieval_time": dashboard["retrieval_time"],
        "selected_range": dashboard["selected_range"],
        "accuracy": dashboard["accuracy"],
    }


async def errors_for_range(start_date: str, end_date: str, limit: int = 10) -> dict[str, Any]:
    analysis = await _analysis_for_range(start_date, end_date)
    metadata = analysis["metadata"]
    if metadata["status"] != "ok":
        return {
            "status": "unavailable",
            "message": metadata["message"],
            "source": metadata["source"],
            "retrieval_time": metadata["retrieval_time"],
            "selected_range": f"{start_date} to {end_date}",
            "largest_errors": [],
            "limit": limit,
        }
    matched = [
        row for row in analysis["rows"]
        if row["forecast_generation"] is not None and row["actual_generation"] is not None
    ]
    largest_errors = sorted(
        (
            {
                "target_time": row["target_time"].isoformat().replace("+00:00", "Z"),
                "forecast_generation": row["forecast_generation"],
                "actual_generation": row["actual_generation"],
                "signed_error": row["forecast_generation"] - row["actual_generation"],
                "absolute_error": abs(row["forecast_generation"] - row["actual_generation"]),
                "publish_time": row["publish_time"].isoformat().replace("+00:00", "Z"),
            }
            for row in matched
        ),
        key=lambda row: row["absolute_error"],
        reverse=True,
    )[:limit]
    return {
        "status": "ok" if matched else "empty",
        "message": None if matched else "No eligible matched forecast and actual periods were found for this range.",
        "source": metadata["source"],
        "retrieval_time": metadata["retrieval_time"],
        "selected_range": f"{start_date} to {end_date}",
        "largest_errors": largest_errors,
        "limit": limit,
    }


async def forecast_history_for_target(
    start_date: str, end_date: str, target_time: str | None = None,
) -> dict[str, Any]:
    metadata = await load_elexon_data(start_date, end_date)
    result: dict[str, Any] = {
        "status": metadata["status"],
        "message": metadata["message"],
        "source": metadata["source"],
        "retrieval_time": metadata["retrieval_time"],
        "selected_range": f"{start_date} to {end_date}",
        "target_time": target_time,
        "history": [],
    }
    if metadata["status"] != "ok":
        return result

    requested = _iso_utc(target_time) if target_time else pd.Timestamp(start_date, tz="UTC")
    if requested is None:
        result.update({"status": "empty", "message": "target_time must be a valid ISO-8601 timestamp."})
        return result
    start = pd.Timestamp(start_date, tz="UTC")
    end_exclusive = pd.Timestamp(end_date, tz="UTC") + timedelta(days=1)
    if not start <= requested < end_exclusive:
        result.update({"status": "empty", "message": "target_time is outside the selected date range."})
        return result
    forecast_map, _, _, _ = _normalise_forecasts(metadata["forecast_records"])
    result["target_time"] = requested.isoformat().replace("+00:00", "Z")
    result["history"] = _select_forecast_history(forecast_map, requested)
    return result
