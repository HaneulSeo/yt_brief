from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from rich.console import Console

from .backtest import compute_backtest
from .channels_loader import load_channels_file
from .db import db_session, ensure_schema
from .extractor import extract_picks
from .recommendation_inferer import infer_recommendations
from .krx_mapper import map_to_ticker
from .price_client import PriceClient
from .target_date_parser import parse_target_date
from .title_filter import DEFAULT_KEYWORDS, match_title
from .transcript_client import TranscriptClient
from .utils_time import KST, ensure_trading_day, parse_ymd
from .youtube_channel_client import YouTubeChannelClient

console = Console()


def _match_title(title: str, keywords: list[str]) -> bool:
    return match_title(title, keywords)


def resolve_channels(db_path: str, channels_file: str, yt_client: YouTubeChannelClient):
    rows = load_channels_file(channels_file)
    with db_session(db_path) as conn:
        for row in rows:
            conn.execute(
                """INSERT OR REPLACE INTO input_channels(source_file, source_row, raw_value, provided_channel_name, normalized_input, resolved_channel_id, status, error_message)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (channels_file, row["source_row"], row["raw"], row["channel_name"], row["normalized"], None, "pending", None),
            )
            resolved = yt_client.resolve_channel(row["channel_id"] or row["url"] or row["normalized"])
            if resolved:
                conn.execute(
                    "INSERT OR REPLACE INTO channels(channel_id, channel_title, uploads_playlist_id, source_type, updated_at) VALUES(?,?,?,?,CURRENT_TIMESTAMP)",
                    (resolved["channel_id"], resolved["channel_title"], resolved["uploads_playlist_id"], "resolved"),
                )
                conn.execute(
                    "UPDATE input_channels SET resolved_channel_id=?, status='resolved' WHERE source_file=? AND source_row=?",
                    (resolved["channel_id"], channels_file, row["source_row"]),
                )
            else:
                conn.execute(
                    "UPDATE input_channels SET status='failed', error_message='unresolved_channel' WHERE source_file=? AND source_row=?",
                    (channels_file, row["source_row"]),
                )


def discover_videos(db_path: str, start: str, end: str, all_videos: bool, keywords: list[str]):
    start_d, end_d = parse_ymd(start), parse_ymd(end)
    with db_session(db_path) as conn:
        channels = conn.execute("SELECT * FROM channels").fetchall()
    from .config import get_settings

    yt = YouTubeChannelClient(get_settings().youtube_api_key)
    with db_session(db_path) as conn:
        for c in channels:
            videos = yt.list_uploads_in_range(c["uploads_playlist_id"], start_d, end_d)
            for v in videos:
                matched = 1 if _match_title(v["title"], keywords) else 0
                if (not all_videos) and not matched:
                    continue
                conn.execute(
                    """INSERT OR REPLACE INTO videos(video_id, channel_id, channel_title, title, description, published_at_utc, published_at_kst, url, title_filter_matched)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (v["video_id"], c["channel_id"], c["channel_title"], v["title"], v["description"], v["published_at_utc"], v["published_at_kst"], v["url"], matched),
                )


def parse_target_dates_stage(db_path: str, start: str, end: str):
    start_d, end_d = parse_ymd(start), parse_ymd(end)
    with db_session(db_path) as conn:
        rows = conn.execute("SELECT video_id, title, published_at_kst FROM videos").fetchall()
        pr = PriceClient()
        for r in rows:
            pub = datetime.fromisoformat(r["published_at_kst"]).astimezone(KST).date()
            if not (start_d <= pub <= end_d):
                continue
            parsed = parse_target_date(r["video_id"], r["title"], pub, pr.is_trading_day)
            target = parsed.target_date_kst
            raw_target = target
            adj = None
            if target:
                target, adj = ensure_trading_day(target, pr.is_trading_day)
            conn.execute(
                """INSERT OR REPLACE INTO target_dates(video_id,target_date_type,target_date_kst,target_week_start_kst,parser_confidence,parser_evidence,parser_notes,status,raw_target_date_kst,adjustment_reason,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (r["video_id"], parsed.target_date_type, str(target) if target else None, str(parsed.target_week_start_kst) if parsed.target_week_start_kst else None, parsed.parser_confidence, parsed.parser_evidence, parsed.parser_notes, parsed.status, str(raw_target) if raw_target else None, adj),
            )
            conn.execute("UPDATE videos SET target_date_status='success' WHERE video_id=?", (r["video_id"],))


def transcripts_stage(db_path: str, retry_failed: bool = False):
    tc = TranscriptClient()
    with db_session(db_path) as conn:
        q = "SELECT video_id, transcript_status FROM videos"
        for r in conn.execute(q).fetchall():
            if r["transcript_status"] == "success" and not retry_failed:
                continue
            res = tc.fetch(r["video_id"])
            conn.execute(
                """INSERT OR REPLACE INTO transcripts(video_id, transcript_lang, transcript_is_generated, transcript_text, transcript_source, transcript_status, error_message, transcript_fetched_at)
                   VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (r["video_id"], res["lang"], int(res["is_generated"]) if res["is_generated"] is not None else None, res["text"], res["source"], res["status"], res["error"]),
            )
            conn.execute("UPDATE videos SET transcript_status=? WHERE video_id=?", (res["status"], r["video_id"]))


def extract_stage(db_path: str, use_llm: bool = False):
    with db_session(db_path) as conn:
        rows = conn.execute(
            "SELECT v.video_id, v.title, v.description, t.transcript_text FROM videos v LEFT JOIN transcripts t ON v.video_id=t.video_id"
        ).fetchall()
        for r in rows:
            picks = extract_picks(r["video_id"], r["title"], r["description"], r["transcript_text"], use_llm=use_llm)
            for p in picks:
                ticker, quality = map_to_ticker(p.normalized_name)
                conn.execute(
                    """INSERT OR REPLACE INTO extracted_picks(video_id,pick_rank,raw_mention,normalized_name,ticker,mapping_quality,extraction_method,confidence_score,evidence_text,is_primary_recommendation)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (p.video_id, p.pick_rank, p.raw_mention, p.normalized_name, ticker or p.ticker, quality, p.extraction_method, p.confidence_score, p.evidence_text, int(p.is_primary_recommendation)),
                )
            conn.execute("UPDATE videos SET extraction_status='success' WHERE video_id=?", (r["video_id"],))


def backtest_stage(db_path: str, week_window: int = 5, intraday_hit: float = 0.10, close_hit: float = 0.05, source: str = "mentions"):
    if source not in {"mentions", "inferred"}:
        raise ValueError("source must be 'mentions' or 'inferred'")
    pc = PriceClient()
    with db_session(db_path) as conn:
        ensure_schema(conn)
        rows = conn.execute(_pick_source_query(source)).fetchall()
        for r in rows:
            td = parse_ymd(r["target_date_kst"])
            ohlcv = pc.get_ohlcv(r["ticker"], td.replace(day=max(1, td.day - 10)), td)
            tail = pc.get_ohlcv(r["ticker"], td, td)
            future_days = pc.get_trading_days(td, week_window)
            if future_days:
                fut = pc.get_ohlcv(r["ticker"], future_days[0], future_days[-1])
                ohlcv = pd.concat([ohlcv, fut]).sort_index()
            else:
                ohlcv = pd.concat([ohlcv, tail]).sort_index()
            res = compute_backtest(r["video_id"], r["ticker"], td, ohlcv, window_days=week_window, intraday_hit=intraday_hit, close_hit=close_hit)
            conn.execute(
                """INSERT OR REPLACE INTO backtest_results(video_id,ticker,target_date_kst,window_days,target_prev_close,target_open,target_high,target_low,target_close,ret_target_open,ret_target_high,ret_target_close,hit_target_intraday,hit_target_close,week_window_start_date,week_window_end_date,week_max_high,week_max_high_date,week_max_close,week_max_close_date,ret_week_max_high,ret_week_max_close,hit_week_intraday,hit_week_close,first_hit_day_offset_intraday,first_hit_day_offset_close,backtest_status,backtest_error,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)""",
                (
                    res.video_id,
                    res.ticker,
                    str(res.target_date_kst),
                    res.window_days,
                    res.target_prev_close,
                    res.target_open,
                    res.target_high,
                    res.target_low,
                    res.target_close,
                    res.ret_target_open,
                    res.ret_target_high,
                    res.ret_target_close,
                    int(res.hit_target_intraday),
                    int(res.hit_target_close),
                    str(res.week_window_start_date) if res.week_window_start_date else None,
                    str(res.week_window_end_date) if res.week_window_end_date else None,
                    res.week_max_high,
                    str(res.week_max_high_date) if res.week_max_high_date else None,
                    res.week_max_close,
                    str(res.week_max_close_date) if res.week_max_close_date else None,
                    res.ret_week_max_high,
                    res.ret_week_max_close,
                    int(res.hit_week_intraday),
                    int(res.hit_week_close),
                    res.first_hit_day_offset_intraday,
                    res.first_hit_day_offset_close,
                    res.backtest_status,
                    res.backtest_error,
                ),
            )


def analyze_stage(db_path: str):
    with db_session(db_path) as conn:
        v = pd.read_sql_query("SELECT * FROM videos", conn)
        p = pd.read_sql_query("SELECT * FROM extracted_picks", conn)
        b = pd.read_sql_query("SELECT * FROM backtest_results", conn)
        from .analytics import channel_summary, date_summary

        cs = channel_summary(v, p, b)
        ds = date_summary(b)
        conn.execute("DELETE FROM analytics_cache")
        conn.execute("INSERT INTO analytics_cache(cache_key,payload_json) VALUES(?,?)", ("channel_summary", cs.to_json(orient="records")))
        conn.execute("INSERT INTO analytics_cache(cache_key,payload_json) VALUES(?,?)", ("date_summary", ds.to_json(orient="records")))


def infer_recommendations_stage(
    db_path: str,
    start: str,
    end: str,
    overwrite: bool = False,
    video_id: str | None = None,
):
    start_d, end_d = parse_ymd(start), parse_ymd(end)
    with db_session(db_path) as conn:
        ensure_schema(conn)
        where = ["date(v.published_at_kst) BETWEEN ? AND ?"]
        args: list[object] = [str(start_d), str(end_d)]
        if video_id:
            where.append("v.video_id=?")
            args.append(video_id)
        rows = conn.execute(
            f"""SELECT v.video_id, v.title, v.published_at_kst, t.transcript_text
                FROM videos v
                LEFT JOIN transcripts t ON v.video_id=t.video_id
                WHERE {' AND '.join(where)}""",
            args,
        ).fetchall()

        for row in rows:
            if not row["transcript_text"]:
                continue
            if overwrite:
                conn.execute("DELETE FROM inferred_recommendations WHERE video_id=?", (row["video_id"],))
            mentions = conn.execute(
                "SELECT normalized_name FROM extracted_picks WHERE video_id=?",
                (row["video_id"],),
            ).fetchall()
            mention_names = [m["normalized_name"] for m in mentions if m["normalized_name"]]
            recs, _meta = infer_recommendations(row["title"] or "", row["transcript_text"], mention_names)
            for rec in recs:
                conn.execute(
                    """INSERT OR REPLACE INTO inferred_recommendations(
                        video_id, rec_rank, stock_name, ticker, market, confidence, method,
                        evidence_text, evidence_start_sec, evidence_end_sec, source_segment_label, created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        row["video_id"],
                        rec.rec_rank,
                        rec.stock_name,
                        rec.ticker,
                        rec.market,
                        rec.confidence,
                        rec.method,
                        rec.evidence_text,
                        rec.evidence_start_sec,
                        rec.evidence_end_sec,
                        rec.source_segment_label,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )


def _pick_source_query(source: str) -> str:
    if source == "mentions":
        return """SELECT DISTINCT p.video_id, p.ticker, td.target_date_kst
               FROM extracted_picks p JOIN target_dates td ON p.video_id=td.video_id
               WHERE p.ticker IS NOT NULL AND td.target_date_kst IS NOT NULL"""
    return """SELECT DISTINCT ir.video_id, ir.ticker, td.target_date_kst
           FROM inferred_recommendations ir JOIN target_dates td ON ir.video_id=td.video_id
           WHERE ir.ticker IS NOT NULL AND td.target_date_kst IS NOT NULL"""
