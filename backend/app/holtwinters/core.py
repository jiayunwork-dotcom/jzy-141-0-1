from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .initialization import initialize
from .schema import ModelSpec


@dataclass(frozen=True)
class HWParams:
    alpha: float
    beta: float = 0.0
    gamma: float = 0.0
    phi: float = 1.0


@dataclass
class HWState:
    level: float
    trend: float
    seasonal: np.ndarray
    next_season_index: int = 0


@dataclass
class RecursionResult:
    fitted: np.ndarray
    residuals: np.ndarray
    sse: float
    final_state: HWState
    states: list[HWState]


def future_horizon_level(level: float, trend: float, h: int, spec: ModelSpec, phi: float) -> float:
    if spec.trend == "none":
        return level
    if spec.damped:
        if abs(phi - 1.0) < 1e-15:
            return level + h * trend
        return level + trend * phi * (1.0 - phi**h) / (1.0 - phi)
    return level + h * trend


def forecast_from_state(
    state: HWState,
    h: int,
    m: int,
    spec: ModelSpec,
    params: HWParams,
) -> np.ndarray:
    levels = np.array(
        [future_horizon_level(state.level, state.trend, k, spec, params.phi) for k in range(1, h + 1)]
    )
    offset = int(getattr(state, "next_season_index", 0))
    seasons = state.seasonal[(np.arange(h) + offset) % m]
    if spec.seasonal == "additive":
        return levels + seasons
    return levels * seasons


def canonicalize(level: float, trend: float, seasonal: np.ndarray, spec: ModelSpec,
                 next_season_index: int = 0) -> HWState:
    """Return a state whose stored seasonal vector satisfies the normalization."""
    s = seasonal.copy().astype(float)
    l = float(level)
    if spec.seasonal == "additive":
        shift = float(np.mean(s))
        s -= shift
        l += shift
        b = float(trend)
    else:
        scale = float(np.mean(s))
        s /= scale
        l *= scale
        b = float(trend) * scale
    return HWState(l, b, s, int(next_season_index) % len(s))


def fit_recursion(y: np.ndarray, m: int, spec: ModelSpec, params: HWParams) -> RecursionResult:
    """Run the documented component-form Holt-Winters recursions.

    With A_t = l_{t-1} + b_{t-1} (or l + phi*b when damped):
      additive      yhat=A+S, l=alpha*(y-S)+(1-alpha)*A, S=gamma*(y-l)+(1-gamma)*S
      multiplicative yhat=A*S, l=alpha*(y/S)+(1-alpha)*A, S=gamma*(y/l)+(1-gamma)*S
    For trend models b_t=beta*(l_t-l_{t-1})+(1-beta)*b_{t-1}, replacing the
    lagged b by phi*b in the damped variant.  The first fitted value uses l0+s0
    (or l0*s0); after that the trend advances the level.
    """
    l, b, s = initialize(y, m, spec)
    fitted = np.empty(len(y), dtype=float)
    residuals = np.empty(len(y), dtype=float)
    states: list[HWState] = []

    for t, value in enumerate(y):
        # Initial state is aligned with the first observation: t=0 uses s0.
        idx = t % m
        if t == 0:
            prior_level = l
            prior_b = 0.0
        else:
            prior_level = l
            prior_b = params.phi * b if (spec.trend == "additive" and spec.damped) else (
                b if spec.trend == "additive" else 0.0
            )
        level_trend = prior_level + prior_b
        season = s[idx]
        pred = level_trend + season if spec.seasonal == "additive" else level_trend * season
        if not np.isfinite(pred):
            raise ValueError("递推预测不是有限数值")
        if spec.seasonal == "multiplicative" and (level_trend <= 0 or season <= 0 or pred <= 0):
            raise ValueError("乘法模型在递推中产生了非正预测")

        residual = float(value - pred)
        fitted[t] = pred
        residuals[t] = residual
        old_l = l

        if spec.seasonal == "additive":
            deseasonalized = value - s[idx]
            new_l = params.alpha * deseasonalized + (1.0 - params.alpha) * level_trend
            new_s_value = params.gamma * (value - new_l) + (1.0 - params.gamma) * s[idx]
        else:
            deseasonalized = value / s[idx]
            new_l = params.alpha * deseasonalized + (1.0 - params.alpha) * level_trend
            if new_l <= 0:
                raise ValueError("乘法模型在递推中产生了非正水平")
            new_s_value = params.gamma * (value / new_l) + (1.0 - params.gamma) * s[idx]
            if new_s_value <= 0:
                raise ValueError("乘法模型在递推中产生了非正季节分量")

        if spec.trend == "additive":
            damped_old_b = params.phi * b if spec.damped else b
            new_b = params.beta * (new_l - old_l) + (1.0 - params.beta) * damped_old_b
        else:
            new_b = 0.0

        l = float(new_l)
        b = float(new_b)
        s = s.copy()
        s[idx] = float(new_s_value)
        states.append(HWState(l, b, s.copy()))

    final = canonicalize(
        states[-1].level,
        states[-1].trend,
        states[-1].seasonal,
        spec,
        next_season_index=len(y) % m,
    )
    sse = float(np.sum(residuals * residuals))
    return RecursionResult(fitted, residuals, sse, final, states)
