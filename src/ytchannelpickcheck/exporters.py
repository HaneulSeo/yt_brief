from __future__ import annotations

from pathlib import Path

import pandas as pd

from .analytics import channel_summary, date_summary


def export_all(conn, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    tables = [
        "input_channels",
        "channels",
        "videos",
        "target_dates",
        "transcripts",
        "extracted_picks",
        "backtest_results",
    ]
    dfs = {}
    for t in tables:
        dfs[t] = pd.read_sql_query(f"SELECT * FROM {t}", conn)

    dfs["channels"].to_csv(out / "channels_resolved.csv", index=False)
    dfs["videos"].to_csv(out / "videos.csv", index=False)
    dfs["target_dates"].to_csv(out / "target_dates.csv", index=False)
    dfs["transcripts"][["video_id", "transcript_status", "error_message"]].to_csv(out / "transcripts_status.csv", index=False)
    dfs["extracted_picks"].to_csv(out / "extracted_picks.csv", index=False)
    dfs["backtest_results"].to_csv(out / "backtest_results.csv", index=False)

    ch = channel_summary(dfs["videos"], dfs["extracted_picks"], dfs["backtest_results"])
    ds = date_summary(dfs["backtest_results"])
    ch.to_csv(out / "channel_summary.csv", index=False)
    ds.to_csv(out / "date_summary.csv", index=False)

    video_report = dfs["videos"].merge(dfs["target_dates"], on="video_id", how="left").merge(
        dfs["backtest_results"], on="video_id", how="left", suffixes=("", "_bt")
    )
    video_report.to_csv(out / "video_level_report.csv", index=False)
    dfs["extracted_picks"][dfs["extracted_picks"]["mapping_quality"].isin(["unmapped", "ambiguous"])].to_csv(
        out / "unmapped_or_ambiguous_picks.csv", index=False
    )
