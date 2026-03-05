"""
MainWindow — QMainWindow with:
  • Left QDockWidget: Scenario + Params + Filter + Scoring panels (scrollable)
  • Central QStackedWidget:
      Page 0 — QTabWidget: Overview, Volatility, History, Email, Help
      Page 1 — AlarmPage (full Strategy Price Monitor)
  • Top toolbar to switch between the two pages
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDockWidget, QMainWindow, QScrollArea, QSizePolicy,
    QStackedWidget, QTabWidget, QToolBar, QVBoxLayout, QWidget,
)

from app.app_state import AppState
from app.sidebar.params_panel import ParamsPanel
from app.sidebar.scenario_panel import ScenarioPanel
from app.sidebar.filter_panel import FilterPanel
from app.sidebar.scoring_panel import ScoringPanel
from app.pages.overview_page import OverviewPage
from app.pages.volatility_page import VolatilityPage
from app.pages.history_page import HistoryPage
from app.pages.email_page import EmailPage
from app.pages.help_page import HelpPage
from app.pages.alarm_page import AlarmPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("M2O — Options Strategy")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        # ── Central State ──────────────────────────────────────────────────
        self._state = AppState()

        # ── Build sidebar ──────────────────────────────────────────────────
        self._pnl_scenario = ScenarioPanel()
        self._pnl_params   = ParamsPanel()
        self._pnl_filter   = FilterPanel()
        self._pnl_scoring  = ScoringPanel()

        sidebar_contents = QWidget()
        sidebar_lay = QVBoxLayout(sidebar_contents)
        sidebar_lay.setContentsMargins(10, 10, 10, 10)
        sidebar_lay.setSpacing(10)
        for w in (self._pnl_scenario, self._pnl_params, self._pnl_filter, self._pnl_scoring):
            sidebar_lay.addWidget(w)
        sidebar_lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(sidebar_contents)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(380)
        scroll.setMaximumWidth(600)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        dock = QDockWidget("Parameters", self)
        dock.setWidget(scroll)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        # ── Update state when sidebar changes ──────────────────────────────
        for pnl in (self._pnl_params, self._pnl_scenario, self._pnl_filter, self._pnl_scoring):
            pnl.changed.connect(self._sync_state)
        self._sync_state()   # initial sync

        # ── Pages ──────────────────────────────────────────────────────────
        self._page_overview  = OverviewPage(self._state)
        self._page_volatility = VolatilityPage(self._state)
        self._page_history   = HistoryPage(self._state)
        self._page_email     = EmailPage(self._state)
        self._page_help      = HelpPage()
        self._page_alarm     = AlarmPage()

        # Wire Volatility "Rerun pipeline" → Overview
        self._page_volatility.rerun_requested.connect(self._page_overview.rerun_with_prefilled)

        # Wire Overview result → refresh Volatility
        self._page_overview.result_available.connect(self._page_volatility.refresh)

        # Wire History restore → populate sidebar + sync
        self._page_history.restore_requested.connect(self._on_restore_from_history)

        # Wire Overview result → refresh History table
        self._page_overview.result_available.connect(self._page_history._load)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._page_overview,   "Overview")
        tabs.addTab(self._page_volatility, "Volatility")
        tabs.addTab(self._page_history,    "History")
        tabs.addTab(self._page_email,      "Email")
        tabs.addTab(self._page_help,       "Help")

        # ── Top navigation toolbar ─────────────────────────────────────────
        toolbar = QToolBar("Navigation", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setStyleSheet("""
            QToolBar { spacing: 8px; padding: 6px 10px; }
            QToolButton {
                font-size: 15px; padding: 6px 20px;
                border: 1px solid transparent; border-radius: 4px;
            }
            QToolButton:checked {
                background: #4A5173; color: white;
                border-color: #4A5173;
            }
            QToolButton:!checked { color: #4A5173; }
            QToolButton:hover:!checked { background: #e8e9ef; }
        """)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        act_strategy = QAction("📊  Stratégies", self)
        act_alarm    = QAction("🔔  Alarmes",    self)
        for a in (act_strategy, act_alarm):
            a.setCheckable(True)
        act_strategy.setChecked(True)
        toolbar.addAction(act_strategy)
        toolbar.addAction(act_alarm)

        # ── Central stacked widget ─────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(tabs)               # page 0 — options strategy
        self._stack.addWidget(self._page_alarm)   # page 1 — alarm monitor
        self.setCentralWidget(self._stack)

        # keep a reference to the dock so we can hide/show it
        self._dock = dock

        def _go_strategy():
            act_strategy.setChecked(True)
            act_alarm.setChecked(False)
            self._stack.setCurrentIndex(0)
            self._dock.show()

        def _go_alarm():
            act_alarm.setChecked(True)
            act_strategy.setChecked(False)
            self._stack.setCurrentIndex(1)
            self._dock.hide()

        act_strategy.triggered.connect(lambda: _go_strategy())
        act_alarm.triggered.connect(lambda: _go_alarm())

    # ------------------------------------------------------------------ sync
    def _sync_state(self) -> None:
        """Push sidebar widget values into AppState."""
        # Guard against partially-initialised widgets during construction
        try:
            self._state.params          = self._pnl_params.get_params()
            self._state.scenarios       = self._pnl_scenario.get_scenarios()
            self._state.filter          = self._pnl_filter.get_filter()
            self._state.scoring_weights = self._pnl_scoring.get_weights()

            # Apply unit conversion to filter (matching original app.py behaviour)
            p = self._state.params
            f = self._state.filter
            if p and p.unit == "64ème":
                from dataclasses import replace
                self._state.filter = replace(
                    f,
                    max_premium=f.max_premium / 64,
                    max_loss_right=f.max_loss_right / 64,
                    max_loss_left=f.max_loss_left / 64,
                    min_premium_sell=f.min_premium_sell / 64,
                )
        except Exception:
            pass

    def _on_restore_from_history(self, entry) -> None:
        """Apply all fields of a HistoryEntry back into the sidebar."""
        try:
            if entry.params:
                self._pnl_params.load_from_params_dict(entry.params)
            if entry.scenarios:
                self._pnl_scenario.load_from_list(entry.scenarios)
            if entry.filter_data:
                self._pnl_filter.load_from_dict(entry.filter_data)
            if entry.scoring_weights:
                weights = entry.scoring_weights
                if isinstance(weights, list):
                    self._pnl_scoring.load_from_weights(weights)
            self._sync_state()
        except Exception as e:
            print(f"Restore from history error: {e}")