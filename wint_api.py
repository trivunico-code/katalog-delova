"""
WINT REST API klijent — direktan HTTP, bez Playwright.
Token traje 8 sati (28800s). Auto-refresh kad istekne.
"""
import time
import requests

BASE      = "https://eshop.wint.rs/rest-sb-wt"
TOKEN_URL = "https://eshop.wint.rs/auth-server-wt/oauth/token"

WINT_USER   = "JOVANS"
WINT_PASS   = "jovan12345"
CLIENT_ID   = "eshop-web"
CLIENT_SECRET = "eshop-web-yztAhGpFW"

_token    = None
_token_ts = 0
TOKEN_TTL = 28000  # malo manje od 8h da imamo buffer

_session = requests.Session()
_session.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json",
})


def login():
    """HTTP login — vraća Bearer token za ~8 sati."""
    global _token, _token_ts
    r = _session.post(
        TOKEN_URL,
        data={
            "username":          WINT_USER,
            "password":          WINT_PASS,
            "grant_type":        "password",
            "scope":             "read write",
            "affiliate":         "wt-sb",
            "login_mode":        "NORMAL",
            "located_affiliate": "wt-sb",
        },
        auth=(CLIENT_ID, CLIENT_SECRET),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15
    )
    r.raise_for_status()
    _token    = "Bearer " + r.json()["access_token"]
    _token_ts = time.time()
    return _token


def _headers():
    global _token, _token_ts
    if not _token or (time.time() - _token_ts) > TOKEN_TTL:
        login()
    return {"Authorization": _token, "Accept": "application/json",
            "Content-Type": "application/json"}


def _get(path, params=None):
    r = _session.get(f"{BASE}{path}", headers=_headers(), params=params, timeout=15)
    if r.status_code == 401:
        login()
        r = _session.get(f"{BASE}{path}", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(path, body):
    r = _session.post(f"{BASE}{path}", headers=_headers(), json=body, timeout=15)
    if r.status_code == 401:
        login()
        r = _session.post(f"{BASE}{path}", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


# ── API metode ─────────────────────────────────────────────────────────────

def get_makes():
    data = _get("/search/vehicles/makes")
    return [{"id": m["makeId"], "name": m["make"]} for m in data if m.get("make")]


def get_models(make_id):
    data = _post("/search/vehicles/advance-aggregation", {
        "fuelType": None, "makeCode": int(make_id),
        "modelCode": None, "typeCode": None,
        "vehicleType": "pc", "yearFrom": None
    })
    models, seen = [], set()
    for series_name, series_list in (data.get("models") or {}).items():
        for m in (series_list or []):
            mid = m.get("modelId")
            if mid and mid not in seen:
                seen.add(mid)
                models.append({
                    "id":    mid,
                    "name":  m.get("model") or series_name,
                    "years": f"{_fmt(m.get('modelDateBegin'))} - {_fmt(m.get('modelDateEnd', 0)) or ''}",
                })
    return models


def get_types(make_id, model_id, size=100):
    data = _post(f"/search/vehicles/advance?page=0&size={size}", {
        "term": {"makeId": int(make_id), "modelId": int(model_id)},
        "filtering": {k: "" for k in [
            "body_type","fuel_type","zylinder","engine",
            "capacity_cc_tech","motor_code","power","drive_type",
            "vehicle_engine_code_raw","vehicle_body_type","vehicle_name","axle_type"
        ]},
        "sorting": {"field": "fulldescription", "order": "asc"},
    })
    veh = data.get("vehicles") or {}
    items = veh.get("content") if isinstance(veh, dict) else (veh if isinstance(veh, list) else [])
    types = []
    for t in (items or []):
        name = t.get("vehTypeDesc") or t.get("fulldescription") or t.get("vehicle_name") or ""
        vid  = t.get("vehicleId") or t.get("vehid") or t.get("id") or ""
        kw   = t.get("vehicle_power_kw") or ""
        ccm  = t.get("vehicle_capacity_cc_tech") or ""
        mc   = t.get("vehicle_engine_code") or ""
        fuel = t.get("vehicle_fuel_type") or ""
        db   = _fmt(t.get("vehicle_built_year_from") or 0)
        de   = _fmt(t.get("vehicle_built_year_till") or 0)
        det  = " | ".join(filter(None, [f"{db}-{de}" if db else "", f"{kw}kW" if kw else "", f"{ccm}ccm" if ccm else "", mc, fuel]))
        if name and vid:
            types.append({"id": vid, "name": name, "details": det})
    return types


def get_categories(vehicle_id):
    data = _get(f"/categories/{vehicle_id}/all", {"vehicleClass": "pc"})
    return [_parse_cat(c) for c in (data.get("ALL") or [])]


def _parse_cat(c):
    return {
        "id":            c.get("id"),
        "name":          c.get("description") or c.get("name") or "",
        "belongedGaIds": c.get("belongedGaIds") or "",
        "children":      [_parse_cat(ch) for ch in (c.get("children") or [])],
    }


def get_parts(vehicle_id, cat_id, belonged_ga_ids="",
              vehicle_manufacturer="", vehicle_model="", vehicle_type=""):
    body = {
        "genArtIdsV3": [{"cateId": cat_id, "belongedGaIds": belonged_ga_ids, "criteria": []}],
        "selectedOilIds": [], "selectedCategoryIds": [],
        "size": 100,
        "vehIds": vehicle_id,
        "selectedFromQuickClick": False,
        "vehicleClass": "pc",
        "vehicle_manufacturer": vehicle_manufacturer,
        "vehicle_model":        vehicle_model,
        "vehicle_type":         vehicle_type,
    }
    data  = _post("/search/v3/parts", body)
    parts = []
    for cat_block in data.get("articlesByCategory", []):
        for art in cat_block.get("articles", []):
            img = next((i.get("ref","") for i in (art.get("images") or []) if i.get("img_typ")=="image_300"), "")
            if not img:
                img = next((i.get("ref","") for i in (art.get("images") or [])), "")
            oe_nums = art.get("oeNumbers") or {}
            all_oe  = list({n.strip() for v in oe_nums.values() for n in v if n.strip()})
            parts.append({
                "name":    art.get("partDesc") or art.get("freetextDisplayDesc") or art.get("name") or "",
                "artnr":   art.get("artnr_display") or art.get("artnr") or "",
                "brand":   art.get("supplier") or art.get("product_brand") or "",
                "oem":     ", ".join(all_oe[:5]),
                "oe_all":  all_oe,
                "img":     img,
                "artid":   art.get("artid") or art.get("id") or "",
            })
    return parts


def search_by_vin(vin):
    try:
        data = _post("/search/vin/vehicle", {"vin": vin.strip().upper()})
        if isinstance(data, dict):
            return data.get("vehicleId") or data.get("vehicle_id") or None
    except Exception:
        pass
    return None


def _fmt(val):
    s = str(val or "")
    if len(s) == 6: return f"{s[4:6]}/{s[:4]}"
    if len(s) == 4: return s
    return ""
