# Saferunners Bot

Telegram bot that tracks an exercise session’s end time & location and alerts
your chosen contacts if you don’t mark yourself as completed by the deadline.
No group chat required.

## Features
- Shareable deep link for **safety contacts** (`/link`).
- Start session with **GPS pin or text location** (`/begin`).
- Set end time via quick buttons or **HH:MM** custom input.
- One-tap **Complete ✅** button.
- Automatic **DM alerts** to contacts if you don’t check in.

## Config: tokens & .env
The bot reads your token from:
1) `BOT_TOKEN` (preferred), else
2) `TELEGRAM_TOKEN`, else
3) defaults to `"PUT-YOUR-TOKEN-HERE"`

## Run

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export TELEGRAM_TOKEN=123456:ABC...   # set your bot token
python -m bot.main
