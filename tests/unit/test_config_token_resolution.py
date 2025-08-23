import importlib
import os
from pathlib import Path
import types

def _reload_config_with_env(monkeypatch, env):
    # Clear env first, then set vars
    for k in list(os.environ.keys()):
        if k in ("BOT_TOKEN", "TELEGRAM_TOKEN"):
            monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    # Ensure we reload bot.config fresh
    if "bot.config" in list(importlib.sys.modules.keys()):
        del importlib.sys.modules["bot.config"]
    conf = importlib.import_module("bot.config")
    importlib.reload(conf)
    return conf

def test_prefers_bot_token(monkeypatch):
    conf = _reload_config_with_env(monkeypatch, {"BOT_TOKEN": "bot_token_here", "TELEGRAM_TOKEN": "legacy"})
    assert conf.TELEGRAM_TOKEN == "bot_token_here"

def test_falls_back_to_telegram_token(monkeypatch):
    conf = _reload_config_with_env(monkeypatch, {"TELEGRAM_TOKEN": "legacy"})
    assert conf.TELEGRAM_TOKEN == "legacy"

def test_missing_token(monkeypatch):
    conf = _reload_config_with_env(monkeypatch, {})
    assert conf.TELEGRAM_TOKEN == "PUT-YOUR-TOKEN-HERE"
