"""Jumia deal bot.

  python run.py get-chat-id          find your Telegram chat id
  python run.py test                 send a test message
  python run.py watch                run forever: deal alerts + sale reminders
  python run.py watch --once         run one check and exit (used by GitHub Actions)
  python run.py login                log in to Jumia in the cart helper's browser (one time)
  python run.py cart URL --at 10:00  add URL to your cart the moment the 10:00 sale opens
"""
import argparse
import logging
import time

from jumiabot.config import ROOT, load_config
from jumiabot.reminders import send_reminders
from jumiabot.state import State
from jumiabot.telegram import Telegram
from jumiabot.watcher import check_deals

log = logging.getLogger("jumiabot")


def cmd_get_chat_id(cfg, args):
    tg = Telegram(cfg["telegram_token"], None)
    chats = tg.recent_chat_ids()
    if not chats:
        print("No messages found. Open your bot in Telegram, send it 'hi', then run this again.")
    for chat_id, name in chats:
        print(f"chat id: {chat_id}   ({name})")


def cmd_test(cfg, args):
    Telegram(cfg["telegram_token"], cfg["telegram_chat_id"]).send("✅ Jumia deal bot is connected!")
    print("Sent. Check Telegram.")


def run_once(cfg, tg):
    state = State(ROOT / cfg["state_file"])
    try:
        n = send_reminders(cfg, state, tg)
        state.save()  # save straight away so a slow deal check can't cause a duplicate reminder
        n += check_deals(cfg, state, tg)
    finally:
        state.save()
    log.info("Check done, %d message(s) sent", n)


def cmd_watch(cfg, args):
    tg = Telegram(cfg["telegram_token"], cfg["telegram_chat_id"])
    if args.once:
        run_once(cfg, tg)
        return
    interval = cfg["check_interval_seconds"]
    print(f"Watching Jumia every {interval}s. Leave this window open. Ctrl+C to stop.")
    next_deal_check = 0
    while True:
        try:
            state = State(ROOT / cfg["state_file"])
            send_reminders(cfg, state, tg)
            state.save()
            if time.time() >= next_deal_check:
                check_deals(cfg, state, tg)
                state.save()
                next_deal_check = time.time() + interval
        except KeyboardInterrupt:
            raise
        except Exception:
            log.exception("Check failed, will retry")
        time.sleep(20)  # reminders are checked every 20s so they arrive on time


def cmd_login(cfg, args):
    from jumiabot.cart_helper import login

    login(cfg)


def cmd_cart(cfg, args):
    from jumiabot.cart_helper import run_cart

    tg = Telegram(cfg["telegram_token"], cfg["telegram_chat_id"]) if cfg["telegram_token"] else None
    run_cart(cfg, tg, args.url, at=args.at, give_up_minutes=args.give_up)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    ap = argparse.ArgumentParser(description="Jumia deal bot")
    ap.add_argument("--config", help="path to config.yaml")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("get-chat-id").set_defaults(fn=cmd_get_chat_id)
    sub.add_parser("test").set_defaults(fn=cmd_test)
    w = sub.add_parser("watch")
    w.add_argument("--once", action="store_true")
    w.set_defaults(fn=cmd_watch)
    sub.add_parser("login").set_defaults(fn=cmd_login)
    c = sub.add_parser("cart")
    c.add_argument("url", help="Jumia product page link")
    c.add_argument("--at", help="sale start time, 24h format e.g. 10:00 (Nigeria time)")
    c.add_argument("--give-up", type=int, default=10, help="minutes to keep trying (default 10)")
    c.set_defaults(fn=cmd_cart)

    args = ap.parse_args()
    args.fn(load_config(args.config), args)


if __name__ == "__main__":
    main()
