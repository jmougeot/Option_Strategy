"""
MainWindow — QMainWindow with:
  • Left QDockWidget: Scenario + Params + Filter + Scoring panels (scrollable)
  • Central QTabWidget: Overview, Volatility, History, Email, Help
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QMainWindow, QScrollArea, QSizePolicy,
    QTabWidget, QVBoxLayout, QWidget,
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
        self.setCentralWidget(tabs)

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