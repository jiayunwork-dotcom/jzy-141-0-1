from __future__ import annotations

import numpy as np

from .schema import ModelSpec


class FitValidationError(ValueError):
    """Raised when a series cannot be fitted with the requested model."""


def validate_series(values: np.ndarray | list[float], m: int, spec: ModelSpec) -> np.ndarray:
    y = np.asarray(values, dtype=float)
    if y.ndim != 1:
        raise FitValidationError("销量序列必须是一维数组")
    if not np.isfinite(y).all():
        raise FitValidationError("销量序列包含缺失值或非有限数字")
    if int(m) != m or m < 2:
        raise FitValidationError("季节周期 m 必须是不小于 2 的整数")
    if len(y) < 2 * int(m):
        raise FitValidationError(
            f"序列长度 {len(y)} 少于两个完整季节（至少需要 {2 * int(m)} 个观测）"
        )
    if spec.seasonal == "multiplicative" and np.any(y <= 0):
        bad = int(np.sum(y <= 0))
        raise FitValidationError(
            f"乘法季节模型要求序列全为正；发现 {bad} 个零或负销量"
        )
    return y
