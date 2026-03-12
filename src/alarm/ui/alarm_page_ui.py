"""Mixin — UI construction for AlarmPage."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout,
    QHeaderView, QLabel, QPushButton, QTableWidget,
    QVBoxLayout, QWidget,
)

from alarm.models.strategy import StrategyStatus, TargetCondition
from alarm.ui.columns import (
    C_ACTION, C_CLIENT, C_COND, C_DELTA,
    C_FUT, C_GAMMA, C_IV, C_LEGS, C_NAME,
    C_PRICE, C_STATUS, C_TARGET, C_THETA,
    HEADERS, C_EXPIRY
)

from app import theme

if TYPE_CHECKING:
    from alarm.handlers.alert_handler import AlertHandler
    from alarm.handlers.file_handler import FileHandler
    from alarm.ui.alarm_state import RowState
    from bloomberg.realtime import BloombergService
    _WidgetBase = QWidget
else:
    _WidgetBase = object


class UIBuildMixin(_WidgetBase):
    """Builds the top bar and the QTableWidget."""

    # Declared here for type-checkers; set by AlarmPage.__init__
    _page_combo: QComboBox
    _bbg_lbl: QLabel
    _table: QTableWidget
    _bbg: BloombergService
    _states: dict[str, RowState]
    _pages: list[dict]
    _cur: int
    _alert: AlertHandler
    _file: FileHandler

    if TYPE_CHECKING:
        # Stubs for methods provided by other mixins / AlarmPage
        def _switch_page(self, index: int) -> None: ...
        def _new_page(self) -> None: ...
        def _delete_page(self) -> None: ...
        def _save(self) -> None: ...
        def _load(self) -> None: ...
        def _on_cell_changed(self, row: int, col: int) -> None: ...
        def _on_cell_double_clicked(self, row: int, col: int) -> None: ...
        def _delete_selected_row(self) -> None: ...
        def _show_context_menu(self, pos: QPoint) -> None: ...
        def _refresh_page_combo(self) -> None: ...
        def _reload_table(self) -> None: ...

    _GHOST_ROWS = 50

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
        StrategyStatus.ANNULE:   QColor("#eceff1"),
        StrategyStatus.EN_COURS: QColor("#fdecea"),
    }

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Top bar ─────────────────────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(8)

        self._page_combo = QComboBox()
        self._page_combo.setMinimumWidth(250)
        self._page_combo.currentIndexChanged.connect(self._switch_page)
        top.addWidget(self._page_combo)

        btn_add_page = QPushButton("Nouvelle page")
        btn_add_page.setMinimumWidth(160)
        btn_add_page.setToolTip("Nouvelle page")
        btn_add_page.clicked.connect(self._new_page)
        top.addWidget(btn_add_page)

        btn_del_page = QPushButton("Supprimer la page")
        btn_del_page.setMinimumWidth(160)
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
        self._table.setStyleSheet("""
            QTableWidget { font-size: 12px; }
            QTableWidget::item:alternate { background-color: #F7FAFF; }
            QTableWidget::item:selected { background-color: #B3D4FC; color: #000000; }
            QTableWidget QLineEdit { font-size: 12px; }
            QTableWidget QAbstractItemView { font-size: 12px; }
        """)

        vh = self._table.verticalHeader()
        if vh:
            vh.setVisible(False)
            vh.setDefaultSectionSize(34)

        self._table.cellChanged.connect(self._on_cell_changed)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        del_sc = QShortcut(QKeySequence(Qt.Key.Key_Delete), self._table)
        del_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        del_sc.activated.connect(self._delete_selected_row)

        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)

        hh = self._table.horizontalHeader()
        if hh:
            hh.setSectionResizeMode(C_CLIENT, QHeaderView.ResizeMode.Interactive)
            hh.setSectionResizeMode(C_NAME,   QHeaderView.ResizeMode.Interactive)
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
            hh.setSectionResizeMode(C_EXPIRY,   QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(C_CLIENT, 200)
        self._table.setColumnWidth(C_NAME,   400)
        self._table.setColumnWidth(C_ACTION, 200)
        self._table.setColumnWidth(C_LEGS,   200)
        self._table.setColumnWidth(C_PRICE,  110)
        self._table.setColumnWidth(C_COND,   130)
        self._table.setColumnWidth(C_TARGET, 100)
        self._table.setColumnWidth(C_STATUS, 100)
        self._table.setColumnWidth(C_DELTA,   80)
        self._table.setColumnWidth(C_GAMMA,   80)
        self._table.setColumnWidth(C_THETA,   80)
        self._table.setColumnWidth(C_IV,      80)
        self._table.setColumnWidth(C_FUT,     80)
        self._table.setColumnWidth(C_EXPIRY,  80)

        root.addWidget(self._table)

        self._refresh_page_combo()
        self._reload_table()
