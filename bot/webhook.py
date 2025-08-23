import logging
import os

from bot.main import build_app
from bot.config import TELEGRAM_TOKEN
from bot.handlers.errors import on_error

# ENV:
# WEBHOOK_URL         - full public base URL of your deployment (e.g., https://example.com)
# WEBHOOK_PATH        - request path for Telegram to call (default: /telegram)
# WEBHOOK_SECRET      - optional secret token to validate Telegram requests
# LISTEN_ADDR         - bind address (default: 0.0.0.0)
# PORT                - listen port (default: 8080)

def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )

    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PUT-YOUR-TOKEN-HERE":
        raise SystemExit(
            "Missing bot token.\n"
            "Set BOT_TOKEN in your environment or .env file (or TELEGRAM_TOKEN for backward-compat)."
        )

    base_url = os.getenv("WEBHOOK_URL")
    if not base_url:
        raise SystemExit("WEBHOOK_URL not set (e.g., https://your.domain)")

    path = os.getenv("WEBHOOK_PATH", "/telegram")
    if not path.startswith("/"):
        path = "/" + path

    secret = os.getenv("WEBHOOK_SECRET", None)
    host = os.getenv("LISTEN_ADDR", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))

    app = build_app()
    # PTB will spin an aiohttp server internally
    app.add_error_handler(on_error)

    app.run_webhook(
        listen=host,
        port=port,
        webhook_url=base_url.rstrip("/") + path,
        secret_token=secret,
    )


if __name__ == "__main__":
    main()
