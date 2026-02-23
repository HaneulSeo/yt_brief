from __future__ import annotations

import time
from datetime import date, datetime

import requests

from .utils_time import KST, UTC

BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeChannelClient:
    def __init__(self, api_key: str, timeout: int = 20):
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, path: str, params: dict, retries: int = 5):
        params = {**params, "key": self.api_key}
        for i in range(retries):
            resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=self.timeout)
            if resp.status_code < 400:
                return resp.json()
            if resp.status_code in {429, 500, 502, 503, 504} and i < retries - 1:
                time.sleep(2**i)
                continue
            resp.raise_for_status()
        return {}

    def resolve_channel(self, raw: str) -> dict | None:
        if raw.startswith("UC"):
            data = self._request("channels", {"part": "snippet,contentDetails", "id": raw})
        else:
            q = raw.split("@")[-1].split("/")[-1]
            data = self._request("search", {"part": "snippet", "type": "channel", "q": q, "maxResults": 1})
            if not data.get("items"):
                return None
            cid = data["items"][0]["snippet"]["channelId"]
            data = self._request("channels", {"part": "snippet,contentDetails", "id": cid})
        items = data.get("items", [])
        if not items:
            return None
        item = items[0]
        return {
            "channel_id": item["id"],
            "channel_title": item["snippet"]["title"],
            "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"],
        }

    def list_uploads_in_range(self, uploads_playlist_id: str, start_date: date, end_date: date) -> list[dict]:
        out = []
        page_token = None
        while True:
            params = {
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": 50,
                "pageToken": page_token,
            }
            data = self._request("playlistItems", {k: v for k, v in params.items() if v})
            for item in data.get("items", []):
                sn = item.get("snippet", {})
                vid = sn.get("resourceId", {}).get("videoId")
                pub_raw = sn.get("publishedAt")
                if not vid or not pub_raw:
                    continue
                pub_utc = datetime.fromisoformat(pub_raw.replace("Z", "+00:00")).astimezone(UTC)
                pub_kst = pub_utc.astimezone(KST)
                if start_date <= pub_kst.date() <= end_date:
                    out.append(
                        {
                            "video_id": vid,
                            "channel_id": sn.get("channelId"),
                            "channel_title": sn.get("channelTitle"),
                            "title": sn.get("title", ""),
                            "description": sn.get("description", ""),
                            "published_at_utc": pub_utc.isoformat(),
                            "published_at_kst": pub_kst.isoformat(),
                            "url": f"https://www.youtube.com/watch?v={vid}",
                        }
                    )
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return out
