from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PointIn(BaseModel):
    date: date
    value: float


class SeriesCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    points: list[PointIn]

    @field_validator("points")
    @classmethod
    def nonempty(cls, v: list[PointIn]) -> list[PointIn]:
        if not v:
            raise ValueError("序列不能为空")
        return v


class FitRequest(BaseModel):
    horizon: int = Field(default=8, ge=1, le=52)
    confidence: float = Field(default=0.95, gt=0, lt=1)
    auto: bool = True
    m: int = Field(default=52, ge=2, le=365)
    seasonal: Literal["additive", "multiplicative"] | None = None
    trend: Literal["none", "additive"] | None = None
    damped: bool | None = None
    fixed_params: dict[str, float] | None = None


class BacktestRequestModel(BaseModel):
    m: int = Field(default=52, ge=2, le=365)
    h: int = Field(default=8, ge=1, le=52)
    start_index: int | None = Field(default=None, ge=0)
    step: int = Field(default=1, ge=1)
    origins: int | None = Field(default=None, ge=1)
    confidence: float = Field(default=0.95, gt=0, lt=1)
    auto: bool = True
    seasonal: Literal["additive", "multiplicative"] | None = None
    trend: Literal["none", "additive"] | None = None
    damped: bool | None = None
    fixed_params: dict[str, float] | None = None
