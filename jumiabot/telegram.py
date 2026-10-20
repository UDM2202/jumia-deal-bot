"""Minimal Telegram Bot API client."""
import requests

API = "https://api.telegram.org/bot{token}/{method}"


class Telegram:
    def __init__(self, token, chat_id):
        if not token:
            raise SystemExit("No Telegram token. Put it in secrets.yaml or the TELEGRAM_BOT_TOKEN env var.")
        self.token = token
        self.chat_id = chat_id

    def _call(self, method, **params):
        r = requests.post(API.format(token=self.token, method=method), json=params, timeout=20)
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram {method} failed: {data.get('description')}")
        return data["result"]

    def send(self, text):
        if not self.chat_id:
            raise SystemExit("No chat id. Run: python run.py get-chat-id")
        return self._call(
            "sendMessage",
            chat_id=self.chat_id,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False,
        )

    def recent_chat_ids(self):
        """Chats that recently messaged the bot, as (chat_id, name) pairs."""
        seen = {}
        for update in self._call("getUpdates"):
            msg = update.get("message") or update.get("channel_post") or {}
            chat = msg.get("chat")
            if chat:
                name = chat.get("title") or " ".join(
                    filter(None, [chat.get("first_name"), chat.get("last_name")])
                )
                seen[chat["id"]] = name
        return list(seen.items())
