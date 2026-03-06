"""
chart_widget.py -- PyQtGraph-based chart widget.
Accepts data dicts produced by build_payoff_figure / build_smile_figure.
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

# ------------------------------------------------------------------
# Global PyQtGraph config (light theme)
# ------------------------------------------------------------------
_BG      = "#FFFFFF"
_GRID    = "#E5E8EF"
_TEXT    = "#1A1D2E"
_AX      = "#4A5173"

pg.setConfigOptions(antialias=True, foreground=_TEXT, background=_BG)


class PlotlyChart(QWidget):
    """PyQtGraph chart widget"""

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
        self._pw.setBackground(_BG)
        # Disable pan (drag), keep scroll-wheel zoom only, no right-click menu
        self._pw.setMouseEnabled(x=False, y=False)
        self._pw.setMenuEnabled(False)
        pi = self._pw.plotItem
        if pi and pi.vb:
            pi.vb.setMouseEnabled(x=False, y=False)
            pi.vb.setMenuEnabled(False)
            pi.vb.wheelEvent = lambda ev, axis=None: ev.ignore()  # type: ignore[assignment]
        lay.addWidget(self._pw)

        # Hover helpers
        self._tooltip = pg.TextItem(anchor=(0, 1), color=_TEXT)
        self._tooltip.setZValue(100)
        self._vline = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(_AX, width=1, style=Qt.PenStyle.DashLine),
        )
        self._vline.setZValue(50)
        self._pw.addItem(self._tooltip)
        self._pw.addItem(self._vline)
        self._tooltip.hide()
        self._vline.hide()

        self._proxy = pg.SignalProxy(
            self._pw.scene().sigMouseMoved, rateLimit=60, slot=self._on_mouse
        )
        self._hover_series: list = []
        self._vb2 = None
        self._data_type: str = ""

    # ------------------------------------------------------------------ public
    def set_title(self, text: str) -> None:
        if text:
            self._title_lbl.setText(text)
            self._title_lbl.show()
        else:
            self._title_lbl.hide()

    def set_figure(self, data) -> None:
        if data is None:
            self.clear()
            return
        dtype = data.get("type") if isinstance(data, dict) else None
        if dtype == "payoff":
            self._render_payoff(data)
        elif dtype == "smile":
            self._render_smile(data)
        else:
            self.clear()

    def set_y_range(self, ymin: float, ymax: float) -> None:
        """Lock the Y-axis to the given range (used to align 0 across tabs)."""
        pi = self._pw.plotItem
        if pi is not None:
            pi.setYRange(ymin, ymax, padding=0)

    def clear(self) -> None:
        self._pw.clear()
        if self._vb2 is not None:
            self._vb2.clear()
            self._vb2 = None
        self._pw.addItem(self._tooltip)
        self._pw.addItem(self._vline)
        self._tooltip.hide()
        self._vline.hide()
        self._hover_series = []
        self._data_type = ""

    # ------------------------------------------------------------------ helpers
    def _style_axes(self):
        pi = self._pw.plotItem
        for name in ("left", "right", "bottom", "top"):
            ax = pi.getAxis(name)
            ax.setPen(_AX)
            ax.setTextPen(_AX)

    # ------------------------------------------------------------------ payoff
    def _render_payoff(self, data: dict) -> None:
        self.clear()
        self._data_type = "payoff"
        pi = self._pw.plotItem
        self._style_axes()

        # Zoom already restricted globally in __init__

        x = data["x"]
        legend = pi.addLegend(offset=(10, 10))
        legend.setBrush(pg.mkBrush(255, 255, 255, 210))
        legend.setPen(pg.mkPen(_GRID))

        self._hover_series = []
        for line in data["pnl_lines"]:
            pen = pg.mkPen(color=line["color"], width=2)
            pi.plot(x, line["y"], pen=pen, name=line["label"])
            lbl, y_arr = line["label"], line["y"]

            def _mkfn(lbl=lbl, x_a=x, y_a=y_arr):
                def fn(i):
                    return f"{lbl}\nPrice: {x_a[i]:.4f}\nP&L: {y_a[i]:.4f}"
                return fn

            self._hover_series.append((x, y_arr, _mkfn()))

        # Breakeven open-circle markers
        for bk in data["breakevens"]:
            sc = pg.ScatterPlotItem(
                [bk["x"]], [0.0], symbol="o", size=10,
                pen=pg.mkPen(bk["color"], width=2),
                brush=pg.mkBrush(None),
            )
            pi.addItem(sc)

        # Zero line
        pi.addItem(pg.InfiniteLine(
            pos=0, angle=0,
            pen=pg.mkPen("#AAAAAA", width=1, style=Qt.PenStyle.DashLine),
        ))

        # Spot vertical line
        spot = data.get("spot")
        if spot:
            pi.addItem(pg.InfiniteLine(
                pos=spot, angle=90,
                pen=pg.mkPen("#E05252", width=1.5),
            ))
            lbl_item = pg.TextItem(f"Spot {spot:.4f}", color="#E05252", anchor=(0, 1))
            lbl_item.setPos(spot, 0)
            pi.addItem(lbl_item)

        # Gaussian mixture on secondary Y axis
        gauss = data.get("gaussian")
        if gauss:
            gx, gy = gauss["x"], gauss["y"]
            vb2 = pg.ViewBox()
            self._vb2 = vb2
            pi.showAxis("right")
            pi.scene().addItem(vb2)
            pi.getAxis("right").linkToView(vb2)
            pi.getAxis("right").setLabel("Probability", color=_AX)
            pi.getAxis("right").setPen(_AX)
            pi.getAxis("right").setTextPen(_AX)
            vb2.setXLink(pi)

            def _sync():
                vb2.setGeometry(pi.vb.sceneBoundingRect())

            pi.vb.sigResized.connect(_sync)
            _sync()

            vb2.addItem(pg.PlotDataItem(
                gx, gy, pen=pg.mkPen("#999999", width=1.5, style=Qt.PenStyle.DashLine)
            ))
            zeros = np.zeros(len(gy))
            fill = pg.FillBetweenItem(
                pg.PlotDataItem(gx, zeros),
                pg.PlotDataItem(gx, gy),
                brush=pg.mkBrush(150, 150, 150, 45),
            )
            vb2.addItem(fill)
            vb2.setYRange(0, float(gy.max()) * 1.3)

        pi.setLabel("bottom", "Underlying Price", color=_AX)
        pi.setLabel("left", "P&L", color=_AX)

        # Compute tight Y-range and auto-range X only
        all_y = np.concatenate([l["y"] for l in data["pnl_lines"]])
        ymin, ymax = float(all_y.min()), float(all_y.max())
        margin = (ymax - ymin) * 0.10 or 0.01
        self._payoff_ymin = ymin - margin
        self._payoff_ymax = ymax + margin
        pi.setYRange(self._payoff_ymin, self._payoff_ymax, padding=0)
        pi.enableAutoRange(axis="x")
        pi.enableAutoRange(axis="y", enable=False)

    # ------------------------------------------------------------------ smile
    def _render_smile(self, data: dict) -> None:
        self.clear()
        self._data_type = "smile"
        pi = self._pw.plotItem
        self._style_axes()

        legend = pi.addLegend(offset=(10, 10))
        legend.setBrush(pg.mkBrush(255, 255, 255, 210))
        legend.setPen(pg.mkPen(_GRID))

        self._hover_series = []

        # Collect all Y values to compute a tight, centred range
        all_x: list = []
        all_y: list = []

        # SABR smooth curve
        sc_data = data.get("sabr_curve")
        if sc_data and sc_data["x"]:
            pi.plot(sc_data["x"], sc_data["y"],
                    pen=pg.mkPen("#F44336", width=2), name="SABR")
            all_x.extend(sc_data["x"])
            all_y.extend(sc_data["y"])

        # Market IV scatter
        nm = data.get("market")
        if nm and nm["x"]:
            sc = pg.ScatterPlotItem(
                nm["x"], nm["y"], symbol="o", size=9,
                pen=pg.mkPen("#2196F3", width=1),
                brush=pg.mkBrush("#2196F3"),
                name="IV marché",
            )
            pi.addItem(sc)
            lbs = nm["labels"]
            self._hover_series.append((nm["x"], nm["y"], lambda i, lb=lbs: lb[i]))
            all_x.extend(nm["x"])
            all_y.extend(nm["y"])

        # Corrected / status=False
        cr = data.get("corrected")
        if cr and cr["x"]:
            sc2 = pg.ScatterPlotItem(
                cr["x"], cr["y"], symbol="x", size=11,
                pen=pg.mkPen("#FF9800", width=2),
                brush=pg.mkBrush(None),
                name="Corrigé",
            )
            pi.addItem(sc2)
            lbs = cr["labels"]
            self._hover_series.append((cr["x"], cr["y"], lambda i, lb=lbs: lb[i]))
            all_x.extend(cr["x"])
            all_y.extend(cr["y"])

        # Compute tight X / Y ranges with padding
        if all_x and all_y:
            x_arr = np.asarray(all_x, dtype=float)
            y_arr = np.asarray(all_y, dtype=float)
            y_arr = y_arr[np.isfinite(y_arr) & (y_arr > 0)]

            x_min, x_max = float(x_arr.min()), float(x_arr.max())
            x_pad = max((x_max - x_min) * 0.05, 0.001)

            if len(y_arr):
                y_min, y_max = float(y_arr.min()), float(y_arr.max())
                y_pad = max((y_max - y_min) * 0.15, 1e-5)
                pi.setXRange(x_min - x_pad, x_max + x_pad, padding=0)
                pi.setYRange(y_min - y_pad, y_max + y_pad, padding=0)
            else:
                pi.setXRange(x_min - x_pad, x_max + x_pad, padding=0)
                pi.enableAutoRange(axis="y")
        else:
            pi.enableAutoRange()

        # Spot / forward — pin label just above the bottom of the visible range
        spot = data.get("spot")
        if spot:
            pi.addItem(pg.InfiniteLine(
                pos=spot, angle=90,
                pen=pg.mkPen("#888888", width=1, style=Qt.PenStyle.DashLine),
            ))
            y_bot = pi.vb.viewRange()[1][0]
            lbl_item = pg.TextItem(f"Fwd {spot:.3f}", color="#888888", anchor=(0.5, 1))
            lbl_item.setPos(spot, y_bot)
            pi.addItem(lbl_item)

        pi.setLabel("bottom", "Strike", color=_AX)
        pi.setLabel("left", "Implied Volatility", color=_AX)

    # ------------------------------------------------------------------ hover
    def _on_mouse(self, evt) -> None:
        pos = evt[0]
        pi = self._pw.plotItem
        if not pi.sceneBoundingRect().contains(pos):
            self._tooltip.hide()
            self._vline.hide()
            return

        mp = pi.vb.mapSceneToView(pos)
        x_mouse = mp.x()
        self._vline.setPos(x_mouse)
        self._vline.show()

        x_range = pi.vb.viewRange()[0]
        x_span = (x_range[1] - x_range[0]) or 1.0

        best_dist = float("inf")
        best_text = ""
        for xs, ys, label_fn in self._hover_series:
            if len(xs) == 0:
                continue
            xa = np.asarray(xs, dtype=float)
            dists = np.abs(xa - x_mouse)
            i = int(np.argmin(dists))
            d_norm = dists[i] / x_span
            if d_norm < 0.03 and d_norm < best_dist:
                best_dist = d_norm
                best_text = label_fn(i)

        if best_text:
            self._tooltip.setText(best_text)
            self._tooltip.setPos(mp.x(), mp.y())
            self._tooltip.show()
        else:
            self._tooltip.hide()
