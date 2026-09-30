from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.holtwinters.backtest import BacktestConfig, run_backtest
from app.holtwinters.fitting import fit_model
from app.holtwinters.schema import ALL_SPECS, ModelSpec
from app.holtwinters.serialize import fit_to_dict


def validate_weekly_dates(dates: list[date]) -> None:
    if len(dates) < 2:
        raise ValueError("至少需要两个日期")
    if any(d.weekday() != 0 for d in dates):
        raise ValueError("周起始日期必须是星期一")
    previous = dates[0]
    for current in dates[1:]:
        if current <= previous:
            raise ValueError("日期必须严格递增")
        if current - previous != timedelta(days=7):
            missing = previous + timedelta(days=7)
            raise ValueError(f"日期不连续，缺少周起始日：{missing.isoformat()}")
        previous = current


def fit_service(
    values: list[float],
    m: int,
    request: dict[str, Any],
    progress=None,
) -> dict[str, Any]:
    horizon = int(request.get("horizon", 8))
    confidence = float(request.get("confidence", 0.95))
    auto = bool(request.get("auto", True))
    fixed_params = request.get("fixed_params") or None

    def report(done: int, total: int, msg: str) -> None:
        if progress:
            progress(done, total, msg)

    if auto:
        candidates = []
        for idx, spec in enumerate(ALL_SPECS):
            report(idx, len(ALL_SPECS), f"拟合候选模型 {spec.name}")
            try:
                fit = fit_model(values, m, spec, horizon, confidence)
                candidates.append({"ok": True, "result": fit_to_dict(fit)})
            except Exception as exc:
                candidates.append(
                    {"ok": False, "model": spec.to_dict(), "error": str(exc)}
                )
        good = [c["result"] for c in candidates if c["ok"]]
        if not good:
            raise ValueError("所有候选模型均无法拟合")
        best = min(good, key=lambda r: r["aic"])
        report(len(ALL_SPECS), len(ALL_SPECS), "自动选型完成")
        return {"best": best, "candidates": candidates}

    spec = _spec_from_request(request)
    report(1, 3, f"拟合 {spec.name}")
    fit = fit_model(values, m, spec, horizon, confidence, fixed_params=fixed_params)
    report(3, 3, "计算预测区间")
    return {"best": fit_to_dict(fit), "candidates": [{"ok": True, "result": fit_to_dict(fit)}]}


def backtest_service(values: list[float], request: dict[str, Any], progress=None) -> dict[str, Any]:
    m = int(request.get("m", 52))
    h = int(request.get("h", 8))
    start = request.get("start_index")
    cfg = BacktestConfig(
        m=m,
        h=h,
        start_index=int(start) if start is not None else None,
        step=int(request.get("step", 1)),
        origins=int(request["origins"]) if request.get("origins") is not None else None,
        confidence=float(request.get("confidence", 0.95)),
        seasonal=request.get("seasonal"),
        trend=request.get("trend"),
        damped=request.get("damped"),
        fixed_params=request.get("fixed_params") or None,
    )
    return run_backtest(values, cfg, progress)


def _spec_from_request(request: dict[str, Any]) -> ModelSpec:
    seasonal = request.get("seasonal", "additive")
    trend = request.get("trend", "none")
    damped = bool(request.get("damped", False))
    if seasonal not in {"additive", "multiplicative"}:
        raise ValueError("seasonal 必须是 additive 或 multiplicative")
    if trend not in {"none", "additive"}:
        raise ValueError("trend 必须是 none 或 additive")
    return ModelSpec(seasonal, trend, damped)  # type: ignore[arg-type]


def extend_weekly_dates(dates: list[date], h: int) -> list[str]:
    return [(dates[-1] + timedelta(days=7 * (i + 1))).isoformat() for i in range(h)]
