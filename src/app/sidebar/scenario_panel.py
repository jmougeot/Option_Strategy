"""
Scenario panel — PyQt6 equivalent of widget_scenario.py.
Each scenario row: target price, σ left, σ right, probability weight.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from app.data_types import ScenarioData


class _ScenarioRow(QWidget):
    """One scenario row."""

    deleted = pyqtSignal(str)   # emits scenario id
    changed = pyqtSignal()

    def __init__(self, scenario_id: str, index: int, price: float = 98.0,
                 std_l: float = 0.10, std_r: float = 0.10, weight: float = 50.0,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.scenario_id = scenario_id
        self._build_ui(index, price, std_l, std_r, weight)

    def _build_ui(self, index: int, price: float, std_l: float, std_r: float, weight: float):
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        lbl = QLabel(f"<b>#{index}</b>")
        lbl.setFixedWidth(22)
        row.addWidget(lbl)

        def _spin(lo: float, hi: float, val: float, dec: int = 4) -> QDoubleSpinBox:
            s = QDoubleSpinBox()
            s.setDecimals(dec)
            s.setRange(lo, hi)
            s.setValue(val)
            s.setSingleStep(0.01)
            s.valueChanged.connect(lambda _: self.changed.emit())
            return s

        self._spn_price  = _spin(0, 9999, price)
        self._spn_std_l  = _spin(0.001, 999, std_l)
        self._spn_std_r  = _spin(0.001, 999, std_r)
        self._spn_weight = _spin(0, 9999, weight, dec=1)

        for w, tip in (
            (self._spn_price,  "Target price"),
            (self._spn_std_l,  "σ left (downside)"),
            (self._spn_std_r,  "σ right (upside)"),
            (self._spn_weight, "Probability weight"),
        ):
            w.setToolTip(tip)
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            row.addWidget(w)

        btn_del = QPushButton("✕")
        btn_del.setFixedWidth(24)
        btn_del.setToolTip("Delete this scenario")
        btn_del.clicked.connect(lambda: self.deleted.emit(self.scenario_id))
        row.addWidget(btn_del)

    def get_data(self) -> Dict:
        return {
            "id": self.scenario_id,
            "price":  self._spn_price.value(),
            "std":    self._spn_std_l.value(),
            "std_r":  self._spn_std_r.value(),
            "weight": self._spn_weight.value(),
        }


class ScenarioPanel(QGroupBox):
    """Panel containing N scenario rows."""

    changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Market Scenarios", parent)
        self._rows: Dict[str, _ScenarioRow] = {}
        self._build_ui()
        self._add_scenario(price=98.0, std_l=0.10, std_r=0.10, weight=50.0)

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(2)

        # Column headers
        hdr = QHBoxLayout()
        for txt, w in (("", 22), ("Price", 0), ("σ↓", 0), ("σ↑", 0), ("Prob", 0), ("", 24)):
            lbl = QLabel(f"<small>{txt}</small>")
            if w:
                lbl.setMinimumWidth(w)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            hdr.addWidget(lbl)
        root.addLayout(hdr)

        # Container for scenario rows
        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(2)
        root.addWidget(self._rows_container)

        # Add button
        btn_add = QPushButton("➕ Add Scenario")
        btn_add.clicked.connect(lambda: self._add_scenario())
        root.addWidget(btn_add)

    # ------------------------------------------------------------------ helpers
    def _add_scenario(self, price: float = 98.0, std_l: float = 0.10,
                      std_r: float = 0.10, weight: float = 25.0) -> None:
        sid = str(uuid.uuid4())
        idx = len(self._rows) + 1
        row = _ScenarioRow(sid, idx, price, std_l, std_r, weight)
        row.deleted.connect(self._remove_scenario)
        row.changed.connect(self.changed.emit)
        self._rows[sid] = row
        self._rows_layout.addWidget(row)
        self.changed.emit()

    def _remove_scenario(self, sid: str) -> None:
        if len(self._rows) <= 1:
            return
        row = self._rows.pop(sid)
        self._rows_layout.removeWidget(row)
        row.deleteLater()
        # Renumber
        for i, r in enumerate(self._rows.values(), start=1):
            r.findChild(QLabel).setText(f"<b>#{i}</b>")
        self.changed.emit()

    # ------------------------------------------------------------------ public
    def get_scenarios(self) -> ScenarioData:
        data = [r.get_data() for r in self._rows.values()]
        total = sum(s["weight"] for s in data) or 1.0
        weights = [s["weight"] / total for s in data]
        return ScenarioData(
            centers=[s["price"]  for s in data],
            std_devs=[s["std"]   for s in data],
            std_devs_r=[s["std_r"] for s in data],
            weights=weights,
        )
