# ytchannelpickcheck

Research/backtesting CLI for Korean YouTube stock-pick channels. It collects channel videos, parses implied target dates (e.g. `12/23 급등주`), extracts picks, maps to KRX tickers, and evaluates exact-day and 1-week outcomes.

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## YouTube API key
Create a YouTube Data API v3 key in Google Cloud Console and set it in `.env`.

## Environment
```bash
cp .env.example .env
# fill YOUTUBE_API_KEY
```

## Input channels file
TXT (one per line):
```txt
https://www.youtube.com/@somehandle
https://www.youtube.com/channel/UCxxxx
UCyyyyyyyyyyyyyyyyyyyyyy
```

CSV:
```csv
channel_url,channel_id,channel_name
https://www.youtube.com/@somehandle,,Alias
,UCyyyyyyyyyyyyyyyyyyyyyy,Another Alias
```

## Single-command run
```bash
ytchannelpickcheck run --channels-file channels.txt --start-date 2025-01-01 --end-date 2025-12-31 --db ytchannelpickcheck.db
```

## Stage commands
```bash
ytchannelpickcheck init-db --db ytchannelpickcheck.db
ytchannelpickcheck resolve-channels --channels-file channels.txt --db ytchannelpickcheck.db
ytchannelpickcheck discover --channels-file channels.txt --start-date 2025-01-01 --end-date 2025-12-31 --db ytchannelpickcheck.db
ytchannelpickcheck parse-target-dates --start-date 2025-01-01 --end-date 2025-12-31 --db ytchannelpickcheck.db
ytchannelpickcheck transcripts --db ytchannelpickcheck.db --retry-failed
ytchannelpickcheck extract --db ytchannelpickcheck.db --use-llm
ytchannelpickcheck backtest --db ytchannelpickcheck.db --week-window 5 --intraday-hit 0.10 --close-hit 0.05
ytchannelpickcheck analyze --db ytchannelpickcheck.db
ytchannelpickcheck export --db ytchannelpickcheck.db --out-dir exports
```

## Metrics
- **Exact day intraday hit**: target day high vs previous trading day close >= `+10%`.
- **Exact day close hit**: target day close vs previous trading day close >= `+5%`.
- **Week intraday hit**: max high within next N trading days vs previous close >= threshold.
- **Week close hit**: any close within next N trading days vs previous close >= threshold.

## Dashboard
```bash
ytchannelpickcheck dashboard --db ytchannelpickcheck.db
```

## Notes
- Transcript availability depends on caption availability and YouTube restrictions.
- Optional LLM extraction mode is only used when `--use-llm` and `OPENAI_API_KEY` are both provided.
- This is a research tool, not investment advice.

## Troubleshooting
- **YouTube quota exceeded**: reduce range and rerun stage-by-stage.
- **Transcript failures**: rerun with `--retry-failed`.
- **pykrx data gaps**: retry later or narrow date windows.
