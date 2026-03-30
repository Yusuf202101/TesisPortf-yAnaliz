import json
import time
from pathlib import Path
from datetime import datetime

CACHE_FILE = Path("facility_cache.json")


def load_cache() -> dict | None:
    """Cache dosyası varsa yükler, yoksa None döner."""
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data
    except Exception:
        return None


def save_cache(facilities: dict) -> None:
    """Tesis listesini ve kayıt zamanını diske yazar."""
    payload = {
        "saved_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "facilities": facilities,   # {label: [org_id, uevcb_id, tesis_name]}
    }
    CACHE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def cache_info(data: dict) -> str:
    saved = data.get("saved_at", "?")
    count = len(data.get("facilities", {}))
    return f"{count} tesis — son güncelleme: {saved}"
