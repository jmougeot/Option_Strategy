"""
AlarmPage — Table-based strategy price monitor.
Live prices come from BloombergService (silent no-op if blpapi unavailable).
Pages are selected with a combo-box at the top.
Save / Load uses a simple JSON file.
"""
from __future__ import annotations

import math
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QMenu, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from alarm.handlers.alert_handler import AlertHandler
from alarm.handlers.file_handler import FileHandler
from alarm.models.strategy import (
    Position, Strategy, StrategyStatus, TargetCondition, normalize_ticker,
)
from bloomberg.realtime import BloombergService
from alarm.ui.alarm_state import RowState
from alarm.ui.columns import (
    C_ACTION, C_CLIENT, C_COND, C_DELTA, C_DOT,
    C_FUT, C_GAMMA, C_IV, C_LEGS, C_NAME,
    C_PRICE, C_STATUS, C_TARGET, C_THETA,
    HEADERS, WARN_DELAY,
)
from alarm.ui.block_dialog import BlockDialog
from alarm.ui.smile_dialog import SmileDialog
from alarm.ui.legs_dialog import LegsDialog
from app import theme


class AlarmPage(QWidget):
    """Table-based strategy price monitor page."""

    # ── class-level cycle tables ──────────────────────────────────────────────
    _COND_CYCLE = [
        (TargetCondition.INFERIEUR, "Inférieur à"),
        (TargetCondition.SUPERIEUR, "Supérieur à"),
    ]
    _STATUS_CYCLE = [
        (StrategyStatus.EN_COURS, "En cours"),
        (StrategyStatus.FAIT,     "Fait"),
        (StrategyStatus.ANNULE,   "Annulé"),
    ]
    _STATUS_COLOUR = {
        StrategyStatus.FAIT:     QColor("#e8f5e9"),
        StrategyStatus.ANNULE:   QColor("#fce4e4"),
        StrategyStatus.EN_COURS: QColor("#ffffff"),
    }

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
        self._bbg.greeks_updated.connect(self._on_greeks_updated)
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

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Top bar ─────────────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(QLabel("<b>Page :</b>"))

        self._page_combo = QComboBox()
        self._page_combo.setMinimumWidth(160)
        self._page_combo.currentIndexChanged.connect(self._switch_page)
        top.addWidget(self._page_combo)

        btn_add_page = QPushButton("+")
        btn_add_page.setFixedWidth(30)
        btn_add_page.setToolTip("Nouvelle page")
        btn_add_page.clicked.connect(self._new_page)
        top.addWidget(btn_add_page)

        btn_del_page = QPushButton("−")
        btn_del_page.setFixedWidth(30)
        btn_del_page.setToolTip("Supprimer la page")
        btn_del_page.clicked.connect(self._delete_page)
        top.addWidget(btn_del_page)

        top.addStretch()

        self._bbg_lbl = QLabel("Bloomberg: ⬤ déconnecté")
        self._bbg_lbl.setStyleSheet(theme.BBG_ERR)
        top.addWidget(self._bbg_lbl)

        btn_save = QPushButton("Sauvegarder")
        btn_save.clicked.connect(self._save)
        top.addWidget(btn_save)

        btn_load = QPushButton("Ouvrir")
        btn_load.clicked.connect(self._load)
        top.addWidget(btn_load)

        root.addLayout(top)

        # Table ───────────────────────────────────────────────────────────────
        self._table = QTableWidget(0, len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.setObjectName("alarmTable")
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.setStyleSheet("QTableWidget { font-size: 11px; }")

        vh = self._table.verticalHeader()
        if vh:
            vh.setVisible(False)
            vh.setDefaultSectionSize(28)

        self._table.cellChanged.connect(self._on_cell_changed)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        del_sc = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._table)
        del_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        del_sc.activated.connect(self._delete_selected_row)

        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(C_DOT,    QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_CLIENT, QHeaderView.ResizeMode.Interactive)
            hh.setSectionResizeMode(C_NAME,   QHeaderView.ResizeMode.Stretch)
            hh.setSectionResizeMode(C_ACTION, QHeaderView.ResizeMode.Interactive)
            hh.setSectionResizeMode(C_LEGS,   QHeaderView.ResizeMode.Interactive)
            hh.setSectionResizeMode(C_PRICE,  QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_COND,   QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_TARGET, QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_STATUS, QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_DELTA,  QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_GAMMA,  QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_THETA,  QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_IV,     QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_FUT,    QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(C_DOT,    30)
        self._table.setColumnWidth(C_CLIENT, 90)
        self._table.setColumnWidth(C_ACTION, 120)
        self._table.setColumnWidth(C_LEGS,   200)
        self._table.setColumnWidth(C_PRICE,  110)
        self._table.setColumnWidth(C_COND,   130)
        self._table.setColumnWidth(C_TARGET, 100)
        self._table.setColumnWidth(C_STATUS, 110)
        self._table.setColumnWidth(C_DELTA,   80)
        self._table.setColumnWidth(C_GAMMA,   80)
        self._table.setColumnWidth(C_THETA,   80)
        self._table.setColumnWidth(C_IV,      70)
        self._table.setColumnWidth(C_FUT,     90)

        root.addWidget(self._table)

        # Bottom bar ──────────────────────────────────────────────────────────
        bot = QHBoxLayout()
        btn_add = QPushButton("＋  Ajouter une stratégie")
        btn_add.setObjectName("btnAlarmAdd")
        btn_add.clicked.connect(lambda: self._add_strategy())
        bot.addWidget(btn_add)
        bot.addStretch()
        root.addLayout(bot)

        self._refresh_page_combo()
        self._reload_table()

    # ── page management ───────────────────────────────────────────────────────
    def _refresh_page_combo(self) -> None:
        self._page_combo.blockSignals(True)
        self._page_combo.clear()
        for p in self._pages:
            self._page_combo.addItem(p["name"])
        self._page_combo.setCurrentIndex(self._cur)
        self._page_combo.blockSignals(False)

    def _switch_page(self, index: int) -> None:
        if 0 <= index < len(self._pages):
            self._cur = index
            self._reload_table()

    def _new_page(self) -> None:
        name, ok = QInputDialog.getText(self, "Nouvelle page", "Nom de la page :")
        if not ok or not name.strip():
            return
        self._pages.append({"name": name.strip(), "strategies": []})
        self._cur = len(self._pages) - 1
        self._refresh_page_combo()
        self._reload_table()

    def _delete_page(self) -> None:
        if len(self._pages) <= 1:
            QMessageBox.warning(self, "Suppression", "Impossible de supprimer la dernière page.")
            return
        r = QMessageBox.question(
            self, "Supprimer",
            f"Supprimer la page « {self._pages[self._cur]['name']} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        for s in self._pages[self._cur]["strategies"]:
            for t in s.get_all_tickers():
                self._bbg.unsubscribe(t)
            self._states.pop(s.id, None)
        self._pages.pop(self._cur)
        self._cur = max(0, self._cur - 1)
        self._refresh_page_combo()
        self._reload_table()

    # ── table population ──────────────────────────────────────────────────────
    def _reload_table(self) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for s in self._pages[self._cur]["strategies"]:
            if s.id not in self._states:
                self._states[s.id] = RowState(s)
            self._append_row(s)
        self._table.blockSignals(False)

    def _append_row(self, strategy: Strategy) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setRowHeight(r, 28)

        # ⬤ alarm dot
        dot = QLabel("⬤")
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setStyleSheet(theme.DOT_IDLE)
        dot.setToolTip("Alarme inactive")
        self._table.setCellWidget(r, C_DOT, dot)

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
        old_tickers = set(strategy.get_all_tickers())
        dlg = LegsDialog(strategy, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_tickers = set(strategy.get_all_tickers())
            for t in old_tickers - new_tickers:
                self._bbg.unsubscribe(t)
                fut = self._future_ticker_from_option(normalize_ticker(t))
                if fut:
                    self._bbg.unsubscribe(fut)
            for t in new_tickers - old_tickers:
                self._bbg.subscribe(t)
                fut = self._future_ticker_from_option(normalize_ticker(t))
                if fut:
                    self._bbg.subscribe(fut)
            legs_item = self._table.item(row, C_LEGS)
            if legs_item:
                legs_item.setText(self._legs_summary(strategy))

    # ── add / remove ──────────────────────────────────────────────────────────
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

    # ── Bloomberg status ──────────────────────────────────────────────────────
    def _on_bbg_status(self, connected: bool, message: str) -> None:
        if connected:
            self._bbg_lbl.setText("Bloomberg: ⬤ connecté")
            self._bbg_lbl.setStyleSheet(theme.BBG_OK)
            self._subscribe_all_tickers()
        else:
            self._bbg_lbl.setText("Bloomberg: ⬤ déconnecté")
            self._bbg_lbl.setStyleSheet(theme.BBG_ERR)

    def _subscribe_all_tickers(self) -> None:
        """(Re)subscribe all tickers across every page."""
        for page in self._pages:
            for s in page["strategies"]:
                for t in s.get_all_tickers():
                    self._bbg.subscribe(t)

    # ── Bloomberg price updates ───────────────────────────────────────────────
    def _on_price_updated(self, ticker: str, last: float, bid: float, ask: float) -> None:
        ticker_n = normalize_ticker(ticker)
        for row, s in enumerate(self._pages[self._cur]["strategies"]):
            option_tickers = {normalize_ticker(t) for t in s.get_all_tickers()}
            if ticker_n in option_tickers:
                for leg in s.legs:
                    if normalize_ticker(leg.ticker or "") == ticker_n:
                        leg.update_price(last, bid, ask)
                self._refresh_price_cell(row, s.calculate_strategy_price())
                self._update_dot(row, s)
            else:
                # Check if this is the underlying future for this strategy
                for opt_t in s.get_all_tickers():
                    fut = self._future_ticker_from_option(normalize_ticker(opt_t))
                    if fut and normalize_ticker(fut) == ticker_n:
                        price = last if last >= 0 else (
                            (bid + ask) / 2 if bid >= 0 and ask >= 0 else None
                        )
                        if price is not None:
                            s.future_price = price
                            self._refresh_greeks_cells(row, s)
                        break

    def _refresh_price_cell(self, row: int, price: Optional[float]) -> None:
        item = self._table.item(row, C_PRICE)
        if item is None:
            return
        if price is None:
            item.setText("--")
            item.setForeground(QColor("#888888"))
        elif price >= 0:
            item.setText(f"{price:.4f}")
            item.setForeground(QColor("#008800"))
        else:
            item.setText(f"{price:.4f}")
            item.setForeground(QColor("#cc2200"))

    # ── Bloomberg greeks updates ──────────────────────────────────────────────
    def _on_greeks_updated(self, ticker: str, delta: float, gamma: float,
                           theta: float, ivol: float) -> None:
        ticker_n = normalize_ticker(ticker)
        for row, s in enumerate(self._pages[self._cur]["strategies"]):
            if ticker_n not in {normalize_ticker(t) for t in s.get_all_tickers()}:
                continue
            for leg in s.legs:
                if normalize_ticker(leg.ticker or "") == ticker_n:
                    leg.update_greeks(delta, gamma, theta, ivol)
            self._refresh_greeks_cells(row, s)

    def _refresh_greeks_cells(self, row: int, s: Strategy) -> None:
        """Update the 5 analytic cells for the given row."""
        def _set(col: int, val: Optional[float], fmt: str,
                 signed_color: bool = False) -> None:
            item = self._table.item(row, col)
            if item is None:
                return
            if val is None or (isinstance(val, float) and math.isnan(val)):
                item.setText("--")
                item.setForeground(QColor("#888888"))
                return
            item.setText(fmt.format(val))
            if signed_color:
                item.setForeground(QColor("#006600") if val >= 0 else QColor("#cc2200"))
            else:
                item.setForeground(QColor("#333333"))

        _set(C_DELTA, s.get_total_delta(), "{:+.4f}", signed_color=True)
        _set(C_GAMMA, s.get_total_gamma(), "{:+.5f}")
        _set(C_THETA, s.get_total_theta(), "{:+.4f}", signed_color=True)
        _set(C_IV,    s.get_average_ivol(), "{:.2%}")
        _set(C_FUT,   s.future_price,       "{:.4f}")

    # ── alarm state machine ───────────────────────────────────────────────────
    def _tick(self) -> None:
        for row, s in enumerate(self._pages[self._cur]["strategies"]):
            self._update_dot(row, s)

    def _update_dot(self, row: int, s: Strategy) -> None:
        dot = self._table.cellWidget(row, C_DOT)
        if dot is None:
            return
        state = self._states.get(s.id)
        if state is None:
            return

        if s.status != StrategyStatus.EN_COURS:
            dot.setStyleSheet(theme.DOT_IDLE)
            dot.setToolTip("Alarme désactivée")
            state.reset()
            return

        hit = s.is_target_reached()

        if hit is None:
            dot.setStyleSheet(theme.DOT_IDLE)
            dot.setToolTip("Cible non définie")
            state.reset()
        elif not hit:
            state.reset()
            self._alert.on_target_left(s.id)
            dot.setStyleSheet(theme.DOT_MISS)
            price = s.calculate_strategy_price()
            if price is not None and s.target_price is not None:
                dot.setToolTip(f"Distance cible : {s.target_price - price:+.4f}")
            else:
                dot.setToolTip("En attente…")
        else:
            if state.confirmed:
                cond = "inf." if s.target_condition == TargetCondition.INFERIEUR else "sup."
                dot.setStyleSheet(theme.DOT_HIT)
                dot.setToolTip(f"✅ ALARME — prix {cond} {s.target_price:.4f}")
            else:
                if state.warning_start is None:
                    state.warning_start = datetime.now()
                elapsed = state.elapsed()
                if elapsed >= WARN_DELAY:
                    state.confirmed = True
                    self._fire_alarm(row, s)
                else:
                    dot.setStyleSheet(theme.DOT_WARN)
                    dot.setToolTip(f"⏳ Alerte dans {WARN_DELAY - elapsed:.1f} s")

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

        dot = self._table.cellWidget(row, C_DOT)
        if dot:
            cond = "inf." if s.target_condition == TargetCondition.INFERIEUR else "sup."
            dot.setStyleSheet(theme.DOT_HIT)
            dot.setToolTip(f"ALARME — prix {cond} {s.target_price:.4f}")

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

    # ── row painting ──────────────────────────────────────────────────────────
    def _paint_row(self, row: int, s: Strategy) -> None:
        colour = self._STATUS_COLOUR.get(s.status, QColor("#ffffff"))
        for col in range(self._table.columnCount()):
            item = self._table.item(row, col)
            if item is None:
                item = QTableWidgetItem()
                self._table.setItem(row, col, item)
            item.setBackground(colour)

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
        dlg = SmileDialog(strategy,parent = self)
        dlg.exec()

    def _show_block(self, strategy: Strategy) -> None:
        dlg = BlockDialog(strategy, parent=self)
        dlg.exec()



    # ── static helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _future_ticker_from_option(option_ticker: str) -> Optional[str]:
        """Derive the underlying future ticker from a Bloomberg option ticker.

        Example: "SFRH6C 98.0 COMDTY" → "SFRH6 COMDTY"
        """
        m = re.match(r'^([A-Z]+[FGHJKMNQUVXZ]\d+)[CP]\s', option_ticker.strip().upper())
        return f"{m.group(1)} COMDTY" if m else None

    # ── cleanup ───────────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._bbg.stop()
        super().closeEvent(event)
