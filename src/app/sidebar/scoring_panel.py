"""
Scoring panel — PyQt6 equivalent of widget_scoring.py.
Renders ranking preset checkboxes and optional custom weight rows.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from app.data_types import (ALL_FIELDS, RANKING_PRESETS, SCORING_FIELDS, _make_full_weights, _preset_summary,)


class _CustomWeightRow(QWidget):
    """Editable row of integer sliders (0-100) for one weight set."""

    deleted = pyqtSignal(str)
    changed = pyqtSignal()

    def __init__(self, weight_id: str, index: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.weight_id = weight_id
        self._spins: Dict[str, QSpinBox] = {}
        self._build_ui(index)

    def _build_ui(self, index: int) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        hdr = QHBoxLayout()
        hdr.addWidget(QLabel(f"<b>Custom #{index}</b>"))
        btn_del = QPushButton("✕")
        btn_del.setFixedWidth(24)
        btn_del.clicked.connect(lambda: self.deleted.emit(self.weight_id))
        hdr.addWidget(btn_del)
        root.addLayout(hdr)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(4)
        for key, label in SCORING_FIELDS.items():
            col = QVBoxLayout()
            col.setSpacing(1)
            col.addWidget(QLabel(f"<small>{label}</small>"))
            spn = QSpinBox()
            spn.setRange(0, 100)
            spn.setValue(0)
            spn.valueChanged.connect(lambda _: self.changed.emit())
            self._spins[key] = spn
            col.addWidget(spn)
            fields_row.addLayout(col)
        root.addLayout(fields_row)

    def get_weights(self) -> Dict[str, float]:
        return {k: v.value() / 100.0 for k, v in self._spins.items()}


class ScoringPanel(QGroupBox):
    """Panel with ranking preset toggles and optional custom weight sets."""

    changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Ranking Presets", parent)
        self._preset_checks: Dict[str, QCheckBox] = {}
        self._custom_rows: Dict[str, _CustomWeightRow] = {}
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(4)

        # Preset checkboxes
        for i, (name, weights) in enumerate(RANKING_PRESETS.items()):
            summary = _preset_summary(weights)
            chk = QCheckBox(f"{name}  ·  {summary}")
            chk.setChecked(i == 0)   # R1 active by default
            chk.toggled.connect(lambda _: self.changed.emit())
            self._preset_checks[name] = chk
            root.addWidget(chk)

        # Container for custom weight rows
        self._custom_container = QWidget()
        self._custom_layout = QVBoxLayout(self._custom_container)
        self._custom_layout.setContentsMargins(0, 0, 0, 0)
        self._custom_layout.setSpacing(4)
        root.addWidget(self._custom_container)

        # Add custom button
        btn_add = QPushButton("➕ Add custom weight set")
        btn_add.clicked.connect(self._add_custom)
        root.addWidget(btn_add)

    # ------------------------------------------------------------------ helpers
    def _add_custom(self) -> None:
        wid = str(uuid.uuid4())
        idx = len(self._custom_rows) + 1
        row = _CustomWeightRow(wid, idx)
        row.deleted.connect(self._remove_custom)
        row.changed.connect(self.changed.emit)
        self._custom_rows[wid] = row
        self._custom_layout.addWidget(row)
        self.changed.emit()

    def _remove_custom(self, wid: str) -> None:
        row = self._custom_rows.pop(wid, None)
        if row:
            self._custom_layout.removeWidget(row)
            row.deleteLater()
            # Renumber
            for i, r in enumerate(self._custom_rows.values(), start=1):
                r.findChild(QLabel).setText(f"<b>Custom #{i}</b>")
            self.changed.emit()

    # ------------------------------------------------------------------ public
    def get_weights(self) -> List[Dict[str, float]]:
        result: List[Dict[str, float]] = []

        for name, chk in self._preset_checks.items():
            if chk.isChecked():
                result.append(_make_full_weights(RANKING_PRESETS[name]))

        for row in self._custom_rows.values():
            result.append(row.get_weights())

        if not result:
            result = [_make_full_weights(RANKING_PRESETS["R1 — Leverage"])]

        return result

    def load_from_weights(self, weights: list) -> None:
        """
        Restore preset checkboxes and/or custom rows from a saved weights list.
        Each item is a full-weight dict {metric: float, ...}.
        """
        if not weights:
            return

        # Build set of full-expanded preset dicts for comparison
        preset_full = {
            name: _make_full_weights(w) for name, w in RANKING_PRESETS.items()
        }

        # Uncheck all presets first
        for chk in self._preset_checks.values():
            chk.blockSignals(True)
            chk.setChecked(False)
            chk.blockSignals(False)

        # Remove existing custom rows
        for wid in list(self._custom_rows.keys()):
            row = self._custom_rows.pop(wid)
            self._custom_layout.removeWidget(row)
            row.deleteLater()

        for w in weights:
            # Normalise the incoming dict to all-keys
            full = _make_full_weights({k: v for k, v in w.items() if v > 0})
            # Try to match a preset
            matched = False
            for name, pf in preset_full.items():
                if all(abs(full.get(k, 0) - pf.get(k, 0)) < 1e-6 for k in pf):
                    chk = self._preset_checks.get(name)
                    if chk:
                        chk.blockSignals(True)
                        chk.setChecked(True)
                        chk.blockSignals(False)
                    matched = True
                    break
            if not matched:
                # Add as custom row
                wid = str(__import__('uuid').uuid4())
                idx = len(self._custom_rows) + 1
                row = _CustomWeightRow(wid, idx)
                row.deleted.connect(self._remove_custom)
                row.changed.connect(self.changed.emit)
                for key, spn in row._spins.items():
                    spn.blockSignals(True)
                    spn.setValue(int(round(w.get(key, 0.0) * 100)))
                    spn.blockSignals(False)
                self._custom_rows[wid] = row
                self._custom_layout.addWidget(row)

        self.changed.emit()
