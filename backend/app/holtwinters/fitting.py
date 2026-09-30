from __future__ import annotations

import numpy as np

from dataclasses import dataclass

from .core import HWParams, RecursionResult, fit_recursion
from .intervals import forecast_intervals
from .optimizer import optimize_parameters
from .schema import ModelSpec, ALL_SPECS
from .validation import validate_series


@dataclass
class FitResult:
    spec: ModelSpec
    params: HWParams
    recursion: RecursionResult
    n: int
    sse: float
    aic: float
    m: int
    forecast: dict[str, np.ndarray] | None = None


def calculate_aic(sse: float, n: int, n_params: int) -> float:
    if sse < 0:
        raise ValueError("SSE 不能为负")
    sigma2 = sse / n
    if sigma2 <= 1e-300:
        # Continuous limit for an exact synthetic fit; avoids -infinity while
        # still representing an exceptionally high likelihood.
        return float(2 * n_params - 700.0 * n)
    return float(n * np.log(sigma2) + 2 * n_params)


def fit_model(
    values: np.ndarray | list[float],
    m: int,
    spec: ModelSpec,
    horizon: int = 0,
    confidence: float = 0.95,
    fixed_params: dict[str, float] | None = None,
) -> FitResult:
    y = validate_series(values, m, spec)
    fixed_params = _validated_fixed(fixed_params or {}, spec)

    def objective(p: HWParams) -> float:
        return fit_recursion(y, m, spec, p).sse

    params, _ = optimize_parameters(objective, spec, fixed_params)
    rec = fit_recursion(y, m, spec, params)
    forecast = None
    if horizon > 0:
        forecast = forecast_intervals(
            rec.final_state, rec.fitted, rec.residuals, horizon, m, spec, params, confidence
        )
    return FitResult(
        spec=spec,
        params=params,
        recursion=rec,
        n=len(y),
        sse=rec.sse,
        aic=calculate_aic(rec.sse, len(y), spec.n_param),
        m=m,
        forecast=forecast,
    )


def fit_all_specs(
    values: np.ndarray | list[float],
    m: int,
    horizon: int = 0,
    confidence: float = 0.95,
    specs: tuple[ModelSpec, ...] = ALL_SPECS,
) -> tuple[FitResult | None, list[FitResult]]:
    results: list[FitResult] = []
    for spec in specs:
        try:
            results.append(fit_model(values, m, spec, horizon, confidence))
        except (ValueError, OverflowError, FloatingPointError):
            # Multiplicative candidates can be inadmissible for positive but
            # awkward series. They are omitted with explicit storage of errors
            # at the API layer.
            continue
    if not results:
        raise ValueError("所有候选模型都无法拟合该序列")
    best = min(results, key=lambda r: r.aic)
    return best, results


def _validated_fixed(fixed: dict[str, float], spec: ModelSpec) -> dict[str, float]:
    allowed = {"alpha", "beta", "gamma"}
    if spec.damped:
        allowed.add("phi")
    for key, value in fixed.items():
        if key not in allowed:
            raise ValueError(f"模型 {spec.name} 不支持锁定参数 {key}")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"参数 {key} 必须位于 [0, 1]")
    if "beta" in fixed and spec.trend == "none":
        raise ValueError("无趋势模型没有 beta 参数")
    if "phi" in fixed and not spec.damped:
        raise ValueError("非阻尼模型没有 phi 参数")
    return {k: float(v) for k, v in fixed.items()}
