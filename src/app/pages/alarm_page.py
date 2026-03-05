"""
AlarmPage — Table-based strategy price monitor.

Each ROW  = one strategy.
Each COLUMN = one attribute:
  ⬤ | Client | Stratégie | Action | Legs | Prix | Alarme si | Cible | Statut

Live prices come from BloombergService (silent no-op if blpapi unavailable).
Pages are selected with a combo-box at the top.
Save / Load uses a simple JSON file.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
    QHeaderView,
    QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QVBoxLayout, QWidget,
)

from alarm.handlers.alert_handler import AlertHandler
from alarm.handlers.file_handler import FileHandler
from alarm.models.strategy import (
    OptionLeg, Position, Strategy, StrategyStatus,
    TargetCondition, normalize_ticker,
)
from alarm.services.bloomberg_service import BloombergService
from app import theme

# ── column indices ────────────────────────────────────────────────────────────
C_DOT    = 0
C_CLIENT = 1
C_NAME   = 2
C_ACTION = 3
C_LEGS   = 4
C_PRICE  = 5
C_COND   = 6
C_TARGET = 7
C_STATUS = 8

HEADERS = ["⬤", "Client", "Stratégie", "Action", "Legs",
           "Prix", "Alarme si", "Cible", "Statut"]

# How long a price must stay in the alarm zone before the alert fires (seconds)
_WARN_DELAY = 5.0


# ─────────────────────────────────────────────────────────────────────────────
class _RowState:
    """Per-strategy alarm state (warning countdown + confirmed)."""

    def __init__(self, strategy: Strategy) -> None:
        self.strategy = strategy
        self.warning_start: Optional[datetime] = None
        self.confirmed: bool = False   # True once 5 s have elapsed

    def reset(self) -> None:
        self.warning_start = None
        self.confirmed = False

    def elapsed(self) -> float:
        if self.warning_start is None:
            return 0.0
        return (datetime.now() - self.warning_start).total_seconds()


# ─────────────────────────────────────────────────────────────────────────────
class _LegsDialog(QDialog):
    """Compact dialog to edit the legs of a strategy."""

    def __init__(self, strategy: Strategy, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.strategy = strategy
        self.setWindowTitle(f"Legs — {strategy.name or 'Sans nom'}")
        self.resize(700, 300)
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Ticker", "Position", "Quantité", ""])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 110)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 60)
        self._table.setAlternatingRowColors(True)
        lay.addWidget(self._table)

        for leg in self.strategy.legs:
            self._append_leg_row(leg)

        btn_add = QPushButton("+ Ajouter un leg")
        btn_add.clicked.connect(self._add_leg)
        lay.addWidget(btn_add)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._commit)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _append_leg_row(self, leg: OptionLeg) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)

        ticker_edit = QLineEdit(leg.ticker or "")
        ticker_edit.setPlaceholderText("SFRF6 96.50 Comdty")
        self._table.setCellWidget(r, 0, ticker_edit)

        pos_combo = QComboBox()
        pos_combo.addItem("Long",  Position.LONG)
        pos_combo.addItem("Short", Position.SHORT)
        if leg.position == Position.SHORT:
            pos_combo.setCurrentIndex(1)
        self._table.setCellWidget(r, 1, pos_combo)

        qty_spin = QSpinBox()
        qty_spin.setRange(1, 999)
        qty_spin.setValue(leg.quantity)
        self._table.setCellWidget(r, 2, qty_spin)

        del_btn = QPushButton("🗑")
        del_btn.setFixedWidth(40)
        del_btn.clicked.connect(lambda _, row=r: self._del_row(row))
        self._table.setCellWidget(r, 3, del_btn)

        ticker_edit.setProperty("leg_id", leg.id)

    def _add_leg(self) -> None:
        leg = self.strategy.add_leg()
        self._append_leg_row(leg)

    def _del_row(self, row: int) -> None:
        w = self._table.cellWidget(row, 0)
        if w:
            w.setProperty("leg_id", "__del__")
        self._table.hideRow(row)

    def _commit(self) -> None:
        """Write table values back into strategy.legs."""
        updated_ids: Set[str] = set()
        for r in range(self._table.rowCount()):
            ticker_w: QLineEdit = self._table.cellWidget(r, 0)
            pos_w:    QComboBox = self._table.cellWidget(r, 1)
            qty_w:    QSpinBox  = self._table.cellWidget(r, 2)
            if ticker_w is None:
                continue
            leg_id = ticker_w.property("leg_id")
            if leg_id == "__del__":
                continue

            leg = self.strategy.get_leg(leg_id)
            if leg is None:
                continue

            raw = ticker_w.text().strip().upper()
            if raw and "COMDTY" not in raw:
                raw = raw + " COMDTY"
            leg.ticker   = raw or None
            leg.position = pos_w.currentData()
            leg.quantity = qty_w.value()
            updated_ids.add(leg_id)

        # remove legs that were deleted
        for leg in list(self.strategy.legs):
            if leg.id not in updated_ids:
                self.strategy.remove_leg(leg.id)

        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
class AlarmPage(QWidget):
    """Table-based strategy price monitor page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Pages: list of {"name": str, "strategies": List[Strategy]}
        self._pages: List[Dict] = [{"name": "Page 1", "strategies": []}]
        self._cur: int = 0

        # Per-strategy alarm state, keyed by strategy.id
        self._states: Dict[str, _RowState] = {}

        # Bloomberg
        self._bbg = BloombergService()
        self._bbg.price_updated.connect(self._on_price_updated)
        self._bbg.connection_status.connect(self._on_bbg_status)

        # Alert handler (son + popup)
        self._alert = AlertHandler(self, self._continue_alarm)

        # File handler (save / load / auto-load)
        self._file = FileHandler(self)

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
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
        )
        self._table.setObjectName("alarmTable")
        self._table.cellChanged.connect(self._on_cell_changed)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # Delete row shortcut
        del_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._table)
        del_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        del_shortcut.activated.connect(self._delete_selected_row)

        hh = self._table.horizontalHeader()
        if hh :
            hh.setSectionResizeMode(C_DOT,    QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_CLIENT, QHeaderView.ResizeMode.Interactive)
            hh.setSectionResizeMode(C_NAME,   QHeaderView.ResizeMode.Stretch)
            hh.setSectionResizeMode(C_ACTION, QHeaderView.ResizeMode.Interactive)
            hh.setSectionResizeMode(C_LEGS,   QHeaderView.ResizeMode.Interactive)
            hh.setSectionResizeMode(C_PRICE,  QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_COND,   QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_TARGET, QHeaderView.ResizeMode.Fixed)
            hh.setSectionResizeMode(C_STATUS, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(C_DOT,    30)
        self._table.setColumnWidth(C_CLIENT, 90)
        self._table.setColumnWidth(C_ACTION, 120)
        self._table.setColumnWidth(C_LEGS,   200)
        self._table.setColumnWidth(C_PRICE,  110)
        self._table.setColumnWidth(C_COND,   130)
        self._table.setColumnWidth(C_TARGET, 100)
        self._table.setColumnWidth(C_STATUS, 110)

        self._table.verticalHeader().setDefaultSectionSize(34)
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
                self._states[s.id] = _RowState(s)
            self._append_row(s)
        self._table.blockSignals(False)

    def _append_row(self, strategy: Strategy) -> None:
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setRowHeight(r, 34)

        # ⬤ alarm dot ─────────────────────────────────────────────────────────
        dot = QLabel("⬤")
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setStyleSheet(theme.DOT_IDLE)
        dot.setToolTip("Alarme inactive")
        self._table.setCellWidget(r, C_DOT, dot)

        # Helper to create uniform items ───────────────────────────────────────
        def _item(text: str, editable: bool = True) -> QTableWidgetItem:
            it = QTableWidgetItem(text)
            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not editable:
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
            return it

        self._table.setItem(r, C_CLIENT, _item(strategy.client or ""))
        self._table.setItem(r, C_NAME,   _item(strategy.name or ""))
        self._table.setItem(r, C_ACTION, _item(strategy.action or ""))

        # Legs (read-only, double-click opens dialog) ─────────────────────────
        self._table.setItem(r, C_LEGS, _item(self._legs_summary(strategy), editable=False))

        # Prix (read-only, updated live) ──────────────────────────────────────
        self._table.setItem(r, C_PRICE, _item("--", editable=False))

        # Condition (read-only, double-click cycles) ──────────────────────────
        cond_text = "Inférieur à" if strategy.target_condition == TargetCondition.INFERIEUR else "Supérieur à"
        self._table.setItem(r, C_COND, _item(cond_text, editable=False))

        # Cible (editable) ────────────────────────────────────────────────────
        target_val = f"{strategy.target_price:.4f}" if strategy.target_price is not None else ""
        self._table.setItem(r, C_TARGET, _item(target_val))

        # Status (read-only, double-click cycles) ─────────────────────────────
        status_text = {StrategyStatus.EN_COURS: "En cours", StrategyStatus.FAIT: "Fait", StrategyStatus.ANNULE: "Annulé"}
        self._table.setItem(r, C_STATUS, _item(status_text.get(strategy.status, "En cours"), editable=False))

        # Subscribe Bloomberg
        for t in strategy.get_all_tickers():
            self._bbg.subscribe(t)

        self._paint_row(r, strategy)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _legs_summary(self, strategy: Strategy) -> str:
        if not strategy.legs:
            return "— aucun leg —"
        parts = []
        for leg in strategy.legs:
            tick = (leg.ticker or "?").replace(" COMDTY", "")
            pos  = "L" if leg.position == Position.LONG else "S"
            parts.append(f"{tick} {pos}×{leg.quantity}")
        return "  |  ".join(parts)

    def _row_by_sid(self, sid: str) -> int:
        for i, s in enumerate(self._pages[self._cur]["strategies"]):
            if s.id == sid:
                return i
        return -1

    # ── delete selected rows ────────────────────────────────────────────────
    def _delete_selected_row(self) -> None:
        rows = sorted({idx.row() for idx in self._table.selectionModel().selectedRows()}, reverse=True)
        if not rows:
            row = self._table.currentRow()
            if row >= 0:
                rows = [row]
        for row in rows:
            s = self._strategy_at_row(row)
            if s is not None:
                self._remove_strategy(s)

    # ── double-click cycling for Condition / Status / Legs ────────────────
    _COND_CYCLE = [
        (TargetCondition.INFERIEUR, "Inférieur à"),
        (TargetCondition.SUPERIEUR, "Supérieur à"),
    ]
    _STATUS_CYCLE = [
        (StrategyStatus.EN_COURS, "En cours"),
        (StrategyStatus.FAIT,     "Fait"),
        (StrategyStatus.ANNULE,   "Annulé"),
    ]

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        s = self._strategy_at_row(row)
        if s is None:
            return

        if col == C_COND:
            cur = next((i for i, (v, _) in enumerate(self._COND_CYCLE) if v == s.target_condition), 0)
            nxt = (cur + 1) % len(self._COND_CYCLE)
            s.target_condition = self._COND_CYCLE[nxt][0]
            self._table.blockSignals(True)
            self._table.item(row, C_COND).setText(self._COND_CYCLE[nxt][1])
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
            self._table.item(row, C_STATUS).setText(self._STATUS_CYCLE[nxt][1])
            self._table.blockSignals(False)
            self._paint_row(row, s)
            self._update_dot(row, s)

        elif col == C_LEGS:
            self._edit_legs(s, row)

    # ── cell callbacks ────────────────────────────────────────────────────────
    def _strategy_at_row(self, row: int) -> Optional[Strategy]:
        strategies = self._pages[self._cur]["strategies"]
        return strategies[row] if 0 <= row < len(strategies) else None

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
                # Restore previous value
                self._table.blockSignals(True)
                prev = f"{s.target_price:.4f}" if s.target_price is not None else ""
                item.setText(prev)
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
                    # update sibling cells without re-triggering cellChanged
                    self._table.blockSignals(True)
                    self._table.item(row, C_NAME).setText(s.name)
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
        dlg = _LegsDialog(strategy, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_tickers = set(strategy.get_all_tickers())
            for t in old_tickers - new_tickers:
                self._bbg.unsubscribe(t)
            for t in new_tickers - old_tickers:
                self._bbg.subscribe(t)
            legs_item = self._table.item(row, C_LEGS)
            if legs_item:
                legs_item.setText(self._legs_summary(strategy))

    # ── add / remove strategy ─────────────────────────────────────────────────
    def _add_strategy(self, strategy: Strategy | None = None) -> None:
        if strategy is None:
            strategy = Strategy(id=str(uuid.uuid4()), name="")
        self._pages[self._cur]["strategies"].append(strategy)
        self._states[strategy.id] = _RowState(strategy)
        self._append_row(strategy)

    def _remove_strategy(self, strategy: Strategy) -> None:
        for t in strategy.get_all_tickers():
            self._bbg.unsubscribe(t)
        self._states.pop(strategy.id, None)
        strategies = self._pages[self._cur]["strategies"]
        row = next((i for i, s in enumerate(strategies) if s.id == strategy.id), -1)
        if row >= 0:
            strategies.pop(row)
            self._table.removeRow(row)

    # ── Bloomberg ─────────────────────────────────────────────────────────────
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

    def _on_price_updated(self, ticker: str, last: float, bid: float, ask: float) -> None:
        ticker_n = normalize_ticker(ticker)
        for row, s in enumerate(self._pages[self._cur]["strategies"]):
            if ticker_n not in {normalize_ticker(t) for t in s.get_all_tickers()}:
                continue
            for leg in s.legs:
                if normalize_ticker(leg.ticker or "") == ticker_n:
                    leg.update_price(last, bid, ask)
            self._refresh_price_cell(row, s.calculate_strategy_price())
            self._update_dot(row, s)

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

    # ── alarm state machine ───────────────────────────────────────────────────
    def _tick(self) -> None:
        for row, s in enumerate(self._pages[self._cur]["strategies"]):
            self._update_dot(row, s)

    def _update_dot(self, row: int, s: Strategy) -> None:
        dot: QLabel = self._table.cellWidget(row, C_DOT)
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
                if elapsed >= _WARN_DELAY:
                    state.confirmed = True
                    self._fire_alarm(row, s)
                else:
                    dot.setStyleSheet(theme.DOT_WARN)
                    dot.setToolTip(f"⏳ Alerte dans {_WARN_DELAY - elapsed:.1f} s")

    def _fire_alarm(self, row: int, s: Strategy) -> None:
        # Passer la stratégie en « Fait » automatiquement
        s.status = StrategyStatus.FAIT
        self._table.blockSignals(True)
        status_item = self._table.item(row, C_STATUS)
        if status_item:
            status_item.setText("Fait")
        self._table.blockSignals(False)
        self._paint_row(row, s)

        # Son + popup via le handler
        self._alert.fire(
            strategy_id=s.id,
            strategy_name=s.name or "Sans nom",
            current_price=s.calculate_strategy_price(),
            target_price=s.target_price,  # type: ignore[arg-type]
            is_inferior=s.target_condition == TargetCondition.INFERIEUR,
        )

        dot: QLabel = self._table.cellWidget(row, C_DOT)
        if dot:
            cond = "inf." if s.target_condition == TargetCondition.INFERIEUR else "sup."
            dot.setStyleSheet(theme.DOT_HIT)
            dot.setToolTip(f"✅ ALARME — prix {cond} {s.target_price:.4f}")

    def _continue_alarm(self, strategy_id: str) -> None:
        """Callback du popup « Continuer l'alarme » — remet En cours."""
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

    # ── row colour by status ──────────────────────────────────────────────────
    _STATUS_COLOUR = {
        StrategyStatus.FAIT:     QColor("#e8f5e9"),
        StrategyStatus.ANNULE:   QColor("#fce4e4"),
        StrategyStatus.EN_COURS: QColor("#ffffff"),
    }

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
        """Remplace les pages courantes par celles chargées."""
        self._bbg.unsubscribe_all()
        self._states.clear()
        self._pages = pages if pages else [{"name": "Page 1", "strategies": []}]
        self._cur = 0
        self._refresh_page_combo()
        self._reload_table()

    # ── cleanup ───────────────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._bbg.stop()
        super().closeEvent(event)
