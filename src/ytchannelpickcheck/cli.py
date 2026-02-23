from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .config import get_settings
from .db import init_db
from .exporters import export_all
from .pipeline import (
    DEFAULT_KEYWORDS,
    analyze_stage,
    backtest_stage,
    discover_videos,
    extract_stage,
    parse_target_dates_stage,
    resolve_channels,
    transcripts_stage,
)
from .youtube_channel_client import YouTubeChannelClient

app = typer.Typer(help="YouTube channel pick checker")
console = Console()


@app.command("init-db")
def cmd_init_db(db: str = typer.Option("ytchannelpickcheck.db")):
    init_db(db)
    console.log(f"initialized {db}")


@app.command("resolve-channels")
def cmd_resolve_channels(channels_file: str = typer.Option(...), db: str = "ytchannelpickcheck.db"):
    yt = YouTubeChannelClient(get_settings().youtube_api_key)
    resolve_channels(db, channels_file, yt)


@app.command("discover")
def cmd_discover(
    channels_file: str = typer.Option(...),
    start_date: str = typer.Option(...),
    end_date: str = typer.Option(...),
    db: str = "ytchannelpickcheck.db",
    all_videos: bool = False,
    video_keywords: str = ",".join(DEFAULT_KEYWORDS),
):
    keywords = [x.strip() for x in video_keywords.split(",") if x.strip()]
    discover_videos(db, start_date, end_date, all_videos=all_videos, keywords=keywords)


@app.command("parse-target-dates")
def cmd_parse_targets(start_date: str = typer.Option(...), end_date: str = typer.Option(...), db: str = "ytchannelpickcheck.db"):
    parse_target_dates_stage(db, start_date, end_date)


@app.command("transcripts")
def cmd_transcripts(db: str = "ytchannelpickcheck.db", retry_failed: bool = False, start_date: str = "", end_date: str = ""):
    transcripts_stage(db, retry_failed=retry_failed)


@app.command("extract")
def cmd_extract(db: str = "ytchannelpickcheck.db", use_llm: bool = False, start_date: str = "", end_date: str = ""):
    extract_stage(db, use_llm=use_llm)


@app.command("backtest")
def cmd_backtest(
    db: str = "ytchannelpickcheck.db",
    week_window: int = 5,
    intraday_hit: float = 0.10,
    close_hit: float = 0.05,
    start_date: str = "",
    end_date: str = "",
):
    backtest_stage(db, week_window=week_window, intraday_hit=intraday_hit, close_hit=close_hit)


@app.command("analyze")
def cmd_analyze(db: str = "ytchannelpickcheck.db", start_date: str = "", end_date: str = ""):
    analyze_stage(db)


@app.command("export")
def cmd_export(out_dir: str = "exports", db: str = "ytchannelpickcheck.db"):
    from .db import connect

    with connect(db) as conn:
        export_all(conn, out_dir)


@app.command("run")
def cmd_run(
    channels_file: str = typer.Option(...),
    start_date: str = typer.Option(...),
    end_date: str = typer.Option(...),
    db: str = "ytchannelpickcheck.db",
    all_videos: bool = False,
    video_keywords: str = ",".join(DEFAULT_KEYWORDS),
    use_llm: bool = False,
    week_window: int = 5,
):
    init_db(db)
    yt = YouTubeChannelClient(get_settings().youtube_api_key)
    keywords = [x.strip() for x in video_keywords.split(",") if x.strip()]
    resolve_channels(db, channels_file, yt)
    discover_videos(db, start_date, end_date, all_videos, keywords)
    parse_target_dates_stage(db, start_date, end_date)
    transcripts_stage(db)
    extract_stage(db, use_llm=use_llm)
    backtest_stage(db, week_window=week_window)
    analyze_stage(db)
    from .db import connect

    with connect(db) as conn:
        export_all(conn, "exports")


@app.command("dashboard")
def cmd_dashboard(db: str = "ytchannelpickcheck.db"):
    import subprocess

    subprocess.run(["streamlit", "run", str(Path(__file__).with_name("dashboard_app.py")), "--", "--db", db], check=False)


if __name__ == "__main__":
    app()
