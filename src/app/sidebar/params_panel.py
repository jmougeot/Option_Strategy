"""
Params panel — PyQt6 equivalent of widget_params.py (sidebar_params).
Emits a UIParams dataclass whenever any field changes.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QSlider, QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt

from app.data_types import UIParams, UNDERLYING_PARAMS, parse_roll_input
from app.utils import strike_list


class ParamsPanel(QGroupBox):
    """Sidebar panel for underlying / expiry / price parameters."""

    changed = pyqtSignal()  # emitted whenever any value changes

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Parameters", parent)
        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(4)

        # ── Options row ────────────────────────────────────────────────
        opts_layout = QHBoxLayout()
        self._chk_brut = QCheckBox("Raw code")
        self._chk_bachelier = QCheckBox("Bachelier")
        self._chk_bachelier.setChecked(True)
        self._chk_sabr = QCheckBox("SABR")
        self._chk_sabr.setChecked(True)
        for w in (self._chk_brut, self._chk_bachelier, self._chk_sabr):
            opts_layout.addWidget(w)
        root.addLayout(opts_layout)

        # ── Standard mode form ────────────────────────────────────────
        self._std_group = QWidget()
        std_form = QFormLayout(self._std_group)
        std_form.setContentsMargins(0, 0, 0, 0)

        self._cmb_underlying = QComboBox()
        self._cmb_underlying.addItems(list(UNDERLYING_PARAMS.keys()))
        std_form.addRow("Underlying:", self._cmb_underlying)

        self._txt_custom_und = QLineEdit()
        self._txt_custom_und.setPlaceholderText("e.g. ER")
        self._txt_custom_und.setVisible(False)
        std_form.addRow("Custom code:", self._txt_custom_und)

        self._txt_years = QLineEdit("6")
        std_form.addRow("Year(s):", self._txt_years)

        self._cmb_months = QComboBox()
        self._cmb_months.addItems(["F","G","H","J","K","M","N","Q","U","V","X","Z"])
        std_form.addRow("Month:", self._cmb_months)

        self._cmb_unit = QComboBox()
        self._cmb_unit.addItems(["100ème", "64ème"])
        std_form.addRow("Unit:", self._cmb_unit)

        root.addWidget(self._std_group)

        # ── Raw code mode ─────────────────────────────────────────────
        self._raw_group = QWidget()
        raw_form = QFormLayout(self._raw_group)
        raw_form.setContentsMargins(0, 0, 0, 0)
        self._txt_brut_code = QLineEdit("RXWF26C2,RXWF26P2")
        raw_form.addRow("Bloomberg code:", self._txt_brut_code)
        self._raw_group.setVisible(False)
        root.addWidget(self._raw_group)

        # ── Price range ───────────────────────────────────────────────
        price_form = QFormLayout()
        price_form.setContentsMargins(0, 0, 0, 0)

        self._spn_price_min = QDoubleSpinBox()
        self._spn_price_min.setDecimals(4)
        self._spn_price_min.setRange(0, 9999)
        self._spn_price_min.setValue(97.0)
        price_form.addRow("Min Price:", self._spn_price_min)

        self._spn_price_max = QDoubleSpinBox()
        self._spn_price_max.setDecimals(4)
        self._spn_price_max.setRange(0, 9999)
        self._spn_price_max.setValue(99.0)
        price_form.addRow("Max Price:", self._spn_price_max)

        self._spn_price_step = QDoubleSpinBox()
        self._spn_price_step.setDecimals(4)
        self._spn_price_step.setSingleStep(0.0001)
        self._spn_price_step.setRange(0.0001, 10)
        self._spn_price_step.setValue(0.0625)
        price_form.addRow("Price Step:", self._spn_price_step)

        self._txt_roll = QLineEdit()
        self._txt_roll.setPlaceholderText("e.g. Z5 or H6,Z5")
        price_form.addRow("Roll months:", self._txt_roll)

        root.addLayout(price_form)

        # ── Max legs slider ───────────────────────────────────────────
        legs_row = QHBoxLayout()
        self._lbl_legs = QLabel("Max legs: 4")
        self._sld_legs = QSlider(Qt.Orientation.Horizontal)
        self._sld_legs.setRange(1, 9)
        self._sld_legs.setValue(4)
        legs_row.addWidget(self._lbl_legs)
        legs_row.addWidget(self._sld_legs)
        root.addLayout(legs_row)

        # ── Leg penalty ───────────────────────────────────────────────
        pen_form = QFormLayout()
        pen_form.setContentsMargins(0, 0, 0, 0)
        self._spn_penalty = QDoubleSpinBox()
        self._spn_penalty.setDecimals(4)
        self._spn_penalty.setSingleStep(0.0001)
        self._spn_penalty.setRange(0, 10)
        self._spn_penalty.setValue(0.0)
        pen_form.addRow("Leg penalty:", self._spn_penalty)
        root.addLayout(pen_form)

    # ------------------------------------------------------------------ signals
    def _connect_signals(self) -> None:
        self._chk_brut.toggled.connect(self._on_brut_toggle)
        self._cmb_underlying.currentTextChanged.connect(self._on_underlying_change)
        self._sld_legs.valueChanged.connect(
            lambda v: (self._lbl_legs.setText(f"Max legs: {v}"), self.changed.emit())
        )
        for w in (
            self._chk_bachelier, self._chk_sabr,
            self._cmb_months, self._cmb_unit,
            self._spn_price_min, self._spn_price_max, self._spn_price_step,
            self._spn_penalty,
        ):
            sig = getattr(w, "toggled", None) or getattr(w, "currentTextChanged", None) or getattr(w, "valueChanged", None)
            if sig:
                sig.connect(lambda _=None: self.changed.emit())

        for txt in (self._txt_years, self._txt_roll, self._txt_brut_code, self._txt_custom_und):
            txt.textChanged.connect(lambda _: self.changed.emit())

    # ------------------------------------------------------------------ slots
    def _on_brut_toggle(self, checked: bool) -> None:
        self._std_group.setVisible(not checked)
        self._raw_group.setVisible(checked)
        self.changed.emit()

    def _on_underlying_change(self, und: str) -> None:
        self._txt_custom_und.setVisible(und == "Other")
        p = UNDERLYING_PARAMS.get(und, {})
        if p:
            self._spn_price_step.setValue(p.get("Step", 0.0625))
            self._spn_price_min.setValue(float(p.get("Min_price", 97)))
            self._spn_price_max.setValue(float(p.get("Max_price", 99)))
        self.changed.emit()

    # ------------------------------------------------------------------ public
    def get_params(self) -> UIParams:
        brut_mode = self._chk_brut.isChecked()

        if brut_mode:
            raw = self._txt_brut_code.text().strip()
            brut_code = [x.strip() for x in raw.split(",") if x.strip()] or None
            underlying = "ER"
            years: List[int] = []
            months: List[str] = []
        else:
            und_sel = self._cmb_underlying.currentText()
            underlying = self._txt_custom_und.text().strip() if und_sel == "Other" else und_sel
            years_raw = self._txt_years.text()
            years = [int(y.strip()) for y in years_raw.split(",") if y.strip().isdigit()]
            months = [self._cmb_months.currentText()]
            brut_code = None

        price_min = self._spn_price_min.value()
        price_max = self._spn_price_max.value()
        price_step = self._spn_price_step.value()

        roll_expiries = parse_roll_input(self._txt_roll.text()) if self._txt_roll.text() else None

        strikes = strike_list(price_min, price_max, price_step)

        return UIParams(
            underlying=underlying,
            months=months,
            years=years,
            price_min=price_min,
            price_max=price_max,
            price_step=price_step,
            max_legs=self._sld_legs.value(),
            strikes=strikes,
            unit=self._cmb_unit.currentText(),
            brut_code=brut_code,
            roll_expiries=roll_expiries,
            use_bachelier=self._chk_bachelier.isChecked(),
            use_sabr=self._chk_sabr.isChecked(),
            operation_penalisation=self._spn_penalty.value(),
        )

    def load_from_params_dict(self, params: dict) -> None:
        """Restore widget values from a saved params dict (e.g. from history)."""
        to_block = [
            self._cmb_underlying, self._cmb_months, self._txt_years,
            self._spn_price_min, self._spn_price_max, self._spn_price_step,
            self._sld_legs, self._chk_bachelier, self._chk_sabr, self._spn_penalty,
        ]
        for w in to_block:
            w.blockSignals(True)
        try:
            underlying = params.get("underlying", "ER")
            idx = self._cmb_underlying.findText(underlying)
            if idx >= 0:
                self._cmb_underlying.setCurrentIndex(idx)

            months = params.get("months", [])
            if months:
                idx_m = self._cmb_months.findText(months[0])
                if idx_m >= 0:
                    self._cmb_months.setCurrentIndex(idx_m)

            years = params.get("years", [])
            if years:
                self._txt_years.setText(",".join(str(y) for y in years))

            price_min = params.get("price_min")
            price_max = params.get("price_max")
            if price_min is not None:
                self._spn_price_min.setValue(float(price_min))
            if price_max is not None:
                self._spn_price_max.setValue(float(price_max))

            max_legs = params.get("max_legs")
            if max_legs is not None:
                self._sld_legs.setValue(int(max_legs))
        finally:
            for w in to_block:
                w.blockSignals(False)
        self.changed.emit()
