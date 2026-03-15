from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    cors_origins: list[str]
    clone_dir: str | None


def get_settings() -> Settings:
    origins_raw = os.getenv("REPOMAP_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
    clone_dir = os.getenv("REPOMAP_CLONE_DIR")
    return Settings(cors_origins=origins, clone_dir=clone_dir)
