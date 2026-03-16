from __future__ import annotations

from repomap_api.config import get_settings
from repomap_api.jobs import RedisJobStore, run_analysis_job as execute_analysis_job


def run_analysis_job(
    job_id: str,
    repo_url: str,
    branch: str | None,
    clone_dir: str | None,
    cache_dir: str | None,
    cache_ttl_seconds: int,
) -> None:
    settings = get_settings()
    if not settings.redis_url:
        raise RuntimeError("REPOMAP_REDIS_URL must be configured for Redis-backed workers.")

    store = RedisJobStore(settings.redis_url, job_ttl_seconds=settings.job_ttl_seconds)
    execute_analysis_job(
        job_id=job_id,
        repo_url=repo_url,
        branch=branch,
        clone_dir=clone_dir,
        cache_dir=cache_dir,
        cache_ttl_seconds=cache_ttl_seconds,
        store=store,
    )


def main() -> None:
    settings = get_settings()
    if settings.job_backend != "redis":
        raise RuntimeError("repomap worker requires REPOMAP_JOB_BACKEND=redis.")
    if not settings.redis_url:
        raise RuntimeError("REPOMAP_REDIS_URL must be configured for Redis-backed workers.")

    from redis import Redis
    from rq import Connection, Worker

    connection = Redis.from_url(settings.redis_url, decode_responses=True)
    with Connection(connection):
        worker = Worker([settings.queue_name], connection=connection)
        worker.work()


if __name__ == "__main__":
    main()
