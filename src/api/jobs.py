"""Thread-safe in-process refresh job registry.

The v1 contract keeps job state behind an interface so a durable queue can
replace this single-process implementation without changing HTTP shapes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from src.api.contracts import DataState, Identity, JobResponse, JobStatus


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, JobResponse] = {}
        self._lock = Lock()

    def create(self, identity: Identity) -> JobResponse:
        now = datetime.now(timezone.utc)
        job_id = uuid4().hex
        job = JobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            identity=identity,
        )
        with self._lock:
            self._jobs[job_id] = job
        return job.model_copy(deep=True)

    def get(self, job_id: str) -> JobResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job else None

    def running(self, job_id: str) -> None:
        self._update(job_id, status=JobStatus.RUNNING)

    def succeeded(self, job_id: str, result: dict[str, Any]) -> None:
        self._update(job_id, status=JobStatus.SUCCEEDED, result=result)

    def failed(self, job_id: str, error: str) -> None:
        self._update(
            job_id,
            status=JobStatus.FAILED,
            error=error,
            data_state=DataState.PROVIDER_FAILURE,
        )

    def _update(self, job_id: str, **values: Any) -> None:
        with self._lock:
            self._jobs[job_id] = self._jobs[job_id].model_copy(
                update={**values, "updated_at": datetime.now(timezone.utc)}
            )
