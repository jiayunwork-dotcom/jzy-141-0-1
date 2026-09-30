from __future__ import annotations

import math

import numpy as np

from .core import HWParams, HWState, forecast_from_state
from .schema import ModelSpec


def normal_quantile(p: float) -> float:
    """Inverse standard normal CDF (Peter Acklam rational approximation)."""
    if not 0.0 < p < 1.0:
        raise ValueError("置信水平对应的尾概率必须位于 (0, 1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
        )
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1
        )
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
        (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1
    )


def _trend_sum(h: int, phi: float, damped: bool) -> float:
    if not damped:
        return float(h)
    if abs(phi - 1.0) < 1e-14:
        return float(h)
    return float(phi * (1.0 - phi**h) / (1.0 - phi))


def innovation_coefficients(h: int, m: int, spec: ModelSpec, p: HWParams) -> np.ndarray:
    """Return q_0, ..., q_{h-1} used in h-step prediction variance.

    q_0=1 for the innovation in the target period. After one update, the
    component-form recursions propagate a unit innovation as level alpha,
    trend beta*alpha, and seasonal gamma*(1-alpha); that updated seasonal
    component next affects forecasts at lag m, 2m, .... The coefficients are
    therefore cumulative squares and naturally non-decreasing before numerical
    adjustment.
    """
    if h <= 0:
        return np.array([], dtype=float)
    q = [1.0]
    for lag in range(1, h):
        level_term = p.alpha
        if spec.trend == "additive":
            level_term += p.beta * p.alpha * _trend_sum(lag, p.phi, spec.damped)
        seasonal_term = 0.0
        if lag % m == 0:
            seasonal_term = p.gamma * (1.0 - p.alpha)
        # Damped season component persists through intervening seasonal updates
        # only when there are intervening observations at same phase. For lag
        # m, this is its first reuse; factor is one.
        if lag >= m:
            seasonal_term *= (1.0 - p.gamma) ** (lag // m - 1)
        q.append(level_term + seasonal_term)
    return np.asarray(q, dtype=float)


def forecast_intervals(
    state: HWState,
    fitted: np.ndarray,
    residuals: np.ndarray,
    h: int,
    m: int,
    spec: ModelSpec,
    params: HWParams,
    level: float = 0.95,
) -> dict[str, np.ndarray]:
    """Analytical normal forecast intervals.

    Additive models use the variance of residuals y-yhat. Multiplicative models
    use a first-order approximation on relative residuals (y-yhat)/yhat and
    convert relative standard errors back to sales units. A cumulative maximum
    guarantees half-widths are monotone non-decreasing in lead time even under
    dampening.
    """
    if not 0.0 < level < 1.0:
        raise ValueError("置信水平必须位于 0 与 1 之间")
    point = forecast_from_state(state, h, m, spec, params)
    fitted = np.asarray(fitted, dtype=float)
    residuals = np.asarray(residuals, dtype=float)
    if len(fitted) != len(residuals) or len(residuals) == 0:
        raise ValueError("fitted 与 residuals 必须等长且非空")

    if spec.seasonal == "additive":
        sigma2 = float(np.sum(residuals**2) / len(residuals))
        variance = np.cumsum(innovation_coefficients(h, m, spec, params) ** 2) * sigma2
    else:
        rel = residuals / np.maximum(fitted, 1e-300)
        sigma2 = float(np.sum(rel**2) / len(rel))
        variance = np.cumsum(innovation_coefficients(h, m, spec, params) ** 2) * sigma2

    z = abs(normal_quantile((1.0 + level) / 2.0))
    std = np.sqrt(np.maximum(variance, 0.0))
    if spec.seasonal == "multiplicative":
        half = point * std * z
    else:
        half = std * z
    half = np.maximum.accumulate(half)
    return {
        "point": point,
        "lower": point - half,
        "upper": point + half,
        "half_width": half,
        "std_error": half / max(z, 1e-300),
    }
