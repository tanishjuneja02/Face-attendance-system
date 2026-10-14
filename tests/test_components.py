import pytest

from core import components


def test_names_from_the_database_are_escaped():
    html = components.result_card("<script>alert(1)</script>", "1", "CS & IT", "Maths", "2026-10-14", "09:00:00")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "CS &amp; IT" in html


def test_result_card_shows_all_details():
    html = components.result_card("Rahul", "101", "CS-3A", "Mathematics", "2026-10-14", "09:05:07")
    for text in ("Rahul", "Roll 101", "CS-3A", "Mathematics", "2026-10-14", "09:05:07"):
        assert text in html


def test_hero_contains_title_subtitle_and_date():
    html = components.hero("Face Attendance", "Scan now", "Wednesday, 14 October 2026")
    assert "Face Attendance" in html and "Scan now" in html and "14 October 2026" in html


def test_stats_row_shows_every_card():
    html = components.stats_row([("🎓", "Students", 12), ("✅", "Present", 5)])
    assert html.count("fa-stat-v") == 2
    assert "Students" in html and "12" in html and "Present" in html


@pytest.mark.parametrize("kind", ["ok", "info", "warn", "err"])
def test_notice_uses_matching_style(kind):
    assert f"fa-{kind}" in components.notice(kind, "Title", "text")


def test_notice_rejects_unknown_kind():
    with pytest.raises(ValueError):
        components.notice("purple", "Title")


def test_notice_escapes_text():
    assert "<b>" not in components.notice("err", "Oops", "<b>bad</b>")


def test_recent_list():
    assert components.recent_list([]) == ""
    html = components.recent_list([{"name": "Asha <3", "subject": "Physics", "time": "09:00:00"}])
    assert "Asha &lt;3" in html and "Physics" in html and "09:00:00" in html
