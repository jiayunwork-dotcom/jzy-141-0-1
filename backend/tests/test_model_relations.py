from __future__ import annotations

import numpy as np
import pytest

from app.holtwinters.backtest import BacktestConfig, run_backtest
from app.holtwinters.fitting import fit_all_specs, fit_model
from app.holtwinters.initialization import initialize
from app.holtwinters.schema import ModelSpec
from app.holtwinters.validation import FitValidationError


def seasonal_additive_series(n: int = 104, m: int = 12, trend: float = 1.7) -> np.ndarray:
    t = np.arange(n)
    season = 3.0 * np.sin(2 * np.pi * t / m)
    return 20.0 + trend * t + season


def test_additive_seasonal_linear_trend_is_exact_and_extrapolates() -> None:
    m = 12
    y = seasonal_additive_series(m=m)
    spec = ModelSpec("additive", "additive", False)
    result = fit_model(y, m, spec, horizon=10)
    assert result.sse < 1e-14
    np.testing.assert_allclose(result.recursion.fitted, y, atol=1e-9)

    t = np.arange(len(y), len(y) + 10)
    expected = 20.0 + 1.7 * t + 3.0 * np.sin(2 * np.pi * t / m)
    np.testing.assert_allclose(result.forecast["point"], expected, atol=1e-7)
    np.testing.assert_allclose(result.forecast["half_width"], 0.0, atol=1e-9)


def test_multiplicative_model_is_scale_invariant() -> None:
    m = 12
    t = np.arange(72)
    y = (40.0 + 0.8 * t) * (1.0 + 0.12 * np.sin(2 * np.pi * t / m))
    scaled = 3.5 * y
    spec = ModelSpec("multiplicative", "additive", False)

    r1 = fit_model(y, m, spec, horizon=8)
    r2 = fit_model(scaled, m, spec, horizon=8)
    for key in ("alpha", "beta", "gamma"):
        np.testing.assert_allclose(getattr(r1.params, key), getattr(r2.params, key), atol=1e-6)
    np.testing.assert_allclose(r2.forecast["point"], 3.5 * r1.forecast["point"], rtol=2e-9)
    np.testing.assert_allclose(r2.recursion.fitted, 3.5 * r1.recursion.fitted, rtol=2e-9)


def test_additive_model_is_shift_invariant() -> None:
    y = seasonal_additive_series(n=72, m=12, trend=0.4)
    shifted = y + 100.0
    spec = ModelSpec("additive", "additive", False)
    r1 = fit_model(y, 12, spec, horizon=8)
    r2 = fit_model(shifted, 12, spec, horizon=8)
    for key in ("alpha", "beta", "gamma"):
        np.testing.assert_allclose(getattr(r1.params, key), getattr(r2.params, key), atol=2e-7)
    np.testing.assert_allclose(r2.forecast["point"], r1.forecast["point"] + 100.0, atol=1e-9)


def test_initial_seasonal_vectors_meet_normalization() -> None:
    y = seasonal_additive_series(m=10)
    for seasonal in ("additive", "multiplicative"):
        values = y if seasonal == "additive" else y + 100
        spec = ModelSpec(seasonal, "additive", False)
        _, _, s = initialize(np.asarray(values, dtype=float), 10, spec)
        if seasonal == "additive":
            assert abs(np.sum(s)) < 1e-12
        else:
            assert abs(np.mean(s) - 1.0) < 1e-12


def test_rejects_non_positive_multiplicative_and_short_series() -> None:
    y = seasonal_additive_series(n=23, m=12)
    with pytest.raises(FitValidationError, match="两个完整季节"):
        fit_model(y, 12, ModelSpec("multiplicative", "none", False))
    bad = seasonal_additive_series(n=30, m=12).copy()
    bad[3] = 0
    with pytest.raises(FitValidationError, match="全为正"):
        fit_model(bad, 12, ModelSpec("multiplicative", "none", False))


def test_interval_widths_are_non_decreasing() -> None:
    rng = np.random.default_rng(7)
    y = seasonal_additive_series(n=96, m=12) + rng.normal(0, 1.0, 96)
    result = fit_model(y, 12, ModelSpec("additive", "additive", True), horizon=30)
    widths = result.forecast["half_width"]
    assert np.all(np.diff(widths) >= -1e-12)


def test_auto_select_returns_all_scores_and_best_aic() -> None:
    rng = np.random.default_rng(1)
    y = seasonal_additive_series(n=96, m=12) + rng.normal(0, 0.8, 96)
    best, results = fit_all_specs(y, 12, horizon=4)
    assert len(results) == 6
    assert best.aic == min(r.aic for r in results)


def test_backtest_ignores_values_after_origin_horizon_and_repeatable() -> None:
    y = seasonal_additive_series(n=70, m=12, trend=0.2)
    cfg = BacktestConfig(m=12, h=4, start_index=50, origins=1)
    r1 = run_backtest(y, cfg)
    contaminated = y.copy()
    contaminated[54:] = 10_000_000.0
    r2 = run_backtest(contaminated, cfg)
    assert r1["origins"][0]["forecast"] == r2["origins"][0]["forecast"]
    assert r1["origins"][0]["actual"] == r2["origins"][0]["actual"]
    r3 = run_backtest(y, cfg)
    assert r1["origins"][0]["forecast"] == r3["origins"][0]["forecast"]


def test_repeated_fit_is_deterministic() -> None:
    rng = np.random.default_rng(99)
    y = seasonal_additive_series(n=96, m=12) + rng.normal(0, 1.2, 96)
    r1 = fit_model(y, 12, ModelSpec("additive", "additive", True), horizon=6)
    r2 = fit_model(y, 12, ModelSpec("additive", "additive", True), horizon=6)
    assert r1.params == r2.params
    assert r1.sse == r2.sse
