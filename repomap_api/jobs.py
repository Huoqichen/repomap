from __future__ import annotations

import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Protocol

try:
    from redis import Redis
except ImportError:  # pragma: no cover - optional at runtime for memory mode
    Redis = None

try:
    from rq import Queue
except ImportError:  # pragma: no cover - optional at runtime for memory mode
    Queue = None

from repomap_api.schemas import AnalyzeJobResponse, AnalyzeResponse


@dataclass(slots=True)
class AnalysisJob:
    id: str
    repo_url: str
    branch: str | None
    status: str = "queued"
    progress: int = 0
    stage: str | None = "queued"
    cached: bool = False
    result: AnalyzeResponse | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_schema(self) -> AnalyzeJobResponse:
        return AnalyzeJobResponse(
            id=self.id,
            repo_url=self.repo_url,
            branch=self.branch,
            status=self.status,
            progress=self.progress,
            stage=self.stage,
            cached=self.cached,
            result=self.result,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> AnalysisJob:
        result_payload = payload.get("result")
        result = AnalyzeResponse.model_validate(result_payload) if isinstance(result_payload, dict) else None
        return cls(
            id=str(payload["id"]),
            repo_url=str(payload["repo_url"]),
            branch=payload.get("branch") if isinstance(payload.get("branch"), str) else None,
            status=str(payload.get("status", "queued")),
            progress=int(payload.get("progress", 0)),
            stage=payload.get("stage") if isinstance(payload.get("stage"), str) else None,
            cached=bool(payload.get("cached", False)),
            result=result,
            error=payload.get("error") if isinstance(payload.get("error"), str) else None,
            created_at=float(payload.get("created_at", time.time())),
            updated_at=float(payload.get("updated_at", time.time())),
        )

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "cached": self.cached,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.result is not None:
            payload["result"] = self.result.model_dump(mode="json")
        return payload


class AnalysisJobManager(Protocol):
    def submit(
        self,
        repo_url: str,
        branch: str | None,
        clone_dir: str | None,
        cache_dir: str | None,
        cache_ttl_seconds: int,
    ) -> AnalyzeJobResponse: ...

    def get(self, job_id: str) -> AnalyzeJobResponse | None: ...


class InMemoryAnalysisJobManager:
    def __init__(self, max_workers: int = 2, job_ttl_seconds: int = 7200) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="repomap-job")
        self._job_ttl_seconds = job_ttl_seconds
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        repo_url: str,
        branch: str | None,
        clone_dir: str | None,
        cache_dir: str | None,
        cache_ttl_seconds: int,
    ) -> AnalyzeJobResponse:
        job = AnalysisJob(id=uuid.uuid4().hex, repo_url=repo_url, branch=branch)
        with self._lock:
            self._purge_expired_locked()
            self._jobs[job.id] = job
        self._executor.submit(
            run_analysis_job,
            job.id,
            repo_url,
            branch,
            clone_dir,
            cache_dir,
            cache_ttl_seconds,
            InMemoryJobStoreAdapter(self),
        )
        return job.to_schema()

    def get(self, job_id: str) -> AnalyzeJobResponse | None:
        with self._lock:
            self._purge_expired_locked()
            job = self._jobs.get(job_id)
            return job.to_schema() if job else None

    def update(self, job_id: str, **updates: object) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in updates.items():
                setattr(job, key, value)
            job.updated_at = time.time()

    def _purge_expired_locked(self) -> None:
        if self._job_ttl_seconds <= 0:
            return
        now = time.time()
        expired_ids = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in {"completed", "failed"} and now - job.updated_at > self._job_ttl_seconds
        ]
        for job_id in expired_ids:
            self._jobs.pop(job_id, None)


class InMemoryJobStoreAdapter:
    def __init__(self, manager: InMemoryAnalysisJobManager) -> None:
        self._manager = manager

    def update(self, job_id: str, **updates: object) -> None:
        self._manager.update(job_id, **updates)


class RedisJobStore:
    def __init__(self, redis_url: str, job_ttl_seconds: int = 7200, prefix: str = "repomap:jobs") -> None:
        if Redis is None:
            raise RuntimeError("redis package is required for Redis-backed jobs.")
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._job_ttl_seconds = job_ttl_seconds
        self._prefix = prefix

    def create(self, job: AnalysisJob) -> None:
        self._write(job)

    def get(self, job_id: str) -> AnalysisJob | None:
        raw_payload = self._redis.get(self._key(job_id))
        if not raw_payload:
            return None
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return AnalysisJob.from_payload(payload)

    def update(self, job_id: str, **updates: object) -> None:
        job = self.get(job_id)
        if job is None:
            return
        for key, value in updates.items():
            setattr(job, key, value)
        job.updated_at = time.time()
        self._write(job)

    def _write(self, job: AnalysisJob) -> None:
        self._redis.set(self._key(job.id), json.dumps(job.to_payload()), ex=self._job_ttl_seconds or None)

    def _key(self, job_id: str) -> str:
        return f"{self._prefix}:{job_id}"


class RedisAnalysisJobManager:
    def __init__(
        self,
        redis_url: str,
        queue_name: str = "repomap-analysis",
        job_ttl_seconds: int = 7200,
    ) -> None:
        if Redis is None or Queue is None:
            raise RuntimeError("redis and rq packages are required for Redis-backed jobs.")
        self._redis_url = redis_url
        self._queue_name = queue_name
        self._job_ttl_seconds = job_ttl_seconds
        self._store = RedisJobStore(redis_url, job_ttl_seconds=job_ttl_seconds)
        self._queue = Queue(name=queue_name, connection=Redis.from_url(redis_url, decode_responses=True))

    def submit(
        self,
        repo_url: str,
        branch: str | None,
        clone_dir: str | None,
        cache_dir: str | None,
        cache_ttl_seconds: int,
    ) -> AnalyzeJobResponse:
        job = AnalysisJob(id=uuid.uuid4().hex, repo_url=repo_url, branch=branch)
        self._store.create(job)
        self._queue.enqueue(
            "repomap_api.worker.run_analysis_job",
            job.id,
            repo_url,
            branch,
            clone_dir,
            cache_dir,
            cache_ttl_seconds,
            result_ttl=self._job_ttl_seconds,
            failure_ttl=self._job_ttl_seconds,
            job_timeout=max(cache_ttl_seconds, 3600),
        )
        return job.to_schema()

    def get(self, job_id: str) -> AnalyzeJobResponse | None:
        job = self._store.get(job_id)
        return job.to_schema() if job else None


def run_analysis_job(
    job_id: str,
    repo_url: str,
    branch: str | None,
    clone_dir: str | None,
    cache_dir: str | None,
    cache_ttl_seconds: int,
    store: InMemoryJobStoreAdapter | RedisJobStore,
) -> None:
    from repomap_api.service import analyze_remote_repository

    store.update(job_id, status="running", progress=5, stage="queued")
    try:
        result = analyze_remote_repository(
            repo_url=repo_url,
            branch=branch,
            clone_dir=clone_dir,
            cache_dir=cache_dir,
            cache_ttl_seconds=cache_ttl_seconds,
            progress_callback=lambda stage, progress: _on_progress(store, job_id, stage, progress),
        )
    except Exception as error:  # noqa: BLE001
        store.update(job_id, status="failed", progress=100, stage="failed", error=str(error))
        return

    cached = False
    current_job = getattr(store, "get", lambda _job_id: None)(job_id)
    if current_job is not None:
        cached = current_job.cached

    store.update(
        job_id,
        status="completed",
        progress=100,
        stage="completed",
        result=result,
        cached=cached,
    )


def _on_progress(
    store: InMemoryJobStoreAdapter | RedisJobStore,
    job_id: str,
    stage: str,
    progress: int,
) -> None:
    updates: dict[str, object] = {
        "stage": stage,
        "progress": progress,
    }
    if stage == "cache_hit":
        updates["cached"] = True
        updates["status"] = "running"
    elif stage != "completed":
        updates["status"] = "running"
    store.update(job_id, **updates)


_JOB_MANAGER: AnalysisJobManager | None = None
_JOB_MANAGER_LOCK = threading.Lock()


def get_job_manager(
    backend: str = "memory",
    max_workers: int = 2,
    job_ttl_seconds: int = 7200,
    redis_url: str | None = None,
    queue_name: str = "repomap-analysis",
) -> AnalysisJobManager:
    global _JOB_MANAGER
    with _JOB_MANAGER_LOCK:
        if _JOB_MANAGER is None:
            if backend == "redis":
                if not redis_url:
                    raise RuntimeError("REPOMAP_REDIS_URL must be set when REPOMAP_JOB_BACKEND=redis.")
                _JOB_MANAGER = RedisAnalysisJobManager(
                    redis_url=redis_url,
                    queue_name=queue_name,
                    job_ttl_seconds=job_ttl_seconds,
                )
            else:
                _JOB_MANAGER = InMemoryAnalysisJobManager(
                    max_workers=max_workers,
                    job_ttl_seconds=job_ttl_seconds,
                )
        return _JOB_MANAGER


def reset_job_manager() -> None:
    global _JOB_MANAGER
    with _JOB_MANAGER_LOCK:
        _JOB_MANAGER = None
