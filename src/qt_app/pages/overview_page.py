"""
Overview page — PyQt6.
Run comparison, display strategy table, payoff diagram.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from app.data_types import FutureData
from app.utils import format_price
from app.widget_comparison import create_comparison_table
from app.widget_payoff import build_payoff_figure
from qt_app.app_state import AppState
from qt_app.chart_widget import PlotlyChart
from qt_app.worker import ProcessingWorker


def _format_large(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1e9:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 1_000:
        return f"{n / 1e3:.1f}K"
    return str(n)


class _MetricLabel(QWidget):
    """Small metric card: title + value."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self._title = QLabel(f"<small>{title}</small>")
        self._value = QLabel("—")
        self._value.setStyleSheet("font-weight: bold; font-size: 14px;")
        lay.addWidget(self._title)
        lay.addWidget(self._value)
        self.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")

    def set_value(self, v: str) -> None:
        self._value.setText(v)


class StrategyTableWidget(QWidget):
    """A QTableWidget wrapper that shows StrategyComparison rows."""

    row_selected = pyqtSignal(list)  # emits selected StrategyComparison objects

    def __init__(self, parent=None):
        super().__init__(parent)
        self._comparisons: List[Any] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        self._lbl_title = QLabel("<b>Top Strategies</b>")
        btn_reset = QPushButton("↺ Reset")
        btn_reset.setFixedWidth(70)
        btn_reset.clicked.connect(self._reset)
        top.addWidget(self._lbl_title)
        top.addStretch()
        top.addWidget(btn_reset)
        lay.addLayout(top)

        self._table = QTableWidget()
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.itemSelectionChanged.connect(self._on_selection)
        self._table.setMinimumHeight(220)
        lay.addWidget(self._table)

    def load(self, comparisons: List[Any], roll_labels=None, unit: str = "100ème") -> None:
        self._comparisons = comparisons
        df = create_comparison_table(comparisons, roll_labels=roll_labels, max_rows=30, unit=unit)
        self._table.clear()
        if df.empty:
            return
        self._table.setColumnCount(len(df.columns))
        self._table.setRowCount(len(df))
        self._table.setHorizontalHeaderLabels(list(df.columns))
        for r, row in df.iterrows():
            for c, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, c, item)  # type: ignore

    def _reset(self) -> None:
        # Re-select all rows
        self._table.clearSelection()

    def _on_selection(self) -> None:
        rows = sorted({idx.row() for idx in self._table.selectedIndexes()})
        selected = [self._comparisons[r] for r in rows if r < len(self._comparisons)]
        if selected:
            self.row_selected.emit(selected)

    def get_top_n(self, n: int = 5) -> List[Any]:
        return self._comparisons[:n]


class _RankingTab(QWidget):
    """One tab = one ranking set (or consensus)."""

    def __init__(self, tab_label: str, unit: str = "100ème", parent=None):
        super().__init__(parent)
        self._unit = unit
        self._comparisons: List[Any] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        # Best strategy metrics
        self._m_strat   = _MetricLabel("Best Strategy")
        self._m_profit  = _MetricLabel("Max Profit")
        self._m_loss    = _MetricLabel("Max Loss")
        self._m_pnl     = _MetricLabel("Expected Gain")
        mrow = QHBoxLayout()
        for m in (self._m_strat, self._m_profit, self._m_loss, self._m_pnl):
            mrow.addWidget(m)
        lay.addLayout(mrow)

        # Strategy table
        self._strat_table = StrategyTableWidget()
        lay.addWidget(self._strat_table)

        # Payoff chart
        self._chart = PlotlyChart(min_height=350)
        lay.addWidget(self._chart)

    def load(self, comparisons: List[Any], mixture, underlying_price, roll_labels=None) -> None:
        self._comparisons = comparisons
        if not comparisons:
            return

        winner = comparisons[0]
        self._m_strat.set_value(winner.strategy_name)
        self._m_profit.set_value(format_price(winner.max_profit, self._unit))
        self._m_loss.set_value(str(winner.max_loss))
        avg = winner.average_pnl or 0.0
        self._m_pnl.set_value(f"{avg:.2f}")

        self._strat_table.load(comparisons, roll_labels=roll_labels, unit=self._unit)
        self._strat_table.row_selected.connect(
            lambda sel: self._update_chart(sel, mixture, underlying_price)
        )

        self._update_chart(comparisons[:5], mixture, underlying_price)

    def _update_chart(self, comparisons, mixture, underlying_price) -> None:
        if not comparisons:
            self._chart.clear()
            return
        try:
            fig = build_payoff_figure(comparisons, mixture, underlying_price)
            self._chart.set_figure(fig)
        except Exception:
            self._chart.clear()


class OverviewPage(QWidget):
    """Main overview page with Run/Stop + results."""

    result_available = pyqtSignal()   # emitted after successful result processing

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._worker: Optional[ProcessingWorker] = None
        self._session_id = str(uuid.uuid4())[:8]
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)

        # ── Action buttons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._btn_run  = QPushButton("▶  Run Comparison")
        self._btn_run.setStyleSheet("font-weight: bold;")
        self._btn_stop = QPushButton("■  STOP")
        self._btn_stop.setEnabled(False)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_stop)
        root.addLayout(btn_row)

        # ── Status bar ─────────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setWordWrap(True)
        root.addWidget(self._status)

        # ── Metrics row ────────────────────────────────────────────────
        mrow = QHBoxLayout()
        self._m_price    = _MetricLabel("Underlying Price")
        self._m_date     = _MetricLabel("Last Tradeable Date")
        self._m_screened = _MetricLabel("Strategies Screened")
        for m in (self._m_price, self._m_date, self._m_screened):
            mrow.addWidget(m)
        root.addLayout(mrow)

        # ── Ranking tabs ───────────────────────────────────────────────
        self._tabs = QTabWidget()
        root.addWidget(self._tabs)

    # ------------------------------------------------------------------ run/stop
    def _on_run(self) -> None:
        params = self._state.params
        scenarios = self._state.scenarios
        filter_ = self._state.filter
        scoring_weights = self._state.scoring_weights

        if params is None or scenarios is None or filter_ is None:
            QMessageBox.warning(self, "Missing params", "Please configure parameters first.")
            return

        params_dict = {
            "brut_code": params.brut_code,
            "underlying": params.underlying,
            "months": params.months,
            "years": params.years,
            "strikes": params.strikes,
            "price_min": params.price_min,
            "price_max": params.price_max,
            "max_legs": params.max_legs,
            "scoring_weights": scoring_weights,
            "scenarios": scenarios,
            "filter": filter_,
            "roll_expiries": params.roll_expiries,
            "use_bachelier": params.use_bachelier,
            "use_sabr": params.use_sabr,
            "operation_penalisation": params.operation_penalisation,
        }

        self._state.is_processing = True
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._status.setText("⏳ Processing…")

        self._worker = ProcessingWorker(self._session_id, params_dict)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker:
            self._worker.request_stop()
        self._reset_buttons()
        self._status.setText("🛑 Stopped by user.")

    def _reset_buttons(self) -> None:
        self._state.is_processing = False
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)

    # ------------------------------------------------------------------ slots
    def _on_result(self, result) -> None:
        self._reset_buttons()
        best_strategies, stats, mixture, future_data = result

        if not best_strategies:
            self._status.setText("⚠️ No strategies generated.")
            return

        # Update state
        from strategy.multi_ranking import MultiRankingResult
        multi = best_strategies
        self._state.multi_ranking = multi
        self._state.comparisons = multi.all_strategies_flat()
        self._state.mixture = mixture
        self._state.future_data = future_data
        self._state.stats = stats
        if "all_options" in stats:
            self._state.all_imported_options = stats["all_options"]

        # Metrics
        if future_data and future_data.underlying_price is not None:
            self._m_price.set_value(f"{future_data.underlying_price:.4f}")
        date_str = (future_data.last_tradable_date or "N/A") if future_data else "N/A"
        self._m_date.set_value(date_str)
        nb = stats.get("nb_strategies_possibles", 0)
        self._m_screened.set_value(_format_large(nb))

        nb_opts = stats.get("nb_options", 0)
        nb_kept = stats.get("nb_strategies_classees", 0)
        self._status.setText(
            f"✅ Done — {nb_opts} options, {_format_large(nb)} screened → {nb_kept} kept."
        )

        # Render tabs
        params = self._state.params
        roll_labels = (
            [f"{m}{y}" for m, y in params.roll_expiries] if params and params.roll_expiries else None
        )
        unit = params.unit if params else "100ème"
        price = future_data.underlying_price if future_data else 0.0

        self._tabs.clear()
        if multi.is_multi:
            consensus_tab = _RankingTab("Consensus", unit)
            consensus_tab.load(self._state.comparisons, mixture, price, roll_labels)
            self._tabs.addTab(consensus_tab, "Meta Ranking")
        for i in range(multi.n_sets):
            label = multi.get_set_label(i)
            tab = _RankingTab(label, unit)
            tab.load(multi.per_set_strategies[i], mixture, price, roll_labels)
            self._tabs.addTab(tab, label)
        if multi.n_sets == 0:
            tab = _RankingTab("Results", unit)
            tab.load(self._state.comparisons, mixture, price, roll_labels)
            self._tabs.addTab(tab, "Results")

        # Notify other pages (e.g. Volatility) that new results are available
        self.result_available.emit()

    def _on_error(self, msg: str) -> None:
        self._reset_buttons()
        if "terminated" in msg.lower():
            self._status.setText("🛑 Processing terminated.")
        else:
            self._status.setText(f"❌ Error: {msg[:200]}")

    # ------------------------------------------------------------------ public: called from Volatility rerun
    def rerun_with_prefilled(self, options: list) -> None:
        if not self._state.params:
            return
        params_dict: Dict[str, Any] = self._state.stats.get("_last_params", {}).copy()
        params_dict["prefilled_options"] = options

        self._state.is_processing = True
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._status.setText("⏳ Rerunning with updated options…")

        self._worker = ProcessingWorker(self._session_id, params_dict)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
