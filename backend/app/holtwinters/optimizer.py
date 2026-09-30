from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

import numpy as np

from .core import HWParams
from .schema import ModelSpec


@dataclass(frozen=True)
class ParamBounds:
    values: tuple[tuple[float, float], ...]

    @property
    def dim(self) -> int:
        return len(self.values)


def _clip(x: np.ndarray, bounds: ParamBounds) -> np.ndarray:
    return np.array(
        [min(max(float(v), lo), hi) for v, (lo, hi) in zip(x, bounds.values)], dtype=float
    )


def make_bounds(spec: ModelSpec) -> ParamBounds:
    bounds = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0)]
    if spec.trend == "none":
        # beta is retained at a fixed place for a simple parameter vector but
        # is not part of the model.
        bounds[1] = (0.0, 0.0)
    if spec.damped:
        bounds.append((0.0, 1.0))
    return ParamBounds(tuple(bounds))


def params_from_vector(x: np.ndarray, spec: ModelSpec) -> HWParams:
    if spec.trend == "none":
        beta = 0.0
    else:
        beta = float(x[1])
    phi = float(x[3]) if spec.damped else 1.0
    return HWParams(alpha=float(x[0]), beta=beta, gamma=float(x[2]), phi=phi)


def vector_from_params(p: HWParams, spec: ModelSpec) -> np.ndarray:
    x = [p.alpha, p.beta if spec.trend == "additive" else 0.0, p.gamma]
    if spec.damped:
        x.append(p.phi)
    return np.array(x, dtype=float)


def initial_vector(spec: ModelSpec) -> np.ndarray:
    x = np.array([0.2, 0.1 if spec.trend == "additive" else 0.0, 0.2], dtype=float)
    if spec.damped:
        x = np.append(x, 0.95)
    return x


def _candidate_grid(spec: ModelSpec) -> list[np.ndarray]:
    a = [0.0, 0.05, 0.2, 0.5, 0.95]
    g = [0.0, 0.05, 0.2, 0.5, 0.95]
    candidates: list[np.ndarray] = []
    if spec.trend == "additive":
        b = [0.0, 0.05, 0.2, 0.5]
        phis = [0.8, 0.95, 1.0] if spec.damped else [1.0]
        for av in a:
            for bv in b:
                for gv in g:
                    for pv in phis:
                        x = np.array([av, bv, gv], dtype=float)
                        if spec.damped:
                            x = np.append(x, pv)
                        candidates.append(x)
    else:
        for av in a:
            for gv in g:
                candidates.append(np.array([av, 0.0, gv], dtype=float))
    selected = candidates[:: max(1, len(candidates) // 22)]
    # Boundary combinations are common exact/near-exact solutions for clean
    # synthetic series and prevent an interior grid from missing them.
    boundary_values = (0.0, 1.0)
    if spec.trend == "additive":
        for av in boundary_values:
            for bv in boundary_values:
                for gv in boundary_values:
                    x = np.array([av, bv, gv], dtype=float)
                    if spec.damped:
                        x = np.append(x, 1.0)
                    selected.append(x)
    else:
        for av in boundary_values:
            for gv in boundary_values:
                selected.append(np.array([av, 0.0, gv], dtype=float))
    zero = [0.0, 0.0 if spec.trend == "additive" else 0.0, 0.0]
    if spec.damped:
        zero.append(1.0)
    selected.append(np.array(zero, dtype=float))
    selected.append(
        np.array(
            [0.0, 0.1 if spec.trend == "additive" else 0.0, 0.0]
            + ([0.95] if spec.damped else []),
            dtype=float,
        )
    )
    selected.append(initial_vector(spec))
    return selected


def nelder_mead_bounded(
    objective: Callable[[np.ndarray], float],
    x0: np.ndarray,
    bounds: ParamBounds,
    max_iter: int = 220,
) -> tuple[np.ndarray, float]:
    """A compact bounded Nelder-Mead search used instead of statsmodels.

    Points are reflected into the bounded box.  The objective is minimized with
    standard reflection/expansion/contraction/shrinkage steps.  Deterministic
    initial simplices make repeated fits reproducible.
    """
    n = bounds.dim
    x0 = _clip(np.asarray(x0, dtype=float), bounds)
    f0 = objective(x0)
    if math.isinf(f0):
        # Find any feasible finite point before local search.
        for grid in _grid_points(bounds, 5):
            f = objective(grid)
            if np.isfinite(f):
                x0, f0 = grid, f
                break

    simplex = [x0]
    spans = np.array([hi - lo for lo, hi in bounds.values], dtype=float)
    for i in range(n):
        point = x0.copy()
        step = 0.12 * spans[i] if spans[i] > 0 else 0.0
        point[i] += step if point[i] + step <= bounds.values[i][1] else -step
        simplex.append(_clip(point, bounds))
    scores = [objective(p) for p in simplex]

    alpha_r, gamma_e, rho_c, sigma_s = 1.0, 2.0, 0.5, 0.5
    for _ in range(max_iter):
        order = np.argsort(scores, kind="mergesort")
        simplex = [simplex[i] for i in order]
        scores = [float(scores[i]) for i in order]
        if scores[0] <= 1e-12:
            break
        best, worst = simplex[0], simplex[-1]
        centroid = np.mean(np.asarray(simplex[:-1]), axis=0)

        reflected = _clip(centroid + alpha_r * (centroid - worst), bounds)
        fr = objective(reflected)
        if scores[0] <= fr < scores[-2]:
            simplex[-1], scores[-1] = reflected, fr
            continue
        if fr < scores[0]:
            expanded = _clip(centroid + gamma_e * (reflected - centroid), bounds)
            fe = objective(expanded)
            if fe < fr:
                simplex[-1], scores[-1] = expanded, fe
            else:
                simplex[-1], scores[-1] = reflected, fr
            continue
        contracted = _clip(centroid + rho_c * (worst - centroid), bounds)
        fc = objective(contracted)
        if fc < scores[-1]:
            simplex[-1], scores[-1] = contracted, fc
            continue
        new_simplex, new_scores = [best], [scores[0]]
        for p in simplex[1:]:
            shrunk = _clip(best + sigma_s * (p - best), bounds)
            new_simplex.append(shrunk)
            new_scores.append(objective(shrunk))
        simplex, scores = new_simplex, new_scores
        if np.max(np.linalg.norm(np.asarray(simplex[1:]) - simplex[0], axis=1)) < 1e-11:
            break

    order = np.argsort(scores, kind="mergesort")
    return simplex[order[0]], float(scores[order[0]])


def _grid_points(bounds: ParamBounds, n: int = 3) -> list[np.ndarray]:
    axes = []
    for lo, hi in bounds.values:
        if hi == lo:
            axes.append(np.array([lo]))
        else:
            axes.append(np.linspace(lo, hi, n))
    mesh = np.meshgrid(*axes, indexing="ij")
    return np.column_stack([x.ravel() for x in mesh])


def optimize_parameters(
    objective: Callable[[HWParams], float],
    spec: ModelSpec,
    fixed: dict[str, float] | None = None,
) -> tuple[HWParams, float]:
    bounds = make_bounds(spec)
    fixed = fixed or {}

    def with_fixed(x: np.ndarray) -> HWParams:
        p = params_from_vector(x, spec)
        values = {"alpha": p.alpha, "beta": p.beta, "gamma": p.gamma, "phi": p.phi}
        values.update(fixed)
        if spec.trend == "none":
            values["beta"] = 0.0
        if not spec.damped:
            values["phi"] = 1.0
        return HWParams(values["alpha"], values["beta"], values["gamma"], values["phi"])

    def scalar_obj(x: np.ndarray) -> float:
        x = _clip(x, bounds)
        try:
            value = float(objective(with_fixed(x)))
            if not np.isfinite(value):
                return float("inf")
            return value
        except (ValueError, ZeroDivisionError, FloatingPointError, OverflowError):
            return float("inf")

    starts = []
    base = initial_vector(spec)
    for key, index in (("alpha", 0), ("beta", 1), ("gamma", 2), ("phi", 3)):
        if key in fixed:
            base[index] = float(fixed[key])
    starts.append(_clip(base, bounds))
    candidates = _candidate_grid(spec)
    for cand in candidates:
        for key, index in (("alpha", 0), ("beta", 1), ("gamma", 2), ("phi", 3)):
            if key in fixed and len(cand) > index:
                cand[index] = float(fixed[key])
        starts.append(_clip(cand, bounds))

    best_x, best_f = starts[0], float("inf")
    best_norm = float("inf")
    seen: set[tuple[float, ...]] = set()
    zero_candidates = [i for i, s in enumerate(starts) if np.all((s == 0.0) | (s == 1.0))]
    start_order = zero_candidates + [i for i in range(len(starts)) if i not in zero_candidates]
    for start_index in start_order:
        start = starts[start_index]
        key = tuple(np.round(start, 10))
        if key in seen:
            continue
        seen.add(key)
        start_value = scalar_obj(start)
        if start_value <= 1e-12 and np.all((start == 0.0) | (start == 1.0)):
            x, f = start, start_value
        else:
            x, f = nelder_mead_bounded(scalar_obj, start, bounds, max_iter=120)
        # A boundary/zero-parameter exact fit is invariant to additive shifts
        # and positive scales. Stop there instead of selecting another
        # numerically exact but representation-dependent parameter vector.
        if f <= 1e-12 and np.all((x == 0.0) | (x == 1.0)):
            best_x, best_f, best_norm = x, f, float(np.linalg.norm(x))
            break
        norm = float(np.linalg.norm(x))
        if f < best_f - 1e-12 or (f <= 1e-12 and best_f <= 1e-12 and norm < best_norm):
            best_x, best_f, best_norm = x, f, norm
    if not np.isfinite(best_f):
        raise ValueError("在给定参数区间内没有找到可行参数")
    return with_fixed(_clip(best_x, bounds)), float(best_f)
