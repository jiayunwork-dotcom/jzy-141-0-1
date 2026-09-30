"""Rolling-origin backtesting for Holt-Winters and seasonal naive baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from .fitting import FitResult, fit_all_specs, fit_model
from .schema import ALL_SPECS, ModelSpec
from .validation import validate_series

Progress = Callable[[int, int, str], None] | None


@dataclass
class BacktestConfig:
    m: int
    h: int = 8
    start_index: int | None = None
    step: int = 1
    origins: int | None = None
    confidence: float = 0.95
    seasonal: str | None = None
    trend: str | None = None
    damped: bool | None = None
    fixed_params: dict[str, float] | None = None


@dataclass
class OriginResult:
    origin: int
    model_name: str
    actual: list[float]
    forecast: list[float]
    naive_forecast: list[float]
    errors: list[float]
    naive_errors: list[float]
    mae: float
    mape: float | None
    mase: float | None
    naive_mae: float
    naive_mape: float | None
    naive_mase: float | None


def _safe_mean(values: Sequence[float | None]) -> float | None:
    finite = [float(v) for v in values if v is not None and np.isfinite(v)]
    return float(np.mean(finite)) if finite else None


def origin_indices(n: int, m: int, h: int, cfg: BacktestConfig) -> list[int]:
    start = cfg.start_index if cfg.start_index is not None else max(2 * m, n - h - 4)
    if start < 2 * m:
        raise ValueError(f"第一个回测原点必须至少为 {2 * m}")
    if start + h > n:
        raise ValueError("至少第一个回测原点之后需要有完整 h 期实际值")
    if cfg.step < 1:
        raise ValueError("origin step 必须为正整数")
    end = n - h
    origins = list(range(start, end + 1, cfg.step))
    if cfg.origins is not None:
        if cfg.origins < 1:
            raise ValueError("origins 必须为正整数")
        origins = origins[: cfg.origins]
    return origins


def seasonal_naive(y: np.ndarray, origin: int, h: int, m: int) -> np.ndarray:
    if origin < m:
        raise ValueError("季节朴素法需要至少一个完整季节历史")
    start = origin - m
    return y[start : start + h].astype(float)


def _fit_one(
    train: np.ndarray,
    cfg: BacktestConfig,
) -> FitResult:
    fixed = cfg.fixed_params
    if cfg.seasonal is None:
        best, _ = fit_all_specs(train, cfg.m, cfg.h, cfg.confidence, ALL_SPECS)
        return best
    if cfg.trend is None:
        trend = "none"
    else:
        trend = cfg.trend
    damped = bool(cfg.damped) if cfg.damped is not None else False
    spec = ModelSpec(cfg.seasonal, trend, damped)  # type: ignore[arg-type]
    return fit_model(train, cfg.m, spec, cfg.h, cfg.confidence, fixed)


def run_backtest(
    values: np.ndarray | list[float],
    cfg: BacktestConfig,
    progress: Progress = None,
) -> dict[str, object]:
    y = np.asarray(values, dtype=float)
    if cfg.h < 1:
        raise ValueError("预测步长 h 必须为正整数")
    # Validation through a representative spec also enforces two seasons and
    # positivity requirements relevant to auto-select multiplicative options.
    validate_series(y, cfg.m, ModelSpec("additive", "none", False))
    indexes = origin_indices(len(y), cfg.m, cfg.h, cfg)
    if not indexes:
        raise ValueError("没有可用的滚动原点")

    origin_results: list[OriginResult] = []
    for number, origin in enumerate(indexes, start=1):
        if progress:
            progress(number - 1, len(indexes), f"正在回测原点 {origin}")
        train = y[:origin]
        result = _fit_one(train, cfg)
        fc = result.forecast
        if fc is None:
            raise RuntimeError("内部错误：回测拟合未返回预测")
        pred = np.asarray(fc["point"], dtype=float)
        actual = y[origin : origin + cfg.h]
        naive = seasonal_naive(y, origin, cfg.h, cfg.m)
        errors = actual - pred
        naive_errors = actual - naive

        # MASE scale is computed only from training data available at this origin.
        diffs = np.abs(train[cfg.m :] - train[: -cfg.m])
        scale = float(np.mean(diffs)) if len(diffs) else float("nan")
        mase = float(np.mean(np.abs(errors)) / scale) if np.isfinite(scale) and scale > 0 else None
        naive_mase = float(np.mean(np.abs(naive_errors)) / scale) if np.isfinite(scale) and scale > 0 else None
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.abs(errors) / np.abs(actual)
            naive_ratio = np.abs(naive_errors) / np.abs(actual)
        mape = float(np.mean(ratio[actual != 0]) * 100) if np.any(actual != 0) else None
        naive_mape = float(np.mean(naive_ratio[actual != 0]) * 100) if np.any(actual != 0) else None

        origin_results.append(
            OriginResult(
                origin=int(origin),
                model_name=result.spec.name,
                actual=[float(v) for v in actual],
                forecast=[float(v) for v in pred],
                naive_forecast=[float(v) for v in naive],
                errors=[float(v) for v in errors],
                naive_errors=[float(v) for v in naive_errors],
                mae=float(np.mean(np.abs(errors))),
                mape=mape,
                mase=mase,
                naive_mae=float(np.mean(np.abs(naive_errors))),
                naive_mape=naive_mape,
                naive_mase=naive_mase,
            )
        )
    if progress:
        progress(len(indexes), len(indexes), "回测完成")

    summary = _summarize(origin_results, cfg.h)
    return {
        "m": cfg.m,
        "h": cfg.h,
        "origins": [_origin_to_dict(o) for o in origin_results],
        "summary": summary,
    }


def _origin_to_dict(o: OriginResult) -> dict[str, object]:
    return {
        "origin": o.origin,
        "model_name": o.model_name,
        "actual": o.actual,
        "forecast": o.forecast,
        "naive_forecast": o.naive_forecast,
        "errors": o.errors,
        "naive_errors": o.naive_errors,
        "mae": o.mae,
        "mape": o.mape,
        "mase": o.mase,
        "naive_mae": o.naive_mae,
        "naive_mape": o.naive_mape,
        "naive_mase": o.naive_mase,
    }


def _summarize(rows: list[OriginResult], h: int) -> dict[str, object]:
    all_errors = np.asarray([r.errors for r in rows], dtype=float)
    all_naive = np.asarray([r.naive_errors for r in rows], dtype=float)
    actuals = np.asarray([r.actual for r in rows], dtype=float)

    def metric_block(errors: np.ndarray, mases: list[float | None]) -> dict[str, object]:
        abs_e = np.abs(errors)
        nonzero = actuals != 0
        per_origin_mae = np.mean(abs_e, axis=1)
        # Global MAPE rather than silently treating zero-actual origins differently.
        mape_values = abs_e[nonzero] / np.abs(actuals[nonzero]) * 100 if np.any(nonzero) else np.array([])
        per_horizon = [
            {
                "horizon": k + 1,
                "mae": float(np.mean(abs_e[:, k])),
                "mape": float(np.mean(abs_e[:, k][actuals[:, k] != 0] / np.abs(actuals[:, k][actuals[:, k] != 0])) * 100)
                if np.any(actuals[:, k] != 0)
                else None,
            }
            for k in range(h)
        ]
        return {
            "mae": float(np.mean(abs_e)),
            "mape": float(np.mean(mape_values)) if len(mape_values) else None,
            "mase": _safe_mean(mases),
            "per_origin_mae": [float(v) for v in per_origin_mae],
            "per_horizon": per_horizon,
        }

    hw = metric_block(all_errors, [r.mase for r in rows])
    naive = metric_block(all_naive, [r.naive_mase for r in rows])
    return {
        "holt_winters": hw,
        "seasonal_naive": naive,
        "origin_count": len(rows),
        "mae_improvement_pct": float((naive["mae"] - hw["mae"]) / naive["mae"] * 100)
        if naive["mae"]
        else None,
    }
