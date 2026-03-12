"""
Overview page — PyQt6.
Run comparison, display strategy table, payoff diagram.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)
from app.pages.history_page import add_to_history
from app.utils import format_price, create_comparison_table
from app.widget_payoff import build_payoff_figure
from app.app_state import AppState, ComputationResult
from app.chart_widget import ChartWidget
from app.worker import ProcessingWorker


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
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(2)
        self._title = QLabel(title.upper())
        self._title.setProperty("class", "metric-label")
        self._value = QLabel("—")
        self._value.setProperty("class", "metric")
        lay.addWidget(self._title)
        lay.addWidget(self._value)
        self.setStyleSheet(
            "background-color: #FFFFFF;"
            "border: 1px solid #DDE0E8;"
            "border-radius: 6px;"
        )

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
        top.addWidget(self._lbl_title)
        top.addStretch()
        lay.addLayout(top)

        self._table = QTableWidget()
        self._table.verticalHeader().setVisible(False) #type: ignore
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setMinimumHeight(220)
        self._table.itemSelectionChanged.connect(self._on_selection)

        # Ctrl+C to copy selected cells
        sc = QShortcut(QKeySequence.StandardKey.Copy, self._table)
        sc.activated.connect(self._copy_selection)

        lay.addWidget(self._table)

    def _apply_column_sizing(self) -> None:
        """Resize columns to content then distribute remaining space."""
        header = self._table.horizontalHeader()
        n = self._table.columnCount()
        if n == 0:
            return
        # First pass: size to content
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents) #type: ignore
        # Force layout so widths are computed
        self._table.horizontalHeader().setStretchLastSection(False) #type: ignore 
        self._table.resizeColumnsToContents()
        # Read content-based widths
        widths = [self._table.columnWidth(c) for c in range(n)]
        # Switch to fixed so we can set widths manually

        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive) #type: ignore
        total_content = sum(widths)
        available = self._table.viewport().width() #type: ignore
        if total_content <= 0:
            return
        
        # Scale all columns proportionally to fill the full width
        scale = max(available / total_content, 1.0)
        for c in range(n):
            self._table.setColumnWidth(c, int(widths[c] * scale))

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
        QTimer.singleShot(0, self._apply_column_sizing)

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        if self._table.columnCount() > 0:
            QTimer.singleShot(0, self._apply_column_sizing)

    def _reset(self) -> None:
        self._table.clearSelection()

    def _copy_selection(self) -> None:
        indexes = sorted(self._table.selectedIndexes(), key=lambda i: (i.row(), i.column()))
        if not indexes:
            return
        rows: dict[int, list[str]] = {}
        for idx in indexes:
            item = self._table.item(idx.row(), idx.column())
            rows.setdefault(idx.row(), []).append(item.text() if item else "")
        text = "\n".join("\t".join(cells) for cells in rows.values())
        QApplication.clipboard().setText(text)

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
        self._tab_label = tab_label
        self._comparisons: List[Any] = []
        self._mixture = None
        self._underlying_price = None
        self._locked_y: Optional[tuple] = None  # (ymin, ymax) once aligned

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

        # Payoff chart (with title)
        self._chart = ChartWidget(min_height=350)
        lay.addWidget(self._chart)

    def load(self, comparisons: List[Any], mixture, underlying_price, roll_labels=None) -> None:
        self._comparisons = comparisons
        self._mixture = mixture
        self._underlying_price = underlying_price
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

        self._chart.set_title(f"Payoff — {self._tab_label}")
        self._update_chart(comparisons[:5], mixture, underlying_price)

    def _update_chart(self, comparisons, mixture, underlying_price) -> None:
        if not comparisons:
            self._chart.clear()
            return
        try:
            fig = build_payoff_figure(comparisons, mixture, underlying_price)
            self._chart.set_figure(fig)
            # Re-apply locked range so Y=0 stays aligned after row selection
            if self._locked_y is not None:
                self._chart.set_y_range(*self._locked_y)
        except Exception:
            self._chart.clear()

    def get_y_range(self) -> Optional[tuple]:
        """Return the (ymin, ymax) computed by the chart, or None."""
        return getattr(self._chart, '_payoff_ymin', None), getattr(self._chart, '_payoff_ymax', None)

    def apply_y_range(self, ymin: float, ymax: float) -> None:
        self._locked_y = (ymin, ymax)
        self._chart.set_y_range(ymin, ymax)


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
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Action buttons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_run  = QPushButton("▶  Run Comparison")
        self._btn_run.setProperty("accent", "true")
        self._btn_run.setMinimumHeight(32)
        self._btn_stop = QPushButton("■  Stop")
        self._btn_stop.setProperty("danger", "true")
        self._btn_stop.setMinimumHeight(32)
        self._btn_stop.setEnabled(False)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_stop)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── Status bar ─────────────────────────────────────────────────
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setProperty("class", "status")
        self._status.setStyleSheet(
            "color: #6B7080; font-size: 11px; padding: 2px 0;"
        )
        root.addWidget(self._status)

        # ── Metrics row ────────────────────────────────────────────────
        from PyQt6.QtWidgets import QFrame
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2D3348;")
        root.addWidget(sep)

        mrow = QHBoxLayout()
        mrow.setSpacing(8)
        self._m_price    = _MetricLabel("Underlying Price")
        self._m_date     = _MetricLabel("Last Tradeable Date")
        self._m_screened = _MetricLabel("Strategies Screened")
        for m in (self._m_price, self._m_date, self._m_screened):
            mrow.addWidget(m)
        mrow.addStretch()
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
            "recalibrate": params.recalibrate,
            "vol_model": params.vol_model,
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
        multi = best_strategies
        self._state.store_result(ComputationResult(
            multi_ranking=multi,
            comparisons=multi.all_strategies_flat(),
            mixture=mixture,
            future_data=future_data,
            stats=stats,
            all_imported_options=stats.get("all_options", []),
            sabr_calibration=stats.get("sabr_calibration"),
        ))

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
            f"Done — {nb_opts} options, {_format_large(nb)} screened → {nb_kept} kept."
        )

        # Render tabs
        params = self._state.params
        roll_labels = (
            [f"{m}{y}" for m, y in params.roll_expiries] if params and params.roll_expiries else None
        )
        unit = params.unit if params else "100ème"
        price = future_data.underlying_price if future_data else 0.0

        self._tabs.clear()
        ranking_tabs: List[_RankingTab] = []
        if multi.is_multi:
            consensus_tab = _RankingTab("Consensus", unit)
            consensus_tab.load(self._state.comparisons, mixture, price, roll_labels)
            self._tabs.addTab(consensus_tab, "Meta Ranking")
            ranking_tabs.append(consensus_tab)
        for i in range(multi.n_sets):
            label = multi.get_set_label(i)
            tab = _RankingTab(label, unit)
            tab.load(multi.per_set_strategies[i], mixture, price, roll_labels)
            self._tabs.addTab(tab, label)
            ranking_tabs.append(tab)
        if multi.n_sets == 0:
            tab = _RankingTab("Results", unit)
            tab.load(self._state.comparisons, mixture, price, roll_labels)
            self._tabs.addTab(tab, "Results")
            ranking_tabs.append(tab)

        # Align Y=0 across all ranking tabs (common Y range)
        global_ymin, global_ymax = 0.0, 0.0
        for t in ranking_tabs:
            ymin, ymax = t.get_y_range()
            if ymin is not None and ymax is not None:
                global_ymin = min(global_ymin, ymin)
                global_ymax = max(global_ymax, ymax)
        if global_ymin < global_ymax:
            for t in ranking_tabs:
                t.apply_y_range(global_ymin, global_ymax)

        # ── Save to history ────────────────────────────────────────────
        try:
            p = self._state.params
            params_h = {
                "underlying": p.underlying if p else "N/A",
                "months": p.months if p else [],
                "years": p.years if p else [],
                "price_min": p.price_min if p else 0,
                "price_max": p.price_max if p else 0,
                "max_legs": p.max_legs if p else 0,
            }
            sc = self._state.scenarios
            scenarios_list = [
                {"center": c, "std_l": sl, "std_r": sr, "weight": w}
                for c, sl, sr, w in zip(
                    sc.centers, sc.std_devs, sc.std_devs_r, sc.weights
                )
            ] if sc else []
            f = self._state.filter
            filter_d = {
                "max_loss_left": f.max_loss_left,
                "max_loss_right": f.max_loss_right,
                "max_premium": f.max_premium,
                "min_premium_sell": f.min_premium_sell,
                "ouvert_gauche": f.ouvert_gauche,
                "ouvert_droite": f.ouvert_droite,
                "delta_min": f.delta_min,
                "delta_max": f.delta_max,
                "limit_left": f.limit_left,
                "limit_right": f.limit_right,
                "premium_only": f.premium_only,
                "premium_only_left": f.premium_only_left,
                "premium_only_right": f.premium_only_right,
            } if f else {}
            self._state.search_history = add_to_history(
                self._state.search_history,
                params_h,
                self._state.comparisons,
                mixture,
                future_data,
                scenarios_list,
                filter_d,
                self._state.scoring_weights,
            )
        except Exception as _he:
            print(f"History save error: {_he}")

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
        params = self._state.params
        scenarios = self._state.scenarios
        filter_ = self._state.filter
        if params is None or scenarios is None or filter_ is None:
            return
        params_dict: Dict[str, Any] = {
            "brut_code": params.brut_code,
            "underlying": params.underlying,
            "months": params.months,
            "years": params.years,
            "strikes": params.strikes,
            "price_min": params.price_min,
            "price_max": params.price_max,
            "max_legs": params.max_legs,
            "scoring_weights": self._state.scoring_weights,
            "scenarios": scenarios,
            "filter": filter_,
            "roll_expiries": params.roll_expiries,
            "recalibrate": params.recalibrate,
            "vol_model": params.vol_model,
            "operation_penalisation": params.operation_penalisation,
            "prefilled_options": options,
        }

        self._state.is_processing = True
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._status.setText("⏳ Rerunning with updated options…")

        self._worker = ProcessingWorker(self._session_id, params_dict)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
