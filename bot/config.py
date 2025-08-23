import os

# Bot token from environment
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN", "PUT-YOUR-TOKEN-HERE")

# Default IANA timezone for interpreting HH:MM
DEFAULT_TZ = os.environ.get("DEFAULT_TZ", "Asia/Singapore")

# Persistence filename (PicklePersistence)
PERSISTENCE_FILE = os.environ.get("STATE_FILE", "saferunner_data.pkl")
