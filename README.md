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

1. Copy `.env.example` to `.env` (or export the variables another way).
2. Set the values that match your deployment mode:

| Variable | Required? | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | ✅ Always | Primary token used by both runners. `TELEGRAM_TOKEN` remains a legacy fallback. |
| `DEFAULT_TZ` | Optional | IANA timezone used when runners provide HH:MM deadlines. Defaults to `Asia/Singapore`. |
| `STATE_FILE` | Optional | Path for the pickle persistence file. Point this at durable storage in stateless/cloud deployments. |
| `ALERT` | Optional | When `true`, DM contacts when they’re added as alerts. Accepts `true/false`, `yes/no`, `1/0`. |
| `WEBHOOK_URL` | ✅ Webhook runner | Public HTTPS base URL Telegram should call (e.g., `https://example.com`). |
| `WEBHOOK_PATH` | Optional | Request path appended to `WEBHOOK_URL`. Defaults to `/telegram`. |
| `WEBHOOK_SECRET` | Optional | Secret token used to validate incoming webhook calls. |
| `LISTEN_ADDR` | Optional | Bind address for the webhook server. Defaults to `0.0.0.0`. |
| `PORT` | Optional | Listen port for the webhook server. Defaults to `8080`. |

> ℹ️ If you stick with long polling (`python -m bot.main`), the webhook-specific variables are ignored.

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
cp .env.example .env  # then edit the values for your deployment
python -m bot.main    # or: python -m bot.webhook
