"""
Payoff diagram builder — returns a data dict consumed by PlotlyChart (PyQtGraph).
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from strategy.strategy_class import StrategyComparison

COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


def create_payoff_diagram(
    comparisons: List[StrategyComparison],
    mixture: Tuple[np.ndarray, np.ndarray, float],
    underlying_price: Optional[float] = None,
) -> Optional[dict]:
    """
    Build and return a data dict for the payoff diagram.
    Consumed by PlotlyChart.set_figure() which renders via PyQtGraph.
    """
    if not comparisons:
        return None

    price_range = np.asarray(comparisons[0].prices, dtype=float)

    pnl_lines: list = []
    breakevens: list = []
    for idx, comp in enumerate(comparisons):
        color = COLORS[idx % len(COLORS)]
        pnl_lines.append({
            "label": comp.strategy_name,
            "color": color,
            "y": np.asarray(comp.pnl_array, dtype=float),
        })
        for bk in (comp.breakeven_points or []):
            breakevens.append({"x": float(bk), "color": color})

    gaussian = None
    if mixture is not None:
        prices_mix, probs, _ = mixture
        gaussian = {
            "x": np.asarray(prices_mix, dtype=float),
            "y": np.asarray(probs, dtype=float),
        }

    return {
        "type": "payoff",
        "x": price_range,
        "pnl_lines": pnl_lines,
        "breakevens": breakevens,
        "spot": float(underlying_price) if underlying_price is not None else None,
        "gaussian": gaussian,
    }


# Alias
build_payoff_figure = create_payoff_diagram