from bot.utils.links import build_deep_link, build_webhook_url


def test_build_deep_link():
    url = build_deep_link("@MyBot", 12345)
    assert url == "https://t.me/MyBot?start=link_12345"


def test_build_webhook_url():
    assert build_webhook_url("https://host", "path") == "https://host/path"
    assert build_webhook_url("https://host/", "/path") == "https://host/path"
