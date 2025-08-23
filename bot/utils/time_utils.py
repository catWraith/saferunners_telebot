from datetime import datetime, timedelta, time as dtime, timezone
from typing import Optional, Tuple

from pytz import timezone as pytz_timezone, UnknownTimeZoneError
from telegram.ext import ContextTypes

from bot.config import DEFAULT_TZ
from bot.constants import UD_TZ


def get_user_tz(context: ContextTypes.DEFAULT_TYPE):
    tzname = context.user_data.get(UD_TZ, DEFAULT_TZ)
    try:
        return pytz_timezone(tzname)
    except UnknownTimeZoneError:
        return pytz_timezone(DEFAULT_TZ)


def parse_hhmm(s: str) -> Optional[Tuple[int, int]]:
    try:
        hh, mm = s.strip().split(":")
        h, m = int(hh), int(mm)
        if 0 <= h <= 23 and 0 <= m <= 59:
            return h, m
        return None
    except Exception:
        return None


def local_hhmm_to_future_dt(h: int, m: int, tz) -> datetime:
    """Return the next occurrence (today or tomorrow) of HH:MM in the user's TZ."""
    now = datetime.now(tz)
    candidate = datetime.combine(now.date(), dtime(hour=h, minute=m), tz)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def to_utc(dt, tz) -> datetime:
    return dt.astimezone(timezone.utc)
