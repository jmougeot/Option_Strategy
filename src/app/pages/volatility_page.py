"""
Volatility page — PyQt6.
Shows the vol smile chart and an editable option table with "Rerun" capability.
"""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np
import pandas as pd
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.utils import split_calls_puts
from app.app_state import AppState
from app.chart_types import SmileFigureSpec
from app.chart_widget import ChartWidget
from option.option_class import Option


# ============================================================================
# Smile figure builder  (ex pages/volatility.py)
# ============================================================================

def build_smile_figure(calls, puts, underlying_price, sabr_calibration=None) -> Optional[SmileFigureSpec]:
    """Build smile data with market IV points + SABR smooth curve."""
    # Gather all options by strike
    calls_by_strike = {o.strike: o for o in calls}
    puts_by_strike  = {o.strike: o for o in puts}
    all_strikes = sorted(set(calls_by_strike) | set(puts_by_strike))
    if not all_strikes:
        return None

    # Market IV points (from bid/ask, before SABR)
    mkt_x, mkt_y, mkt_labels = [], [], []
    # SABR curve (smooth, all strikes)
    sabr_x, sabr_y = [], []
    # Corrected points (status=False)
    warn_x, warn_y, warn_labels = [], [], []

    for K in all_strikes:
        c = calls_by_strike.get(K)
        p = puts_by_strike.get(K)
        opts = [o for o in (c, p) if o is not None]

        # SABR vol (always available after calibration)
        sabr_vols = [o.sabr_volatility for o in opts if o.sabr_volatility > 0]
        if sabr_vols:
            sv = sum(sabr_vols) / len(sabr_vols)
            sabr_x.append(K)
            sabr_y.append(sv)

        # Market IV (original from price) — only genuine market data
        mkt_ivs = [o.market_implied_volatility for o in opts if o.market_implied_volatility > 0]
        is_corrected = any(not o.status for o in opts)

        if mkt_ivs:
            mkt_iv = sum(mkt_ivs) / len(mkt_ivs)
            sabr_iv = sabr_vols[0] if sabr_vols else 0.0
            res_bp = (mkt_iv - sabr_iv) * 10_000 if sabr_iv > 0 else 0.0
            lbl = f"K={K:.3f}\nmkt={mkt_iv*1e4:.1f}bp"
            if sabr_iv > 0:
                lbl += f"\nSABR={sabr_iv*1e4:.1f}bp\n\u0394={res_bp:+.1f}bp"
            if is_corrected:
                warn_x.append(K); warn_y.append(mkt_iv)
                warn_labels.append(lbl + "\n! Corrige")
            else:
                mkt_x.append(K); mkt_y.append(mkt_iv)
                mkt_labels.append(lbl)

    # Build smooth SABR curve on a dense grid
    if sabr_calibration is not None and len(all_strikes) >= 2:
        K_min = min(all_strikes) * 0.98
        K_max = max(all_strikes) * 1.02
        k_dense = np.linspace(K_min, K_max, 200)
        try:
            sabr_dense = np.maximum(sabr_calibration.predict(k_dense), 0.0)
            sabr_curve_x: list = k_dense.tolist()
            sabr_curve_y: list = sabr_dense.tolist()
        except Exception:
            sabr_curve_x = sabr_x
            sabr_curve_y = sabr_y
    elif len(sabr_x) >= 4:
        # Fallback: cubic spline through calibrated points
        from scipy.interpolate import CubicSpline
        k_dense = np.linspace(sabr_x[0], sabr_x[-1], 200)
        cs = CubicSpline(sabr_x, sabr_y)
        sabr_curve_x = k_dense.tolist()
        sabr_curve_y = np.maximum(cs(k_dense), 0.0).tolist()
    else:
        sabr_curve_x = sabr_x
        sabr_curve_y = sabr_y

    return {
        "type": "smile",
        "market":    {"x": mkt_x,  "y": mkt_y,  "labels": mkt_labels}  if mkt_x  else None,
        "corrected": {"x": warn_x, "y": warn_y, "labels": warn_labels} if warn_x else None,
        "sabr_curve": {"x": sabr_curve_x, "y": sabr_curve_y} if sabr_curve_x else None,
        "spot": float(underlying_price) if underlying_price is not None else None,
    }


class VolatilityPage(QWidget):
    """Volatility analysis: smile chart + editable options table."""

    rerun_requested = pyqtSignal(list)  # emits modified options list

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._options: List[Any] = []
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        header = QLabel("<h2>Volatility Analysis</h2>")
        root.addWidget(header)

        self._info_lbl = QLabel("Run a comparison in Overview first to get volatility data.")
        self._info_lbl.setVisible(True)
        root.addWidget(self._info_lbl)

        self._tabs = QTabWidget()
        self._tabs.setVisible(False)
        root.addWidget(self._tabs)

        # Smile tab
        self._smile_tab = QWidget()
        smile_lay = QVBoxLayout(self._smile_tab)
        smile_lay.setContentsMargins(0, 0, 0, 0)
        self._smile_chart = ChartWidget(min_height=450)
        smile_lay.addWidget(self._smile_chart)
        self._tabs.addTab(self._smile_tab, "Smile")

        # Table tab
        self._table_tab = QWidget()
        table_lay = QVBoxLayout(self._table_tab)
        table_lay.setContentsMargins(4, 4, 4, 4)
        self._opt_table = QTableWidget()
        self._opt_table.setAlternatingRowColors(True)
        self._opt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch) #type: ignore 
        self._opt_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        table_lay.addWidget(self._opt_table)

        self._btn_rerun = QPushButton("▶  Rerun pipeline with updated values")
        self._btn_rerun.setStyleSheet("font-weight: bold; padding: 6px;")
        self._btn_rerun.clicked.connect(self._on_rerun)
        table_lay.addWidget(self._btn_rerun)
        self._tabs.addTab(self._table_tab, "Table")

    # ------------------------------------------------------------------ public
    def refresh(self) -> None:
        """Called when Overview finishes to load fresh data."""
        options = self._state.all_imported_options
        if not options:
            self._info_lbl.setVisible(True)
            self._tabs.setVisible(False)
            return

        self._options = sorted(options, key=lambda o: o.strike)
        self._info_lbl.setVisible(False)
        self._tabs.setVisible(True)

        future_data = self._state.future_data
        underlying_price = (
            future_data.underlying_price if future_data and future_data.underlying_price else None
        )
        calls, puts = split_calls_puts(self._options)

        # Smile chart
        sabr_calibration = getattr(self._state, "sabr_calibration", None)
        fig = build_smile_figure(calls, puts, underlying_price, sabr_calibration=sabr_calibration)
        if fig is not None:
            self._smile_chart.set_figure(fig)
        else:
            self._smile_chart.clear()

        # Options table
        self._load_table(self._options)

    # ------------------------------------------------------------------ helpers
    COLUMNS = ["Type", "Expiry", "Strike", "Premium", "Bid", "Ask", "IV (%)", "Delta", "Gamma", "Theta", "Status"]

    def _load_table(self, options: List[Any]) -> None:
        self._opt_table.clear()
        self._opt_table.setColumnCount(len(self.COLUMNS))
        self._opt_table.setHorizontalHeaderLabels(self.COLUMNS)
        self._opt_table.setRowCount(len(options))

        editable_cols = {self.COLUMNS.index("IV (%)"), self.COLUMNS.index("Premium")}

        for r, o in enumerate(options):
            vals = [
                "Call" if o.is_call() else "Put",
                f"{o.expiration_month}{o.expiration_year}",
                f"{o.strike:.4f}",
                f"{o.premium:.6f}" if o.premium else "0",
                f"{o.bid:.6f}" if o.bid else "0",
                f"{o.ask:.6f}" if o.ask else "0",
                f"{o.implied_volatility * 100:.4f}" if o.implied_volatility else "0",
                f"{o.delta:.4f}" if o.delta else "0",
                f"{o.gamma:.6f}" if o.gamma else "0",
                f"{o.theta:.6f}" if o.theta else "0",
                "Ok" if o.status else "⚠️ Corrected",
            ]
            for c, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c not in editable_cols:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._opt_table.setItem(r, c, item)

    def _on_rerun(self) -> None:
        """Propagate edited IV/Premium back to options, then signal rerun."""
        iv_col  = self.COLUMNS.index("IV (%)")
        prem_col = self.COLUMNS.index("Premium")
        for r, o in enumerate(self._options):
            iv_item   = self._opt_table.item(r, iv_col)
            prem_item = self._opt_table.item(r, prem_col)
            if iv_item is not None:
                try:
                    o.implied_volatility = float(iv_item.text()) / 100.0
                except ValueError:
                    pass
            if prem_item is not None:
                try:
                    o.premium = float(prem_item.text())
                except ValueError:
                    pass

        self.rerun_requested.emit(list(self._options))
