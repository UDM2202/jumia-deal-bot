"""Loads config.yaml plus the Telegram secrets (from secrets.yaml or env vars)."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path=None):
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    secrets = {}
    secrets_path = ROOT / "secrets.yaml"
    if secrets_path.exists():
        with open(secrets_path, encoding="utf-8") as f:
            secrets = yaml.safe_load(f) or {}

    cfg["telegram_token"] = os.environ.get("TELEGRAM_BOT_TOKEN") or secrets.get("telegram_token", "")
    cfg["telegram_chat_id"] = str(os.environ.get("TELEGRAM_CHAT_ID") or secrets.get("telegram_chat_id", "")).strip()
    cfg.setdefault("timezone", "Africa/Lagos")
    cfg.setdefault("base_url", "https://www.jumia.com.ng")
    cfg.setdefault("check_interval_seconds", 120)
    cfg.setdefault("state_file", "state.json")
    return cfg
