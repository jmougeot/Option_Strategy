"""
AlarmPage — Table-based strategy price monitor.

Composed from mixins:
  - UIBuildMixin        (alarm_page_ui.py)       — toolbar + table construction
  - PagesMixin          (alarm_page_pages.py)     — page combo CRUD
  - TableMixin          (alarm_page_table.py)     — row population, helpers, add/remove
  - EditingMixin        (alarm_page_editing.py)   — cell editing & double-click cycling
  - BloombergMixin      (alarm_page_bloomberg.py) — price/greeks/subscription
  - AlarmMixin          (alarm_page_alarm.py)     — alarm state machine
"""
from __future__ import annotations

from typing import Dict, List

from PyQt6.QtCore import QPoint, QTimer
from PyQt6.QtWidgets import QMenu, QWidget

from alarm.handlers.alert_handler import AlertHandler
from alarm.handlers.file_handler import FileHandler
from alarm.models.strategy import Strategy
from alarm.ui.alarm_state import RowState
from alarm.ui.block_dialog import BlockDialog
from alarm.ui.smile_dialog import SmileDialog
from bloomberg.realtime import BloombergService

from alarm.ui.alarm_page_alarm import AlarmMixin
from alarm.ui.alarm_page_bloomberg import BloombergMixin
from alarm.ui.alarm_page_editing import EditingMixin
from alarm.ui.alarm_page_pages import PagesMixin
from alarm.ui.alarm_page_table import TableMixin
from alarm.ui.alarm_page_ui import UIBuildMixin


class AlarmPage(
    UIBuildMixin,
    PagesMixin,
    TableMixin,
    EditingMixin,
    BloombergMixin,
    AlarmMixin,
    QWidget,
):
    """Table-based strategy price monitor page."""

    # ── init ──────────────────────────────────────────────────────────────────
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Pages: list of {"name": str, "strategies": List[Strategy]}
        self._pages: List[Dict] = [{"name": "Page 1", "strategies": []}]
        self._cur: int = 0

        # Per-strategy alarm state, keyed by strategy.id
        self._states: Dict[str, RowState] = {}

        # Bloomberg
        self._bbg = BloombergService()
        self._bbg.price_updated.connect(self._on_price_updated)
        self._bbg.connection_status.connect(self._on_bbg_status)

        # Handlers
        self._alert = AlertHandler(self, self._continue_alarm)
        self._file  = FileHandler(self)

        self._build_ui()

        # Auto-load last workspace
        loaded = self._file.auto_load()
        if loaded:
            self._apply_loaded_pages(loaded)

        # Periodic tick: check alarm countdowns every 500 ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

        # Start Bloomberg 1 s after the widget is first shown
        QTimer.singleShot(1000, self._bbg.start)

    # ── save / load ───────────────────────────────────────────────────────────
    def _save(self) -> None:
        self._file.save(self._pages)

    def _load(self) -> None:
        pages = self._file.load()
        if pages is not None:
            self._apply_loaded_pages(pages)

    def _apply_loaded_pages(self, pages: List[Dict]) -> None:
        self._bbg.unsubscribe_all()
        self._states.clear()
        self._pages = pages if pages else [{"name": "Page 1", "strategies": []}]
        for page in self._pages:
            for strategy in page["strategies"]:
                self._states[strategy.id] = RowState(strategy)
        self._cur = 0
        self._refresh_page_combo()
        self._reload_table()

    # ── context menu ──────────────────────────────────────────────────────────
    def _show_context_menu(self, pos: QPoint) -> None:
        row = self._table.rowAt(pos.y())
        if row < 0:
            return
        s = self._strategy_at_row(row)
        if s is None:
            return
        menu = QMenu(self)
        act_plot   = menu.addAction("Plot Backtest")
        act_payoff = menu.addAction("Show Payoff")
        act_block = menu.addAction("Show Block")
        act_smile = menu.addAction("Show Smile")
        vp = self._table.viewport()
        action = menu.exec(vp.mapToGlobal(pos) if vp else pos)
        if action == act_plot:
            self._plot_backtest(s)
        elif action == act_payoff:
            self._show_payoff(s)
        elif action == act_block:
            self._show_block(s)
        elif action == act_smile:
            self._show_smile(s)

    def _plot_backtest(self, strategy: Strategy) -> None:
        """À implémenter — affiche le backtest de la stratégie."""
        pass  # TODO

    def _show_payoff(self, strategy: Strategy) -> None:
        """À implémenter — affiche le profil de gain/perte de la stratégie."""
        pass  # TODO

    def _show_smile(self, strategy: Strategy) -> None:
        dlg = SmileDialog(strategy, parent=self)
        dlg.exec()

    def _show_block(self, strategy: Strategy) -> None:
        dlg = BlockDialog(strategy, parent=self)
        dlg.exec()

    # ── cleanup ───────────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._bbg.stop()
        super().closeEvent(event)
