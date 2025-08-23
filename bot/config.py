import os

# Bot token from environment
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN", "PUT-YOUR-TOKEN-HERE")

# Default IANA timezone for interpreting HH:MM
DEFAULT_TZ = os.environ.get("EXGUARD_DEFAULT_TZ", "Asia/Singapore")

# Persistence filename (PicklePersistence)
PERSISTENCE_FILE = os.environ.get("EXGUARD_STATE_FILE", "exercise_guard_data.pkl")
