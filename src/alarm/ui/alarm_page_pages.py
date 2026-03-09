"""Mixin — Page management (add / switch / delete pages)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QComboBox, QInputDialog, QMessageBox, QWidget

if TYPE_CHECKING:
    from alarm.ui.alarm_state import RowState
    from bloomberg.realtime import BloombergService
    _WidgetBase = QWidget
else:
    _WidgetBase = object


class PagesMixin(_WidgetBase):
    """Handles the page combo-box and CRUD on pages."""

    _page_combo: QComboBox
    _pages: list[dict]
    _cur: int
    _bbg: BloombergService
    _states: dict[str, RowState]

    if TYPE_CHECKING:
        # Stubs for methods provided by other mixins
        def _reload_table(self) -> None: ...

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
