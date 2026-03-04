"""
History page — PyQt6.
Shows search history in a table with restore capability.
"""

from __future__ import annotations

from typing import Any, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from app.pages.history import (
    HistoryEntry, load_history_from_json, save_history_to_json,
)
from app.app_state import AppState


class HistoryPage(QWidget):
    """Display past searches and allow restoring parameters."""

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._entries: List[HistoryEntry] = []
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)

        root.addWidget(QLabel("<h2>Search History</h2>"))

        # Buttons row
        btn_row = QHBoxLayout()
        self._btn_restore = QPushButton("↩ Restore selected")
        self._btn_delete  = QPushButton("🗑 Delete selected")
        self._btn_refresh = QPushButton("↺ Refresh")
        self._btn_restore.clicked.connect(self._on_restore)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_refresh.clicked.connect(self._load)
        for b in (self._btn_restore, self._btn_delete, self._btn_refresh):
            btn_row.addWidget(b)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Table
        self._table = QTableWidget()
        cols = ["#", "Time", "Underlying", "Months", "Years", "Price range",
                "Max legs", "Strategies", "Best", "Score"]
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        root.addWidget(self._table)

    # ------------------------------------------------------------------ helpers
    def _load(self) -> None:
        self._entries = load_history_from_json()
        self._table.setRowCount(len(self._entries))
        for r, e in enumerate(self._entries):
            vals = [
                str(r + 1),
                e.timestamp,
                e.underlying,
                ",".join(e.months),
                ",".join(str(y) for y in e.years),
                e.price_range,
                str(e.max_legs),
                str(e.num_strategies),
                e.best_strategy,
                f"{e.best_score:.4f}",
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(r, c, item)

    def _selected_entry(self) -> Optional[HistoryEntry]:
        rows = [i.row() for i in self._table.selectedIndexes()]
        if not rows:
            return None
        return self._entries[rows[0]]

    # ------------------------------------------------------------------ slots
    def _on_restore(self) -> None:
        entry = self._selected_entry()
        if not entry:
            QMessageBox.information(self, "History", "Select a row first.")
            return
        # The main window will read _pending_restore from state and apply sidebar values
        self._state.search_history = self._entries
        # Store the entry to restore in a temporary slot on state
        self._state._pending_restore = entry  # type: ignore
        QMessageBox.information(
            self, "History",
            f"Parameters from '{entry.timestamp}' queued for restore.\n"
            "Switch to Overview and press Run Comparison."
        )

    def _on_delete(self) -> None:
        entry = self._selected_entry()
        if not entry:
            return
        self._entries = [e for e in self._entries if e.id != entry.id]
        self._state.search_history = self._entries
        save_history_to_json(self._entries)
        self._load()
