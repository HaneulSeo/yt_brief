from __future__ import annotations

from youtube_transcript_api import YouTubeTranscriptApi


class TranscriptClient:
    def __init__(self):
        self.api = YouTubeTranscriptApi()

    @staticmethod
    def _snip_get(snippet, key: str, default=None):
        if isinstance(snippet, dict):
            return snippet.get(key, default)
        return getattr(snippet, key, default)

    def _join_text(self, snippets) -> str:
        return " ".join(
            [
                text
                for text in (self._snip_get(snippet, "text", "") for snippet in snippets)
                if text
            ]
        )

    def fetch(self, video_id: str) -> dict:
        try:
            transcript_list = self.api.list(video_id)
            for langs in (["ko"], ["ko-KR"], ["en"]):
                try:
                    t = transcript_list.find_transcript(langs)
                    data = t.fetch()
                    return {
                        "status": "success",
                        "lang": t.language_code,
                        "is_generated": bool(getattr(t, "is_generated", False)),
                        "text": self._join_text(data),
                        "source": "youtube-transcript-api",
                        "error": None,
                    }
                except Exception:
                    continue
            generated = transcript_list.find_generated_transcript(["ko", "en"])
            data = generated.fetch()
            return {
                "status": "success",
                "lang": generated.language_code,
                "is_generated": True,
                "text": self._join_text(data),
                "source": "youtube-transcript-api",
                "error": None,
            }
        except Exception as e:
            return {
                "status": "failed",
                "lang": None,
                "is_generated": None,
                "text": None,
                "source": "youtube-transcript-api",
                "error": str(e),
            }
