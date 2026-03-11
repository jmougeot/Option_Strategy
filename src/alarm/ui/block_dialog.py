"""
Block Dialog — Legs editor + Bloomberg prices + price adjustment.

Merges the former LegsDialog (leg editing) and BlockDialog (block pricing)
into a single dialog.  Opened both from the Legs column (double-click)
and from the context-menu "Show Block".
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from alarm.models.strategy import OptionLeg, Position, Strategy, parse_leg_ticker
from alarm.services.block_service import (
    adjust_prices,
    build_confirmation_message,
    compute_total_quantities,
)
from app import theme

# Column indices
C_TICKER   = 0
C_POS      = 1
C_QTY      = 2
C_TOTAL    = 3
C_BBG      = 4
C_ADJUSTED = 5
_HEADERS = ["Ticker", "Pos", "Qty", "Total", "Mid BBG", "Mid Ajusté"]


class BlockDialog(QDialog):
    """Legs editor with live Bloomberg prices and block-price adjustment."""

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._strategy = strategy
        self._leg_ids: list[str] = []          # parallel to table rows
        self._base_total: Optional[int] = None

        self.setWindowTitle(f"Block — {strategy.name or 'Sans nom'}")
        self.setMinimumSize(820, 440)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._build()

        # Live-refresh Bloomberg mid prices every 500 ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_live_prices)
        self._timer.start(500)

    # ── construction ───────────────────────────────────────────────────────
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Title
        title = QLabel(f"<b>{self._strategy.name or 'Sans nom'}</b>")
        title.setStyleSheet(f"font-size: 15px; color: {theme.TEXT_ACCENT};")
        root.addWidget(title)

        # Table
        self._table = QTableWidget(0, len(_HEADERS))
        self._table.setHorizontalHeaderLabels(_HEADERS)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked | QTableWidget.EditTrigger.EditKeyPressed
        )
        vh = self._table.verticalHeader()
        if vh:
            vh.setVisible(False)
            vh.setDefaultSectionSize(32)
        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(C_TICKER, QHeaderView.ResizeMode.Stretch)
            for c in range(1, len(_HEADERS)):
                hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self._table.cellDoubleClicked.connect(self._on_dbl_click)
        self._table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self._table)

        # Price row
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Bloomberg Price:"))
        self._lbl_bbg_price = QLabel("—")
        self._lbl_bbg_price.setStyleSheet("font-weight: bold;")
        price_row.addWidget(self._lbl_bbg_price)
        price_row.addStretch()
        price_row.addWidget(QLabel("Target Price:"))
        self._spin_price = QDoubleSpinBox()
        self._spin_price.setRange(-999.0, 999.0)
        self._spin_price.setDecimals(4)
        self._spin_price.setSingleStep(0.0025)
        self._spin_price.setValue(self._strategy.target_price or 0.0)
        self._spin_price.valueChanged.connect(self._on_target_changed)
        price_row.addWidget(self._spin_price)
        root.addLayout(price_row)

        # Status
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(self._lbl_status)

        # Buttons
        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Leg")
        btn_add.clicked.connect(self._add_leg)
        btn_row.addWidget(btn_add)
        btn_row.addStretch()

        self._btn_copy = QPushButton("Copier message")
        self._btn_copy.clicked.connect(self._copy_message)
        btn_row.addWidget(self._btn_copy)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._commit)
        bb.rejected.connect(self.reject)
        btn_row.addWidget(bb)
        root.addLayout(btn_row)

        # Delete key
        sc = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._table)
        sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        sc.activated.connect(self._del_selected)

        # Initial populate
        self._populate_table()
        self._refresh_bbg_price()
        self._run_adjust()

    # ── table population ──────────────────────────────────────────────────
    def _populate_table(self) -> None:
        """Rebuild the full table from strategy legs."""
        compute_total_quantities(self._strategy, self._base_total)
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        self._leg_ids.clear()
        for row, leg in enumerate(self._strategy.legs):
            self._append_row(leg, editable_total=row == 0)
        self._table.blockSignals(False)
        self._update_status()

    def _append_row(self, leg: OptionLeg, *, editable_total: bool = False) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._leg_ids.append(leg.id)

        # Ticker — editable
        self._set_cell(r, C_TICKER, leg.ticker or "", editable=True)
        # Pos — toggle via double-click
        self._set_cell(r, C_POS, "Long" if leg.position == Position.LONG else "Short")
        # Qty — editable
        self._set_cell(r, C_QTY, str(leg.quantity), editable=True)
        # Total
        self._set_cell(r, C_TOTAL, self._fmt_int(leg.total_qty), editable=editable_total)
        # Mid BBG — live, read-only
        self._set_cell(r, C_BBG, self._fmt(leg.mid))
        # Mid Ajusté — read-only
        self._set_cell(r, C_ADJUSTED, self._fmt(leg.adjusted_mid))

    # ── cell helpers ──────────────────────────────────────────────────────
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
    def _fmt_int(val: Optional[int]) -> str:
        return str(val) if val is not None else "—"

    # ── interactions ──────────────────────────────────────────────────────
    def _on_dbl_click(self, row: int, col: int) -> None:
        if col != C_POS or row < 0 or row >= len(self._leg_ids):
            return
        leg = self._strategy.get_leg(self._leg_ids[row])
        if leg is None:
            return
        leg.position = Position.SHORT if leg.position == Position.LONG else Position.LONG
        self._table.blockSignals(True)
        item = self._table.item(row, C_POS)
        if item:
            item.setText("Long" if leg.position == Position.LONG else "Short")
        self._table.blockSignals(False)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        row, col = item.row(), item.column()
        if row < 0 or row >= len(self._leg_ids):
            return
        leg = self._strategy.get_leg(self._leg_ids[row])
        if leg is None:
            return

        if col == C_TICKER:
            raw = item.text().strip().upper()
            if raw and "COMDTY" not in raw:
                raw += " COMDTY"
            leg.ticker, leg.underlying, leg.strike = parse_leg_ticker(raw)

        elif col == C_QTY:
            try:
                leg.quantity = max(1, int(item.text()))
            except ValueError:
                leg.quantity = 1

        elif col == C_TOTAL and row == 0:
            text = item.text().strip().replace(",", ".")
            if not text or text == "—":
                self._base_total = None
            else:
                try:
                    self._base_total = int(round(float(text)))
                except ValueError:
                    self._lbl_status.setText("✗ Total invalide")
                    self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")
                    return
            self._run_adjust()

    def _add_leg(self) -> None:
        leg = self._strategy.add_leg()
        self._table.blockSignals(True)
        self._append_row(leg)
        self._table.blockSignals(False)

    def _del_selected(self) -> None:
        row = self._table.currentRow()
        if 0 <= row < len(self._leg_ids):
            leg_id = self._leg_ids.pop(row)
            self._strategy.remove_leg(leg_id)
            self._table.removeRow(row)

    # ── live price refresh ────────────────────────────────────────────────
    def _refresh_live_prices(self) -> None:
        for r in range(min(self._table.rowCount(), len(self._leg_ids))):
            leg = self._strategy.get_leg(self._leg_ids[r])
            if leg is None:
                continue
            it = self._table.item(r, C_BBG)
            if it:
                if leg.mid is not None:
                    it.setText(f"{leg.mid:.4f}")
                    it.setForeground(QColor(theme.TEXT_PRIMARY))
                else:
                    it.setText("—")
                    it.setForeground(QColor("#888"))
        self._refresh_bbg_price()

    def _refresh_bbg_price(self) -> None:
        contributions = [leg.get_price_contribution() for leg in self._strategy.legs]
        if all(c is not None for c in contributions):
            total = sum(c for c in contributions if c is not None)
            color = "#006600" if total >= 0 else "#cc2200"
            self._lbl_bbg_price.setText(f"<span style='color:{color}'>{total:+.4f}</span>")
        else:
            self._lbl_bbg_price.setText("—")

    def _update_status(self) -> None:
        n = len(self._strategy.legs)
        missing = sum(1 for leg in self._strategy.legs if leg.mid is None)
        if missing == 0:
            self._lbl_status.setText(f"{n} legs — tous les prix disponibles")
            self._lbl_status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px;")
        else:
            self._lbl_status.setText(
                f"{missing}/{n} leg(s) sans prix — ajustement sur les legs disponibles"
            )
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")

    # ── block adjust ──────────────────────────────────────────────────────
    def _on_target_changed(self, value: float) -> None:
        self._strategy.target_price = value
        self._run_adjust()

    def _run_adjust(self) -> None:
        if not self._strategy.legs:
            return
        adjust_prices(self._strategy)
        self._populate_table()

    def _copy_message(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is None:
            self._lbl_status.setText("✗ Impossible d'accéder au presse-papiers")
            self._lbl_status.setStyleSheet(f"color: {theme.WARNING}; font-size: 12px;")
            return
        clipboard.setText(build_confirmation_message(self._strategy))
        self._lbl_status.setText("✓ Message copié dans le presse-papiers")
        self._lbl_status.setStyleSheet(f"color: {theme.SUCCESS}; font-size: 12px;")

    # ── commit ────────────────────────────────────────────────────────────
    def _commit(self) -> None:
        """Legs are already synced live — just remove deleted legs and accept."""
        self._strategy.target_price = self._spin_price.value()
        active_ids = set(self._leg_ids)
        for leg in list(self._strategy.legs):
            if leg.id not in active_ids:
                self._strategy.remove_leg(leg.id)
        self.accept()

    # ── cleanup ───────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)