"""
Volatility smile builder — pure matplotlib, fully interactive in Qt.
"""
from __future__ import annotations

from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

from option.option_class import Option


def build_smile_figure(
    calls: List[Option], puts: List[Option], underlying_price: Optional[float]
):
    """
    Build and return a matplotlib Figure for the volatility smile.
    Interactive: zoom, pan, hover tooltips (via mplcursors).
    Returns None if no IV data is available.
    """
    calls_by_strike: dict = {o.strike: o for o in calls if o.implied_volatility > 0}
    puts_by_strike:  dict = {o.strike: o for o in puts  if o.implied_volatility > 0}

    all_strikes = sorted(set(calls_by_strike) | set(puts_by_strike))
    if not all_strikes:
        return None

    smile_x, smile_y = [], []
    sabr_x, sabr_y, sabr_model_y, sabr_labels = [], [], [], []
    warn_x, warn_y = [], []

    for K in all_strikes:
        c = calls_by_strike.get(K)
        p = puts_by_strike.get(K)
        ivs   = [o.implied_volatility for o in (c, p) if o is not None]
        iv_avg = float(sum(ivs) / len(ivs))
        is_corrected = any(not o.status for o in (c, p) if o is not None)
        is_anomaly   = any(getattr(o, "sabr_is_anomaly", False) for o in (c, p) if o is not None)

        if is_corrected:
            warn_x.append(K); warn_y.append(iv_avg)
        elif is_anomaly:
            sabr_x.append(K); sabr_y.append(iv_avg)
            sabr_vol_model = next(
                (getattr(o, "sabr_volatility", 0.0) for o in (c, p)
                 if o is not None and getattr(o, "sabr_volatility", 0.0) > 0), 0.0)
            res_bp = (iv_avg - sabr_vol_model) * 10_000
            sabr_model_y.append(sabr_vol_model)
            sabr_labels.append(f"K={K:.3f}\nmkt={iv_avg*1e4:.1f}bp\nSABR={sabr_vol_model*1e4:.1f}bp\nΔ={res_bp:+.1f}bp")
        else:
            smile_x.append(K); smile_y.append(iv_avg)

    # ── Figure ────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#161b22")
    ax.tick_params(colors="#cdd9e5")
    ax.xaxis.label.set_color("#cdd9e5")
    ax.yaxis.label.set_color("#cdd9e5")
    for spine in ax.spines.values():
        spine.set_color("#30363d")
    ax.grid(True, color="#21262d", linewidth=0.6, linestyle="--")
    ax.set_xlabel("Strike", fontsize=10)
    ax.set_ylabel("Implied Volatility", fontsize=10)

    # Smile line (connecting all points)
    all_x_sorted = sorted(smile_x + warn_x + sabr_x)
    all_y_dict = {}
    all_y_dict.update(zip(smile_x, smile_y))
    all_y_dict.update(zip(warn_x, warn_y))
    all_y_dict.update(zip(sabr_x, sabr_y))
    if all_x_sorted:
        ax.plot(all_x_sorted, [all_y_dict[k] for k in all_x_sorted],
                color="#2196F3", linewidth=1.8, label="Smile", zorder=1)

    # Normal IV points
    normal_sc = None
    if smile_x:
        normal_sc = ax.scatter(smile_x, smile_y, color="#2196F3", s=50,
                               zorder=3, label="IV marché")

    # Corrected / extrapolated
    warn_sc = None
    if warn_x:
        warn_sc = ax.scatter(warn_x, warn_y, color="#FF9800", s=70,
                             marker="x", linewidths=2, zorder=4, label="Corrigé")

    # SABR anomalies
    sabr_sc = None
    if sabr_x:
        for K, iv_mkt, iv_mod in zip(sabr_x, sabr_y, sabr_model_y):
            ax.plot([K, K], [iv_mkt, iv_mod], color="#F44336",
                    linewidth=1, linestyle=":", zorder=2)
        sabr_sc = ax.scatter(sabr_x, sabr_y, color="#F44336", s=90,
                             marker="D", zorder=5, label="Anomalie SABR")
        ax.scatter(sabr_x, sabr_model_y, color="#F44336", s=50,
                   marker="s", facecolors="none", linewidths=1.5,
                   zorder=5, label="SABR (modèle)")

    # Forward price
    if underlying_price and underlying_price > 0:
        ax.axvline(underlying_price, color="#888", linewidth=1.0,
                   linestyle="--", alpha=0.7)
        ax.annotate(f" Fwd {underlying_price:.3f}",
                    xy=(underlying_price, ax.get_ylim()[0] if ax.get_ylim()[0] != 0 else 0),
                    color="#888", fontsize=8, va="bottom")

    ax.legend(facecolor="#161b22", labelcolor="#cdd9e5",
              edgecolor="#30363d", fontsize=8)

    # ── Hover tooltips ────────────────────────────────────────────────
    try:
        import mplcursors
        hover_artists = [a for a in [normal_sc, warn_sc, sabr_sc] if a is not None]
        if hover_artists:
            cursor = mplcursors.cursor(hover_artists, hover=True)

            @cursor.connect("add")
            def _on_add(sel):
                idx = sel.index
                artist = sel.artist
                if artist is sabr_sc:
                    strike = sabr_x[idx]
                    label = sabr_labels[idx]
                elif artist is warn_sc:
                    strike = warn_x[idx]
                    label = f"K={strike:.3f}\nIV={warn_y[idx]*1e4:.1f}bp\n⚠ Corrigé"
                else:
                    strike = smile_x[idx]
                    label = f"K={strike:.3f}\nIV={smile_y[idx]*1e4:.1f}bp"
                sel.annotation.set_text(label)
                sel.annotation.get_bbox_patch().set(
                    facecolor="#1f2937", edgecolor="#4b5563", alpha=0.92)
                sel.annotation.set_color("#f0f6fc")
    except Exception:
        pass

    fig.tight_layout()
    plt.close(fig)
    return fig
