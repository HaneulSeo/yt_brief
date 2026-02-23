import pandas as pd
from datetime import date

from ytchannelpickcheck.db import connect, init_db
from ytchannelpickcheck.pipeline import backtest_stage, infer_recommendations_stage


class FakePriceClient:
    def is_trading_day(self, d):
        return True

    def get_trading_days(self, start, window):
        return [start]

    def get_ohlcv(self, ticker, start, end):
        rows = [
            {"date": date(2025, 1, 2), "open": 100, "high": 102, "low": 99, "close": 100},
            {"date": date(2025, 1, 3), "open": 105, "high": 112, "low": 103, "close": 108},
        ]
        return pd.DataFrame(rows).set_index("date")


def test_inferred_recommendations_upsert_and_overwrite(tmp_path, monkeypatch):
    db = tmp_path / "a.db"
    init_db(db)

    monkeypatch.setattr(
        "ytchannelpickcheck.recommendation_inferer.map_to_ticker",
        lambda name: {"삼성전자": ("005930", "normalized_exact")}.get(name, (None, "unmapped")),
    )

    with connect(db) as conn:
        conn.execute("INSERT INTO videos(video_id,title,published_at_kst) VALUES('v1','내일 상한가 유력 3종목','2025-01-02T10:00:00+09:00')")
        conn.execute("INSERT INTO transcripts(video_id, transcript_text) VALUES('v1','첫 번째 종목 삼성전자 실적 이유')")
        conn.execute("INSERT INTO extracted_picks(video_id, raw_mention, normalized_name, extraction_method, confidence_score, evidence_text, is_primary_recommendation) VALUES('v1','삼성전자','삼성전자','dict',0.8,'m',0)")

    infer_recommendations_stage(str(db), "2025-01-01", "2025-01-03")
    infer_recommendations_stage(str(db), "2025-01-01", "2025-01-03")

    with connect(db) as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM inferred_recommendations WHERE video_id='v1'").fetchone()[0]
        assert cnt == 1

    infer_recommendations_stage(str(db), "2025-01-01", "2025-01-03", overwrite=True)
    with connect(db) as conn:
        cnt2 = conn.execute("SELECT COUNT(*) FROM inferred_recommendations WHERE video_id='v1'").fetchone()[0]
        assert cnt2 == 1


def test_backtest_uses_inferred_source(tmp_path, monkeypatch):
    db = tmp_path / "b.db"
    init_db(db)
    monkeypatch.setattr("ytchannelpickcheck.pipeline.PriceClient", FakePriceClient)

    with connect(db) as conn:
        conn.execute("INSERT INTO target_dates(video_id,target_date_kst,status) VALUES('v1','2025-01-03','success')")
        conn.execute("INSERT INTO inferred_recommendations(video_id,rec_rank,stock_name,ticker,confidence,method,created_at) VALUES('v1',1,'삼성전자','005930','high','rule_sequence','2025-01-01T00:00:00+00:00')")

    backtest_stage(str(db), source="inferred")

    with connect(db) as conn:
        row = conn.execute("SELECT ticker, backtest_status FROM backtest_results WHERE video_id='v1'").fetchone()
        assert row[0] == "005930"
        assert row[1] == "success"
