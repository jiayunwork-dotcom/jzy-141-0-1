from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from .connection import conn


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def create_series(name: str, dates: list[date], values: list[float], period: str = "W") -> dict[str, Any]:
    sid = uuid.uuid4()
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                INSERT INTO series (id, name, dates, values, period)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, name, dates, values, period, created_at
                """,
                (sid, name, dates, values, period),
            )
            return cur.fetchone()  # type: ignore[return-value]


def list_series() -> list[dict[str, Any]]:
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, dates, values, period, created_at
                FROM series
                ORDER BY created_at DESC, name
                """
            )
            return cur.fetchall()  # type: ignore[return-value]


def get_series(series_id: uuid.UUID | str) -> dict[str, Any] | None:
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, dates, values, period, created_at
                FROM series WHERE id = %s
                """,
                (str(series_id),),
            )
            return cur.fetchone()


def create_fit_run(series_id: str, request: dict[str, Any]) -> dict[str, Any]:
    job_id = uuid.uuid4()
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fit_runs (series_id, job_id, request, status, message)
                VALUES (%s, %s, %s, 'pending', '排队中')
                RETURNING id, series_id, job_id, status, progress, message, request, created_at
                """,
                (series_id, job_id, _json(request)),
            )
            row = cur.fetchone()
    return row  # type: ignore[return-value]


def update_job(kind: str, job_id: str, status: str, progress: int, message: str,
               result: dict[str, Any] | None = None, error: str | None = None) -> None:
    table = "fit_runs" if kind == "fit" else "backtests"
    progress = max(0, min(100, int(progress)))
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                f"""
                UPDATE {table}
                SET status=%s, progress=%s, message=%s,
                    result=COALESCE(%s::jsonb, result),
                    error=%s,
                    finished_at=CASE WHEN %s IN ('succeeded','failed') THEN now() ELSE finished_at END
                WHERE job_id=%s
                """,
                (status, progress, message, _json(result) if result is not None else None, error, status, job_id),
            )


def get_job(kind: str, job_id: str) -> dict[str, Any] | None:
    table = "fit_runs" if kind == "fit" else "backtests"
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(f"SELECT * FROM {table} WHERE job_id=%s", (job_id,))
            return cur.fetchone()


def list_runs_for_series(series_id: str) -> dict[str, list[dict[str, Any]]]:
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT * FROM fit_runs WHERE series_id=%s ORDER BY created_at DESC",
                (series_id,),
            )
            fits = cur.fetchall()
            cur.execute(
                "SELECT * FROM backtests WHERE series_id=%s ORDER BY created_at DESC",
                (series_id,),
            )
            backtests = cur.fetchall()
    return {"fits": fits, "backtests": backtests}


def create_backtest_run(series_id: str, request: dict[str, Any]) -> dict[str, Any]:
    job_id = uuid.uuid4()
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                INSERT INTO backtests (series_id, job_id, request, status, message)
                VALUES (%s, %s, %s, 'pending', '排队中')
                RETURNING id, series_id, job_id, status, progress, message, request, created_at
                """,
                (series_id, job_id, _json(request)),
            )
            return cur.fetchone()  # type: ignore[return-value]
