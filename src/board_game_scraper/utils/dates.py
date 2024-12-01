from datetime import datetime, timezone


def now(tz: timezone = timezone.utc) -> datetime:
    """Return the current time with the given timezone."""
    return datetime.now(tz)
