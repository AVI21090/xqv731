from __future__ import annotations

import asyncio

import httpx
import pandas as pd

from app.data_service import _normalise_actuals, _normalise_forecasts, load_elexon_data


def test_actual_normalization_filters_fuel_and_keeps_latest_revision() -> None:
    records = [
        {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-02T00:00:00Z", "generation": 20},
        {"fuelType": "WIND", "startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-03T00:00:00Z", "generation": 25},
        {"fuelType": "CCGT", "startTime": "2026-01-01T00:00:00Z", "generation": 500},
        {"fuelType": "WIND", "startTime": "bad timestamp", "generation": 10},
    ]

    values, duplicates, invalid, valid = _normalise_actuals(records)

    assert values[pd.Timestamp("2026-01-01T00:00:00Z")] == 25
    assert (duplicates, invalid, valid) == (1, 1, 1)


def test_forecast_normalization_preserves_publication_vintages() -> None:
    records = [
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T08:30:00Z", "generation": 100},
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2025-12-31T11:30:00Z", "generation": 110},
        {"startTime": "bad", "publishTime": "2025-12-31T11:30:00Z", "generation": 110},
    ]

    forecasts, duplicates, invalid, valid = _normalise_forecasts(records)

    target = pd.Timestamp("2026-01-01T00:00:00Z")
    assert [row["generation"] for row in forecasts[target]] == [100, 110]
    assert (duplicates, invalid, valid) == (0, 1, 2)


def test_loader_uses_keyless_stream_filters_and_publication_window(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    async def _fake_fetch(dataset: str, params: dict[str, str]):
        calls.append((dataset, params))
        return [], "2026-02-01T00:00:00Z"

    monkeypatch.setattr("app.data_service._fetch_dataset", _fake_fetch)
    metadata = asyncio.run(load_elexon_data("2026-01-01", "2026-01-31"))

    actual = next(params for dataset, params in calls if dataset == "FUELHH")
    forecast = next(params for dataset, params in calls if dataset == "WINDFOR")
    assert actual == {
        "settlementDateFrom": "2026-01-01",
        "settlementDateTo": "2026-01-31",
        "fuelType": "WIND",
    }
    assert forecast["publishDateTimeFrom"] == "2025-12-29T00:00:00Z"
    assert forecast["publishDateTimeTo"] == "2026-01-30T12:00:00Z"
    assert metadata["status"] == "ok"
    assert metadata["upstream_available"] is True


def test_loader_returns_honest_unavailable_state_on_upstream_error(monkeypatch) -> None:
    async def _fake_fetch(dataset: str, _params: dict[str, str]):
        if dataset == "FUELHH":
            raise httpx.ConnectError("offline")
        return [], "2026-02-01T00:00:00Z"

    monkeypatch.setattr("app.data_service._fetch_dataset", _fake_fetch)
    metadata = asyncio.run(load_elexon_data("2026-01-01", "2026-01-01"))

    assert metadata["status"] == "unavailable"
    assert metadata["upstream_available"] is False
    assert "ConnectError" in metadata["upstream_error"]
    assert "No values were invented" in metadata["message"]
