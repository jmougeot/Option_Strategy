"""
chart_widget.py -- PyQtGraph-based chart widget.
Accepts data dicts produced by build_payoff_figure / build_smile_figure.
"""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget

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

        self._pw = pg.PlotWidget()
        self._pw.setBackground(_BG)
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

        # Smile connecting line
        sl = data["smile_line"]
        if sl["x"]:
            pi.plot(sl["x"], sl["y"],
                    pen=pg.mkPen("#2196F3", width=2), name="Smile")

        # Normal IV scatter
        nm = data.get("normal")
        if nm and nm["x"]:
            sc = pg.ScatterPlotItem(
                nm["x"], nm["y"], symbol="o", size=9,
                pen=pg.mkPen("#2196F3", width=1),
                brush=pg.mkBrush("#2196F3"),
                name="IV marche",
            )
            pi.addItem(sc)
            lbs = nm["labels"]
            self._hover_series.append((nm["x"], nm["y"], lambda i, lb=lbs: lb[i]))

        # Corrected / extrapolated
        cr = data.get("corrected")
        if cr and cr["x"]:
            sc2 = pg.ScatterPlotItem(
                cr["x"], cr["y"], symbol="x", size=11,
                pen=pg.mkPen("#FF9800", width=2),
                brush=pg.mkBrush(None),
                name="Corrige",
            )
            pi.addItem(sc2)
            lbs = cr["labels"]
            self._hover_series.append((cr["x"], cr["y"], lambda i, lb=lbs: lb[i]))

        # SABR anomalies
        sb = data.get("sabr")
        if sb and sb["x"]:
            for K, ymkt, ymod in zip(sb["x"], sb["y_mkt"], sb["y_mod"]):
                pi.plot([K, K], [ymkt, ymod],
                        pen=pg.mkPen("#F44336", width=1, style=Qt.PenStyle.DotLine))
            sc3 = pg.ScatterPlotItem(
                sb["x"], sb["y_mkt"], symbol="d", size=12,
                pen=pg.mkPen("#F44336", width=1),
                brush=pg.mkBrush("#F44336"),
                name="Anomalie SABR",
            )
            pi.addItem(sc3)
            sc4 = pg.ScatterPlotItem(
                sb["x"], sb["y_mod"], symbol="s", size=8,
                pen=pg.mkPen("#F44336", width=1.5),
                brush=pg.mkBrush(None),
                name="SABR (modele)",
            )
            pi.addItem(sc4)
            lbs = sb["labels"]
            self._hover_series.append((sb["x"], sb["y_mkt"], lambda i, lb=lbs: lb[i]))

        # Spot / forward
        spot = data.get("spot")
        if spot:
            pi.addItem(pg.InfiniteLine(
                pos=spot, angle=90,
                pen=pg.mkPen("#888888", width=1, style=Qt.PenStyle.DashLine),
            ))
            lbl_item = pg.TextItem(f"Fwd {spot:.3f}", color="#888888", anchor=(0, 0))
            lbl_item.setPos(spot, 0)
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
