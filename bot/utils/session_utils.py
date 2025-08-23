from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Session:
    end_dt_utc_iso: Optional[str]
    location: Optional[Dict[str, Any]]  # {"type":"coords","lat":..,"lon":..} or {"type":"text","text":..}

    @staticmethod
    def from_user_data(d: dict) -> "Session":
        if not d:
            return Session(None, None)
        return Session(d.get("end_dt_utc"), d.get("location"))

    def to_user_data(self) -> dict:
        return {
            "end_dt_utc": self.end_dt_utc_iso,
            "location": self.location,
        }


def format_location_summary(location: Optional[Dict[str, Any]]) -> str:
    if not location:
        return "Location: (not provided)"
    if location.get("type") == "coords":
        return f"Location: (lat {location['lat']:.5f}, lon {location['lon']:.5f})"
    if location.get("type") == "text":
        return f"Location: {location['text']}"
    return "Location: (unknown)"
