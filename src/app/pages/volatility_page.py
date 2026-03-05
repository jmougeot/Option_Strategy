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
from app.chart_widget import PlotlyChart
from option.option_class import Option


# ============================================================================
# Smile figure builder  (ex pages/volatility.py)
# ============================================================================

def build_smile_figure(calls, puts, underlying_price):
    calls_by_strike = {o.strike: o for o in calls if o.implied_volatility > 0}
    puts_by_strike  = {o.strike: o for o in puts  if o.implied_volatility > 0}
    all_strikes = sorted(set(calls_by_strike) | set(puts_by_strike))
    if not all_strikes:
        return None

    smile_x, smile_y, smile_labels = [], [], []
    warn_x,  warn_y,  warn_labels  = [], [], []
    sabr_x,  sabr_y_mkt, sabr_y_mod, sabr_labels = [], [], [], []

    for K in all_strikes:
        c = calls_by_strike.get(K)
        p = puts_by_strike.get(K)
        ivs = [o.implied_volatility for o in (c, p) if o is not None]
        iv_avg = float(sum(ivs) / len(ivs))
        is_corrected = any(not o.status for o in (c, p) if o is not None)
        is_anomaly   = any(getattr(o, "sabr_is_anomaly", False) for o in (c, p) if o is not None)

        if is_corrected:
            warn_x.append(K); warn_y.append(iv_avg)
            warn_labels.append(f"K={K:.3f}\nIV={iv_avg*1e4:.1f}bp\n! Corrige")
        elif is_anomaly:
            sabr_vol_model = next(
                (getattr(o, "sabr_volatility", 0.0) for o in (c, p)
                 if o is not None and getattr(o, "sabr_volatility", 0.0) > 0), 0.0)
            res_bp = (iv_avg - sabr_vol_model) * 10_000
            sabr_x.append(K); sabr_y_mkt.append(iv_avg); sabr_y_mod.append(sabr_vol_model)
            sabr_labels.append(
                f"K={K:.3f}\nmkt={iv_avg*1e4:.1f}bp\nSABR={sabr_vol_model*1e4:.1f}bp\nD={res_bp:+.1f}bp"
            )
        else:
            smile_x.append(K); smile_y.append(iv_avg)
            smile_labels.append(f"K={K:.3f}\nIV={iv_avg*1e4:.1f}bp")

    all_y_dict = {}
    all_y_dict.update(zip(smile_x, smile_y))
    all_y_dict.update(zip(warn_x, warn_y))
    all_y_dict.update(zip(sabr_x, sabr_y_mkt))
    line_x = sorted(all_y_dict.keys())
    line_y = [all_y_dict[k] for k in line_x]

    return {
        "type": "smile",
        "normal":    {"x": smile_x, "y": smile_y, "labels": smile_labels} if smile_x else None,
        "corrected": {"x": warn_x,  "y": warn_y,  "labels": warn_labels}  if warn_x  else None,
        "sabr": {
            "x": sabr_x, "y_mkt": sabr_y_mkt,
            "y_mod": sabr_y_mod, "labels": sabr_labels,
        } if sabr_x else None,
        "smile_line": {"x": line_x, "y": line_y},
        "spot": float(underlying_price) if underlying_price else None,
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
        self._smile_chart = PlotlyChart(min_height=450)
        smile_lay.addWidget(self._smile_chart)
        self._tabs.addTab(self._smile_tab, "📈 Smile")

        # Table tab
        self._table_tab = QWidget()
        table_lay = QVBoxLayout(self._table_tab)
        table_lay.setContentsMargins(4, 4, 4, 4)
        self._opt_table = QTableWidget()
        self._opt_table.setAlternatingRowColors(True)
        self._opt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._opt_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        table_lay.addWidget(self._opt_table)

        self._btn_rerun = QPushButton("▶  Rerun pipeline with updated values")
        self._btn_rerun.setStyleSheet("font-weight: bold; padding: 6px;")
        self._btn_rerun.clicked.connect(self._on_rerun)
        table_lay.addWidget(self._btn_rerun)
        self._tabs.addTab(self._table_tab, "📋 Table")

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
        fig = build_smile_figure(calls, puts, underlying_price)
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
                f"{o.implied_volatility:.4f}" if o.implied_volatility else "0",
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
                    o.implied_volatility = float(iv_item.text())
                except ValueError:
                    pass
            if prem_item is not None:
                try:
                    o.premium = float(prem_item.text())
                except ValueError:
                    pass

        self.rerun_requested.emit(list(self._options))
