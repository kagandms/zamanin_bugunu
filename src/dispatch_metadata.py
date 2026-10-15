from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone

from src.publication_policy import find_open_window, require_utc


@dataclass(frozen=True)
class DispatchMetadata:
    """Validated, non-secret correlation context; invalid raw inputs never reach logs/DB."""
    trigger_source: str = "manual"
    correlation_id: str = ""
    intended_at: datetime | None = None
    intended_day: str = ""
    intended_slot: str = ""
    error: str | None = None


def read_dispatch(environment: Mapping[str, str]) -> DispatchMetadata:
    """Parse optional workflow inputs. Returns sanitized context or a fixed rejection code."""
    values = tuple(environment.get(f"ZAMANIN_{key}", "") for key in (
        "TRIGGER_SOURCE", "CORRELATION_ID", "INTENDED_AT", "INTENDED_DAY", "INTENDED_SLOT"))
    if values[0] in ("", "manual") and not any(values[1:]):
        return DispatchMetadata(trigger_source="native" if environment.get("GITHUB_EVENT_NAME") == "schedule" else "manual")
    try:
        return _parse_dispatch(values)
    except ValueError:
        return DispatchMetadata(trigger_source="invalid", error="skip_invalid_dispatch")


def _parse_dispatch(values: tuple[str, ...]) -> DispatchMetadata:
    source, correlation, timestamp, day, slot = values
    if source != "cloudflare" or not re.fullmatch(r"cf-(publication|analytics)-\d{13}", correlation):
        raise ValueError("Invalid dispatch identity")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z", timestamp):
        raise ValueError("UTC timestamp required")
    intended = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if int(intended.timestamp() * 1000) != int(correlation.rsplit("-", 1)[1]):
        raise ValueError("Correlation timestamp mismatch")
    is_publication = correlation.startswith("cf-publication-")
    if is_publication:
        window = find_open_window(intended)
        if window is None or date.fromisoformat(day).isoformat() != window.local_day or slot != window.key:
            raise ValueError("Invalid intended slot")
    elif day or slot:
        raise ValueError("Analytics cannot request a publication slot")
    return DispatchMetadata(source, correlation, intended, day, slot)


def reject_publication_dispatch(metadata: DispatchMetadata, observed: datetime) -> str | None:
    """Reject stale/future/mismatched external inputs before slot claim, auth or preparation."""
    if metadata.error:
        return metadata.error
    if metadata.trigger_source != "cloudflare":
        return None
    current = require_utc(observed)
    if not metadata.correlation_id.startswith("cf-publication-") or metadata.intended_at is None:
        return "skip_invalid_dispatch"
    if metadata.intended_at > current:
        return "skip_stale_dispatch"
    window = find_open_window(current)
    if window is None or (window.local_day, window.key) != (metadata.intended_day, metadata.intended_slot):
        return "skip_slot_mismatch"
    return None


def validate_analytics_dispatch(metadata: DispatchMetadata, observed: datetime) -> None:
    """Validate CLI metadata without importing publication code. Raises ValueError for invalid input."""
    if metadata.error or (metadata.trigger_source == "cloudflare" and (
        not metadata.correlation_id.startswith("cf-analytics-") or metadata.intended_at is None
        or metadata.intended_at > require_utc(observed)
    )):
        raise ValueError("Invalid analytics dispatch metadata")


def format_dispatch(metadata: DispatchMetadata) -> str:
    """Return only sanitized metadata for analytics/run correlation logs."""
    intended = metadata.intended_at.astimezone(timezone.utc).isoformat() if metadata.intended_at else "none"
    return (f"trigger_source={metadata.trigger_source} correlation_id={metadata.correlation_id or 'none'} "
            f"intended_at={intended} intended_day={metadata.intended_day or 'none'} "
            f"intended_slot={metadata.intended_slot or 'none'}")
