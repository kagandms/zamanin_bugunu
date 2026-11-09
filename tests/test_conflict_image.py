"""Conflict and politics events must not use a flag, emblem, leader portrait or poster as the picture."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.event_preparation import _choose_image, is_blocked_image

FLAG = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Flag_of_Azerbaijan.svg/250px-Flag_of_Azerbaijan.svg.png"
PORTRAIT = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Portrait_of_a_leader.jpg/250px-Portrait_of_a_leader.jpg"
POSTER = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Propaganda_poster_1940.jpg"
MAP = "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Nagorno-Karabakh_map.png/250px-Nagorno-Karabakh_map.png"
PHOTO = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Shusha_street.jpg/250px-Shusha_street.jpg"


def _rewrite(topic: str, *page_images: str) -> SimpleNamespace:
    pages = [{"thumbnail": {"source": url}} for url in page_images]
    return SimpleNamespace(candidate={"text": "Bir olay.", "_topic_category": topic, "pages": pages}, image_prompt=None)


@pytest.mark.parametrize("url", [FLAG, PORTRAIT, POSTER])
def test_symbols_portraits_and_posters_are_blocked(url: str) -> None:
    assert is_blocked_image(url)


@pytest.mark.parametrize("topic", ["SAVAS_ASKERI", "SIYASET"])
def test_a_flag_is_rejected_for_conflict_and_politics_topics(topic: str) -> None:
    url, source = _choose_image(_rewrite(topic, FLAG))

    assert url is None
    assert source == "no_neutral_image"


def test_a_map_is_accepted_and_preferred_over_a_photograph() -> None:
    url, _ = _choose_image(_rewrite("SAVAS_ASKERI", FLAG, PHOTO, MAP))

    assert url == MAP
    assert not is_blocked_image(MAP)


def test_a_photograph_from_another_linked_page_replaces_a_blocked_main_image() -> None:
    url, source = _choose_image(_rewrite("SIYASET", PORTRAIT, PHOTO))

    assert url == PHOTO
    assert source == "wikipedia_thumbnail"


def test_other_topics_keep_the_existing_image_choice() -> None:
    url, _ = _choose_image(_rewrite("KULTUR_SANAT", FLAG))

    assert url == FLAG
