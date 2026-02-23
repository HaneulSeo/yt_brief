from __future__ import annotations

import sqlite3
import sys

import pandas as pd
import streamlit as st


def get_db_arg(default: str = "ytchannelpickcheck.db") -> str:
    argv = sys.argv
    if "--db" in argv:
        return argv[argv.index("--db") + 1]
    return default


def main():
    st.set_page_config(layout="wide", page_title="ytchannelpickcheck")
    db = get_db_arg()
    conn = sqlite3.connect(db)
    videos = pd.read_sql_query("SELECT * FROM videos", conn)
    backtest = pd.read_sql_query("SELECT * FROM backtest_results", conn)
    picks = pd.read_sql_query("SELECT * FROM extracted_picks", conn)
    target_dates = pd.read_sql_query("SELECT * FROM target_dates", conn)

    st.title("ytchannelpickcheck Dashboard")
    if backtest.empty:
        st.warning("No backtest data yet")
        return

    chs = sorted(videos["channel_title"].dropna().unique().tolist())
    selected = st.multiselect("Channels", chs, default=chs)
    min_ex = st.slider("Min extraction confidence", 0.0, 1.0, 0.5)

    merged = backtest.merge(videos[["video_id", "channel_title", "title", "url", "published_at_kst"]], on="video_id", how="left")
    merged = merged.merge(picks[["video_id", "ticker", "confidence_score", "normalized_name"]], on=["video_id", "ticker"], how="left")
    merged = merged[merged["channel_title"].isin(selected)]
    merged = merged[merged["confidence_score"].fillna(0) >= min_ex]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Backtested picks", len(merged))
    c2.metric("Exact intraday hit", f"{merged['hit_target_intraday'].mean():.1%}")
    c3.metric("Week intraday hit", f"{merged['hit_week_intraday'].mean():.1%}")
    c4.metric("Avg target close ret", f"{merged['ret_target_close'].mean():.2%}")

    st.subheader("Channel leaderboard")
    leaderboard = merged.groupby("channel_title").agg(picks=("id", "count"), exact=("hit_target_intraday", "mean"), week=("hit_week_intraday", "mean")).reset_index()
    st.dataframe(leaderboard.sort_values("week", ascending=False), use_container_width=True)

    st.subheader("Video detail")
    st.dataframe(merged[["channel_title", "title", "url", "target_date_kst", "ticker", "normalized_name", "ret_target_close", "ret_week_max_high"]], use_container_width=True)

    st.download_button("Download filtered CSV", data=merged.to_csv(index=False).encode("utf-8"), file_name="filtered_results.csv")


if __name__ == "__main__":
    main()
