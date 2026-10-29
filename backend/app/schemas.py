from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DataSourceStatus(BaseModel):
    status: Literal["ok", "unavailable", "empty"]
    message: str | None = None
    source: str | None = None
    source_url: str | None = None
    retrieval_time: str | None = None
    coverage_start: str | None = None
    coverage_end: str | None = None
    records_returned: int = 0
    valid_records: int = 0
    duplicate_records: int = 0
    missing_actual_records: int = 0
    missing_forecast_records: int = 0
    invalid_records: int = 0
    upstream_available: bool = False
    upstream_error: str | None = None
    actual_endpoint: str | None = None
    forecast_endpoint: str | None = None
    selected_cutoff_assumption: str = "Latest WINDFOR publication at or before 12:00 UTC on the day before delivery; assignment assumption, not an official purchasing deadline."


class TimeSeriesPoint(BaseModel):
    time: str
    forecast: float | None = None
    actual: float | None = None
    error: float | None = None


class AccuracyMetric(BaseModel):
    mae_mw: float | None = None
    rmse_mw: float | None = None
    bias_mw: float | None = None
    mape_pct: float | None = None
    matched_periods: int = 0
    missing_actual_records: int = 0
    missing_forecast_records: int = 0
    zero_actual_count: int = 0
    total_records: int = 0
    coverage_pct: float | None = None


class DashboardResponse(BaseModel):
    status: Literal["ok", "unavailable", "empty"]
    message: str | None = None
    source: str | None = None
    retrieval_time: str | None = None
    selected_range: str | None = None
    metadata: DataSourceStatus | None = None
    kpis: dict[str, float | int | str | None] = Field(default_factory=dict)
    series: list[TimeSeriesPoint] = Field(default_factory=list)
    accuracy: dict[str, Any] = Field(default_factory=dict)
    largest_errors: list[dict[str, Any]] = Field(default_factory=list)
    forecast_history: list[dict[str, Any]] = Field(default_factory=list)
