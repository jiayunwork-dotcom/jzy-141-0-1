"""In-process asynchronous job execution.

A bounded ThreadPoolExecutor gives independent workers to planners working on
different series. CPU-bound NumPy calls release very little GIL, but the pool
still isolates long jobs from the request path and surfaces progress; scaling
across containers only requires replacing this module with a real queue while
keeping the same repository/job API.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable
from typing import Any

from app.db.repository import update_job

_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="forecast-job")


def progress_callback(kind: str, job_id: str) -> Callable[[int, int, str], None]:
    def callback(done: int, total: int, message: str) -> None:
        pct = 8 + int(90 * done / max(total, 1))
        update_job(kind, job_id, "running", pct, message)

    return callback


def submit(kind: str, job_id: str, fn: Callable[..., dict[str, Any]], *args: Any) -> None:
    def wrapper() -> None:
        try:
            update_job(kind, job_id, "running", 5, "开始计算")
            result = fn(*args, progress_callback(kind, job_id))
            update_job(kind, job_id, "succeeded", 100, "完成", result=result)
        except Exception as exc:  # surfaced to UI and stored for debugging
            update_job(kind, job_id, "failed", 100, "计算失败", error=str(exc))

    _executor.submit(wrapper)


def shutdown() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)
