"""Opens Jumia in a real browser on your PC and puts an item in your cart at sale time.

It deliberately STOPS before payment: you press the final "Confirm order" button
yourself. That keeps your account safe (Jumia's terms forbid automated purchasing)
and avoids accidental orders.
"""
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import TimeoutError as PwTimeout
from playwright.sync_api import sync_playwright

from .config import ROOT

PROFILE_DIR = ROOT / "browser-profile"
ADD_TO_CART = re.compile(r"add\s+to\s+cart|buy\s+now", re.I)


def _launch(p):
    kwargs = dict(user_data_dir=str(PROFILE_DIR), headless=False, viewport=None, args=["--start-maximized"])
    try:
        return p.chromium.launch_persistent_context(channel="chrome", **kwargs)  # your installed Chrome
    except Exception:
        return p.chromium.launch_persistent_context(**kwargs)  # Playwright's own Chromium


def login(cfg):
    """One-time: log in to Jumia in the bot's browser so later runs are already signed in."""
    with sync_playwright() as p:
        ctx = _launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(cfg["base_url"] + "/customer/account/login/")
        print("Log in to Jumia in the browser window (also save your delivery address).")
        input("When you're logged in, come back here and press Enter... ")
        ctx.close()


def _wait_until(target, tz):
    while True:
        left = (target - datetime.now(tz)).total_seconds()
        if left <= 0:
            return
        print(f"\rWaiting {int(left)}s until {target:%H:%M:%S}...   ", end="", flush=True)
        time.sleep(min(left, 1))


def run_cart(cfg, telegram, url, at=None, refresh_seconds=1.5, give_up_minutes=10):
    tz = ZoneInfo(cfg["timezone"])
    if at:
        hh, mm = map(int, at.split(":"))
        sale = datetime.now(tz).replace(hour=hh, minute=mm, second=0, microsecond=0)
        if sale < datetime.now(tz) - timedelta(minutes=give_up_minutes):
            sale += timedelta(days=1)
        _wait_until(sale - timedelta(seconds=45), tz)  # open the page a bit early
        print()

    with sync_playwright() as p:
        ctx = _launch(p)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        if at:
            _wait_until(sale, tz)
            print()

        deadline = time.time() + give_up_minutes * 60
        added = False
        while time.time() < deadline:
            btn = page.get_by_role("button", name=ADD_TO_CART).first
            try:
                if btn.is_visible(timeout=1000) and btn.is_enabled():
                    btn.click()
                    added = _confirm_added(page)
                    if added:
                        break
            except PwTimeout:
                pass
            time.sleep(refresh_seconds)
            page.reload(wait_until="domcontentloaded")

        if not added:
            msg = f"❌ Couldn't add the item to cart within {give_up_minutes} min (sold out or not live).\n{url}"
            print(msg)
            if telegram:
                telegram.send(msg)
            ctx.close()
            return False

        page.goto(cfg["base_url"] + "/cart/", wait_until="domcontentloaded")
        try:
            page.get_by_role("link", name=re.compile(r"checkout", re.I)).first.click(timeout=5000)
        except PwTimeout:
            try:
                page.get_by_role("button", name=re.compile(r"checkout", re.I)).first.click(timeout=5000)
            except PwTimeout:
                pass

        msg = "✅ Item is in your Jumia cart and checkout is open on your PC. Confirm and pay NOW!\n" + url
        print(msg)
        if telegram:
            telegram.send(msg)
        input("Finish payment in the browser, then press Enter here to close it... ")
        ctx.close()
        return True


def _confirm_added(page):
    """Jumia may pop up a size/variant picker; pick the first available option."""
    page.wait_for_timeout(800)
    popup = page.locator("[class*='popup'], [role='dialog']").filter(has=page.get_by_role("button", name=ADD_TO_CART))
    if popup.count():
        options = popup.first.locator("input[type='radio']:not([disabled]), label")
        if options.count():
            options.first.click()
            popup.first.get_by_role("button", name=ADD_TO_CART).first.click()
            page.wait_for_timeout(800)
    text = page.content().lower()
    return "added to cart" in text or "successfully added" in text or _cart_count(page) > 0


def _cart_count(page):
    try:
        badge = page.locator("[class*='cart'] [class*='badge'], #ci").first
        return int(re.sub(r"\D", "", badge.inner_text(timeout=1000)) or 0)
    except Exception:
        return 0
