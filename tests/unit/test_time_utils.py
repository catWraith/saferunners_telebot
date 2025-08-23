from datetime import datetime, timezone, timedelta
from pytz import timezone as pytz_timezone

from bot.utils.time_utils import parse_hhmm, local_hhmm_to_future_dt, to_utc, delay_seconds_from_utc_deadline, is_valid_tz


def test_parse_hhmm_ok():
    assert parse_hhmm("00:00") == (0, 0)
    assert parse_hhmm("23:59") == (23, 59)
#    assert parse_hhmm("7:05") is None  # require 2-digit HH
#    assert parse_hhmm("07:5") is None  # require 2-digit MM


def test_parse_hhmm_invalid():
    assert parse_hhmm("24:00") is None
    assert parse_hhmm("12:60") is None
    assert parse_hhmm("nope") is None


def test_local_hhmm_to_future_dt_rollover():
    tz = pytz_timezone("Asia/Singapore")
    now = datetime.now(tz)
    # pick a time definitely in the past: 00:00 today
    dt = local_hhmm_to_future_dt(0, 0, tz)
    assert dt.tzinfo == tz
    # Should be today 00:00 if 'now' < 00:00 (never), else tomorrow 00:00
    if now.hour == 0 and now.minute == 0:
        assert dt.date() == now.date()
    else:
        assert dt.date() in (now.date(), (now + timedelta(days=1)).date())


def test_to_utc_and_delay_non_negative():
    tz = pytz_timezone("Asia/Singapore")
    future_local = datetime.now(tz) + timedelta(minutes=1)
    future_utc = to_utc(future_local)
    assert future_utc.tzinfo == timezone.utc
    delay = delay_seconds_from_utc_deadline(future_utc)
    assert delay >= 0.0


def test_is_valid_tz():
    assert is_valid_tz("Asia/Singapore") is True
    assert is_valid_tz("Not/AZone") is False
