import requests
import time

BASE_URL = "https://seffaflik.epias.com.tr/electricity-service/v1"
TGT_URL  = "https://giris.epias.com.tr/cas/v1/tickets"

_tgt_cache = {"token": None, "ts": 0}


def get_tgt(username: str, password: str) -> str:
    now = time.time()
    if _tgt_cache["token"] and (now - _tgt_cache["ts"]) < 7000:
        return _tgt_cache["token"]
    r = requests.post(
        TGT_URL,
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code != 201:
        raise RuntimeError(f"TGT alınamadı → HTTP {r.status_code}")
    tgt = r.headers["Location"].split("/")[-1]
    _tgt_cache.update({"token": tgt, "ts": now})
    return tgt


def _headers(tgt: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "TGT": tgt,
    }


def _post(endpoint: str, payload: dict, tgt: str) -> list:
    r = requests.post(
        f"{BASE_URL}{endpoint}",
        json=payload,
        headers=_headers(tgt),
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("items", [])


def get_organizations(start: str, end: str, tgt: str) -> list:
    return _post("/generation/data/organization-list",
                 {"startDate": start, "endDate": end}, tgt)


def get_uevcb_list(org_id: int, start: str, tgt: str) -> list:
    return _post("/generation/data/uevcb-list",
                 {"organizationId": str(org_id), "startDate": start}, tgt)


def get_entso_organizations(period: str, tgt: str) -> list:
    return _post("/transmission/data/entso-w-organization",
                 {"period": period}, tgt)


def get_kudüp(org_id, uevcb_id, start: str, end: str, tgt: str) -> list:
    return _post("/generation/data/sbfgp", {
        "startDate": start, "endDate": end, "region": "TR1",
        "organizationId": str(org_id), "uevcbId": str(uevcb_id),
    }, tgt)


def get_kgüp(org_id, uevcb_id, start: str, end: str, tgt: str) -> list:
    return _post("/generation/data/dpp", {
        "startDate": start, "endDate": end, "region": "TR1",
        "organizationId": str(org_id), "uevcbId": str(uevcb_id),
    }, tgt)


def get_uevm(pp_id, start: str, end: str, tgt: str) -> list:
    return _post("/generation/data/injection-quantity", {
        "startDate": start, "endDate": end,
        "powerplantId": str(pp_id),
    }, tgt)


def items_to_series(items: list, value_key: str = "toplam") -> dict:
    result = {}
    for it in items:
        date_str = it["date"][:10]
        hour_val = it.get("time") or f"{it.get('hour', 0):02d}:00"
        result[f"{date_str} {hour_val}"] = it.get(value_key, 0)
    return result
