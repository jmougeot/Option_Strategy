"""
Chart widget — matplotlib FigureCanvasQTAgg embedded in Qt.
Fully interactive: zoom, pan, hover tooltips via NavigationToolbar2QT.

Usage:
    chart = PlotlyChart(parent)
    chart.set_figure(fig)   # matplotlib Figure
    chart.clear()
"""
from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy


class PlotlyChart(QWidget):
    """
    Interactive chart widget backed by matplotlib FigureCanvasQTAgg.
    Navigation toolbar: zoom, pan, save, home.
    """

    def __init__(self, parent: Optional[QWidget] = None, min_height: int = 420):
        super().__init__(parent)
        self._min_height = min_height
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._show_figure(self._empty_figure())

    # ------------------------------------------------------------------
    def set_figure(self, fig) -> None:
        """Display a matplotlib Figure (or a plotly figure as fallback PNG)."""
        if hasattr(fig, "to_image"):
            mpl_fig = self._plotly_to_mpl(fig)
        else:
            mpl_fig = fig
        self._show_figure(mpl_fig)

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self._show_figure(self._empty_figure())

    # ------------------------------------------------------------------ private
    def _show_figure(self, fig: Figure) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        canvas = FigureCanvasQTAgg(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        canvas.setMinimumHeight(self._min_height)

        toolbar = NavigationToolbar2QT(canvas, self)
        toolbar.setStyleSheet("QToolBar { border: none; }")

        self._layout.addWidget(toolbar)
        self._layout.addWidget(canvas)
        canvas.draw_idle()

    @staticmethod
    def _empty_figure() -> Figure:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_visible(False)
        fig.patch.set_facecolor("#0d1117")
        fig.text(0.5, 0.5, "No chart", ha="center", va="center",
                 color="#888", fontsize=13)
        plt.close(fig)
        return fig

    @staticmethod
    def _plotly_to_mpl(plotly_fig) -> Figure:
        """Fallback: render a plotly figure as PNG and embed in an image axis."""
        try:
            import io
            import plotly.io as pio
            from matplotlib.image import imread
            png_bytes = pio.to_image(plotly_fig, format="png", width=1200, height=500, scale=1.5)
            img = imread(io.BytesIO(png_bytes))
            fig, ax = plt.subplots(figsize=(10, 4.5))
            ax.imshow(img)
            ax.axis("off")
            fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
            plt.close(fig)
            return fig
        except Exception as exc:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, f"Chart error:\n{exc}", ha="center", va="center",
                    transform=ax.transAxes, color="red")
            plt.close(fig)
            return fig
