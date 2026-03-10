"""
Block Dialog — Popup affichant les legs avec prix Bloomberg ajustés.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDoubleSpinBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton,
    QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from alarm.models.strategy import OptionLeg, Position, Strategy
from alarm.services.block_service import (
    adjust_prices,
    build_confirmation_message,
    tick_for_underlying,
)
from app import theme


class BlockDialog(QDialog):
    """Popup qui affiche les legs, fetch Bloomberg, et ajuste les prix."""

    _COLS = ["Ticker", "Pos", "Qty", "Mid BBG", "Mid Ajusté"]

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._strategy = strategy
        self._results: List[OptionLeg] = list(strategy.legs)

        self.setWindowTitle(f"Block {strategy.name or ''}")
        self.setMinimumSize(800, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._build()

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

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_copy = QPushButton("Copier message")
        self._btn_copy.clicked.connect(self._copy_message)
        btn_row.addWidget(self._btn_copy)

        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

        # Remplir la table avec les prix temps réel et lancer l'ajustement
        self._populate_results()
        contributions = [leg.get_price_contribution() for leg in self._results]
        if all(c is not None for c in contributions):
            self._lbl_bbg_price.setText(f"{sum(c for c in contributions if c is not None):.4f}")
        self._run_adjust()

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
            self._set_cell(r, 0, lr.ticker or "—")
            self._set_cell(r, 1, "L" if lr.position == Position.LONG else "S")
            self._set_cell(r, 2, str(lr.quantity))
            self._set_cell(r, 3, self._fmt(lr.mid))
            self._set_cell(r, 4, self._fmt(lr.adjusted_mid))

        # Mise à jour du status
        n = len(self._results)
        if missing_count == 0:
            self._lbl_status.setText(f"✓ {n} legs — tous les prix disponibles")
            self._lbl_status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px;")
        else:
            self._lbl_status.setText(
                f"{missing_count}/{n} leg(s) sans prix — ajustement sur les legs disponibles"
            )
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, col, item)

    @staticmethod
    def _fmt(val: Optional[float]) -> str:
        return f"{val:.4f}" if val is not None else "—"

    def _copy_message(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            self._lbl_status.setText("✗ Impossible d'accéder au presse-papiers")
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")
            return

        clipboard.setText(build_confirmation_message(self._results, self._spin_price.value()))
        self._lbl_status.setText("✓ Message copié dans le presse-papiers")
        self._lbl_status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px;")

    def _on_price_changed(self) -> None:
        """Appelé quand le prix cible change — re-ajuste automatiquement."""
        self._run_adjust()

    def _run_adjust(self) -> None:
        """Ajuste les prix si on a des résultats et un prix cible."""
        if not self._results:
            return
        step = tick_for_underlying(self._results[0].underlying)
        target = self._spin_price.value()
        self._results = adjust_prices(self._results, step, target)
        self._populate_results()