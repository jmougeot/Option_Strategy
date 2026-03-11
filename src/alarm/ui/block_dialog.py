"""
Block Dialog — Popup affichant les legs avec prix Bloomberg ajustés.
"""
from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt
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
    compute_total_quantities,
    tick_for_underlying,
)
from app import theme


class BlockDialog(QDialog):
    """Popup qui affiche les legs, fetch Bloomberg, et ajuste les prix."""

    C_TICKER = 0
    C_POS = 1
    C_QTY = 2
    C_TOTAL = 3
    C_BBG = 4
    C_ADJUSTED = 5

    _COLS = ["Ticker", "Pos", "Qty", "Total", "Mid BBG", "Mid Ajusté"]

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._strategy = strategy
        self._results: List[OptionLeg] = list(strategy.legs)
        self._base_total: Optional[int] = None

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
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )
        self._table.itemChanged.connect(self._on_item_changed)
        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            for c in range(1, len(self._COLS)):
                hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self._table)

        # Ligne prix stratégie
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Bloomberg Price:"))
        self._lbl_bbg_price = QLabel("—")
        self._lbl_bbg_price.setStyleSheet("font-weight: bold;")
        price_row.addWidget(self._lbl_bbg_price)
        price_row.addStretch()

        price_row.addWidget(QLabel("Target Price :"))
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
        self._refresh_bbg_price()
        self._run_adjust()

    def _refresh_bbg_price(self) -> None:
        """Met à jour le label du prix Bloomberg agrégé."""
        contributions = [leg.get_price_contribution() for leg in self._results]
        if all(c is not None for c in contributions):
            self._lbl_bbg_price.setText(f"{sum(c for c in contributions if c is not None):.4f}")
        else:
            self._lbl_bbg_price.setText("—")

    # ── helpers table ──────────────────────────────────────────────────────
    def _populate_results(self) -> None:
        """Remplit la table avec les résultats fetch + ajustement."""
        compute_total_quantities(self._results, self._base_total)
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        missing_count = 0
        for row, leg in enumerate(self._results):
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._set_cell(r, self.C_TICKER, leg.ticker or "—")
            self._set_cell(r, self.C_POS, "L" if leg.position == Position.LONG else "S")
            self._set_cell(r, self.C_QTY, str(leg.quantity))
            self._set_cell(r, self.C_TOTAL, self._fmt_total(leg.total_qty), editable=row == 0)
            self._set_cell(r, self.C_BBG, self._fmt(leg.mid))
            self._set_cell(r, self.C_ADJUSTED, self._fmt(leg.adjusted_mid))

            if leg.mid is None:
                missing_count += 1

        self._table.blockSignals(False)

        # Mise à jour du status
        n = len(self._results)
        if missing_count == 0:
            self._lbl_status.setText(f"{n} legs — tous les prix disponibles")
            self._lbl_status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px;")
        else:
            self._lbl_status.setText(
                f"{missing_count}/{n} leg(s) sans prix — ajustement sur les legs disponibles"
            )
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")

    def _set_cell(self, row: int, col: int, text: str, editable: bool = False) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if not editable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(row, col, item)

    @staticmethod
    def _fmt(val: Optional[float]) -> str:
        return f"{val:.4f}" if val is not None else "—"

    @staticmethod
    def _fmt_total(val: Optional[int]) -> str:
        return str(val) if val is not None else "—"

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.row() != 0 or item.column() != self.C_TOTAL:
            return

        text = item.text().strip().replace(",", ".")
        if not text or text == "—":
            self._base_total = None
            self._populate_results()
            return

        try:
            self._base_total = int(round(float(text)))
        except ValueError:
            self._lbl_status.setText("✗ Total invalide")
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")
            self._populate_results()
            return

        self._populate_results()

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