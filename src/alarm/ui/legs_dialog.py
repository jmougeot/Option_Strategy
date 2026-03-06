"""
Dialog for editing the legs of a strategy — with live prices from Bloomberg.
"""
from __future__ import annotations

from typing import Set

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from alarm.models.strategy import OptionLeg, Position, Strategy
from app import theme

# Column indices
_C_TICKER = 0
_C_POS    = 1
_C_QTY    = 2
_C_BID    = 3
_C_ASK    = 4
_C_MID    = 5
_C_CONTRIB = 6
_C_IV     = 7
_C_DEL    = 8
_HEADERS  = ["Ticker", "Pos", "Qty", "Bid", "Ask", "Mid", "Contrib.", "IV%", ""]
_NCOLS    = len(_HEADERS)


class LegsDialog(QDialog):
    """Dialog to edit option legs with live price display."""

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.strategy = strategy
        self.setWindowTitle(f"Legs — {strategy.name or 'Sans nom'}")
        self.setMinimumSize(850, 320)
        self._build()

        # Live refresh every 500ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_prices)
        self._timer.start(500)
        self._refresh_prices()

    # ── build ──────────────────────────────────────────────────────────────
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        self._table = QTableWidget(0, _NCOLS)
        self._table.setHorizontalHeaderLabels(_HEADERS)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("QTableWidget { font-size: 11px; }")

        vh = self._table.verticalHeader()
        if vh:
            vh.setVisible(False)
            vh.setDefaultSectionSize(26)

        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(_C_TICKER, QHeaderView.ResizeMode.Stretch)
            for c in range(1, _NCOLS):
                hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_C_POS,    80)
        self._table.setColumnWidth(_C_QTY,    50)
        self._table.setColumnWidth(_C_BID,    68)
        self._table.setColumnWidth(_C_ASK,    68)
        self._table.setColumnWidth(_C_MID,    68)
        self._table.setColumnWidth(_C_CONTRIB, 78)
        self._table.setColumnWidth(_C_IV,     55)
        self._table.setColumnWidth(_C_DEL,    36)
        lay.addWidget(self._table)

        for leg in self.strategy.legs:
            self._append_leg_row(leg)

        # Summary
        self._lbl_total = QLabel("")
        self._lbl_total.setStyleSheet("font-size: 12px; font-weight: bold; padding: 2px 0;")
        lay.addWidget(self._lbl_total)

        # Bottom buttons
        bot = QHBoxLayout()
        btn_add = QPushButton("+ Ajouter un leg")
        btn_add.clicked.connect(self._add_leg)
        bot.addWidget(btn_add)
        bot.addStretch()

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._commit)
        bb.rejected.connect(self.reject)
        bot.addWidget(bb)
        lay.addLayout(bot)

    # ── row management ─────────────────────────────────────────────────────
    def _append_leg_row(self, leg: OptionLeg) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)

        ticker_edit = QLineEdit(leg.ticker or "")
        ticker_edit.setPlaceholderText("SFRH6C 98 Comdty")
        ticker_edit.setStyleSheet("font-size: 11px;")
        self._table.setCellWidget(r, _C_TICKER, ticker_edit)
        ticker_edit.setProperty("leg_id", leg.id)

        pos_combo = QComboBox()
        pos_combo.setStyleSheet("font-size: 11px;")
        pos_combo.addItem("Long",  Position.LONG)
        pos_combo.addItem("Short", Position.SHORT)
        if leg.position == Position.SHORT:
            pos_combo.setCurrentIndex(1)
        self._table.setCellWidget(r, _C_POS, pos_combo)

        qty_spin = QSpinBox()
        qty_spin.setStyleSheet("font-size: 11px;")
        qty_spin.setRange(1, 999)
        qty_spin.setValue(leg.quantity)
        self._table.setCellWidget(r, _C_QTY, qty_spin)

        # Price cells (read-only)
        for col in (_C_BID, _C_ASK, _C_MID, _C_CONTRIB, _C_IV):
            item = QTableWidgetItem("—")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(r, col, item)

        del_btn = QPushButton("🗑")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda _, row=r: self._del_row(row))
        self._table.setCellWidget(r, _C_DEL, del_btn)

    def _add_leg(self) -> None:
        leg = self.strategy.add_leg()
        self._append_leg_row(leg)

    def _del_row(self, row: int) -> None:
        w = self._table.cellWidget(row, _C_TICKER)
        if w:
            w.setProperty("leg_id", "__del__")
        self._table.hideRow(row)

    # ── live prices ────────────────────────────────────────────────────────
    def _refresh_prices(self) -> None:
        total = 0.0
        all_priced = True
        n_legs = 0

        for r in range(self._table.rowCount()):
            if self._table.isRowHidden(r):
                continue
            ticker_w = self._table.cellWidget(r, _C_TICKER)
            if ticker_w is None:
                continue
            leg_id = ticker_w.property("leg_id")
            if leg_id == "__del__":
                continue

            leg = self.strategy.get_leg(leg_id)
            if leg is None:
                continue

            n_legs += 1
            self._set_price(r, _C_BID, leg.bid)
            self._set_price(r, _C_ASK, leg.ask)
            self._set_price(r, _C_MID, leg.mid)

            contrib = leg.get_price_contribution()
            item = self._table.item(r, _C_CONTRIB)
            if item:
                if contrib is not None:
                    item.setText(f"{contrib:+.4f}")
                    item.setForeground(QColor("#006600") if contrib >= 0 else QColor("#cc2200"))
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                    total += contrib
                else:
                    item.setText("—")
                    item.setForeground(QColor("#888"))
                    all_priced = False

            iv_item = self._table.item(r, _C_IV)
            if iv_item:
                if leg.implied_vol:
                    iv_item.setText(f"{leg.implied_vol:.2%}")
                else:
                    iv_item.setText("—")

        if all_priced and n_legs > 0:
            color = "#006600" if total >= 0 else "#cc2200"
            self._lbl_total.setText(
                f"Prix stratégie : <span style='color:{color}'>{total:+.4f}</span>"
            )
        elif n_legs > 0:
            self._lbl_total.setText("Prix stratégie : en attente de données…")
        else:
            self._lbl_total.setText("")

    def _set_price(self, r: int, col: int, val) -> None:
        item = self._table.item(r, col)
        if item is None:
            return
        if val is not None:
            item.setText(f"{val:.4f}")
            item.setForeground(QColor(theme.TEXT_PRIMARY))
        else:
            item.setText("—")
            item.setForeground(QColor("#888"))

    # ── commit ─────────────────────────────────────────────────────────────
    def _commit(self) -> None:
        """Write table values back into strategy.legs."""
        updated_ids: Set[str] = set()
        for r in range(self._table.rowCount()):
            ticker_w = self._table.cellWidget(r, _C_TICKER)
            pos_w    = self._table.cellWidget(r, _C_POS)
            qty_w    = self._table.cellWidget(r, _C_QTY)
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

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)
