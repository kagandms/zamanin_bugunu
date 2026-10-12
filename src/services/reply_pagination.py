from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse


class ReplyPaginationError(ValueError):
    """The reply set or its continuation cannot be verified."""


@dataclass(frozen=True)
class ReplyPage:
    replies: tuple[dict[str, object], ...]
    next_cursor: str | None


@dataclass(frozen=True)
class ReplyCounts:
    external: int = 0
    own: int = 0
    ownership_by_id: Mapping[str, bool] = field(default_factory=dict)


def parse_reply_page(payload: object, expected_url: str) -> ReplyPage:
    """Validate a Graph page; absence of paging.next is completion, regardless of limit.

    Args: payload: decoded response; expected_url: permitted endpoint.
    Returns: validated rows and continuation. Raises: ReplyPaginationError on malformed metadata.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ReplyPaginationError("reply_response_malformed")
    rows = payload["data"]
    if not all(isinstance(row, dict) for row in rows):
        raise ReplyPaginationError("reply_response_malformed")
    paging = payload.get("paging", {})
    if not isinstance(paging, dict):
        raise ReplyPaginationError("reply_paging_malformed")
    cursors = paging.get("cursors", {})
    if not isinstance(cursors, dict):
        raise ReplyPaginationError("reply_paging_malformed")
    after = cursors.get("after")
    if after is not None and (not isinstance(after, str) or not after):
        raise ReplyPaginationError("reply_cursor_malformed")
    next_url = paging.get("next")
    if next_url is None:
        return ReplyPage(tuple(rows), None)
    return ReplyPage(tuple(rows), _parse_next_cursor(next_url, expected_url, after))


def _parse_next_cursor(next_url: object, expected_url: str, after: str | None) -> str:
    if not isinstance(next_url, str) or not next_url:
        raise ReplyPaginationError("reply_next_malformed")
    actual = urlparse(next_url)
    expected = urlparse(expected_url)
    if actual.scheme != "https" or actual.netloc != expected.netloc or actual.path != expected.path:
        raise ReplyPaginationError("reply_next_endpoint_unverified")
    cursor_values = parse_qs(actual.query).get("after", [])
    if len(cursor_values) > 1:
        raise ReplyPaginationError("reply_cursor_malformed")
    url_cursor = cursor_values[0] if cursor_values else None
    if after and url_cursor and after != url_cursor:
        raise ReplyPaginationError("reply_cursor_mismatch")
    cursor = after or url_cursor
    if not cursor:
        raise ReplyPaginationError("reply_next_cursor_missing")
    return cursor


def count_verified_replies(state: ReplyCounts, page: ReplyPage, post_id: str) -> ReplyCounts:
    """Deduplicate verified direct replies without mutating the prior page state.

    Args: state: previous counts; page: validated page; post_id: requested parent.
    Returns: updated counts. Raises: ReplyPaginationError on unknown ownership/parent/conflicts.
    """
    ownership_by_id = dict(state.ownership_by_id)
    own = state.own
    external = state.external
    for row in page.replies:
        reply_id = row.get("id")
        parent = row.get("replied_to")
        ownership = row.get("is_reply_owned_by_me")
        if not isinstance(reply_id, str) or not reply_id or not isinstance(parent, dict):
            raise ReplyPaginationError("reply_author_or_parent_unverified")
        if parent.get("id") != post_id or not isinstance(ownership, bool):
            raise ReplyPaginationError("reply_author_or_parent_unverified")
        if reply_id in ownership_by_id:
            if ownership_by_id[reply_id] != ownership:
                raise ReplyPaginationError("reply_ownership_conflict")
            continue
        ownership_by_id[reply_id] = ownership
        own += int(ownership)
        external += int(not ownership)
    return ReplyCounts(external, own, ownership_by_id)
