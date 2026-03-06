"""
Smile Dialog — Popup affichant le smile de volatilité implicite.

Fetch les IV depuis Bloomberg pour une grille de strikes autour de l'ATM,
calibre SABR, et affiche le graphique + la table des données.
"""
from __future__ import annotations

import re
from typing import List, Optional

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from alarm.models.strategy import Strategy
from alarm.services.smile_service import SmilePoint, SmileResult, fetch_smile, parse_option_ticker
from app.chart_widget import PlotlyChart
from app import theme

_COLOR_WARN = QColor("#FFEAEA")
_COLOR_OK   = QColor("#EAFFF0")


class SmileDialog(QDialog):
    """Popup affichant le smile de volatilité implicite."""

    _COLS = ["Strike", "Call IV (bp)", "Put IV (bp)", "Call Mid", "Put Mid"]

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._strategy = strategy
        self._result: Optional[SmileResult] = None

        # Extraire underlying + expiry depuis le premier leg ticker
        self._underlying, self._expiry = self._extract_info(strategy)

        self.setWindowTitle(f"Smile — {self._underlying}{self._expiry}")
        self.setMinimumSize(1000, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._build()

        QTimer.singleShot(50, self._on_fetch)

    # ── extraction info ───────────────────────────────────────────────────
    @staticmethod
    def _extract_info(strategy: Strategy) -> tuple[str, str]:
        """Extrait underlying et expiry depuis la stratégie ou ses tickers."""
        if strategy.underlying and strategy.expiration:
            return strategy.underlying, strategy.expiration

        for leg in strategy.legs:
            if leg.ticker:
                parsed = parse_option_ticker(leg.ticker)
                if parsed:
                    return parsed["underlying"], parsed["expiry"]

        # Fallback: regex sur le ticker brut
        for leg in strategy.legs:
            if leg.ticker:
                m = re.match(r'^([A-Z]+)([FGHJKMNQUVXZ]\d+)', leg.ticker.strip().upper())
                if m:
                    return m.group(1), m.group(2)

        return "???", "??"

    # ── construction UI ───────────────────────────────────────────────────
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Titre
        title = QLabel(f"<b>Smile de volatilité — {self._underlying} {self._expiry}</b>")
        title.setStyleSheet(f"font-size: 15px; color: {theme.TEXT_ACCENT};")
        root.addWidget(title)

        # Splitter: chart (gauche) + table (droite)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Chart
        self._chart = PlotlyChart(min_height=350)
        splitter.addWidget(self._chart)

        # Table
        table_container = QWidget()
        table_lay = QVBoxLayout(table_container)
        table_lay.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, len(self._COLS))
        self._table.setHorizontalHeaderLabels(self._COLS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            for c in range(1, len(self._COLS)):
                hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        table_lay.addWidget(self._table)

        splitter.addWidget(table_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter)

        # Status + SABR info
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(self._lbl_status)

        self._lbl_sabr = QLabel("")
        self._lbl_sabr.setStyleSheet("font-size: 11px; color: #555; font-family: monospace;")
        root.addWidget(self._lbl_sabr)

        # Boutons
        btn_row = QHBoxLayout()
        self._btn_fetch = QPushButton("↻ Refresh")
        self._btn_fetch.setStyleSheet(
            f"background: {theme.ACCENT}; color: white; padding: 6px 16px;"
            f" border-radius: {theme.RADIUS_SM};"
        )
        self._btn_fetch.clicked.connect(self._on_fetch)
        btn_row.addWidget(self._btn_fetch)

        btn_row.addStretch()

        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    # ── fetch ─────────────────────────────────────────────────────────────
    def _on_fetch(self) -> None:
        from bloomberg.connection import get_session
        try:
            get_session()
        except ConnectionError:
            self._lbl_status.setText("Bloomberg non connecté — fetch ignoré")
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")
            return

        self._btn_fetch.setEnabled(False)
        self._btn_fetch.setText("Fetching…")
        self._lbl_status.setText("Connexion à Bloomberg…")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            self._result = fetch_smile(self._underlying, self._expiry)
            self._populate_table()
            self._build_chart()
            n = len(self._result.points)
            n_ok = sum(1 for p in self._result.points if p.call_iv or p.put_iv)
            self._lbl_status.setText(f"✓ {n_ok}/{n} strikes avec IV")
            self._lbl_status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px;")
        except Exception as e:
            self._lbl_status.setText(f"✗ Erreur : {e}")
            self._lbl_status.setStyleSheet(f"color: {theme.DANGER}; font-size: 12px;")
        finally:
            self._btn_fetch.setEnabled(True)
            self._btn_fetch.setText("↻ Refresh")

    # ── table ─────────────────────────────────────────────────────────────
    def _populate_table(self) -> None:
        if not self._result:
            return
        self._table.setRowCount(0)
        for sp in self._result.points:
            if sp.call_iv is None and sp.put_iv is None:
                continue
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_cell(r, 0, f"{sp.strike:g}")
            self._set_cell(r, 1, f"{sp.call_iv * 10000:.1f}" if sp.call_iv else "—")
            self._set_cell(r, 2, f"{sp.put_iv * 10000:.1f}" if sp.put_iv else "—")
            self._set_cell(r, 3, f"{sp.call_mid:.4f}" if sp.call_mid else "—")
            self._set_cell(r, 4, f"{sp.put_mid:.4f}" if sp.put_mid else "—")

            if sp.warning:
                for c in range(len(self._COLS)):
                    item = self._table.item(r, c)
                    if item:
                        item.setBackground(_COLOR_WARN)

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, col, item)

    # ── chart ─────────────────────────────────────────────────────────────
    def _build_chart(self) -> None:
        if not self._result or not self._result.points:
            self._chart.clear()
            return

        points = self._result.points
        forward = self._result.forward_price

        # Collecter les IV marché (moyenne call/put si les deux existent)
        mkt_x, mkt_y, mkt_labels = [], [], []
        for sp in points:
            ivs = [v for v in [sp.call_iv, sp.put_iv] if v is not None and v > 0]
            if not ivs:
                continue
            iv = sum(ivs) / len(ivs)
            mkt_x.append(sp.strike)
            mkt_y.append(iv)
            lbl = f"K={sp.strike:g}\nIV={iv * 10000:.1f}bp"
            if sp.call_iv and sp.put_iv:
                lbl += f"\nC={sp.call_iv * 10000:.1f} / P={sp.put_iv * 10000:.1f}"
            mkt_labels.append(lbl)

        if not mkt_x:
            self._chart.clear()
            self._lbl_sabr.setText("")
            return

        # Calibrer SABR
        sabr_curve_x, sabr_curve_y = [], []
        warn_x, warn_y, warn_labels = [], [], []

        try:
            from option.sabr import SABRCalibration
            strikes_arr = np.array(mkt_x)
            ivs_arr = np.array(mkt_y)
            F = forward if forward else float(np.median(strikes_arr))

            sabr = SABRCalibration(F=F, T=0.25, beta=0.0, vol_type="normal")
            res = sabr.fit(strikes_arr, ivs_arr)

            # Courbe lissée
            K_min, K_max = strikes_arr.min(), strikes_arr.max()
            pad = (K_max - K_min) * 0.05
            k_dense = np.linspace(K_min - pad, K_max + pad, 200)
            sabr_dense = np.maximum(sabr.predict(k_dense), 0.0)
            sabr_curve_x = k_dense.tolist()
            sabr_curve_y = sabr_dense.tolist()

            # Détecter les anomalies
            anomalies = sabr.anomalies(threshold=2.0, min_error_bps=1.0)
            anomaly_strikes = {a["strike"] for a in anomalies}

            # Séparer points normaux vs corrigés
            new_mkt_x, new_mkt_y, new_mkt_labels = [], [], []
            for x, y, lbl in zip(mkt_x, mkt_y, mkt_labels):
                if round(x, 4) in anomaly_strikes:
                    warn_x.append(x)
                    warn_y.append(y)
                    warn_labels.append(lbl + "\n⚠ Anomalie SABR")
                else:
                    new_mkt_x.append(x)
                    new_mkt_y.append(y)
                    new_mkt_labels.append(lbl)
            mkt_x, mkt_y, mkt_labels = new_mkt_x, new_mkt_y, new_mkt_labels

            self._lbl_sabr.setText(sabr.summary())
        except Exception as e:
            self._lbl_sabr.setText(f"SABR non calibré : {e}")

        # Construire le dict au format attendu par PlotlyChart._render_smile
        smile_data = {
            "type": "smile",
            "market": {"x": mkt_x, "y": mkt_y, "labels": mkt_labels} if mkt_x else None,
            "corrected": {"x": warn_x, "y": warn_y, "labels": warn_labels} if warn_x else None,
            "sabr_curve": {"x": sabr_curve_x, "y": sabr_curve_y} if sabr_curve_x else None,
            "spot": float(forward) if forward else None,
        }

        self._chart.set_title(f"Smile {self._underlying} {self._expiry}")
        self._chart.set_figure(smile_data)

