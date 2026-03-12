"""
Filter panel — PyQt6 equivalent of widget_filter.py.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget,
)

from app.data_types import FilterData, StrategyType


class FilterPanel(QGroupBox):
    """Sidebar panel for strategy filters."""

    changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Filters", parent)
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(6)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)

        def _dbl(lo: float, hi: float, val: float, step: float = 0.001, dec: int = 4) -> QDoubleSpinBox:
            s = QDoubleSpinBox()
            s.setDecimals(dec)
            s.setRange(lo, hi)
            s.setValue(val)
            s.setSingleStep(step)
            s.valueChanged.connect(lambda _: self.changed.emit())
            return s

        self._chk_premium_only = QCheckBox("Risk Premium only")
        self._chk_premium_only.toggled.connect(self._on_premium_only)
        root.addWidget(self._chk_premium_only)

        # Loss limits (hidden when premium_only)
        self._loss_widget = QWidget()
        loss_form = QFormLayout(self._loss_widget)
        loss_form.setContentsMargins(0, 0, 0, 0)

        self._spn_loss_left  = _dbl(-9999, 9999, 0.1)
        self._spn_limit_left = _dbl(0, 9999, 98.5)
        self._chk_po_left    = QCheckBox("Premium only")
        self._chk_po_left.toggled.connect(lambda _: self.changed.emit())

        row_left = QHBoxLayout()
        for w in (self._spn_loss_left, self._spn_limit_left, self._chk_po_left):
            row_left.addWidget(w)
        lbl_left = QLabel("Max loss ↓ / from / prem.only")
        loss_form.addRow(lbl_left, row_left)

        self._spn_loss_right  = _dbl(-9999, 9999, 0.1)
        self._spn_limit_right = _dbl(0, 9999, 98.0)
        self._chk_po_right    = QCheckBox("Premium only")
        self._chk_po_right.toggled.connect(lambda _: self.changed.emit())

        row_right = QHBoxLayout()
        for w in (self._spn_loss_right, self._spn_limit_right, self._chk_po_right):
            row_right.addWidget(w)
        lbl_right = QLabel("Max loss ↑ / from / prem.only")
        loss_form.addRow(lbl_right, row_right)

        root.addWidget(self._loss_widget)
        root.addLayout(form)

        # Premium bounds
        prem_form = QFormLayout()
        prem_form.setContentsMargins(0, 0, 0, 0)
        self._spn_max_prem  = _dbl(-9999, 9999, 0.010)
        self._spn_min_short = _dbl(0, 9999, 0.005)
        prem_form.addRow("Max premium:", self._spn_max_prem)
        prem_form.addRow("Min short price:", self._spn_min_short)
        root.addLayout(prem_form)

        # Open legs (int spinboxes)
        legs_form = QFormLayout()
        legs_form.setContentsMargins(0, 0, 0, 0)
        self._spn_og = QSpinBox(); self._spn_og.setRange(-99, 99); self._spn_og.setValue(0)
        self._spn_od = QSpinBox(); self._spn_od.setRange(-99, 99); self._spn_od.setValue(0)
        self._spn_og.valueChanged.connect(lambda _: self.changed.emit())
        self._spn_od.valueChanged.connect(lambda _: self.changed.emit())
        legs_form.addRow("PUT short-long:", self._spn_og)
        legs_form.addRow("CALL short-long:", self._spn_od)
        root.addLayout(legs_form)

        # Delta bounds
        delta_form = QFormLayout()
        delta_form.setContentsMargins(0, 0, 0, 0)
        self._spn_delta_min = _dbl(-1, 1, -0.75, step=0.01, dec=2)
        self._spn_delta_max = _dbl(-1, 1,  0.75, step=0.01, dec=2)
        delta_form.addRow("Delta min:", self._spn_delta_min)
        delta_form.addRow("Delta max:", self._spn_delta_max)
        root.addLayout(delta_form)

        # Strategy type filter
        self._chk_filter_type = QCheckBox("Select strategy types")
        self._chk_filter_type.toggled.connect(self._on_filter_type)
        root.addWidget(self._chk_filter_type)

        self._strat_widget = QWidget()
        strat_layout = QVBoxLayout(self._strat_widget)
        strat_layout.setContentsMargins(4, 0, 0, 0)
        self._chk_put_condor  = QCheckBox("Put Condor")
        self._chk_call_condor = QCheckBox("Call Condor")
        self._chk_put_ladder  = QCheckBox("Put Ladder")
        self._chk_call_ladder = QCheckBox("Call Ladder")
        self._chk_put_fly     = QCheckBox("Put Fly")
        self._chk_call_fly    = QCheckBox("Call Fly")
        for chk in (self._chk_put_condor, self._chk_call_condor, self._chk_put_ladder,
                    self._chk_call_ladder, self._chk_put_fly, self._chk_call_fly):
            chk.toggled.connect(lambda _: self.changed.emit())
            strat_layout.addWidget(chk)
        self._strat_widget.setVisible(False)
        root.addWidget(self._strat_widget)

    # ------------------------------------------------------------------ slots
    def _on_premium_only(self, checked: bool) -> None:
        self._loss_widget.setVisible(not checked)
        self.changed.emit()

    def _on_filter_type(self, checked: bool) -> None:
        self._strat_widget.setVisible(checked)
        self.changed.emit()

    # ------------------------------------------------------------------ public
    def get_filter(self) -> FilterData:
        premium_only = self._chk_premium_only.isChecked()
        if premium_only:
            max_loss_left = max_loss_right = 100.0
            limit_left = limit_right = 98.0
            po_left = po_right = False
        else:
            max_loss_left  = self._spn_loss_left.value()
            max_loss_right = self._spn_loss_right.value()
            limit_left     = self._spn_limit_left.value()
            limit_right    = self._spn_limit_right.value()
            po_left        = self._chk_po_left.isChecked()
            po_right       = self._chk_po_right.isChecked()

        filter_type = self._chk_filter_type.isChecked()
        strat_include = None
        if filter_type:
            strat_include = StrategyType(
                put_condor=self._chk_put_condor.isChecked(),
                call_condor=self._chk_call_condor.isChecked(),
                put_ladder=self._chk_put_ladder.isChecked(),
                call_ladder=self._chk_call_ladder.isChecked(),
                put_fly=self._chk_put_fly.isChecked(),
                call_fly=self._chk_call_fly.isChecked(),
            )

        return FilterData(
            max_loss_left=max_loss_left,
            max_loss_right=max_loss_right,
            max_premium=self._spn_max_prem.value(),
            ouvert_gauche=self._spn_og.value(),
            ouvert_droite=self._spn_od.value(),
            min_premium_sell=self._spn_min_short.value(),
            filter_type=filter_type,
            strategies_include=strat_include,
            delta_min=self._spn_delta_min.value(),
            delta_max=self._spn_delta_max.value(),
            limit_left=limit_left,
            limit_right=limit_right,
            premium_only=premium_only,
            premium_only_right=po_right,
            premium_only_left=po_left,
        )

    def load_from_dict(self, d: dict) -> None:
        """Restore widget values from a saved filter dict."""
        widgets = [
            self._chk_premium_only, self._spn_loss_left, self._spn_loss_right,
            self._spn_limit_left, self._spn_limit_right, self._chk_po_left, self._chk_po_right,
            self._spn_max_prem, self._spn_min_short, self._spn_og, self._spn_od,
            self._spn_delta_min, self._spn_delta_max, self._chk_filter_type,
        ]
        for w in widgets:
            w.blockSignals(True)
        try:
            po = d.get("premium_only", False)
            self._chk_premium_only.setChecked(po)
            self._loss_widget.setVisible(not po)

            if "max_loss_left" in d:
                self._spn_loss_left.setValue(float(d["max_loss_left"]))
            if "max_loss_right" in d:
                self._spn_loss_right.setValue(float(d["max_loss_right"]))
            if "limit_left" in d:
                self._spn_limit_left.setValue(float(d["limit_left"]))
            if "limit_right" in d:
                self._spn_limit_right.setValue(float(d["limit_right"]))
            if "premium_only_left" in d:
                self._chk_po_left.setChecked(bool(d["premium_only_left"]))
            if "premium_only_right" in d:
                self._chk_po_right.setChecked(bool(d["premium_only_right"]))
            if "max_premium" in d:
                self._spn_max_prem.setValue(float(d["max_premium"]))
            if "min_premium_sell" in d:
                self._spn_min_short.setValue(float(d["min_premium_sell"]))
            if "ouvert_gauche" in d:
                self._spn_og.setValue(int(d["ouvert_gauche"]))
            if "ouvert_droite" in d:
                self._spn_od.setValue(int(d["ouvert_droite"]))
            if "delta_min" in d:
                self._spn_delta_min.setValue(float(d["delta_min"]))
            if "delta_max" in d:
                self._spn_delta_max.setValue(float(d["delta_max"]))
        finally:
            for w in widgets:
                w.blockSignals(False)
        self.changed.emit()
