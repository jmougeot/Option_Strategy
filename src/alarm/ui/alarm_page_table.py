"""Mixin — Table population, row helpers, add / remove strategies."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

from alarm.models.strategy import (
    Position, Strategy, StrategyStatus, TargetCondition, normalize_ticker,
)
from alarm.ui.alarm_state import RowState
from alarm.ui.columns import (
    C_ACTION, C_CLIENT, C_COND, C_DELTA,
    C_FUT, C_GAMMA, C_IV, C_LEGS, C_NAME,
    C_PRICE, C_STATUS, C_TARGET, C_THETA,
)
from app import theme

if TYPE_CHECKING:
    from bloomberg.realtime import BloombergService


class TableMixin:
    """Table population, row lookup helpers, add / remove strategies."""

    _GHOST_ROWS: int
    _STATUS_COLOUR: dict
    _table: QTableWidget
    _pages: list[dict]
    _cur: int
    _states: dict[str, RowState]
    _bbg: BloombergService

    if TYPE_CHECKING:
        # Stubs for methods provided by other mixins
        @staticmethod
        def _future_ticker_from_option(option_ticker: str) -> Optional[str]: ...

    # ── table population ──────────────────────────────────────────────────────
    def _reload_table(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for s in self._pages[self._cur]["strategies"]:
            if s.id not in self._states:
                self._states[s.id] = RowState(s)
            self._append_row(s)
        self._fill_ghost_rows()
        self._table.blockSignals(False)

    def _fill_ghost_rows(self) -> None:
        """Ensure there are always _GHOST_ROWS empty rows at the bottom."""
        n_strat = len(self._pages[self._cur]["strategies"])
        current_total = self._table.rowCount()
        n_ghosts = current_total - n_strat
        need = self._GHOST_ROWS - n_ghosts
        if need <= 0:
            return
        self._table.blockSignals(True)
        for _ in range(need):
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._table.setRowHeight(r, 34)
            for col in range(self._table.columnCount()):
                editable = col in (C_CLIENT, C_NAME, C_ACTION, C_TARGET)
                it = QTableWidgetItem("")
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if not editable:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._table.setItem(r, col, it)
        self._table.blockSignals(False)

    def _append_row(self, strategy: Strategy) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setRowHeight(r, 34)

        def _item(text: str, editable: bool = True) -> QTableWidgetItem:
            it = QTableWidgetItem(text)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not editable:
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            return it

        self._table.setItem(r, C_CLIENT, _item(strategy.client or ""))
        self._table.setItem(r, C_NAME,   _item(strategy.name or ""))
        self._table.setItem(r, C_ACTION, _item(strategy.action or ""))
        self._table.setItem(r, C_LEGS,   _item(self._legs_summary(strategy), editable=False))
        self._table.setItem(r, C_PRICE,  _item("--", editable=False))

        cond_text = "Inférieur à" if strategy.target_condition == TargetCondition.INFERIEUR else "Supérieur à"
        self._table.setItem(r, C_COND, _item(cond_text, editable=False))

        target_val = f"{strategy.target_price:.4f}" if strategy.target_price is not None else ""
        self._table.setItem(r, C_TARGET, _item(target_val))

        status_text = {
            StrategyStatus.EN_COURS: "En cours",
            StrategyStatus.FAIT:     "Fait",
            StrategyStatus.ANNULE:   "Annulé",
        }
        self._table.setItem(r, C_STATUS, _item(status_text.get(strategy.status, "En cours"), editable=False))

        # Greek / live analytic cells
        for col in (C_DELTA, C_GAMMA, C_THETA, C_IV, C_FUT):
            self._table.setItem(r, col, _item("--", editable=False))

        # Bloomberg subscriptions — options + underlying futures
        for t in strategy.get_all_tickers():
            self._bbg.subscribe(t)
            fut = self._future_ticker_from_option(normalize_ticker(t))
            if fut:
                self._bbg.subscribe(fut)

        self._paint_row(r, strategy)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _legs_summary(self, strategy: Strategy) -> str:
        if not strategy.legs:
            return "—"
        parts = []
        for leg in strategy.legs:
            tick = (leg.ticker or "?").replace(" COMDTY", "")
            sign = "+" if leg.position == Position.LONG else "−"
            qty = leg.quantity
            parts.append(f"{sign}{qty} {tick}")
        return " / ".join(parts)

    def _row_by_sid(self, sid: str) -> int:
        for i, s in enumerate(self._pages[self._cur]["strategies"]):
            if s.id == sid:
                return i
        return -1

    def _strategy_at_row(self, row: int) -> Optional[Strategy]:
        strategies = self._pages[self._cur]["strategies"]
        return strategies[row] if 0 <= row < len(strategies) else None

    # ── delete ────────────────────────────────────────────────────────────────
    def _delete_selected_row(self) -> None:
        sm = self._table.selectionModel()
        rows = sorted({idx.row() for idx in sm.selectedRows()}, reverse=True) if sm else []
        if not rows:
            row = self._table.currentRow()
            if row >= 0:
                rows = [row]
        for row in rows:
            s = self._strategy_at_row(row)
            if s is not None:
                self._remove_strategy(s)

    # ── add / remove ──────────────────────────────────────────────────────────
    def _promote_ghost_row(self, row: int) -> Optional[Strategy]:
        """Turn a ghost row into a real strategy and refill ghosts."""
        strategies = self._pages[self._cur]["strategies"]
        if row < len(strategies):
            return None  # not a ghost row
        strategy = Strategy(id=str(uuid.uuid4()), name="")
        strategies.append(strategy)
        self._states[strategy.id] = RowState(strategy)

        # Make non-editable cells functional
        for col in (C_LEGS, C_PRICE, C_COND, C_STATUS, C_DELTA, C_GAMMA, C_THETA, C_IV, C_FUT):
            item = self._table.item(row, col)
            if item:
                if col == C_LEGS:
                    item.setText("—")
                elif col == C_PRICE:
                    item.setText("--")
                elif col == C_COND:
                    item.setText("Inférieur à")
                elif col == C_STATUS:
                    item.setText("En cours")
                elif col in (C_DELTA, C_GAMMA, C_THETA, C_IV, C_FUT):
                    item.setText("--")

        self._fill_ghost_rows()
        return strategy

    def _add_strategy(self, strategy: Strategy | None = None) -> None:
        if strategy is None:
            strategy = Strategy(id=str(uuid.uuid4()), name="")
        self._pages[self._cur]["strategies"].append(strategy)
        self._states[strategy.id] = RowState(strategy)
        self._append_row(strategy)

    def _remove_strategy(self, strategy: Strategy) -> None:
        for t in strategy.get_all_tickers():
            self._bbg.unsubscribe(t)
            fut = self._future_ticker_from_option(normalize_ticker(t))
            if fut:
                self._bbg.unsubscribe(fut)
        self._states.pop(strategy.id, None)
        strategies = self._pages[self._cur]["strategies"]
        row = next((i for i, s in enumerate(strategies) if s.id == strategy.id), -1)
        if row >= 0:
            strategies.pop(row)
            self._table.removeRow(row)
            self._fill_ghost_rows()

    # ── row painting ──────────────────────────────────────────────────────────
    def _paint_row(self, row: int, s: Strategy) -> None:
        hit = s.is_target_reached()
        if s.status == StrategyStatus.ANNULE:
            colour = self._STATUS_COLOUR[StrategyStatus.ANNULE]
        elif s.status == StrategyStatus.FAIT or hit is True:
            colour = self._STATUS_COLOUR[StrategyStatus.FAIT]
        else:
            colour = self._STATUS_COLOUR[StrategyStatus.EN_COURS]

        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item is None:
                item = QTableWidgetItem()
                self._table.setItem(row, col, item)
            item.setBackground(colour)
