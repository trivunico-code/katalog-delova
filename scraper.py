"""
Katalog Delova — scraper/cache sloj
Data source: WINT REST API (eshop.wint.rs)
Cache: SQLite 24h TTL
"""
import json, time, sqlite3
import wint_api

DB_PATH = "cache.db"
TTL     = 24 * 3600

# ── Cache ──────────────────────────────────────────────────────────────────
def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, data TEXT, ts INTEGER)")
    conn.commit()
    return conn

def cache_get(key):
    with _db() as c:
        r = c.execute("SELECT data, ts FROM cache WHERE key=?", (key,)).fetchone()
        if r and (time.time() - r[1]) < TTL:
            return json.loads(r[0])
    return None

def cache_set(key, data):
    with _db() as c:
        c.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)",
                  (key, json.dumps(data, ensure_ascii=False), int(time.time())))

def cache_clear():
    with _db() as c:
        c.execute("DELETE FROM cache")

# ── API wrappers sa cacheom ────────────────────────────────────────────────

def get_makes():
    cached = cache_get("makes")
    if cached: return cached
    data = wint_api.get_makes()
    if data: cache_set("makes", data)
    return data

def get_models(make_id):
    key = f"models|{make_id}"
    cached = cache_get(key)
    if cached: return cached
    data = wint_api.get_models(make_id)
    if data: cache_set(key, data)
    return data

def get_car_types(make_id, model_id):
    key = f"types|{make_id}|{model_id}"
    cached = cache_get(key)
    if cached: return cached
    data = wint_api.get_types(make_id, model_id)
    if data: cache_set(key, data)
    return data

def get_categories(vehicle_id):
    key = f"cats|{vehicle_id}"
    cached = cache_get(key)
    if cached: return cached
    data = wint_api.get_categories(vehicle_id)
    if data: cache_set(key, data)
    return data

def get_parts(vehicle_id, cat_id, belonged_ga_ids="",
              vehicle_manufacturer="", vehicle_model="", vehicle_type=""):
    key = f"parts|{vehicle_id}|{cat_id}"
    cached = cache_get(key)
    if cached: return cached
    data = wint_api.get_parts(vehicle_id, cat_id, belonged_ga_ids,
                               vehicle_manufacturer, vehicle_model, vehicle_type)
    if data: cache_set(key, data)
    return data

def search_by_vin(vin):
    key = f"vin|{vin.upper()}"
    cached = cache_get(key)
    if cached: return cached
    vehicle_id = wint_api.search_by_vin(vin)
    if vehicle_id:
        cache_set(key, {"vehicle_id": vehicle_id})
        return {"vehicle_id": vehicle_id}
    return None

def search_by_oem(oem):
    """Direktna pretraga u CIAK-u po OEM broju (otvara CIAK login)."""
    return []
