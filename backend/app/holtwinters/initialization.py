from __future__ import annotations

import numpy as np

from .schema import ModelSpec


def initialize(y: np.ndarray, m: int, spec: ModelSpec) -> tuple[float, float, np.ndarray]:
    """Estimate initial state from the first two complete seasons.

    Explicit documented rule:
    1. For each of the first two seasons, calculate the mean of all m observations.
    2. Set the initial trend to (mean_season_2 - mean_season_1) / m. When the
       model has no trend component, b0 is stored as zero but not used by the
       recursions.
    3. Detrend each observation to its season-center time, then calculate raw
       seasonal offsets. For season one the level at position i is
       mean1 + b*(i-(m-1)/2); season two uses mean2 with the same offset:
       additive: y[i] - detrended_level(i); multiplicative: y[i] / level(i).
    4. Average the two raw offsets by seasonal position.
    5. Normalize the vector of m initial seasonal components:
       additive components sum to zero; multiplicative components have mean one.
       The level is adjusted so that the first fitted observation is unchanged.
    """
    first = y[:m]
    second = y[m : 2 * m]
    mean1 = float(np.mean(first))
    mean2 = float(np.mean(second))
    b0 = (mean2 - mean1) / m if spec.trend == "additive" else 0.0

    # Detrend each season around its own center.  After seasonal normalization,
    # l0 is aligned to make the first one-step fitted value equal y0.
    positions = np.arange(m, dtype=float) - (m - 1) / 2.0
    if spec.seasonal == "additive":
        raw1 = first - (mean1 + b0 * positions)
        raw2 = second - (mean2 + b0 * positions)
        seasonal = 0.5 * (raw1 + raw2)
        shift = float(np.mean(seasonal))
        seasonal = seasonal - shift
        l0 = y[0] - seasonal[0] if len(y) else mean1
    else:
        raw1 = first / (mean1 + b0 * positions)
        raw2 = second / (mean2 + b0 * positions)
        seasonal = 0.5 * (raw1 + raw2)
        scale = float(np.mean(seasonal))
        if scale <= 0:
            raise ValueError("无法从输入序列估计正的乘法季节分量")
        seasonal = seasonal / scale
        l0 = y[0] / seasonal[0] if len(y) else mean1

    if not np.isfinite(l0) or not np.isfinite(b0) or not np.all(np.isfinite(seasonal)):
        raise ValueError("初始状态不是有限数值")
    if spec.seasonal == "multiplicative" and (l0 <= 0 or np.any(seasonal <= 0)):
        raise ValueError("乘法模型初始水平或季节分量必须为正")
    return float(l0), float(b0), seasonal.astype(float)
