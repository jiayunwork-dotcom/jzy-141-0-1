from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

DSN = os.getenv(
    "DATABASE_URL",
    "postgresql://forecast:forecast@postgres:5432/forecast",
)


@contextmanager
def conn() -> Iterator[psycopg.Connection]:
    connection = psycopg.connect(DSN, row_factory=dict_row, autocommit=False)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(retries: int = 30) -> None:
    sql = (Path(__file__).parent / "init.sql").read_text(encoding="utf-8")
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with psycopg.connect(DSN, autocommit=True) as connection:
                with connection.cursor() as cur:
                    cur.execute(sql)
            return
        except psycopg.OperationalError as exc:
            last_error = exc
            if attempt == retries - 1:
                raise
            import time

            time.sleep(1.0)
    if last_error:
        raise last_error
