"""Mixin — Cell editing and double-click cycling."""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QTableWidget, QWidget

from alarm.models.strategy import Strategy, TargetCondition
from alarm.ui.columns import (
    C_ACTION, C_CLIENT, C_COND, C_LEGS, C_NAME,
    C_STATUS, C_TARGET,
)
from alarm.ui.block_dialog import BlockDialog

if TYPE_CHECKING:
    from alarm.handlers.alert_handler import AlertHandler
    from alarm.ui.alarm_state import RowState
    from bloomberg.realtime import BloombergService
    _WidgetBase = QWidget
else:
    _WidgetBase = object


class EditingMixin(_WidgetBase):
    """Handles cell double-click cycling and cell-changed editing."""

    _COND_CYCLE: list
    _STATUS_CYCLE: list
    _table: QTableWidget
    _states: dict[str, RowState]
    _bbg: BloombergService
    _alert: AlertHandler

    if TYPE_CHECKING:
        # Stubs for methods provided by other mixins
        def _strategy_at_row(self, row: int) -> Strategy | None: ...
        def _update_dot(self, row: Optional[int], s: Strategy) -> None: ...
        def _paint_row(self, row: int, s: Strategy) -> None: ...
        def _refresh_price_cell(self, row: int, price: Optional[float]) -> None: ...
        def _refresh_greeks_cells(self, row: int, s: Strategy) -> None: ...
        def _promote_ghost_row(self, row: int) -> Strategy | None: ...
        def _legs_summary(self, strategy: Strategy) -> str: ...
        def _row_by_sid(self, sid: str) -> int: ...

    # ── double-click cycling ──────────────────────────────────────────────────
    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        s = self._strategy_at_row(row)
        if s is None:
            return

        if col == C_COND:
            cur = next((i for i, (v, _) in enumerate(self._COND_CYCLE) if v == s.target_condition), 0)
            nxt = (cur + 1) % len(self._COND_CYCLE)
            s.target_condition = self._COND_CYCLE[nxt][0]
            self._table.blockSignals(True)
            item = self._table.item(row, C_COND)
            if item:
                item.setText(self._COND_CYCLE[nxt][1])
            self._table.blockSignals(False)
            self._update_dot(row, s)

        elif col == C_STATUS:
            cur = next((i for i, (v, _) in enumerate(self._STATUS_CYCLE) if v == s.status), 0)
            nxt = (cur + 1) % len(self._STATUS_CYCLE)
            s.status = self._STATUS_CYCLE[nxt][0]
            state = self._states.get(s.id)
            if state:
                state.reset()
            # Clear anti-spam so alarm can re-fire when set back to "En cours"
            self._alert.on_target_left(s.id)
            self._table.blockSignals(True)
            item = self._table.item(row, C_STATUS)
            if item:
                item.setText(self._STATUS_CYCLE[nxt][1])
            self._table.blockSignals(False)
            self._paint_row(row, s)
            self._update_dot(row, s)

        elif col == C_LEGS:
            self._edit_legs(s, row)

    # ── cell change ───────────────────────────────────────────────────────────
    def _on_cell_changed(self, row: int, col: int) -> None:
        s = self._strategy_at_row(row)

        # Ghost row → promote to real strategy on first edit
        if s is None:
            item = self._table.item(row, col)
            if item is None or not item.text().strip():
                return
            s = self._promote_ghost_row(row)
            if s is None:
                return

        item = self._table.item(row, col)
        if item is None:
            return
        text = item.text().strip()

        if col == C_CLIENT:
            s.client = text or None

        elif col == C_ACTION:
            s.action = text or None

        elif col == C_TARGET:
            try:
                val = float(text) if text else 0.0
            except ValueError:
                self._table.blockSignals(True)
                item.setText(f"{s.target_price:.4f}" if s.target_price is not None else "")
                self._table.blockSignals(False)
                return
            self._on_target_changed(val, s)

        elif col == C_NAME:
            try:
                from alarm.models.name_to_strategy import str_to_strat
                parsed = str_to_strat(text)
                if parsed and parsed.legs:
                    for t in s.get_all_tickers():
                        self._bbg.unsubscribe(t)
                    s.name   = parsed.name
                    s.client = parsed.client or s.client
                    s.action = parsed.action or s.action
                    s.legs   = parsed.legs
                    self._table.blockSignals(True)
                    name_item = self._table.item(row, C_NAME)
                    if name_item:
                        name_item.setText(s.name)
                    ci = self._table.item(row, C_CLIENT)
                    if ci and s.client:
                        ci.setText(s.client)
                    ai = self._table.item(row, C_ACTION)
                    if ai and s.action:
                        ai.setText(s.action)
                    self._table.blockSignals(False)
                    legs_item = self._table.item(row, C_LEGS)
                    if legs_item:
                        legs_item.setText(self._legs_summary(s))
                    for t in s.get_all_tickers():
                        self._bbg.subscribe(t)
                else:
                    s.name = text
            except Exception:
                s.name = text

    def _on_target_changed(self, v: float, s: Strategy) -> None:
        s.target_price = v if v != 0.0 else None
        row = self._row_by_sid(s.id)
        if row >= 0:
            self._update_dot(row, s)

    # ── legs dialog ───────────────────────────────────────────────────────────
    def _edit_legs(self, strategy: Strategy, row: int) -> None:
        dlg = BlockDialog(strategy, self, bbg=self._bbg)
        dlg.exec()

        row = self._row_by_sid(strategy.id)
        if row < 0:
            return

        legs_item = self._table.item(row, C_LEGS)
        if legs_item:
            legs_item.setText(self._legs_summary(strategy))

        target_item = self._table.item(row, C_TARGET)
        if target_item:
            target_item.setText(f"{strategy.target_price:.4f}" if strategy.target_price is not None else "")

        self._refresh_price_cell(row, strategy.calculate_strategy_price())
        self._refresh_greeks_cells(row, strategy)
        self._paint_row(row, strategy)
        self._update_dot(row, strategy)
