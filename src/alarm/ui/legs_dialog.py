"""
Dialog for editing the legs of a strategy — with live mid prices.
"""
from __future__ import annotations

from typing import Optional, Set

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout,
    QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from alarm.models.strategy import OptionLeg, Position, Strategy, parse_leg_ticker
from app import theme

# Column indices — plain text items only, no widgets
_C_TICKER = 0
_C_POS    = 1
_C_QTY    = 2
_C_MID    = 3
_HEADERS  = ["Ticker", "Pos", "Qty", "Mid"]
_NCOLS    = len(_HEADERS)

_POS_CYCLE = [("Long", Position.LONG), ("Short", Position.SHORT)]


class LegsDialog(QDialog):
    """Simple legs editor: plain text cells + live mid price."""

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.strategy = strategy
        self.setWindowTitle(f"Legs — {strategy.name or 'Sans nom'}")
        self.setMinimumSize(420, 240)
        self._leg_ids: list[str] = []  # parallel to visible row indices
        self._build()

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
        self._table.setStyleSheet("QTableWidget { font-size: 13px; }")

        vh = self._table.verticalHeader()
        if vh:
            vh.setVisible(False)
            vh.setDefaultSectionSize(30)

        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(_C_TICKER, QHeaderView.ResizeMode.Stretch)
            for c in (_C_POS, _C_QTY, _C_MID):
                hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(_C_POS, 65)
        self._table.setColumnWidth(_C_QTY, 45)
        self._table.setColumnWidth(_C_MID, 80)

        self._table.cellDoubleClicked.connect(self._on_dbl_click)
        lay.addWidget(self._table)

        for leg in self.strategy.legs:
            self._append_row(leg)

        # Total label
        self._lbl_total = QLabel("")
        self._lbl_total.setStyleSheet("font-size: 13px; font-weight: bold; padding: 2px 0;")
        lay.addWidget(self._lbl_total)

        # Buttons
        bot = QHBoxLayout()
        btn_add = QPushButton("+ Leg")
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

        # Delete key removes selected row
        sc = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._table)
        sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc.activated.connect(self._del_selected)

    # ── row helpers ────────────────────────────────────────────────────────
    def _append_row(self, leg: OptionLeg) -> None:
        self._table.blockSignals(True)
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._leg_ids.append(leg.id)

        # Ticker — editable
        it_t = QTableWidgetItem(leg.ticker or "")
        it_t.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._table.setItem(r, _C_TICKER, it_t)

        # Pos — read-only, toggle via double-click
        pos_label = "Long" if leg.position == Position.LONG else "Short"
        it_p = QTableWidgetItem(pos_label)
        it_p.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it_p.setFlags(it_p.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(r, _C_POS, it_p)

        # Qty — editable
        it_q = QTableWidgetItem(str(leg.quantity))
        it_q.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(r, _C_QTY, it_q)

        # Mid — read-only, live
        it_m = QTableWidgetItem("—")
        it_m.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it_m.setFlags(it_m.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self._table.setItem(r, _C_MID, it_m)

        self._table.blockSignals(False)

    def _on_dbl_click(self, row: int, col: int) -> None:
        if col == _C_POS:
            item = self._table.item(row, _C_POS)
            if item:
                cur = item.text()
                item.setText("Short" if cur == "Long" else "Long")

    def _add_leg(self) -> None:
        leg = self.strategy.add_leg()
        self._append_row(leg)

    def _del_selected(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._leg_ids):
            self._leg_ids.pop(row)
            self._table.removeRow(row)
            self._refresh_prices()

    # ── live prices ────────────────────────────────────────────────────────
    def _refresh_prices(self) -> None:
        total = 0.0
        all_priced = True
        n = 0

        for r in range(self._table.rowCount()):
            if r >= len(self._leg_ids):
                break
            leg = self.strategy.get_leg(self._leg_ids[r])
            if leg is None:
                continue
            n += 1
            it = self._table.item(r, _C_MID)
            if it:
                if leg.mid is not None:
                    it.setText(f"{leg.mid:.4f}")
                    it.setForeground(QColor(theme.TEXT_PRIMARY))
                else:
                    it.setText("—")
                    it.setForeground(QColor("#888"))
                    all_priced = False

            contrib = leg.get_price_contribution()
            if contrib is not None:
                total += contrib
            else:
                all_priced = False

        if all_priced and n > 0:
            color = "#006600" if total >= 0 else "#cc2200"
            self._lbl_total.setText(
                f"Prix stratégie : <span style='color:{color}'>{total:+.4f}</span>"
            )
        elif n > 0:
            self._lbl_total.setText("Prix stratégie : en attente…")
        else:
            self._lbl_total.setText("")

    # ── commit ─────────────────────────────────────────────────────────────
    def _commit(self) -> None:
        updated_ids: Set[str] = set()
        for r in range(self._table.rowCount()):
            if r >= len(self._leg_ids):
                break
            leg = self.strategy.get_leg(self._leg_ids[r])
            if leg is None:
                continue

            raw = (self._table.item(r, _C_TICKER).text().strip().upper()
                   if self._table.item(r, _C_TICKER) else "")
            if raw and "COMDTY" not in raw:
                raw += " COMDTY"
            ticker, underlying, strike = parse_leg_ticker(raw)
            leg.ticker = ticker
            leg.underlying = underlying
            leg.strike = strike

            pos_text = (self._table.item(r, _C_POS).text()
                        if self._table.item(r, _C_POS) else "Long")
            leg.position = Position.SHORT if pos_text == "Short" else Position.LONG

            qty_text = (self._table.item(r, _C_QTY).text()
                        if self._table.item(r, _C_QTY) else "1")
            try:
                leg.quantity = max(1, int(qty_text))
            except ValueError:
                leg.quantity = 1

            updated_ids.add(leg.id)

        for leg in list(self.strategy.legs):
            if leg.id not in updated_ids:
                self.strategy.remove_leg(leg.id)

        self.accept()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)
