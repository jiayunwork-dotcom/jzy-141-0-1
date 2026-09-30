from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder

from app.db import repository
from app.jobs import submit
from app.schemas_api import BacktestRequestModel, FitRequest, SeriesCreate
from app.services import backtest_service, fit_service, validate_weekly_dates

router = APIRouter(prefix="/api", tags=["forecast"])


def _serialize(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return json.loads(json.dumps(row, ensure_ascii=False, default=str))


def _load_series(series_id: str) -> dict[str, Any]:
    row = repository.get_series(series_id)
    if row is None:
        raise HTTPException(status_code=404, detail="序列不存在")
    return row


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/series")
def create_series(payload: SeriesCreate) -> dict[str, Any]:
    points = sorted(payload.points, key=lambda p: p.date)
    dates = [p.date for p in points]
    values = [float(p.value) for p in points]
    try:
        validate_weekly_dates(dates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _serialize(repository.create_series(payload.name, dates, values))  # type: ignore[return-value]


@router.get("/series")
def list_series() -> list[dict[str, Any]]:
    return [jsonable_encoder(r) for r in repository.list_series()]


@router.get("/series/{series_id}")
def get_series(series_id: UUID) -> dict[str, Any]:
    return jsonable_encoder(_load_series(str(series_id)))


@router.post("/series/{series_id}/fit")
def create_fit(series_id: UUID, payload: FitRequest) -> dict[str, Any]:
    row = _load_series(str(series_id))
    try:
        request = payload.model_dump()
        if payload.auto:
            request["auto"] = True
        job = repository.create_fit_run(str(series_id), request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    submit(
        "fit",
        str(job["job_id"]),
        fit_service,
        list(row["values"]),
        payload.m,
        request,
    )
    return jsonable_encoder(job)


@router.post("/series/{series_id}/backtest")
def create_backtest(series_id: UUID, payload: BacktestRequestModel) -> dict[str, Any]:
    row = _load_series(str(series_id))
    try:
        request = payload.model_dump(exclude_none=True)
        if not payload.auto:
            request["seasonal"] = payload.seasonal or "additive"
            request["trend"] = payload.trend or "none"
            request["damped"] = bool(payload.damped)
        else:
            request["seasonal"] = None
            request["trend"] = None
            request["damped"] = None
        job = repository.create_backtest_run(str(series_id), request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    submit(
        "backtest",
        str(job["job_id"]),
        backtest_service,
        list(row["values"]),
        request,
    )
    return jsonable_encoder(job)


@router.get("/jobs/{kind}/{job_id}")
def get_job(kind: str, job_id: UUID) -> dict[str, Any]:
    if kind not in {"fit", "backtest"}:
        raise HTTPException(status_code=404, detail="未知任务类型")
    row = repository.get_job(kind, str(job_id))
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return jsonable_encoder(row)


@router.get("/series/{series_id}/runs")
def list_runs(series_id: UUID) -> dict[str, list[dict[str, Any]]]:
    _load_series(str(series_id))
    return jsonable_encoder(repository.list_runs_for_series(str(series_id)))
