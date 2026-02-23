from __future__ import annotations

import re

from .krx_mapper import get_krx_universe, map_to_ticker, normalize_name
from .schemas import ExtractedPick


def extract_picks(video_id: str, title: str, description: str, transcript_text: str | None, use_llm: bool = False) -> list[ExtractedPick]:
    text = " ".join([title or "", description or "", transcript_text or ""])
    universe = get_krx_universe()
    picks: dict[str, ExtractedPick] = {}

    for raw_name in set(re.findall(r"[가-힣A-Za-z]{2,10}", text)):
        norm = normalize_name(raw_name)
        if norm in universe:
            ticker, quality = map_to_ticker(raw_name)
            score = 0.85 if quality != "unmapped" else 0.3
            p = ExtractedPick(
                video_id=video_id,
                raw_mention=raw_name,
                normalized_name=raw_name,
                ticker=ticker,
                extraction_method="dict",
                confidence_score=score,
                evidence_text=f"matched:{raw_name}",
                is_primary_recommendation=False,
            )
            if raw_name not in picks or picks[raw_name].confidence_score < p.confidence_score:
                picks[raw_name] = p

    primary_hits = re.findall(r"(\d+)\s*[.)]\s*([가-힣A-Za-z]{2,10})", text)
    for rank_str, name in primary_hits:
        ticker, _ = map_to_ticker(name)
        picks[name] = ExtractedPick(
            video_id=video_id,
            pick_rank=int(rank_str),
            raw_mention=name,
            normalized_name=name,
            ticker=ticker,
            extraction_method="hybrid",
            confidence_score=0.9,
            evidence_text=f"ranked:{rank_str}",
            is_primary_recommendation=True,
        )

    return list(picks.values())
