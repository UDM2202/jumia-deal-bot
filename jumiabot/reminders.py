"""Sends 'sale starts in N minutes' messages based on the schedule in config.yaml."""
import html
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def due_reminders(cfg, now=None):
    """Yield (id, message) for every reminder that should go out right now."""
    rcfg = cfg.get("reminders") or {}
    if not rcfg.get("enabled", True):
        return
    tz = ZoneInfo(cfg["timezone"])
    now = now or datetime.now(tz)
    today = now.date()

    start, end = rcfg.get("active_from"), rcfg.get("active_until")
    if start and today < date.fromisoformat(str(start)):
        return
    if end and today > date.fromisoformat(str(end)):
        return

    # How late a reminder may still go out (covers GitHub Actions delays / PC sleep).
    grace = timedelta(minutes=rcfg.get("grace_minutes", 4))
    weekday = DAYS[today.weekday()]

    for event in rcfg.get("schedule", []):
        days = [d.lower()[:3] for d in event.get("days", DAYS)]
        if weekday not in days:
            continue
        for t in event["times"]:
            hh, mm = map(int, str(t).split(":"))
            start_at = datetime.combine(today, datetime.min.time(), tz).replace(hour=hh, minute=mm)
            for before in rcfg.get("minutes_before", [5]):
                send_at = start_at - timedelta(minutes=before)
                if send_at <= now < min(send_at + grace, start_at):
                    rid = f"{today}|{event['label']}|{t}|{before}"
                    msg = (
                        f"⏰ <b>{html.escape(event['label'])}</b> starts in {before} min "
                        f"({start_at:%H:%M})\n"
                    )
                    if event.get("note"):
                        msg += html.escape(event["note"]) + "\n"
                    if event.get("url"):
                        msg += event["url"]
                    yield rid, msg


def send_reminders(cfg, state, telegram, now=None):
    sent = 0
    for rid, msg in due_reminders(cfg, now):
        if rid in state.data["reminders"]:
            continue
        telegram.send(msg)
        state.data["reminders"].append(rid)
        sent += 1
    return sent
