"""
Payoff diagram builder — pure matplotlib, fully interactive in Qt.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
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
):
    """
    Build and return a matplotlib Figure for the payoff diagram.
    Interactive: zoom, pan, hover tooltips (via mplcursors).
    """
    if not comparisons:
        return None

    price_range = comparisons[0].prices
    has_mixture = mixture is not None

    fig, ax1 = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0d1117")
    ax1.set_facecolor("#161b22")
    ax1.tick_params(colors="#cdd9e5")
    ax1.xaxis.label.set_color("#cdd9e5")
    ax1.yaxis.label.set_color("#cdd9e5")
    for spine in ax1.spines.values():
        spine.set_color("#30363d")
    ax1.grid(True, color="#21262d", linewidth=0.6, linestyle="--")

    # ── Strategy PnL lines ─────────────────────────────────────────────
    strategy_lines = []
    for idx, comp in enumerate(comparisons):
        color = COLORS[idx % len(COLORS)]
        line, = ax1.plot(
            price_range, comp.pnl_array,
            color=color, linewidth=2.0,
            label=comp.strategy_name,
        )
        strategy_lines.append(line)

        # Breakeven markers
        if comp.breakeven_points:
            ax1.scatter(
                comp.breakeven_points,
                [0] * len(comp.breakeven_points),
                color=color, s=60, zorder=5,
                marker="o", facecolors="none", linewidths=2,
            )

    ax1.axhline(0, color="#555", linewidth=0.8, linestyle="--")
    ax1.set_xlabel("Underlying Price", fontsize=10)
    ax1.set_ylabel("P&L", fontsize=10, color="#cdd9e5")

    # ── Gaussian mixture (secondary Y axis) ───────────────────────────
    if has_mixture:
        prices_mix, probs, _ = mixture
        ax2 = ax1.twinx()
        ax2.set_facecolor("#161b22")
        ax2.tick_params(colors="#555")
        ax2.set_ylabel("Probability", fontsize=9, color="#555")
        for spine in ax2.spines.values():
            spine.set_color("#30363d")
        ax2.fill_between(prices_mix, probs, alpha=0.18, color="#888")
        ax2.plot(prices_mix, probs, color="#888", linewidth=1.2,
                 linestyle="--", label="Distribution")
        ax2.set_ylim(bottom=0)

    # ── Spot line ──────────────────────────────────────────────────────
    if underlying_price is not None:
        ax1.axvline(underlying_price, color="#e05252", linewidth=1.2,
                    linestyle="-", alpha=0.85)
        ax1.annotate(
            f" Spot {underlying_price:.4f}",
            xy=(underlying_price, ax1.get_ylim()[0]),
            color="#e05252", fontsize=8,
            va="bottom", ha="left",
        )

    # ── Legend ─────────────────────────────────────────────────────────
    ax1.legend(
        facecolor="#161b22", labelcolor="#cdd9e5",
        edgecolor="#30363d", fontsize=8,
        loc="upper right",
    )

    # ── Hover tooltips ─────────────────────────────────────────────────
    try:
        import mplcursors
        cursor = mplcursors.cursor(strategy_lines, hover=True)

        @cursor.connect("add")
        def _on_add(sel):
            comp = comparisons[strategy_lines.index(sel.artist)]
            xi = sel.index if hasattr(sel, "index") else 0
            try:
                price_val = float(price_range[xi])
                pnl_val = float(comp.pnl_array[xi])
            except Exception:
                price_val = sel.target[0]
                pnl_val = sel.target[1]
            sel.annotation.set_text(
                f"{comp.strategy_name}\nPrice: {price_val:.4f}\nP&L: {pnl_val:.4f}"
            )
            sel.annotation.get_bbox_patch().set(
                facecolor="#1f2937", edgecolor="#4b5563", alpha=0.92
            )
            sel.annotation.set_color("#f0f6fc")

    except Exception:
        pass

    fig.tight_layout()
    plt.close(fig)
    return fig


# Alias
build_payoff_figure = create_payoff_diagram
