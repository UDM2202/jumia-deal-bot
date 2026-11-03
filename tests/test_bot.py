from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jumiabot.reminders import due_reminders, send_reminders
from jumiabot.scraper import parse_listing, parse_naira
from jumiabot.state import State
from jumiabot.watcher import check_deals, matches

FIXTURE = (Path(__file__).parent / "fixtures" / "listing.html").read_text(encoding="utf-8")
BASE = "https://www.jumia.com.ng"
TZ = ZoneInfo("Africa/Lagos")


class FakeTelegram:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)


def test_parse_naira():
    assert parse_naira("₦ 1,050,000") == 1050000
    assert parse_naira("₦ 189,000 - ₦ 210,000") == 189000
    assert parse_naira("") is None


def test_parse_listing():
    products = parse_listing(FIXTURE, BASE)
    assert len(products) == 3
    iphone, case, samsung = products
    assert iphone.key == "AP123MP4567NAFAMZ"
    assert iphone.url == BASE + "/apple-iphone-15-128gb-black-301234567.html"
    assert (iphone.price, iphone.old_price, iphone.discount) == (1050000, 1500000, 30)
    assert samsung.discount is None and samsung.effective_discount == 37
    assert samsung.items_left == 3


def test_matches_filters_accessories_and_price():
    iphone, case, samsung = parse_listing(FIXTURE, BASE)
    rule = {"include": ["iphone"], "exclude": ["case"], "min_price": 150000, "max_price": 1100000, "min_discount": 30}
    assert matches(iphone, rule)
    assert not matches(case, rule)
    assert not matches(iphone, {**rule, "max_price": 900000})
    assert not matches(samsung, rule)


def test_reminders_fire_once_in_window(tmp_path):
    cfg = {
        "timezone": "Africa/Lagos",
        "reminders": {
            "active_from": "2026-10-30",
            "active_until": "2026-11-30",
            "minutes_before": [5, 1],
            "schedule": [{"label": "Flash", "days": ["fri"], "times": ["10:00"], "url": "u"}],
        },
    }
    fri = datetime(2026, 11, 27, 9, 56, tzinfo=TZ)
    assert [r for r, _ in due_reminders(cfg, fri)] == ["2026-11-27|Flash|10:00|5"]
    assert list(due_reminders(cfg, datetime(2026, 11, 27, 9, 50, tzinfo=TZ))) == []
    assert list(due_reminders(cfg, datetime(2026, 11, 26, 9, 56, tzinfo=TZ))) == []  # Thursday
    assert list(due_reminders(cfg, datetime(2026, 12, 4, 9, 56, tzinfo=TZ))) == []  # after campaign

    state, tg = State(tmp_path / "s.json"), FakeTelegram()
    assert send_reminders(cfg, state, tg, fri) == 1
    assert send_reminders(cfg, state, tg, fri) == 0  # no duplicate


def test_check_deals_alerts_once_then_on_price_drop(tmp_path, monkeypatch):
    html = {"v": FIXTURE}
    monkeypatch.setattr("jumiabot.scraper.JumiaClient._get", lambda self, url: html["v"] if "page=1" in url else "")
    cfg = {
        "base_url": BASE,
        "request_delay_seconds": 0,
        "watches": [{"name": "iPhone", "query": "iphone", "include": ["iphone"], "exclude": ["case"], "min_discount": 20}],
    }
    state, tg = State(tmp_path / "s.json"), FakeTelegram()
    assert check_deals(cfg, state, tg) == 1
    assert "Apple iPhone 15" in tg.sent[0] and "₦1,050,000" in tg.sent[0]
    assert check_deals(cfg, state, tg) == 0
    html["v"] = FIXTURE.replace("₦ 1,050,000", "₦ 990,000")
    assert check_deals(cfg, state, tg) == 1


def test_dated_midnight_event_reminds_the_night_before():
    cfg = {
        "timezone": "Africa/Lagos",
        "reminders": {
            "active_from": "2026-10-30",
            "active_until": "2026-11-30",
            "minutes_before": [5],
            "schedule": [{"label": "Explosion", "dates": ["2026-11-06"], "times": ["00:00"]}],
        },
    }
    assert [r for r, _ in due_reminders(cfg, datetime(2026, 11, 5, 23, 56, tzinfo=TZ))] == ["2026-11-06|Explosion|00:00|5"]
    assert list(due_reminders(cfg, datetime(2026, 11, 12, 23, 56, tzinfo=TZ))) == []  # not a listed date


def test_shipped_config_loads_and_has_7pm_reminder():
    from jumiabot.config import load_config

    cfg = load_config()
    msgs = [m for _, m in due_reminders(cfg, datetime(2026, 11, 4, 18, 55, tzinfo=TZ))]
    assert any("Grab it" in m for m in msgs)
