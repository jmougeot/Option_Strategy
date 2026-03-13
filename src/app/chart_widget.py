"""Reusable PyQtGraph chart widget.

The input figure is only a typed description of what should be drawn.
The widget does not compute payoff, SABR, or Gaussian models.
"""
from __future__ import annotations

from typing import Any, Callable, Sequence, cast

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.chart_types import (
    ChartFigureSpec,
    LabeledXYSeriesSpec,
    PayoffFigureSpec,
    PayoffLineSpec,
    SmileFigureSpec,
    SurfaceFigureSpec,
    XYSeriesSpec,
)

# ------------------------------------------------------------------
# Global PyQtGraph config (light theme)
# ------------------------------------------------------------------
_BG      = "#FFFFFF"
_GRID    = "#E5E8EF"
_TEXT    = "#1A1D2E"
_AX      = "#4A5173"

pg.setConfigOptions(antialias=True, foreground=_TEXT, background=_BG)


class ChartWidget(QWidget):
    """PyQtGraph chart widget for payoff and smile figures."""

    def __init__(self, min_height: int = 300, parent=None):
        super().__init__(parent)
        if min_height:
            self.setMinimumHeight(min_height)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel("")
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #1A1D2E; padding: 4px 0;"
        )
        self._title_lbl.hide()
        lay.addWidget(self._title_lbl)

        self._pw = pg.PlotWidget()
        self._configure_plot_widget()
        lay.addWidget(self._pw)
        self._vb2: Any | None = None
        self._vb2_sync: Callable[[], None] | None = None
        self._payoff_ymin: float | None = None
        self._payoff_ymax: float | None = None

    # ------------------------------------------------------------------ public
    def set_title(self, text: str) -> None:
        if text:
            self._title_lbl.setText(text)
            self._title_lbl.show()
        else:
            self._title_lbl.hide()

    def set_figure(self, data: ChartFigureSpec | None) -> None:
        if data is None:
            self.clear()
            return
        dtype = data["type"]
        if dtype == "payoff":
            self._render_payoff(cast(PayoffFigureSpec, data))
        elif dtype == "smile":
            self._render_smile(cast(SmileFigureSpec, data))
        elif dtype == "surface":
            self._render_surface(cast(SurfaceFigureSpec, data))
        else:
            self.clear()

    def set_y_range(self, ymin: float, ymax: float) -> None:
        """Lock the Y-axis to the given range (used to align 0 across tabs)."""
        x_min, x_max = self._main_view_box().viewRange()[0]
        self._lock_view(float(x_min), float(x_max), ymin, ymax)

    def clear(self) -> None:
        self._detach_secondary_view()
        self._pw.clear()
        self._payoff_ymin = None
        self._payoff_ymax = None

    # ------------------------------------------------------------------ helpers
    def _configure_plot_widget(self) -> None:
        self._pw.setBackground(_BG)
        self._pw.setMouseEnabled(x=False, y=False)
        self._pw.setMenuEnabled(False)
        self._pw.hideButtons()
        self._pw.setCursor(Qt.CursorShape.ArrowCursor)
        view_box = self._main_view_box()
        view_box.setMouseEnabled(x=False, y=False)
        view_box.setMenuEnabled(False)
        view_box.wheelEvent = lambda ev, axis=None: ev.ignore()  # type: ignore[assignment]

    def _plot_item(self) -> Any:
        return cast(Any, self._pw.getPlotItem())

    def _main_view_box(self) -> Any:
        return cast(Any, self._plot_item().vb)

    def _detach_secondary_view(self) -> None:
        if self._vb2 is None:
            return

        if self._vb2_sync is not None:
            try:
                self._main_view_box().sigResized.disconnect(self._vb2_sync)
            except Exception:
                pass
            self._vb2_sync = None

        plot_item = self._plot_item()
        try:
            cast(Any, plot_item.scene()).removeItem(self._vb2)
        except Exception:
            pass

        plot_item.hideAxis("right")
        self._vb2.clear()
        self._vb2 = None

    def _style_axes(self) -> None:
        pi = self._plot_item()
        for name in ("left", "right", "bottom", "top"):
            ax = pi.getAxis(name)
            ax.setPen(_AX)
            ax.setTextPen(_AX)

    def _lock_view(self, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
        x_span = max(x_max - x_min, 1e-9)
        y_span = max(y_max - y_min, 1e-9)

        plot_item = self._plot_item()
        view_box = self._main_view_box()
        plot_item.setXRange(x_min, x_max, padding=0)
        plot_item.setYRange(y_min, y_max, padding=0)
        plot_item.enableAutoRange(axis="x", enable=False)
        plot_item.enableAutoRange(axis="y", enable=False)
        view_box.setLimits(
            xMin=x_min,
            xMax=x_max,
            yMin=y_min,
            yMax=y_max,
            minXRange=x_span,
            maxXRange=x_span,
            minYRange=y_span,
            maxYRange=y_span,
        )

    def _add_legend(self) -> None:
        legend = self._plot_item().addLegend(offset=(10, 10))
        legend.setBrush(pg.mkBrush(255, 255, 255, 210))
        legend.setPen(pg.mkPen(_GRID))

    def _add_vertical_marker(
        self,
        x_value: float,
        *,
        label: str,
        color: str,
        y_value: float,
        dashed: bool = False,
        anchor: tuple[float, float] = (0, 1),
    ) -> None:
        pen = pg.mkPen(
            color,
            width=1.5 if not dashed else 1,
            style=Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine,
        )
        plot_item = self._plot_item()
        plot_item.addItem(pg.InfiniteLine(pos=x_value, angle=90, pen=pen))
        label_item = pg.TextItem(label, color=color, anchor=anchor)
        label_item.setPos(x_value, y_value)
        plot_item.addItem(label_item)

    def _set_payoff_range(self, x_values: np.ndarray, pnl_lines: Sequence[PayoffLineSpec]) -> None:
        if not pnl_lines:
            return

        all_y = np.concatenate([np.asarray(line["y"], dtype=float) for line in pnl_lines])
        x_min, x_max = float(x_values.min()), float(x_values.max())
        ymin, ymax = float(all_y.min()), float(all_y.max())
        margin = (ymax - ymin) * 0.10 or 0.01
        self._payoff_ymin = ymin - margin
        self._payoff_ymax = ymax + margin
        self._lock_view(x_min, x_max, self._payoff_ymin, self._payoff_ymax)

    def _apply_smile_ranges(self, all_x: list[float], all_y: list[float]) -> None:
        if not all_x or not all_y:
            return

        x_arr = np.asarray(all_x, dtype=float)
        y_arr = np.asarray(all_y, dtype=float)
        y_arr = y_arr[np.isfinite(y_arr) & (y_arr > 0)]

        x_min, x_max = float(x_arr.min()), float(x_arr.max())
        x_pad = max((x_max - x_min) * 0.05, 0.001)
        x_min -= x_pad
        x_max += x_pad

        if len(y_arr):
            y_min, y_max = float(y_arr.min()), float(y_arr.max())
            y_pad = max((y_max - y_min) * 0.15, 1e-5)
        else:
            y_min, y_max = float(np.min(all_y)), float(np.max(all_y))
            y_pad = max((y_max - y_min) * 0.15, 1e-5)

        self._lock_view(x_min, x_max, y_min - y_pad, y_max + y_pad)

    def _attach_gaussian_overlay(self, gaussian: XYSeriesSpec | None) -> None:
        if gaussian is None:
            return

        gx = np.asarray(gaussian["x"], dtype=float)
        gy = np.asarray(gaussian["y"], dtype=float)
        if gx.size == 0 or gy.size == 0:
            return

        plot_item = self._plot_item()
        view_box = self._main_view_box()
        vb2 = pg.ViewBox()
        self._vb2 = vb2
        vb2.setMouseEnabled(x=False, y=False)
        vb2.setMenuEnabled(False)

        plot_item.showAxis("right")
        cast(Any, plot_item.scene()).addItem(vb2)
        plot_item.getAxis("right").linkToView(vb2)
        plot_item.getAxis("right").setLabel("Probability", color=_AX)
        plot_item.getAxis("right").setPen(_AX)
        plot_item.getAxis("right").setTextPen(_AX)
        vb2.setXLink(plot_item)

        def sync() -> None:
            vb2.setGeometry(view_box.sceneBoundingRect())

        self._vb2_sync = sync
        view_box.sigResized.connect(sync)
        sync()

        vb2.addItem(pg.PlotDataItem(
            gx, gy, pen=pg.mkPen("#999999", width=1.5, style=Qt.PenStyle.DashLine)
        ))
        zeros = np.zeros(len(gy))
        vb2.addItem(pg.FillBetweenItem(
            pg.PlotDataItem(gx, zeros),
            pg.PlotDataItem(gx, gy),
            brush=pg.mkBrush(150, 150, 150, 45),
        ))
        vb2.setYRange(0, float(gy.max()) * 1.3)

    def _plot_scatter_series(
        self,
        series: LabeledXYSeriesSpec | None,
        *,
        name: str,
        symbol: str,
        size: int,
        pen,
        brush,
    ) -> tuple[list[float], list[float]]:
        if not series or not series["x"]:
            return [], []

        x_values = list(series["x"])
        y_values = list(series["y"])
        scatter = pg.ScatterPlotItem(
            x_values,
            y_values,
            symbol=symbol,
            size=size,
            pen=pen,
            brush=brush,
            name=name,
        )
        self._plot_item().addItem(scatter)
        return x_values, y_values

    # ------------------------------------------------------------------ payoff
    def _render_payoff(self, data: PayoffFigureSpec) -> None:
        self.clear()
        self._style_axes()
        self._add_legend()

        pi = self._plot_item()
        x_values = np.asarray(data["x"], dtype=float)
        for line in data["pnl_lines"]:
            y_values = np.asarray(line["y"], dtype=float)
            pen = pg.mkPen(color=line["color"], width=2)
            pi.plot(x_values, y_values, pen=pen, name=line["label"])

        for bk in data["breakevens"]:
            pi.addItem(pg.ScatterPlotItem(
                [bk["x"]], [0.0], symbol="o", size=10,
                pen=pg.mkPen(bk["color"], width=2),
                brush=pg.mkBrush(None),
            ))

        pi.addItem(pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen("#AAAAAA", width=1, style=Qt.PenStyle.DashLine),
        ))

        spot = data.get("spot")
        if spot is not None:
            self._add_vertical_marker(
                spot,
                label=f"Spot {spot:.4f}",
                color="#E05252",
                y_value=0,
            )

        self._attach_gaussian_overlay(data.get("gaussian"))

        pi.setLabel("bottom", "Underlying Price", color=_AX)
        pi.setLabel("left", "P&L", color=_AX)
        self._set_payoff_range(x_values, data["pnl_lines"])

    # ------------------------------------------------------------------ smile
    def _render_smile(self, data: SmileFigureSpec) -> None:
        self.clear()
        self._style_axes()
        self._add_legend()

        pi = self._plot_item()

        # Plot market data first to collect the "reference" ranges
        market_x, market_y = self._plot_scatter_series(
            data.get("market"),
            name="IV marché",
            symbol="o",
            size=9,
            pen=pg.mkPen("#2196F3", width=1),
            brush=pg.mkBrush("#2196F3"),
        )
        corrected_x, corrected_y = self._plot_scatter_series(
            data.get("corrected"),
            name="Corrigé",
            symbol="x",
            size=11,
            pen=pg.mkPen("#FF9800", width=2),
            brush=pg.mkBrush(None),
        )

        # Ranges based on market points only (not SABR extrapolation)
        ref_x: list = list(market_x) + list(corrected_x)
        ref_y: list = list(market_y) + list(corrected_y)

        # Blended IV curve (market/model weighted average)
        bl_data = data.get("blended")
        if bl_data and bl_data["x"]:
            pi.plot(bl_data["x"], bl_data["y"],
                    pen=pg.mkPen("#9C27B0", width=2.5), name="IV blendée")
            ref_x.extend(list(bl_data["x"]))
            ref_y.extend(list(bl_data["y"]))

        # Plot SABR curve, clipped to market strike range for range calc
        sc_data = data.get("sabr_curve")
        if sc_data and sc_data["x"]:
            pi.plot(sc_data["x"], sc_data["y"],
                    pen=pg.mkPen("#F44336", width=2), name="SABR")
            # Only include SABR Y-values within the market strike range for
            # axis scaling — prevents extreme wing values from crushing the view
            if ref_x:
                x_lo, x_hi = min(ref_x), max(ref_x)
                for sx, sy in zip(sc_data["x"], sc_data["y"]):
                    if x_lo <= sx <= x_hi:
                        ref_y.append(sy)
            if not ref_x:
                ref_x.extend(list(sc_data["x"]))
                ref_y.extend(list(sc_data["y"]))

        # Plot SVI curve
        sv_data = data.get("svi_curve")
        if sv_data and sv_data["x"]:
            pi.plot(sv_data["x"], sv_data["y"],
                    pen=pg.mkPen("#4CAF50", width=2, style=Qt.PenStyle.DashLine), name="SVI")
            if ref_x:
                x_lo, x_hi = min(ref_x), max(ref_x)
                for sx, sy in zip(sv_data["x"], sv_data["y"]):
                    if x_lo <= sx <= x_hi:
                        ref_y.append(sy)
            if not ref_x:
                ref_x.extend(list(sv_data["x"]))
                ref_y.extend(list(sv_data["y"]))

        self._apply_smile_ranges(ref_x, ref_y)

        spot = data.get("spot")
        if spot is not None:
            y_bottom = float(self._main_view_box().viewRange()[1][0])
            self._add_vertical_marker(
                spot,
                label=f"Fwd {spot:.3f}",
                color="#888888",
                y_value=y_bottom,
                dashed=True,
                anchor=(0.5, 1),
            )

        pi.setLabel("bottom", "Strike", color=_AX)
        pi.setLabel("left", "Implied Volatility", color=_AX)

    # ------------------------------------------------------------------ surface
    def _render_surface(self, data: SurfaceFigureSpec) -> None:
        self.clear()
        self._style_axes()
        self._add_legend()
        pi = self._plot_item()

        all_x: list[float] = []
        all_y: list[float] = []

        # Market scatter per expiry
        for mkt in data.get("market", []):
            xs, ys = list(mkt["x"]), list(mkt["y"])
            pi.addItem(pg.ScatterPlotItem(
                xs, ys, symbol="o", size=7,
                pen=pg.mkPen(mkt["color"], width=1),
                brush=pg.mkBrush(mkt["color"]),
                name=mkt["label"],
            ))
            all_x.extend(xs)
            all_y.extend(ys)

        # SVI model curves per expiry
        for curve in data.get("curves", []):
            xs, ys = list(curve["x"]), list(curve["y"])
            pi.plot(xs, ys, pen=pg.mkPen(curve["color"], width=2), name=curve["label"])
            all_x.extend(xs)
            all_y.extend(ys)

        self._apply_smile_ranges(all_x, all_y)
        pi.setLabel("bottom", "Strike", color=_AX)
        pi.setLabel("left", "Implied Volatility (bps)", color=_AX)


PlotlyChart = ChartWidget
