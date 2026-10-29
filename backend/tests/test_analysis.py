import math

import pandas as pd

from app.forecast_selection import select_eligible_forecast
from app.metrics import compute_accuracy_metrics


def test_forecast_before_cutoff_is_selected():
    target = pd.Timestamp("2026-01-01T00:30:00+00:00")
    cutoff = pd.Timestamp("2026-01-01T12:00:00+00:00")
    forecasts = [
        {"startTime": target, "publishTime": pd.Timestamp("2026-01-01T06:00:00+00:00"), "generation": 120.0},
        {"startTime": target, "publishTime": pd.Timestamp("2026-01-01T11:30:00+00:00"), "generation": 140.0},
    ]
    selected = select_eligible_forecast(forecasts, target, cutoff)
    assert selected is not None
    assert selected["generation"] == 140.0


def test_late_forecast_after_cutoff_is_excluded():
    target = pd.Timestamp("2026-01-01T01:00:00+00:00")
    cutoff = pd.Timestamp("2026-01-01T12:00:00+00:00")
    forecasts = [
        {"startTime": target, "publishTime": pd.Timestamp("2026-01-01T13:00:00+00:00"), "generation": 140.0},
        {"startTime": target, "publishTime": pd.Timestamp("2026-01-01T11:00:00+00:00"), "generation": 110.0},
    ]
    selected = select_eligible_forecast(forecasts, target, cutoff)
    assert selected is not None
    assert selected["generation"] == 110.0


def test_metrics_calculate_mae_rmse_bias_and_mape():
    rows = [
        {"forecast_generation": 100.0, "actual_generation": 90.0},
        {"forecast_generation": 80.0, "actual_generation": 100.0},
        {"forecast_generation": 0.0, "actual_generation": 0.0},
    ]
    metrics = compute_accuracy_metrics(rows)
    assert metrics["mae_mw"] == 10.0
    assert math.isclose(metrics["rmse_mw"], 12.909944487358056, rel_tol=1e-9, abs_tol=1e-9)
    assert metrics["bias_mw"] == -3.3333333333333335
    assert math.isclose(metrics["mape_pct"], 15.555555555555557, rel_tol=1e-9, abs_tol=1e-9)
    assert metrics["matched_periods"] == 3
    assert metrics["zero_actual_count"] == 1


def test_missing_actuals_are_excluded():
    rows = [
        {"forecast_generation": 90.0, "actual_generation": 80.0},
        {"forecast_generation": 50.0, "actual_generation": None},
    ]
    metrics = compute_accuracy_metrics(rows)
    assert metrics["matched_periods"] == 1
    assert metrics["missing_actual_records"] == 1
    assert metrics["mae_mw"] == 10.0


def test_mape_is_undefined_when_every_actual_is_zero():
    metrics = compute_accuracy_metrics([
        {"forecast_generation": 0.0, "actual_generation": 0.0},
        {"forecast_generation": 5.0, "actual_generation": 0.0},
    ])

    assert metrics["matched_periods"] == 2
    assert metrics["zero_actual_count"] == 2
    assert metrics["mape_pct"] is None
