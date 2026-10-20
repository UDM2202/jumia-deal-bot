# Jumia Deal Bot 🛒

A Telegram bot for Jumia Nigeria's Black Friday sales. It does three things:

1. **Deal alerts.** It watches Jumia for the phones, laptops and wares you want and messages you when one matches your price or discount rules, or drops further in price.
2. **Sale reminders.** It messages you 5 minutes and 1 minute before every flash sale and treasure hunt.
3. **Cart helper (on your Windows PC).** At sale time it opens Jumia, keeps refreshing until "Add to cart" goes live, adds the item, opens checkout and pings you on Telegram. **You press the final pay button yourself.** It never pays on its own, because Jumia's terms ban automated buying and an auto-checkout could get your account blocked.

---

## Step 1: Create your Telegram bot (2 minutes)

1. Open Telegram and search for **@BotFather** (it has a blue tick).
2. Tap **Start**, then send `/newbot`.
3. BotFather asks for a **name**. Type anything, e.g. `My Jumia Deals`.
4. It then asks for a **username**, which must end in `bot`, e.g. `daniel_jumia_deals_bot`.
5. BotFather replies with a **token** that looks like `7123456789:AAHk3x...`. **Copy it and keep it secret.** Anyone with it can control your bot.
6. Tap the link BotFather gives you (`t.me/your_bot_name`) to open your new bot, press **Start**, and send it `hi`. The bot can only message you after you've messaged it first.

## Step 2: Set it up on your Windows PC

1. Install **Python 3.12** from https://www.python.org/downloads/. On the first installer screen, **tick "Add python.exe to PATH"**.
2. On this GitHub page, click the green **Code** button → **Download ZIP**, then unzip it, e.g. to `Documents\jumia-deal-bot`.
3. Double-click **`setup.bat`** and wait for it to finish. It takes a few minutes.
4. Open **`secrets.yaml`** with Notepad and paste your token between the quotes after `telegram_token:`. Save.
5. In the folder, click the address bar, type `cmd` and press Enter. In the black window, run:
   ```
   .venv\Scripts\activate
   python run.py get-chat-id
   ```
   It prints a number like `chat id: 123456789`. Paste that number into `secrets.yaml` after `telegram_chat_id:` and save.
6. Test it with `python run.py test`. You should get "✅ Jumia deal bot is connected!" on Telegram.

## Step 3: Choose what to watch

Open **`config.yaml`** in Notepad. It comes with watches for iPhones, Samsung phones, laptops and kitchen wares. Change the prices and discounts to suit you:

```yaml
  - name: Samsung deal
    query: samsung galaxy phone     # what to type in Jumia's search
    include: [samsung]              # name must contain these words
    exclude: *accessories           # skip cases, chargers, etc.
    max_price: 600000               # alert at ₦600k or less...
    min_discount: 30                # ...and at least 30% off
```

To add another item, copy a block and edit it. Keep the spacing exactly as it is, because YAML cares about indentation.

**Before the sale starts:** when Jumia announces its 2026 Black Friday times, update the `reminders → schedule` section. The current times are from the 2025 schedule.

## Step 4: Run the watcher

Double-click **`start_watcher.bat`** and leave the window open. It checks Jumia every 2 minutes and sends reminders on time. If it crashes, it restarts by itself.

> Tip: to start it automatically when your PC turns on, press `Win + R`, type `shell:startup`, press Enter, and put a shortcut to `start_watcher.bat` in that folder. Also set your PC never to sleep while it's plugged in (Settings → System → Power).

## Step 5: Use the cart helper on sale day

1. **One time only:** in the cmd window (with `.venv\Scripts\activate` done), run `python run.py login`. Log in to Jumia in the browser that opens, make sure your **delivery address** and **phone number** are saved, then press Enter in the cmd window.
2. When you see the item you want in the upcoming flash sale, double-click **`grab_item.bat`**. Paste the product link and the sale start time, e.g. `14:00`.
3. Leave it running. It opens the page about 45 seconds early, then keeps refreshing until "Add to cart" appears and clicks it. Next it opens checkout and sends you a Telegram message: **finish payment straight away.** If the item has sizes or colours, it picks the first available one.

You can run several `grab_item.bat` windows for different items, but don't run so many that Jumia sees it as abuse.

## Optional: cloud alerts while your PC is off

The repo includes a GitHub Actions job (`.github/workflows/watch.yml`). It runs the deal check and reminders every 15 minutes, from 7am to 11pm Nigeria time, even when your PC is off.

To switch it on:

1. On GitHub, open the repo, then go to **Settings → Secrets and variables → Actions → New repository secret**.
2. Add `TELEGRAM_BOT_TOKEN` with your token as the value.
3. Add `TELEGRAM_CHAT_ID` with your chat id as the value.
4. Go to the **Actions** tab and enable workflows if GitHub asks. Then press **Run workflow** once to test it.

Notes:
- GitHub often starts scheduled jobs a few minutes late, so the **PC watcher is the reliable one** for reminders.
- Private repos get 2,000 free Action minutes a month. This schedule uses about 1,900, so don't make it more frequent unless you make the repo public.
- Jumia may block GitHub's servers. If the Actions log shows `403` errors, rely on the PC watcher.
- After the sale, disable the job: **Actions → Jumia deal watch → ⋯ → Disable workflow**.

## Being realistic

- Flash-sale stock is tiny, sometimes 5 to 20 units, and thousands of people are trying. The bot gives you a fast start, not a guarantee.
- The bot reads Jumia's public pages like a normal browser and waits between page loads. Don't lower `check_interval_seconds` below 60. Hammering the site gets your connection blocked.
- If alerts stop arriving and the window shows `0 products scanned`, Jumia has probably changed its page layout. The fix goes in `jumiabot/scraper.py`.

## Commands

| Command | What it does |
|---|---|
| `python run.py get-chat-id` | Show your Telegram chat id |
| `python run.py test` | Send a test message |
| `python run.py watch` | Run alerts and reminders until you close it |
| `python run.py watch --once` | Run one check and stop |
| `python run.py login` | Log in to Jumia in the helper's browser |
| `python run.py cart LINK --at 14:00` | Grab an item at 2pm |
| `python -m pytest` | Run the tests (needs `pip install pytest`) |
