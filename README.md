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
- Two-way sharing:
  - Runners ➜ contacts (`/link`)
  - Contacts ➜ runners (`/contactlink`)

## Config: tokens & .env
The bot reads your token from:
1) `BOT_TOKEN` (preferred), else
2) `TELEGRAM_TOKEN`, else
3) defaults to `"PUT-YOUR-TOKEN-HERE"`

## Commands
- `/contactlink` – (for contacts) generate a link you can share with runners
- `/unlink <contact_id>`     – remove that contact from your alert list
- `/contactlist`             – show your contacts
- `/blacklist list|add|remove <runner_id>`  – (for contacts) control who can alert you
- `/contactlink`             – generate a link you (a contact) can share with runners
- `/bundle <id1> <id2> ... [me]` – one link that adds multiple contacts to a runner


## Run

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
export TELEGRAM_TOKEN=123456:ABC...   # set your bot token
python -m bot.main
