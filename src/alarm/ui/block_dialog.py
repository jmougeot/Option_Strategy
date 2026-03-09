"""
Block Dialog — Popup affichant les legs avec prix Bloomberg ajustés.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QDoubleSpinBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton,
    QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from alarm.models.strategy import Position, Strategy
from alarm.services.block_service import LegResult, adjust_prices
from app import theme

_COLOR_MISSING = QColor("#FFEAEA")   # fond rose pâle pour prix manquant
_COLOR_OK      = QColor("#EAFFF0")   # fond vert pâle pour ajusté OK

DATA_UNDERLYING = {
    "SFR": 0.0025,   # SOFR 3M
    "SFI": 0.0025,   # SONIA 1M
    "ER": 0.0025,   # Euribor 3M
    "0R": 0.0025,   # Euribor mid-curve
    "0Q": 0.005,   # SOFR mid-curve
    "0N": 0.0025,   # SONIA mid-curve
    "RX": 0.01,   # Euro-Bund 10Y
    "OE": 0.005,   # Euro-Bobl 5Y
    "DU": 0.005,   # Euro-Schatz 2Y
}


def _tick_for(underlying: str) -> float:
    """Retourne la taille du tick pour un underlying (ex: 'SFR', 'ER', 'RX')."""
    return DATA_UNDERLYING.get(underlying.upper(), 0.0025)


def _snap_to_quarter_tick(price: float, tick: float) -> float:
    """Arrondit un prix au quart de tick le plus proche."""
    step = tick / 4
    return round(price / step) * step


class BlockDialog(QDialog):
    """Popup qui affiche les legs, fetch Bloomberg, et ajuste les prix."""

    _COLS = ["Ticker", "Pos", "Qty", "Mid BBG", "Mid Ajusté"]

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._strategy = strategy
        self._results: List[LegResult] = []

        self.setWindowTitle(f"Block — {strategy.name or 'Sans nom'}")
        self.setMinimumSize(800, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._build()
        self._on_fetch()

    # ── construction ───────────────────────────────────────────────────────
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Titre
        title = QLabel(f"<b>{self._strategy.name}</b>")
        title.setStyleSheet(f"font-size: 15px; color: {theme.TEXT_ACCENT};")
        root.addWidget(title)

        # Table des legs
        self._table = QTableWidget(0, len(self._COLS))
        self._table.setHorizontalHeaderLabels(self._COLS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for c in range(1, len(self._COLS)):
                hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self._table)

        # Ligne prix stratégie
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Prix stratégie Bloomberg :"))
        self._lbl_bbg_price = QLabel("—")
        self._lbl_bbg_price.setStyleSheet("font-weight: bold;")
        price_row.addWidget(self._lbl_bbg_price)
        price_row.addStretch()

        price_row.addWidget(QLabel("Prix cible :"))
        self._spin_price = QDoubleSpinBox()
        self._spin_price.setRange(-999.0, 999.0)
        self._spin_price.setDecimals(4)
        self._spin_price.setSingleStep(0.0025)
        self._spin_price.setValue(self._strategy.target_price or 0.0)
        self._spin_price.valueChanged.connect(self._on_price_changed)
        price_row.addWidget(self._spin_price)
        root.addLayout(price_row)

        # Status / warnings
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(self._lbl_status)

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

        # Pré-remplir la table avec les legs (sans prix)
        self._populate_legs_only()

    # ── helpers table ──────────────────────────────────────────────────────
    def _populate_legs_only(self) -> None:
        """Remplit la table avec les legs sans données de prix."""
        self._table.setRowCount(0)
        for leg in self._strategy.legs:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_cell(r, 0, leg.ticker or "—")
            self._set_cell(r, 1, "L" if leg.position == Position.LONG else "S")
            self._set_cell(r, 2, str(leg.quantity))
            for c in range(3, len(self._COLS)):
                self._set_cell(r, c, "…")

    def _populate_results(self) -> None:
        """Remplit la table avec les résultats fetch + ajustement."""
        self._table.setRowCount(0)
        missing_count = 0
        for lr in self._results:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_cell(r, 0, lr.leg.ticker or "—")
            self._set_cell(r, 1, "L" if lr.leg.position == Position.LONG else "S")
            self._set_cell(r, 2, str(lr.leg.quantity))
            self._set_cell(r, 3, self._fmt(lr.bbg_mid))
            self._set_cell(r, 4, self._fmt(lr.adjusted_mid))

            # Colorer la ligne selon l'état
            is_missing = lr.bbg_mid is None
            if is_missing:
                missing_count += 1
            bg = _COLOR_MISSING if is_missing else (_COLOR_OK if lr.adjusted_mid is not None else None)
            if bg:
                for c in range(len(self._COLS)):
                    item = self._table.item(r, c)
                    if item:
                        item.setBackground(bg)

        # Mise à jour du status
        n = len(self._results)
        if missing_count == 0:
            self._lbl_status.setText(f"✓ {n} legs — tous les prix disponibles")
            self._lbl_status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px;")
        else:
            self._lbl_status.setText(
                f"⚠ {missing_count}/{n} leg(s) sans prix — ajustement sur les legs disponibles"
            )
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, col, item)

    @staticmethod
    def _fmt(val: Optional[float]) -> str:
        return f"{val:.4f}" if val is not None else "—"

    def _compute_bbg_strategy_price(self) -> Optional[float]:
        """Calcule le prix stratégie à partir des mids Bloomberg disponibles."""
        total = 0.0
        has_any = False
        for lr in self._results:
            if lr.bbg_mid is None:
                continue
            has_any = True
            sign = 1 if lr.leg.position == Position.LONG else -1
            total += sign * lr.leg.quantity * lr.bbg_mid
        return total if has_any else None

    def _run_adjust(self) -> None:
        """Ajuste les prix si on a des résultats et un prix cible."""
        if not self._results:
            return
        target = self._spin_price.value()
        if target != 0:
            self._results = adjust_prices(self._results, target)
        else:
            for lr in self._results:
                lr.adjusted_mid = lr.bbg_mid

        # Snap chaque prix ajusté au quart de tick de l'instrument
        for lr in self._results:
            if lr.adjusted_mid is not None:
                tick = _tick_for(lr.leg.underlying or "")
                lr.adjusted_mid = _snap_to_quarter_tick(lr.adjusted_mid, tick)

        self._populate_results()

    # ── actions ────────────────────────────────────────────────────────────
    def _on_fetch(self) -> None:
        """Construit les LegResult depuis les prix déjà disponibles dans les legs, puis ajuste."""
        self._results = [
            LegResult(leg=leg, bbg_mid=leg.mid)
            for leg in self._strategy.legs
        ]
        bbg_price = self._compute_bbg_strategy_price()
        self._lbl_bbg_price.setText(f"{bbg_price:.4f}" if bbg_price is not None else "—")
        self._run_adjust()

    def _on_price_changed(self) -> None:
        """Appelé quand le prix cible change — re-ajuste automatiquement."""
        self._run_adjust()
