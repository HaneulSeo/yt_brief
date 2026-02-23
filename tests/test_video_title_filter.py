from ytchannelpickcheck.title_filter import match_title


def test_match_title_with_date_pattern():
    assert match_title("12/23 추천 종목", ["급등"])
    assert match_title("2025-01-03 브리핑", ["급등"])
    assert match_title("1월 5일 시장 정리", ["급등"])


def test_match_title_with_keyword_only():
    assert match_title("내일 급등 예상주", ["급등"])


def test_no_match_without_date_or_keyword():
    assert not match_title("오늘 시황 브리핑", ["급등"])
