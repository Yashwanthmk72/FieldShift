# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Chromium tests against tests/frontend/mock_api.py (a STAND-IN for the FastAPI app, which cannot be installed here).
Verifies the real frontend code in a real browser; it does NOT verify the real backend."""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import seed  # noqa: E402


def start(port, xss=False):
    env = {**os.environ, "MOCK_XSS": "1" if xss else ""}
    p = subprocess.Popen([sys.executable, str(Path(__file__).parent / "mock_api.py"), str(port)], env=env, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1); return p
        except Exception:
            time.sleep(0.2)
    p.kill(); raise RuntimeError("mock server did not start")


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch(); yield b; b.close()


def open_app(browser, base, route="#overview", mobile=False):
    ctx = browser.new_context(viewport={"width": 390, "height": 800} if mobile else {"width": 1280, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('fs-workspace','{seed.WS}')")
    page = ctx.new_page()
    errors, dialogs = [], []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.route("**/unpkg.com/**", lambda r: r.abort()); page.route("**/fonts.*/**", lambda r: r.abort())  # CDN is unreachable offline; irrelevant to these checks
    page.goto(base + "/" + route)
    return page, errors, dialogs


def ignorable(e):
    return any(s in e for s in ("ERR_FAILED", "ERR_BLOCKED", "Failed to load resource", "maplibregl", "net::"))


def test_app_loads_and_crop_advisor_profit_control_is_inert(browser):
    srv = start(8791)
    try:
        base = "http://127.0.0.1:8791"
        farm = seed.seed_field(base)
        page, errors, _ = open_app(browser, base, f"#crops")
        page.wait_for_timeout(1500)
        page.evaluate(f"location.hash = '#field/{farm['id']}'"); page.wait_for_timeout(800)
        page.evaluate("location.hash = '#crops'"); page.wait_for_timeout(1200)
        assert page.locator(".crop-card").count() >= 27
        assert page.locator("[data-sw=profit]").count() == 0 and page.locator("[data-row=profit]").count() == 0  # v0.7: the Yield & value slider is hidden (no real yield data)
        assert page.locator(".crop-card .conf").count() >= 27 and page.locator(".crop-card .badge-illus").count() >= 27  # confidence + illustrative badge on every recommendation
        top_before = page.locator(".crop-card").first.get_attribute("data-crop")
        page.locator("[data-rg=resilience]").first.evaluate("e => { e.value = 100; e.dispatchEvent(new Event('input')) }")
        assert page.locator(".crop-card").count() >= 27 and top_before
        assert [e for e in errors if not ignorable(e)] == []
        page.close()
    finally:
        srv.kill()


def test_xss_probe_in_every_server_string_does_not_execute(browser):
    srv = start(8792, xss=True)
    try:
        base = "http://127.0.0.1:8792"
        farm = seed.seed_field(base, name="<img src=x onerror=window.__pwned=1>")
        page, errors, dialogs = open_app(browser, base, "#overview")
        page.wait_for_timeout(1200)
        for route in ("#overview", "#fields", f"#field/{farm['id']}", "#crops", "#rotation", "#management", "#settings"):
            page.evaluate(f"location.hash = '{route}'"); page.wait_for_timeout(700)
        page.evaluate("location.hash = '#crop/maize'"); page.wait_for_timeout(900)
        assert page.evaluate("window.__pwned") is None and dialogs == []
        assert page.locator("img[src='x']").count() == 0
        page.close()
    finally:
        srv.kill()


def test_mobile_viewport_has_no_horizontal_scroll(browser):
    srv = start(8793)
    try:
        page, _, _ = open_app(browser, "http://127.0.0.1:8793", "#overview", mobile=True)
        page.wait_for_timeout(1200)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.close()
    finally:
        srv.kill()


def test_v07_pages_render_without_console_errors(browser):
    """Market, Climate, Accuracy, Credits and the crop risks panel, against the stand-in server with fixture data (not live data)."""
    srv = start(8793)
    try:
        base = "http://127.0.0.1:8793"
        farm = seed.seed_field(base)
        page, errors, _ = open_app(browser, base, "#market")
        page.wait_for_selector(".mk-card", timeout=8000)
        txt = page.locator("#marketBody").inner_text()
        assert "monthly" in txt and "live" not in page.locator(".fresh").first.inner_text().lower() and "no data" in txt.lower()
        assert page.locator(".ticker .tick").count() >= 1 and page.locator("[data-chart] svg").count() >= 1
        page.select_option("#mkCur", "INR"); page.wait_for_timeout(300)
        assert "INR" in page.locator(".mk-price").first.inner_text()
        page.fill("#gvArea", "2"); page.fill("#gvYield", "3"); page.click("#gvGo"); page.wait_for_selector("#gvOut .kv", timeout=5000)
        assert "NOT profit" in page.locator("#gvOut").inner_text() or "not profit" in page.locator("#gvOut").inner_text().lower()
        page.evaluate(f"location.hash = '#field/{farm['id']}'"); page.wait_for_timeout(600)
        page.evaluate("location.hash = '#climate'"); page.wait_for_selector("#chTemp svg", timeout=8000)
        ct = page.locator("#climateBody").inner_text()
        assert "~50 km" in ct and "lags real time" in ct
        page.evaluate("location.hash = '#accuracy'"); page.wait_for_timeout(300)
        assert "No yield guarantee" in page.locator("#accuracyBody").inner_text()
        page.evaluate("location.hash = '#credits'"); page.wait_for_selector(".src-grid", timeout=5000)
        assert "NASA POWER" in page.locator("#creditsBody").inner_text() and "IMF" in page.locator("#creditsBody").inner_text()
        page.evaluate("location.hash = '#crop/tomato'"); page.wait_for_function("document.querySelector('#risksCard')?.innerText.toLowerCase().includes('could make this advice wrong')", timeout=10000)  # v0.8: wait for the text, not just the element (was flaky under load)
        rt = page.locator("#risksCard").inner_text().lower()
        assert "risks" in rt and "could make this advice wrong" in rt and "price volatility" in rt
        assert [e for e in errors if not ignorable(e)] == []
        page.close()
    finally:
        srv.kill()


NEW_VIEWS = ("#weather", "#irrigation", "#soilhealth", "#pests", "#finance")


def test_v08_screens_render_with_real_content_and_no_console_errors(browser):
    """Overview dashboard + Weather, Irrigation, Soil health, Pests, Finance against the stand-in server (fixture data, not live)."""
    srv = start(8794)
    try:
        base = "http://127.0.0.1:8794"
        farm = seed.seed_field(base)
        page, errors, _ = open_app(browser, base, f"#field/{farm['id']}")
        page.wait_for_timeout(1200)
        # dashboard cards on the overview
        page.evaluate("location.hash = '#overview'"); page.wait_for_selector("#dashWx .kv", timeout=8000)
        ov = page.locator("#overviewBody").inner_text()
        assert "CROP SUITABILITY" in ov and "not</strong> a measure of field health" not in ov and "not a measure of field health" in ov
        assert "POWERED BY NASA POWER" in ov and page.locator(".donut-svg").count() >= 1 and page.locator("#dashWet svg").count() == 1
        assert "field health" in ov.lower() and "forecast" in page.locator("#dashWx").inner_text().lower()
        # weather
        page.evaluate("location.hash = '#weather'"); page.wait_for_selector("#wxTemp svg", timeout=8000)
        assert "Forecast, not observation" in page.locator("#weatherBody").inner_text() and "real-time" in page.locator("#weatherBody").inner_text()
        # irrigation (editable assumptions)
        page.evaluate("location.hash = '#irrigation'"); page.wait_for_selector("#irrChart svg", timeout=8000)
        t = page.locator("#irrigationBody").inner_text()
        assert "ASSUMPTIONS" in t and page.locator("#irRoot").count() == 1 and page.locator("#irDep").count() == 1 and "TOTAL AVAILABLE WATER" in t
        page.fill("#irRoot", "0.9"); page.click("#irRun"); page.wait_for_function("document.querySelector('#irrResult').innerText.includes('0.9')", timeout=8000)
        # soil health
        page.evaluate("location.hash = '#soilhealth'"); page.wait_for_selector(".lim, #shBody .kv", timeout=8000)
        t = page.locator("#soilhealthBody").inner_text()
        assert "Nitrogen, phosphorus, potassium, salinity" in t and "SOIL SAMPLING PLAN" in t and "not estimated" in t
        # pests
        page.evaluate("location.hash = '#pests'"); page.wait_for_selector("#pestCrop", timeout=8000)
        assert "not diagnoses" in page.locator("#pestsBody").inner_text()
        # finance: empty inputs are reported as missing, never guessed; then a full calculation
        page.evaluate("location.hash = '#finance'"); page.wait_for_selector("#fCalc", timeout=8000)
        page.click("#fCalc"); page.wait_for_selector("#finResult .kv", timeout=8000)
        assert "missing" in page.locator("#finResult").inner_text().lower() and "\u2014" in page.locator("#finResult").inner_text()
        page.fill("#fYield", "3"); page.fill("#fPrice", "250")
        for k in ("seed", "fertilizer", "soil_prep", "irrigation", "labour", "pesticide", "machinery", "transport", "other"):
            page.fill(f"#fc_{k}", "50")
        page.click("#fCalc"); page.wait_for_function("document.querySelector('#finResult').innerText.includes('SCENARIOS')", timeout=8000)
        ft = page.locator("#finResult").inner_text()
        assert "300" in ft and "ASSUMPTION" in ft.upper() and "Illustrative simulation" in ft  # net profit 3*250-450 = 300 per ha
        page.click("#fSave"); page.wait_for_selector("[data-del]", timeout=8000)
        assert [e for e in errors if not ignorable(e)] == []
        page.close()
    finally:
        srv.kill()


def test_v08_screens_survive_xss_probe_and_fit_mobile(browser):
    srv = start(8795, xss=True)
    try:
        base = "http://127.0.0.1:8795"
        farm = seed.seed_field(base, name="<img src=x onerror=window.__pwned=1>")
        page, errors, dialogs = open_app(browser, base, f"#field/{farm['id']}", mobile=True)
        page.wait_for_timeout(1200)
        for route in ("#overview",) + NEW_VIEWS:
            page.evaluate(f"location.hash = '{route}'"); page.wait_for_timeout(1500)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), route
        page.evaluate("location.hash = '#finance'"); page.wait_for_selector("#fCalc", timeout=8000); page.click("#fCalc"); page.wait_for_timeout(800); page.click("#fSave"); page.wait_for_timeout(800)
        assert page.evaluate("window.__pwned") is None and dialogs == [] and page.locator("img[src='x']").count() == 0
        page.close()
    finally:
        srv.kill()
