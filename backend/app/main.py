from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, DEFAULT_END_DATE, DEFAULT_START_DATE
from app.data_service import accuracy_for_range, build_dashboard, errors_for_range, forecast_history_for_target
from app.schemas import DashboardResponse

app = FastAPI(title="WindSight API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_date_range(start_date: str, end_date: str) -> None:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Dates must use YYYY-MM-DD format") from exc
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be earlier than or equal to end_date")


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": "WindSight API",
        "healthy": True,
    }


@app.get("/api/metadata")
async def metadata() -> dict[str, object]:
    dashboard = await build_dashboard(DEFAULT_START_DATE, DEFAULT_END_DATE)
    metadata_payload = dashboard.get("metadata") or {}
    return {
        "status": dashboard["status"],
        "message": dashboard["message"],
        "source": dashboard["source"],
        "retrieval_time": dashboard["retrieval_time"],
        "coverage_start": DEFAULT_START_DATE,
        "coverage_end": DEFAULT_END_DATE,
        "records_returned": metadata_payload.get("records_returned", 0),
        "valid_records": metadata_payload.get("valid_records", 0),
        "upstream_available": metadata_payload.get("upstream_available", False),
        "upstream_error": metadata_payload.get("upstream_error"),
        "source_url": metadata_payload.get("source_url"),
        "missing_data": {
            "actual_records": int(metadata_payload.get("missing_actual_records", 0)),
            "forecast_records": int(metadata_payload.get("missing_forecast_records", 0)),
        },
        "methodology": {
            "decision_cutoff_assumption": metadata_payload.get("selected_cutoff_assumption"),
        },
    }


@app.get("/api/dashboard", response_model=DashboardResponse)
async def dashboard(
    start_date: str = Query(DEFAULT_START_DATE, description="Start date in YYYY-MM-DD format."),
    end_date: str = Query(DEFAULT_END_DATE, description="End date in YYYY-MM-DD format."),
) -> DashboardResponse:
    validate_date_range(start_date, end_date)
    payload = await build_dashboard(start_date, end_date)
    return DashboardResponse(**payload)


@app.get("/api/accuracy")
async def accuracy(
    start_date: str = Query(DEFAULT_START_DATE, description="Start date in YYYY-MM-DD format."),
    end_date: str = Query(DEFAULT_END_DATE, description="End date in YYYY-MM-DD format."),
) -> dict[str, object]:
    validate_date_range(start_date, end_date)
    return await accuracy_for_range(start_date, end_date)


@app.get("/api/errors")
async def errors(
    start_date: str = Query(DEFAULT_START_DATE, description="Start date in YYYY-MM-DD format."),
    end_date: str = Query(DEFAULT_END_DATE, description="End date in YYYY-MM-DD format."),
    limit: int = Query(10, ge=1, le=100),
) -> dict[str, object]:
    validate_date_range(start_date, end_date)
    return await errors_for_range(start_date, end_date, limit)


@app.get("/api/forecast-history")
async def forecast_history(
    start_date: str = Query(DEFAULT_START_DATE, description="Start date in YYYY-MM-DD format."),
    end_date: str = Query(DEFAULT_END_DATE, description="End date in YYYY-MM-DD format."),
    target_time: str | None = Query(None, description="Optional target period start time in ISO-8601 format."),
) -> dict[str, object]:
    validate_date_range(start_date, end_date)
    return await forecast_history_for_target(start_date, end_date, target_time)
