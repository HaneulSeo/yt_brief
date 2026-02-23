from __future__ import annotations

import pandas as pd


def channel_summary(videos_df: pd.DataFrame, picks_df: pd.DataFrame, backtest_df: pd.DataFrame) -> pd.DataFrame:
    if backtest_df.empty:
        return pd.DataFrame()
    merged = backtest_df.merge(picks_df[["video_id", "ticker"]], on=["video_id", "ticker"], how="left").merge(
        videos_df[["video_id", "channel_id", "channel_title", "published_at_kst"]], on="video_id", how="left"
    )
    grp = merged.groupby(["channel_id", "channel_title"], dropna=False)
    out = grp.agg(
        backtested_picks=("id", "count"),
        exact_day_intraday_hit_rate=("hit_target_intraday", "mean"),
        exact_day_close_hit_rate=("hit_target_close", "mean"),
        week_intraday_hit_rate=("hit_week_intraday", "mean"),
        week_close_hit_rate=("hit_week_close", "mean"),
        avg_target_close_return=("ret_target_close", "mean"),
        median_week_high_return=("ret_week_max_high", "median"),
    ).reset_index()
    out["reliability_score"] = out["week_intraday_hit_rate"] * (out["backtested_picks"] / (out["backtested_picks"] + 20))
    return out.sort_values("reliability_score", ascending=False)


def date_summary(backtest_df: pd.DataFrame) -> pd.DataFrame:
    if backtest_df.empty:
        return pd.DataFrame()
    grp = backtest_df.groupby("target_date_kst", dropna=False)
    return grp.agg(
        picks=("id", "count"),
        exact_intraday_hit=("hit_target_intraday", "mean"),
        week_intraday_hit=("hit_week_intraday", "mean"),
        avg_target_ret=("ret_target_close", "mean"),
    ).reset_index()
