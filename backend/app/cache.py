import json
import hashlib
from pathlib import Path
from typing import Any

from app.config import CACHE_DIR


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def read_cache(key: str) -> Any | None:
    try:
        path = _cache_path(key)
    except OSError:
        return None
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def write_cache(key: str, payload: Any) -> None:
    try:
        path = _cache_path(key)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, default=str)
    except OSError:
        return
