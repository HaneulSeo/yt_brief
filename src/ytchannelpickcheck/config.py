from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    youtube_api_key: str = Field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY", ""))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    tz: str = Field(default_factory=lambda: os.getenv("TZ", "Asia/Seoul"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    default_db: Path = Path("ytchannelpickcheck.db")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
