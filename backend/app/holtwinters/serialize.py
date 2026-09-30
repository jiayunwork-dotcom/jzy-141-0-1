from __future__ import annotations

from typing import Any

import numpy as np

from .fitting import FitResult


def _list(x: Any) -> list[float]:
    if x is None:
        return []
    return [float(v) for v in np.asarray(x).ravel()]


def params_to_dict(result: FitResult) -> dict[str, float | None]:
    p = result.params
    return {
        "alpha": float(p.alpha),
        "beta": float(p.beta) if result.spec.trend == "additive" else None,
        "gamma": float(p.gamma),
        "phi": float(p.phi) if result.spec.damped else None,
    }


def state_to_dict(result: FitResult) -> dict[str, Any]:
    state = result.recursion.final_state
    return {
        "level": float(state.level),
        "trend": float(state.trend),
        "seasonal": _list(state.seasonal),
        "next_season_index": int(getattr(state, "next_season_index", 0)),
    }


def fit_to_dict(result: FitResult) -> dict[str, Any]:
    forecast = None
    if result.forecast is not None:
        forecast = {
            "point": _list(result.forecast["point"]),
            "lower": _list(result.forecast["lower"]),
            "upper": _list(result.forecast["upper"]),
            "half_width": _list(result.forecast["half_width"]),
        }
    return {
        "model": result.spec.to_dict(),
        "parameters": params_to_dict(result),
        "sse": float(result.sse),
        "aic": float(result.aic),
        "fitted": _list(result.recursion.fitted),
        "residuals": _list(result.recursion.residuals),
        "final_state": state_to_dict(result),
        "forecast": forecast,
    }
