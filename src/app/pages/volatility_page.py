"""
Volatility page — PyQt6.
Shows the vol smile chart and an editable option table with "Rerun" capability.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QHeaderView, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.utils import split_calls_puts
from app.app_state import AppState
from app.chart_types import SmileFigureSpec, SurfaceFigureSpec
from app.chart_widget import ChartWidget
from option.option_class import Option


# ============================================================================
# Smile figure builder
# ============================================================================

def build_smile_figure(
    calls, puts, underlying_price,
    sabr_calibration=None,
    svi_calibration=None,
) -> Optional[SmileFigureSpec]:
    """Build smile data with market IV points + SABR/SVI smooth curve(s)."""
    calls_by_strike = {o.strike: o for o in calls}
    puts_by_strike  = {o.strike: o for o in puts}
    all_strikes = sorted(set(calls_by_strike) | set(puts_by_strike))
    if not all_strikes:
        return None

    mkt_x, mkt_y, mkt_labels = [], [], []
    warn_x, warn_y, warn_labels = [], [], []
    blend_x, blend_y = [], []

    for K in all_strikes:
        opts = [o for o in (calls_by_strike.get(K), puts_by_strike.get(K)) if o is not None]

        # IV marché brute (avant blending)
        raw_ivs = [getattr(o, 'market_implied_volatility', None) or o.implied_volatility for o in opts]
        raw_ivs = [iv for iv in raw_ivs if iv and iv > 0]
        if not raw_ivs:
            continue
        mkt_iv = sum(raw_ivs) / len(raw_ivs)

        # IV blendée (après calibration)
        blended_ivs = [o.implied_volatility for o in opts if o.implied_volatility and o.implied_volatility > 0]
        if blended_ivs:
            blend_x.append(K)
            blend_y.append(sum(blended_ivs) / len(blended_ivs))

        sabr_vols = [o.sabr_volatility for o in opts if o.sabr_volatility and o.sabr_volatility > 0]
        sabr_iv = sum(sabr_vols) / len(sabr_vols) if sabr_vols else 0.0

        lbl = f"K={K:.3f}\nmkt={mkt_iv * 1e4:.1f}bp"
        if sabr_iv > 0:
            lbl += f"\nmod={sabr_iv * 1e4:.1f}bp\n\u0394={(mkt_iv - sabr_iv) * 1e4:+.1f}bp"

        if any(not o.status for o in opts):
            warn_x.append(K); warn_y.append(mkt_iv)
            warn_labels.append(lbl + "\n! Corrigé")
        else:
            mkt_x.append(K); mkt_y.append(mkt_iv)
            mkt_labels.append(lbl)

    k_lo = min(all_strikes) * 0.98
    k_hi = max(all_strikes) * 1.02

    # Dense SABR curve
    sabr_curve_x, sabr_curve_y = [], []
    if sabr_calibration is not None and len(all_strikes) >= 2:
        try:
            k_dense = np.linspace(k_lo, k_hi, 200)
            sabr_curve_y = np.maximum(sabr_calibration.predict(k_dense), 0.0).tolist()
            sabr_curve_x = k_dense.tolist()
        except Exception:
            pass

    # Dense SVI curve
    svi_curve_x, svi_curve_y = [], []
    if svi_calibration is not None and len(all_strikes) >= 2:
        try:
            k_dense = np.linspace(k_lo, k_hi, 200)
            svi_curve_y = np.maximum(svi_calibration.predict(k_dense), 0.0).tolist()
            svi_curve_x = k_dense.tolist()
        except Exception:
            pass

    return {
        "type": "smile",
        "market":     {"x": mkt_x,  "y": mkt_y,  "labels": mkt_labels}  if mkt_x  else None,
        "corrected":  {"x": warn_x, "y": warn_y, "labels": warn_labels} if warn_x else None,
        "blended":    {"x": blend_x, "y": blend_y} if blend_x else None,
        "sabr_curve": {"x": sabr_curve_x, "y": sabr_curve_y} if sabr_curve_x else None,
        "svi_curve": {"x": svi_curve_x, "y": svi_curve_y} if svi_curve_x else None,
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
        smile_lay.setSpacing(4)

        # Paramètres de calibration (au-dessus du chart)
        self._calib_lbl = QLabel("")
        self._calib_lbl.setStyleSheet(
            "font-size: 11px; font-family: monospace; color: #444;"
            " background: #f5f5f5; padding: 4px 6px; border-radius: 4px;"
        )
        self._calib_lbl.setVisible(False)
        smile_lay.addWidget(self._calib_lbl)

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

        # Surface tab
        self._surface_tab = QWidget()
        surface_lay = QVBoxLayout(self._surface_tab)
        surface_lay.setContentsMargins(0, 0, 0, 0)
        self._surface_chart = ChartWidget(min_height=450)
        surface_lay.addWidget(self._surface_chart)
        self._tabs.addTab(self._surface_tab, "Surface")

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

        # Détecter les calibrations (SABR / SVI / les deux)
        raw_cal = getattr(self._state, "sabr_calibration", None)
        sabr_cal: Any = None
        svi_cal: Any = None
        if raw_cal is not None:
            try:
                from option.bachelier import CalibrationBundle
                if isinstance(raw_cal, CalibrationBundle):
                    sabr_cal = raw_cal.sabr
                    svi_cal = raw_cal.svi
                else:
                    # ancien objet (SABRCalibration seul)
                    sabr_cal = raw_cal
            except ImportError:
                sabr_cal = raw_cal

        # Label paramètres de calibration
        calib_lines: list[str] = []
        if sabr_cal is not None and hasattr(sabr_cal, "summary"):
            calib_lines.append(sabr_cal.summary())
        if svi_cal is not None and hasattr(svi_cal, "summary"):
            calib_lines.append(svi_cal.summary())
        # Surface SVI multi-expiration
        if raw_cal is not None and hasattr(raw_cal, "surface") and raw_cal.surface is not None:
            calib_lines.append(raw_cal.surface.summary())
        if calib_lines:
            self._calib_lbl.setText("\n".join(calib_lines))
            self._calib_lbl.setVisible(True)
        else:
            self._calib_lbl.setVisible(False)

        # Smile chart
        fig = build_smile_figure(
            calls, puts, underlying_price,
            sabr_calibration=sabr_cal,
            svi_calibration=svi_cal,
        )
        if fig is not None:
            self._smile_chart.set_figure(fig)
        else:
            self._smile_chart.clear()

        # Options table
        self._load_table(self._options)

        # Surface chart (multi-expiry SVI)
        surface = getattr(raw_cal, "surface", None) if raw_cal is not None else None
        if surface is not None:
            sfig = self._build_surface_figure(surface, self._options)
            if sfig is not None:
                self._surface_chart.set_figure(sfig)
            else:
                self._surface_chart.clear()
        else:
            self._surface_chart.clear()

    # ------------------------------------------------------------------ surface
    _SURFACE_COLORS = [
        "#2196F3", "#F44336", "#4CAF50", "#FF9800",
        "#9C27B0", "#00BCD4", "#795548", "#607D8B",
    ]

    @staticmethod
    def _build_surface_figure(
        surface, options: List[Option],
    ) -> Optional[SurfaceFigureSpec]:
        """Build multi-expiry overlay from SVISurfaceResult + market options."""
        from option.svi import SVICalibration, SVISurfaceResult
        if not isinstance(surface, SVISurfaceResult) or not surface.slices:
            return None

        colors = VolatilityPage._SURFACE_COLORS
        curves: list = []
        market: list = []

        # Group options by expiry for market dots
        by_expiry: Dict[Tuple[str, int], List[Option]] = defaultdict(list)
        for o in options:
            by_expiry[(o.expiration_month, o.expiration_year)].append(o)

        # Match surface slices (keyed by T) to option groups
        # Build (T, label, F, SVIResult) sorted list
        sorted_slices = sorted(surface.slices.items())  # (T, SVIResult)

        for idx, (T, res) in enumerate(sorted_slices):
            col = colors[idx % len(colors)]
            label = f"T={T:.3f}a"

            # Model curve
            if res.strikes.size > 0:
                k_lo = res.strikes.min() * 0.98
                k_hi = res.strikes.max() * 1.02
            else:
                continue
            k_dense = np.linspace(k_lo, k_hi, 200)
            vols = np.array([
                SVICalibration.normal_vol(res.F, K, T, res.theta, res.rho, res.eta, res.gamma)
                for K in k_dense
            ])
            curves.append({"label": label, "color": col, "x": k_dense.tolist(), "y": vols.tolist()})

            # Market dots for this T
            if res.strikes.size and res.sigmas_mkt.size:
                market.append({
                    "label": f"{label} mkt",
                    "color": col,
                    "x": res.strikes.tolist(),
                    "y": res.sigmas_mkt.tolist(),
                })

        if not curves:
            return None
        return {"type": "surface", "curves": curves, "market": market}

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
