from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

SeasonalKind = Literal["additive", "multiplicative"]
TrendKind = Literal["none", "additive"]


@dataclass(frozen=True)
class ModelSpec:
    seasonal: SeasonalKind
    trend: TrendKind
    damped: bool

    def __post_init__(self) -> None:
        if self.seasonal not in {"additive", "multiplicative"}:
            raise ValueError("seasonal must be 'additive' or 'multiplicative'")
        if self.trend not in {"none", "additive"}:
            raise ValueError("trend must be 'none' or 'additive'")
        if self.damped and self.trend == "none":
            raise ValueError("a damped trend requires trend='additive'")

    @property
    def name(self) -> str:
        trend = "none" if self.trend == "none" else ("damped" if self.damped else "additive")
        return f"HW-{self.seasonal[0]}-t-{trend}"

    @property
    def n_param(self) -> int:
        # Number of smoothing parameters used by AIC.
        return 2 + (1 if self.trend == "additive" else 0) + (1 if self.damped else 0)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["name"] = self.name
        return data


ALL_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec("additive", "none", False),
    ModelSpec("additive", "additive", False),
    ModelSpec("additive", "additive", True),
    ModelSpec("multiplicative", "none", False),
    ModelSpec("multiplicative", "additive", False),
    ModelSpec("multiplicative", "additive", True),
)


def get_spec(seasonal: SeasonalKind, trend: TrendKind = "none", damped: bool = False) -> ModelSpec:
    return ModelSpec(seasonal=seasonal, trend=trend, damped=damped)
