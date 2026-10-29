from __future__ import annotations

import math
from typing import Any


def compute_accuracy_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_rows = [
        row for row in rows if row.get("forecast_generation") is not None and row.get("actual_generation") is not None
    ]
    missing_actual_records = sum(
        1 for row in rows if row.get("actual_generation") is None and row.get("forecast_generation") is not None
    )
    zero_actual_count = sum(
        1 for row in valid_rows if abs(float(row["actual_generation"])) < 1e-9
    )

    errors = [
        float(row["forecast_generation"]) - float(row["actual_generation"])
        for row in valid_rows
    ]
    abs_errors = [abs(value) for value in errors]
    squared_errors = [value ** 2 for value in errors]

    mae = sum(abs_errors) / len(abs_errors) if abs_errors else None
    rmse = math.sqrt(sum(squared_errors) / len(squared_errors)) if squared_errors else None
    bias = sum(errors) / len(errors) if errors else None

    mape_values = []
    for row, error in zip(valid_rows, errors):
        actual = float(row["actual_generation"])
        if abs(actual) < 1e-9:
            continue
        mape_values.append(abs(error / actual) * 100)
    mape = sum(mape_values) / len(mape_values) if mape_values else None

    coverage = (len(valid_rows) / len(rows) * 100) if rows else 0.0

    return {
        "mae_mw": mae,
        "rmse_mw": rmse,
        "bias_mw": bias,
        "mape_pct": mape,
        "matched_periods": len(valid_rows),
        "missing_actual_records": missing_actual_records,
        "missing_forecast_records": sum(
            1 for row in rows if row.get("forecast_generation") is None and row.get("actual_generation") is not None
        ),
        "zero_actual_count": zero_actual_count,
        "total_records": len(rows),
        "coverage_pct": coverage,
    }
