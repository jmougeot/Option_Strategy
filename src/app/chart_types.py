"""
Shared figure specs for chart rendering.

This is only drawing data passed to the chart widget.
It does not contain pricing or calibration logic.
"""
from __future__ import annotations

from typing import Literal, TypeAlias, TypedDict

import numpy as np

NumberSeries: TypeAlias = list[float] | np.ndarray


class XYSeriesSpec(TypedDict):
    x: NumberSeries
    y: NumberSeries


class LabeledXYSeriesSpec(XYSeriesSpec):
    labels: list[str]


class PayoffLineSpec(TypedDict):
    label: str
    color: str
    y: np.ndarray


class MarkerSpec(TypedDict):
    x: float
    color: str


class PayoffFigureSpec(TypedDict):
    type: Literal["payoff"]
    x: np.ndarray
    pnl_lines: list[PayoffLineSpec]
    breakevens: list[MarkerSpec]
    spot: float | None
    gaussian: XYSeriesSpec | None


class SmileFigureSpec(TypedDict):
    type: Literal["smile"]
    market: LabeledXYSeriesSpec | None
    corrected: LabeledXYSeriesSpec | None
    blended: XYSeriesSpec | None
    sabr_curve: XYSeriesSpec | None
    svi_curve: XYSeriesSpec | None
    spline_curve: XYSeriesSpec | None
    spot: float | None


class SurfaceCurveSpec(TypedDict):
    label: str
    color: str
    x: NumberSeries
    y: NumberSeries


class SurfaceMarketSpec(TypedDict):
    label: str
    color: str
    x: NumberSeries
    y: NumberSeries


class SurfaceFigureSpec(TypedDict):
    type: Literal["surface"]
    curves: list[SurfaceCurveSpec]
    market: list[SurfaceMarketSpec]


ChartFigureSpec: TypeAlias = PayoffFigureSpec | SmileFigureSpec | SurfaceFigureSpec