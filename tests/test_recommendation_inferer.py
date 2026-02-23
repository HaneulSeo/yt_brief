from ytchannelpickcheck.recommendation_inferer import (
    build_sections,
    detect_sequence_markers,
    infer_recommendations,
    split_transcript_lines,
)


def test_sequence_marker_detection_and_section_split():
    transcript = """
첫 번째 종목 삼성전자입니다. 실적 이유 설명.
두 번째 종목은 SK하이닉스 차트 포인트.
세 번째 종목은 NAVER 수급 이야기.
"""
    lines = split_transcript_lines(transcript)
    markers = detect_sequence_markers(lines)
    assert [m[1] for m in markers] == ["first_stock", "second_stock", "third_stock"]
    sections = build_sections(lines, expected_count=3)
    assert [s.label for s in sections] == ["first_stock", "second_stock", "third_stock"]


def test_excludes_theme_words_and_selects_one_per_section(monkeypatch):
    ticker_map = {
        "삼성전자": ("005930", "normalized_exact"),
        "하이닉스": ("000660", "normalized_exact"),
        "네이버": ("035420", "normalized_exact"),
        "AI": (None, "unmapped"),
    }

    def fake_map(name):
        return ticker_map.get(name, (None, "unmapped"))

    monkeypatch.setattr("ytchannelpickcheck.recommendation_inferer.map_to_ticker", fake_map)

    transcript = """
첫 번째 종목 삼성전자입니다. AI 반도체 대장주라는 테마만 보지 마세요. 실적 포인트.
두 번째 종목 하이닉스입니다. 수급 이유.
세 번째 종목 네이버입니다. 차트 포인트.
"""
    picks, meta = infer_recommendations("[주식] 내일 상한가 유력 3종목", transcript)
    assert meta["expected_count"] == 3
    assert len(picks) == 3
    assert [p.stock_name for p in picks] == ["삼성전자", "하이닉스", "네이버"]


def test_fallback_without_markers(monkeypatch):
    ticker_map = {
        "삼성전자": ("005930", "normalized_exact"),
        "포스코홀딩스": ("005490", "normalized_exact"),
    }

    monkeypatch.setattr("ytchannelpickcheck.recommendation_inferer.map_to_ticker", lambda name: ticker_map.get(name, (None, "unmapped")))
    transcript = """
00:05 오늘 추천 드릴 기업 삼성전자입니다 이유는 실적 개선.
00:50 다음으로 포스코홀딩스 수급과 차트를 봅니다.
01:40 구독 좋아요 부탁드립니다.
"""
    picks, meta = infer_recommendations("다음주 급등 유력 3종목", transcript)
    assert len(picks) >= 2
    assert meta["confidence_summary"] in {"medium", "low"}
