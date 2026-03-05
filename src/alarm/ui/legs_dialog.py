"""
Dialog for editing the legs of a strategy.
"""
from __future__ import annotations

from typing import Set

from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox,
    QHeaderView, QLineEdit, QPushButton,
    QSpinBox, QTableWidget, QVBoxLayout, QWidget,
)

from alarm.models.strategy import OptionLeg, Position, Strategy


class LegsDialog(QDialog):
    """Compact dialog to view / edit the option legs of a strategy."""

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.strategy = strategy
        self.setWindowTitle(f"Legs — {strategy.name or 'Sans nom'}")
        self.resize(700, 300)
        self._build()

    # ── build ──────────────────────────────────────────────────────────────────
    def _build(self) -> None:
        lay = QVBoxLayout(self)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Ticker", "Position", "Quantité", ""])
        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 110)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 60)
        self._table.setAlternatingRowColors(True)
        lay.addWidget(self._table)

        for leg in self.strategy.legs:
            self._append_leg_row(leg)

        btn_add = QPushButton("+ Ajouter un leg")
        btn_add.clicked.connect(self._add_leg)
        lay.addWidget(btn_add)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._commit)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _append_leg_row(self, leg: OptionLeg) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)

        ticker_edit = QLineEdit(leg.ticker or "")
        ticker_edit.setPlaceholderText("SFRF6 96.50 Comdty")
        self._table.setCellWidget(r, 0, ticker_edit)

        pos_combo = QComboBox()
        pos_combo.addItem("Long",  Position.LONG)
        pos_combo.addItem("Short", Position.SHORT)
        if leg.position == Position.SHORT:
            pos_combo.setCurrentIndex(1)
        self._table.setCellWidget(r, 1, pos_combo)

        qty_spin = QSpinBox()
        qty_spin.setRange(1, 999)
        qty_spin.setValue(leg.quantity)
        self._table.setCellWidget(r, 2, qty_spin)

        del_btn = QPushButton("🗑")
        del_btn.setFixedWidth(40)
        del_btn.clicked.connect(lambda _, row=r: self._del_row(row))
        self._table.setCellWidget(r, 3, del_btn)

        ticker_edit.setProperty("leg_id", leg.id)

    def _add_leg(self) -> None:
        leg = self.strategy.add_leg()
        self._append_leg_row(leg)

    def _del_row(self, row: int) -> None:
        w = self._table.cellWidget(row, 0)
        if w:
            w.setProperty("leg_id", "__del__")
        self._table.hideRow(row)

    def _commit(self) -> None:
        """Write table values back into strategy.legs."""
        updated_ids: Set[str] = set()
        for r in range(self._table.rowCount()):
            ticker_w = self._table.cellWidget(r, 0)
            pos_w    = self._table.cellWidget(r, 1)
            qty_w    = self._table.cellWidget(r, 2)
            if ticker_w is None:
                continue
            leg_id = ticker_w.property("leg_id")
            if leg_id == "__del__":
                continue

            leg = self.strategy.get_leg(leg_id)
            if leg is None:
                continue

            raw = ticker_w.text().strip().upper()  # type: ignore[attr-defined]
            if raw and "COMDTY" not in raw:
                raw = raw + " COMDTY"
            leg.ticker   = raw or ""
            leg.position = pos_w.currentData()  # type: ignore[attr-defined]
            leg.quantity = qty_w.value()         # type: ignore[attr-defined]
            updated_ids.add(leg_id)

        # remove legs that were deleted in the dialog
        for leg in list(self.strategy.legs):
            if leg.id not in updated_ids:
                self.strategy.remove_leg(leg.id)

        self.accept()
