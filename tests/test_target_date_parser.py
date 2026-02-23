from datetime import date

from ytchannelpickcheck.target_date_parser import parse_target_date


def test_explicit_mmdd():
    r = parse_target_date("v1", "12/23 급등주", date(2025, 12, 22))
    assert r.target_date_kst == date(2025, 12, 23)
    assert r.target_date_type == "explicit_date"


def test_tomorrow():
    r = parse_target_date("v2", "내일 급등주", date(2025, 12, 19))
    assert r.target_date_type == "relative_tomorrow"


def test_next_week():
    r = parse_target_date("v3", "다음주 추천주", date(2025, 12, 19))
    assert r.target_date_type == "relative_next_week"
    assert r.target_week_start_kst is not None


def test_weekday():
    r = parse_target_date("v4", "월요일 급등주", date(2025, 12, 19))
    assert r.target_date_type == "weekday_inferred"
