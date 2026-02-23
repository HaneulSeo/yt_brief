from __future__ import annotations

import csv
import re
from pathlib import Path

YOUTUBE_CHANNEL_ID_RE = re.compile(r"^(UC[\w-]{20,})$")


def normalize_channel_input(value: str) -> str:
    v = value.strip()
    if not v:
        return ""
    return v.rstrip("/")


def parse_channel_line(value: str) -> dict:
    n = normalize_channel_input(value)
    if not n:
        return {"raw": value, "normalized": "", "channel_id": None, "url": None}
    if YOUTUBE_CHANNEL_ID_RE.match(n):
        return {"raw": value, "normalized": n, "channel_id": n, "url": None}
    if "youtube.com" in n:
        m = re.search(r"/channel/(UC[\w-]{20,})", n)
        channel_id = m.group(1) if m else None
        return {"raw": value, "normalized": n, "channel_id": channel_id, "url": n}
    return {"raw": value, "normalized": n, "channel_id": None, "url": n}


def load_channels_file(path: str | Path) -> list[dict]:
    path = Path(path)
    rows: list[dict] = []
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=2):
                raw = row.get("channel_url") or row.get("channel_id") or ""
                parsed = parse_channel_line(raw)
                parsed["channel_name"] = (row.get("channel_name") or "").strip() or None
                parsed["source_row"] = idx
                rows.append(parsed)
    else:
        with path.open("r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                parsed = parse_channel_line(line)
                parsed["channel_name"] = None
                parsed["source_row"] = idx
                rows.append(parsed)

    dedup = {}
    for row in rows:
        key = row["channel_id"] or row["normalized"]
        if key and key not in dedup:
            dedup[key] = row
    return list(dedup.values())
