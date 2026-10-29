import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT_DIR / ".cache"
load_dotenv(ROOT_DIR.parent / ".env")

DEFAULT_START_DATE = os.getenv("DEFAULT_START_DATE", "2026-01-01")
DEFAULT_END_DATE = os.getenv("DEFAULT_END_DATE", "2026-01-31")
ELEXON_BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1").rstrip("/")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
FORECAST_CUTOFF_UTC_HOUR = int(os.getenv("FORECAST_CUTOFF_UTC_HOUR", "12"))

if not 0 <= FORECAST_CUTOFF_UTC_HOUR <= 23:
    raise ValueError("FORECAST_CUTOFF_UTC_HOUR must be between 0 and 23")

ELEXON_DATASETS = ("FUELHH", "WINDFOR")
