def build_deep_link(bot_username: str, owner_id: int) -> str:
    username = bot_username.lstrip("@")
    return f"https://t.me/{username}?start=link_{owner_id}"


def build_webhook_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path
