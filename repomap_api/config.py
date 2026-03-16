from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    cors_origins: list[str]
    clone_dir: str | None
    cache_dir: str
    cache_ttl_seconds: int
    max_async_workers: int
    job_ttl_seconds: int
    job_backend: str
    redis_url: str | None
    queue_name: str


def get_settings() -> Settings:
    origins_raw = os.getenv("REPOMAP_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = [origin.strip() for origin in origins_raw.split(",") if origin.strip()]
    clone_dir = os.getenv("REPOMAP_CLONE_DIR")
    default_cache_dir = Path(__file__).resolve().parents[1] / ".codex-temp-cache" / "analysis-cache"
    cache_dir = os.getenv("REPOMAP_CACHE_DIR", str(default_cache_dir))
    cache_ttl_seconds = int(os.getenv("REPOMAP_CACHE_TTL_SECONDS", "86400"))
    max_async_workers = int(os.getenv("REPOMAP_MAX_ASYNC_WORKERS", "2"))
    job_ttl_seconds = int(os.getenv("REPOMAP_JOB_TTL_SECONDS", "7200"))
    job_backend = os.getenv("REPOMAP_JOB_BACKEND", "memory").strip().lower() or "memory"
    redis_url = os.getenv("REPOMAP_REDIS_URL")
    queue_name = os.getenv("REPOMAP_QUEUE_NAME", "repomap-analysis")
    return Settings(
        cors_origins=origins,
        clone_dir=clone_dir,
        cache_dir=cache_dir,
        cache_ttl_seconds=cache_ttl_seconds,
        max_async_workers=max_async_workers,
        job_ttl_seconds=job_ttl_seconds,
        job_backend=job_backend,
        redis_url=redis_url,
        queue_name=queue_name,
    )
