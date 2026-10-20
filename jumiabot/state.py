"""Remembers what has already been alerted so you don't get the same message twice."""
import json
from pathlib import Path


class State:
    def __init__(self, path):
        self.path = Path(path)
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}
        self.data.setdefault("deals", {})
        self.data.setdefault("reminders", [])

    def save(self):
        # keep the reminder log small
        self.data["reminders"] = self.data["reminders"][-500:]
        self.path.write_text(json.dumps(self.data, indent=1), encoding="utf-8")
