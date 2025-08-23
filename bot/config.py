import os
from pathlib import Path

# Load .env early so other modules see variables on import.
# We try a few reasonable locations:
#   - <repo>/.env
#   - <repo>/.env/.env
#   - any .env discoverable via current working dir
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
except Exception:
    load_dotenv = None
    find_dotenv = None

def _load_env_files():
    if load_dotenv is None:
        return
    # 1) discover via CWD
    found = find_dotenv(usecwd=True) if find_dotenv else ""
    if found:
        load_dotenv(found)  # does not override existing env by default

    # 2) explicit repo-root paths relative to this file
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root / ".env",          # standard .env file in root
        repo_root / ".env" / ".env", # if user placed a .env *folder* containing a .env file
        repo_root / ".env" / "local.env",
        repo_root / ".env" / "dev.env",
    ]
    for p in candidates:
        if p.is_file():
            load_dotenv(p, override=False)

_load_env_files()

# ---------- Config values ----------

# Token resolution order:
# 1) BOT_TOKEN (your stated var)
# 2) TELEGRAM_TOKEN (legacy/alt name)
# Fallback: "PUT-YOUR-TOKEN-HERE"
TELEGRAM_TOKEN = (
    os.environ.get("BOT_TOKEN")
    or os.environ.get("TELEGRAM_TOKEN")
    or "PUT-YOUR-TOKEN-HERE"
)

# Default IANA timezone for interpreting HH:MM
DEFAULT_TZ = os.environ.get("DEFAULT_TZ", "Asia/Singapore")

# Persistence filename (PicklePersistence)
PERSISTENCE_FILE = os.environ.get("STATE_FILE", "saferunner_data.pkl")
