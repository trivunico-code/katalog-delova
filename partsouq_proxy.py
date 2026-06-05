"""
Partsouq.com screenshot proxy — koristi pravi Chrome (headless=False ali minimiziran),
zaobilazi Cloudflare challenge. Thread-safe via Lock.
"""
import threading, base64, time
from playwright.sync_api import sync_playwright

PARTSOUQ = "https://partsouq.com"

_lock   = threading.Lock()
_pw     = None
_browser= None
_page   = None
_ready  = False

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")


def _init():
    global _pw, _browser, _page, _ready
    for obj in (_browser, _pw):
        try:
            if obj:
                if hasattr(obj, 'close'):
                    obj.close()
                elif hasattr(obj, 'stop'):
                    obj.stop()
        except Exception:
            pass

    import os
    # Trajni Chrome profil — cookies se pamte, Cloudflare pamti browser
    profile_dir = os.path.join(os.path.dirname(__file__), "chrome_profile")
    os.makedirs(profile_dir, exist_ok=True)

    _pw = sync_playwright().start()

    try:
        _browser = _pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            channel="chrome",
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--window-position=300,100",
                "--window-size=1000,700",
            ],
            user_agent=UA,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        # launch_persistent_context vraća context direktno, ne browser
        ctx = _browser
        _browser = None   # nije nam potreban
    except Exception:
        # Fallback: headless Chromium bez trajnog profila
        _browser = _pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = _browser.new_context(
            user_agent=UA,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
    ctx.add_init_script("""
        delete Object.getPrototypeOf(navigator).webdriver;
        Object.defineProperty(navigator, 'webdriver',  {get: () => undefined});
        Object.defineProperty(navigator, 'plugins',    {get: () => [1,2,3,4,5]});
        Object.defineProperty(navigator, 'languages',  {get: () => ['en-US','en']});
        window.chrome = {runtime:{}};
    """)
    _page  = ctx.new_page()
    _page.on("dialog", lambda d: d.accept())
    _ready = True


def _ensure():
    global _ready
    if not _ready or _page is None:
        _init()
        return
    try:
        # Provjeri je li browser još živ
        _ = _page.url
        _page.evaluate("() => 1")   # prazna provjera konekcije
    except Exception:
        _ready = False
        _init()


def _wait_cf(max_sec=25):
    """Čeka dok Cloudflare challenge ne prođe (max max_sec sekundi)."""
    deadline = time.time() + max_sec
    cf_texts = ["just a moment", "security check", "verification",
                "checking", "please wait", "cf-browser-verification"]
    while time.time() < deadline:
        try:
            title = _page.title().lower()
            body  = _page.evaluate(
                "() => (document.body && document.body.innerText || '').toLowerCase().slice(0,500)"
            )
            if any(x in title or x in body for x in cf_texts):
                time.sleep(0.8)
            else:
                break
        except Exception:
            break
    time.sleep(1.2)


def _shot():
    raw = _page.screenshot(type="jpeg", quality=85, full_page=False)
    return base64.b64encode(raw).decode()


# ── Public API ─────────────────────────────────────────────────────────────

def search_vin(vin: str) -> dict:
    with _lock:
        _ensure()
        vin = vin.strip().upper()

        # Partsouq search URL: /en/search/all?q={VIN}
        url = f"{PARTSOUQ}/en/search/all?q={vin}"
        _page.goto(url, wait_until="domcontentloaded", timeout=40000)
        _wait_cf()
        time.sleep(1.5)

        return {"img": _shot(), "url": _page.url}


def screenshot() -> dict:
    with _lock:
        _ensure()
        return {"img": _shot(), "url": _page.url}


def click_at(x_pct: float, y_pct: float) -> dict:
    with _lock:
        _ensure()
        vp = _page.viewport_size
        _page.mouse.click(int(x_pct * vp["width"]), int(y_pct * vp["height"]))
        time.sleep(1.8)
        try:
            _page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        _wait_cf(8)
        return {"img": _shot(), "url": _page.url}


def go_back() -> dict:
    with _lock:
        _ensure()
        try:
            _page.go_back(wait_until="domcontentloaded", timeout=10000)
        except Exception:
            pass
        time.sleep(1.0)
        return {"img": _shot(), "url": _page.url}


def navigate_and_shot(url: str) -> dict:
    with _lock:
        _ensure()
        _page.goto(url, wait_until="domcontentloaded", timeout=40000)
        _wait_cf()
        return {"img": _shot(), "url": _page.url}
