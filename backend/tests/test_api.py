from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_date_validation() -> None:
    client = TestClient(app)
    response = client.get("/api/dashboard", params={"start_date": "2026-01-31", "end_date": "2026-01-01"})
    assert response.status_code == 400

    invalid = client.get("/api/dashboard", params={"start_date": "not-a-date", "end_date": "2026-01-31"})
    assert invalid.status_code == 400


def test_dashboard_uses_unavailable_status_when_upstream_unavailable(monkeypatch) -> None:
    async def _fake_load(_start: str, _end: str) -> dict[str, object]:
        return {
            "status": "unavailable",
            "message": "upstream down",
            "source": "Elexon BMRS",
            "retrieval_time": "2026-01-01T00:00:00Z",
            "coverage_start": "2026-01-01",
            "coverage_end": "2026-01-31",
            "records_returned": 0,
            "valid_records": 0,
            "duplicate_records": 0,
            "invalid_records": 0,
            "missing_actual_records": 0,
            "missing_forecast_records": 0,
            "upstream_available": False,
            "upstream_error": "ConnectError",
            "selected_cutoff_assumption": "cutoff",
        }

    monkeypatch.setattr("app.data_service.load_elexon_data", _fake_load)

    client = TestClient(app)
    response = client.get("/api/dashboard", params={"start_date": "2026-01-01", "end_date": "2026-01-31"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["series"] == []


def test_dashboard_does_not_claim_ok_without_processed_series(monkeypatch) -> None:
    async def _fake_load(_start: str, _end: str) -> dict[str, object]:
        return {
            "status": "ok",
            "message": "upstream reached",
            "source": "Elexon BMRS",
            "retrieval_time": "2026-01-01T00:00:00Z",
            "coverage_start": "2026-01-01",
            "coverage_end": "2026-01-31",
            "records_returned": 2,
            "valid_records": 2,
            "duplicate_records": 0,
            "invalid_records": 0,
            "missing_actual_records": 0,
            "missing_forecast_records": 0,
            "upstream_available": True,
            "upstream_error": None,
            "selected_cutoff_assumption": "cutoff",
            "actual_records": [],
            "forecast_records": [],
        }

    monkeypatch.setattr("app.data_service.load_elexon_data", _fake_load)

    client = TestClient(app)
    response = client.get("/api/dashboard", params={"start_date": "2026-01-01", "end_date": "2026-01-31"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "empty"
    assert len(body["series"]) == 1488
    assert body["kpis"]["matched_periods"] == 0
    assert body["series"][0]["forecast"] is None


def _matched_january_data(_start: str, _end: str) -> dict[str, object]:
    actual = []
    forecast = []
    day = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for period in range(48):
        target = day + timedelta(minutes=30 * period)
        actual.append({
            "dataset": "FUELHH",
            "fuelType": "WIND",
            "startTime": target.isoformat().replace("+00:00", "Z"),
            "publishTime": "2026-01-02T00:00:00Z",
            "generation": 100,
        })
        if target.minute == 0:
            forecast.append({
                "dataset": "WINDFOR",
                "startTime": target.isoformat().replace("+00:00", "Z"),
                "publishTime": "2025-12-31T11:30:00Z",
                "generation": 110,
            })
    return {
        "status": "ok",
        "message": None,
        "source": "Elexon BMRS Insights API",
        "source_url": "https://developer.data.elexon.co.uk/",
        "retrieval_time": "2026-02-01T00:00:00Z",
        "coverage_start": "2026-01-01",
        "coverage_end": "2026-01-01",
        "records_returned": len(actual) + len(forecast),
        "valid_records": 0,
        "duplicate_records": 0,
        "invalid_records": 0,
        "missing_actual_records": 0,
        "missing_forecast_records": 0,
        "upstream_available": True,
        "upstream_error": None,
        "selected_cutoff_assumption": "Previous-day 12:00 UTC",
        "actual_records": actual,
        "forecast_records": forecast,
    }


def test_dashboard_normalizes_and_matches_elexon_wind_records(monkeypatch) -> None:
    async def _fake_load(_start: str, _end: str) -> dict[str, object]:
        return _matched_january_data(_start, _end)

    monkeypatch.setattr("app.data_service.load_elexon_data", _fake_load)
    body = TestClient(app).get(
        "/api/dashboard",
        params={"start_date": "2026-01-01", "end_date": "2026-01-01"},
    ).json()

    assert body["status"] == "ok"
    assert body["kpis"]["matched_periods"] == 48
    assert body["accuracy"]["coverage_pct"] == 100.0
    assert body["accuracy"]["mae_mw"] == 10.0
    assert body["accuracy"]["rmse_mw"] == 10.0
    assert body["accuracy"]["bias_mw"] == 10.0
    assert body["accuracy"]["mape_pct"] == 10.0
    assert body["series"][1]["forecast"] == 110
    assert body["forecast_history"][0]["selected"] is True
    assert body["largest_errors"][0]["absolute_error"] == 10.0


def test_forecast_published_after_previous_day_cutoff_is_not_used(monkeypatch) -> None:
    payload = _matched_january_data("2026-01-01", "2026-01-01")
    payload["forecast_records"] = [
        {**record, "publishTime": "2025-12-31T12:30:00Z"}
        for record in payload["forecast_records"]
    ]

    async def _fake_load(_start: str, _end: str) -> dict[str, object]:
        return payload

    monkeypatch.setattr("app.data_service.load_elexon_data", _fake_load)
    body = TestClient(app).get(
        "/api/dashboard",
        params={"start_date": "2026-01-01", "end_date": "2026-01-01"},
    ).json()

    assert body["status"] == "empty"
    assert body["kpis"]["matched_periods"] == 0
    assert body["metadata"]["missing_forecast_records"] == 48


def test_accuracy_errors_and_forecast_history_share_processed_data(monkeypatch) -> None:
    async def _fake_load(_start: str, _end: str) -> dict[str, object]:
        return _matched_january_data(_start, _end)

    monkeypatch.setattr("app.data_service.load_elexon_data", _fake_load)
    client = TestClient(app)
    params = {"start_date": "2026-01-01", "end_date": "2026-01-01"}

    accuracy = client.get("/api/accuracy", params=params).json()["accuracy"]
    errors = client.get("/api/errors", params={**params, "limit": 2}).json()["largest_errors"]
    history = client.get("/api/forecast-history", params={**params, "target_time": "2026-01-01T00:30:00Z"}).json()["history"]

    assert accuracy["matched_periods"] == 48
    assert len(errors) == 2
    assert len(history) == 1
    assert history[0]["selected"] is True
