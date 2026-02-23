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
        "inferred_recommendations",
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
    dfs["inferred_recommendations"].to_csv(out / "inferred_recommendations.csv", index=False)
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


    inf = dfs["inferred_recommendations"]
    expected = dfs["videos"][["video_id", "title"]].copy()
    expected["expected_count"] = expected["title"].str.contains("3종목", na=False).map({True: 3, False: 0})
    inf_counts = inf.groupby("video_id").size().rename("inferred_count").reset_index()
    conf = inf.groupby("video_id")["confidence"].agg(lambda x: ",".join(sorted(set(x)))).rename("confidence_summary").reset_index()
    pivot = inf.sort_values(["video_id", "rec_rank"]).pivot_table(index="video_id", columns="rec_rank", values=["stock_name", "ticker"], aggfunc="first")
    pivot.columns = [f"rec{rank}_{'name' if kind == 'stock_name' else 'ticker'}" for kind, rank in pivot.columns]
    audit = expected.merge(inf_counts, on="video_id", how="left").merge(conf, on="video_id", how="left").merge(pivot.reset_index(), on="video_id", how="left")
    audit["inferred_count"] = audit["inferred_count"].fillna(0).astype(int)
    audit.to_csv(out / "video_inference_audit.csv", index=False)

    mention_counts = dfs["extracted_picks"].groupby("video_id").size().rename("raw_mentions_count").reset_index()
    compare = expected[["video_id"]].merge(mention_counts, on="video_id", how="left").merge(inf_counts, on="video_id", how="left")
    compare.to_csv(out / "mentions_vs_inferred_comparison.csv", index=False)
