from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS input_channels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT,
  source_row INTEGER,
  raw_value TEXT,
  provided_channel_name TEXT,
  normalized_input TEXT,
  resolved_channel_id TEXT,
  status TEXT,
  error_message TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_file, source_row)
);
CREATE TABLE IF NOT EXISTS channels (
  channel_id TEXT PRIMARY KEY,
  channel_title TEXT,
  uploads_playlist_id TEXT,
  source_type TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS videos (
  video_id TEXT PRIMARY KEY,
  channel_id TEXT,
  channel_title TEXT,
  title TEXT,
  description TEXT,
  published_at_utc TEXT,
  published_at_kst TEXT,
  url TEXT,
  discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
  title_filter_matched INTEGER DEFAULT 0,
  transcript_status TEXT DEFAULT 'pending',
  extraction_status TEXT DEFAULT 'pending',
  target_date_status TEXT DEFAULT 'pending',
  notes TEXT,
  error_message TEXT
);
CREATE TABLE IF NOT EXISTS target_dates (
  video_id TEXT UNIQUE,
  target_date_type TEXT,
  target_date_kst TEXT,
  target_week_start_kst TEXT,
  parser_confidence REAL,
  parser_evidence TEXT,
  parser_notes TEXT,
  status TEXT,
  raw_target_date_kst TEXT,
  adjustment_reason TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS transcripts (
  video_id TEXT UNIQUE,
  transcript_lang TEXT,
  transcript_is_generated INTEGER,
  transcript_text TEXT,
  transcript_source TEXT,
  transcript_status TEXT,
  error_message TEXT,
  transcript_fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS extracted_picks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT,
  pick_rank INTEGER,
  raw_mention TEXT,
  normalized_name TEXT,
  ticker TEXT,
  mapping_quality TEXT,
  extraction_method TEXT,
  confidence_score REAL,
  evidence_text TEXT,
  is_primary_recommendation INTEGER,
  extraction_created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(video_id, normalized_name, ticker, pick_rank, is_primary_recommendation)
);
CREATE TABLE IF NOT EXISTS inferred_recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT NOT NULL,
  rec_rank INTEGER NOT NULL,
  stock_name TEXT,
  ticker TEXT,
  market TEXT,
  confidence TEXT NOT NULL,
  method TEXT NOT NULL,
  evidence_text TEXT,
  evidence_start_sec REAL,
  evidence_end_sec REAL,
  source_segment_label TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(video_id, rec_rank)
);
CREATE TABLE IF NOT EXISTS backtest_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  video_id TEXT,
  ticker TEXT,
  target_date_kst TEXT,
  window_days INTEGER,
  target_prev_close REAL,
  target_open REAL,
  target_high REAL,
  target_low REAL,
  target_close REAL,
  ret_target_open REAL,
  ret_target_high REAL,
  ret_target_close REAL,
  hit_target_intraday INTEGER,
  hit_target_close INTEGER,
  week_window_start_date TEXT,
  week_window_end_date TEXT,
  week_max_high REAL,
  week_max_high_date TEXT,
  week_max_close REAL,
  week_max_close_date TEXT,
  ret_week_max_high REAL,
  ret_week_max_close REAL,
  hit_week_intraday INTEGER,
  hit_week_close INTEGER,
  first_hit_day_offset_intraday INTEGER,
  first_hit_day_offset_close INTEGER,
  backtest_status TEXT,
  backtest_error TEXT,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(video_id, ticker, target_date_kst, window_days)
);
CREATE TABLE IF NOT EXISTS analytics_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cache_key TEXT UNIQUE,
  payload_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_videos_channel_pub ON videos(channel_id, published_at_kst);
CREATE INDEX IF NOT EXISTS idx_target_dates_date ON target_dates(target_date_kst);
CREATE INDEX IF NOT EXISTS idx_picks_ticker ON extracted_picks(ticker);
CREATE INDEX IF NOT EXISTS idx_inferred_video_id ON inferred_recommendations(video_id);
CREATE INDEX IF NOT EXISTS idx_inferred_ticker ON inferred_recommendations(ticker);
CREATE INDEX IF NOT EXISTS idx_backtest_ticker_date ON backtest_results(ticker, target_date_kst);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)


@contextmanager
def db_session(db_path: str | Path):
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
