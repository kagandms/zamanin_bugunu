"""Topic cooldown: a topic published in the last 7 days loses points but is never excluded."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.data.database import init_db
from src.data.models import PostHistory
from src.data.repository import HistoryRepository, topic_title
from src.services.content_service import ContentService

KARABAKH_PAGE = "İkinci_Dağlık_Karabağ_Savaşı"


def _candidate(page_title: str, year: int | None) -> dict[str, object]:
    return {"text": "Bir olay yaşandı.", "year": year, "_category": "events",
            "pages": [{"title": page_title, "titles": {"canonical": page_title}}]}


def _score(item: dict[str, object], recent: list[tuple[str, int | None]]) -> int:
    service = ContentService()
    service.recent_topics = recent
    return service._calculate_fame_score(item)


def test_same_page_and_year_as_a_recent_post_loses_eighty_points_but_stays_selectable() -> None:
    # Yesterday's Şuşa post (2020) cools down today's Karabağ ceasefire (2020).
    candidate = _candidate(KARABAKH_PAGE, 2020)

    cooled = _score(candidate, [("İkinci Dağlık Karabağ Savaşı", 2020)])
    normal = _score(candidate, [])

    assert normal - cooled == ContentService.TOPIC_COOLDOWN_PENALTY == 80


def test_a_year_within_one_year_still_counts_as_the_same_topic() -> None:
    assert _score(_candidate(KARABAKH_PAGE, 2021), [("İkinci Dağlık Karabağ Savaşı", 2020)]) < _score(
        _candidate(KARABAKH_PAGE, 2021), [])


@pytest.mark.parametrize(("page", "year"), [
    (KARABAKH_PAGE, 2025),             # same page, far year: a different event
    ("Birahane_Darbesi", 2020),       # different page
])
def test_other_years_or_other_pages_are_not_cooled(page: str, year: int) -> None:
    candidate = _candidate(page, year)

    assert _score(candidate, [("İkinci Dağlık Karabağ Savaşı", 2020)]) == _score(candidate, [])


def test_topic_title_comes_from_the_source_url_slug_or_the_source_id() -> None:
    assert topic_title("x", "https://tr.wikipedia.org/wiki/%C4%B0kinci_Da%C4%9Fl%C4%B1k_Karaba%C4%9F_Sava%C5%9F%C4%B1") == \
        "İkinci Dağlık Karabağ Savaşı"
    assert topic_title("Birahane Darbesi", None) == "Birahane Darbesi"
    assert topic_title(None, None) == ""


@pytest.mark.asyncio
async def test_repository_returns_only_posts_from_the_last_seven_days() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        session.add_all([
            PostHistory(content_text="yeni", source_id="x", event_year="2020", posted_at=now - timedelta(days=1),
                        source_url="https://tr.wikipedia.org/wiki/%C4%B0kinci_Da%C4%9Fl%C4%B1k_Karaba%C4%9F_Sava%C5%9F%C4%B1"),
            PostHistory(content_text="eski", source_id="Eski Sayfa", event_year="1999", posted_at=now - timedelta(days=9)),
        ])
        await session.commit()

        topics = await HistoryRepository(session).get_recent_topic_titles(days=7)

    assert topics == [("İkinci Dağlık Karabağ Savaşı", 2020)]
