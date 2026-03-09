"""Mixin — Alarm state machine (tick, dot update, fire, continue)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QTableWidget

from alarm.models.strategy import Strategy, StrategyStatus, TargetCondition
from alarm.ui.columns import C_STATUS, WARN_DELAY

if TYPE_CHECKING:
    from alarm.handlers.alert_handler import AlertHandler
    from alarm.ui.alarm_state import RowState


class AlarmMixin:
    """Alarm countdown, dot indicator, fire and continue logic."""

    _table: QTableWidget
    _pages: list[dict]
    _cur: int
    _states: dict[str, RowState]
    _alert: AlertHandler

    if TYPE_CHECKING:
        # Stubs for methods provided by other mixins
        def _paint_row(self, row: int, s: Strategy) -> None: ...

    def _tick(self) -> None:
        for row, s in enumerate(self._pages[self._cur]["strategies"]):
            self._update_dot(row, s)

    def _update_dot(self, row: int, s: Strategy) -> None:
        state = self._states.get(s.id)
        if state is None:
            return

        status_item = self._table.item(row, C_STATUS)
        self._paint_row(row, s)

        if s.status != StrategyStatus.EN_COURS:
            if status_item:
                status_item.setToolTip("Alarme désactivée")
            state.reset()
            return

        hit = s.is_target_reached()

        if hit is None:
            if status_item:
                status_item.setToolTip("Cible non définie")
            state.reset()
        elif not hit:
            state.reset()
            self._alert.on_target_left(s.id)
            price = s.calculate_strategy_price()
            if status_item:
                if price is not None and s.target_price is not None:
                    status_item.setToolTip(f"Distance cible : {s.target_price - price:+.4f}")
                else:
                    status_item.setToolTip("En attente…")
        else:
            if state.confirmed:
                cond = "inf." if s.target_condition == TargetCondition.INFERIEUR else "sup."
                if status_item:
                    status_item.setToolTip(f"ALARME — prix {cond} {s.target_price:.4f}")
            else:
                if state.warning_start is None:
                    state.warning_start = datetime.now()
                elapsed = state.elapsed()
                if elapsed >= WARN_DELAY:
                    state.confirmed = True
                    self._fire_alarm(row, s)
                else:
                    if status_item:
                        status_item.setToolTip(f"Alerte dans {WARN_DELAY - elapsed:.1f} s")

    def _fire_alarm(self, row: int, s: Strategy) -> None:
        s.status = StrategyStatus.FAIT
        self._table.blockSignals(True)
        status_item = self._table.item(row, C_STATUS)
        if status_item:
            status_item.setText("Fait")
        self._table.blockSignals(False)
        self._paint_row(row, s)

        self._alert.fire(
            strategy_id=s.id,
            strategy_name=s.name or "Sans nom",
            current_price=s.calculate_strategy_price(),
            target_price=s.target_price,  # type: ignore[arg-type]
            is_inferior=s.target_condition == TargetCondition.INFERIEUR,
        )

        status_item = self._table.item(row, C_STATUS)
        if status_item:
            cond = "inf." if s.target_condition == TargetCondition.INFERIEUR else "sup."
            status_item.setToolTip(f"ALARME — prix {cond} {s.target_price:.4f}")

    def _continue_alarm(self, strategy_id: str) -> None:
        """Callback from the popup 'Continuer l'alarme' — resets to En cours."""
        for row, s in enumerate(self._pages[self._cur]["strategies"]):
            if s.id == strategy_id:
                s.status = StrategyStatus.EN_COURS
                state = self._states.get(s.id)
                if state:
                    state.reset()
                self._table.blockSignals(True)
                status_item = self._table.item(row, C_STATUS)
                if status_item:
                    status_item.setText("En cours")
                self._table.blockSignals(False)
                self._paint_row(row, s)
                self._update_dot(row, s)
                break
