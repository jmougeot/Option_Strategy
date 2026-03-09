"""
Email page — PyQt6.
Compose a trade-recommendation email from current session results,
using the share_result module for Outlook HTML + PDF generation.
"""

from __future__ import annotations

from typing import Any, List

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QScrollArea, QSpinBox,
    QTextEdit, QVBoxLayout, QWidget,
)

from app.app_state import AppState
from app.chart_widget import ChartWidget

MONTH_NAMES = {
    "F": "January", "G": "February", "H": "March", "K": "April",
    "M": "June",    "N": "July",     "Q": "August", "U": "September",
    "V": "October", "X": "November", "Z": "December",
}


def _expiry_label(params) -> str:
    if params is None:
        return ""
    m = params.months[0] if params.months else ""
    y = params.years[0]  if params.years  else ""
    year_str = f"20{y}" if isinstance(y, int) and y < 100 else str(y)
    return f"{MONTH_NAMES.get(m, m)} {year_str}"


def _expiry_code(params) -> str:
    """Short code like 'ERU6'."""
    if params is None:
        return ""
    und = params.underlying or ""
    m = params.months[0] if params.months else ""
    y = params.years[0]  if params.years  else ""
    return f"{und}{m}{y}"


class _StrategyBlock(QGroupBox):
    """One editable block per recommended strategy."""

    def __init__(self, idx: int, comp: Any, ref: str, parent=None):
        super().__init__(f"Strategy {idx}", parent)
        self._idx = idx
        self._comp = comp
        self._build(comp, ref)

    def _build(self, comp, ref: str) -> None:
        form = QFormLayout(self)

        prem = abs(comp.premium or 0.0)
        delta = getattr(comp, "total_delta", 0.0)
        self._summary = QLineEdit(
            f"{comp.strategy_name}, mkt={prem:.4f}, ref={ref}, Δ={delta:+.3f}"
        )
        self._comment = QTextEdit()
        self._comment.setFixedHeight(60)
        self._comment.setPlaceholderText("Why this strategy? (used in the email body)")

        form.addRow("Summary:", self._summary)
        form.addRow("Comment:", self._comment)

    def get_strat_data(self) -> dict:
        """Return the dict expected by generate_html_email_from_template's strat_data."""
        c = self._comp
        be = (
            " / ".join(f"{bp:.4f}" for bp in c.breakeven_points)
            if c.breakeven_points else "N/A"
        )
        # Find price at max PnL
        max_at = "N/A"
        if c.pnl_array is not None and c.prices is not None:
            import numpy as np
            idx = int(np.argmax(c.pnl_array))
            max_at = f"{c.prices[idx]:.4f}"

        return {
            "idx": self._idx,
            "line": self._summary.text(),
            "commentary": self._comment.toPlainText() or "it has the best overall score",
            "premium": c.premium or 0.0,
            "avg_pnl": c.average_pnl or 0.0,
            "max_profit": c.max_profit or 0.0,
            "max_profit_at": max_at,
            "leverage": c.avg_pnl_levrage or 0.0,
            "breakeven": be,
        }


class EmailPage(QWidget):
    """Draft and send a structured trade recommendation email via Outlook or PDF."""

    def __init__(self, state: AppState, parent=None):
        super().__init__(parent)
        self._state = state
        self._strategy_blocks: List[_StrategyBlock] = []
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.addWidget(QLabel("<h2>Email Generator</h2>"))

        # ── Header / recipient form ────────────────────────────────────
        hdr = QGroupBox("Header")
        hdr_form = QFormLayout(hdr)
        self._fld_client    = QLineEdit("XXX")
        self._fld_to        = QLineEdit()
        self._fld_signature = QLineEdit()
        hdr_form.addRow("Client name:", self._fld_client)
        hdr_form.addRow("To:", self._fld_to)
        hdr_form.addRow("Signature:", self._fld_signature)
        root.addWidget(hdr)

        # ── Market context form ────────────────────────────────────────
        ctx = QGroupBox("Market Context")
        ctx_form = QFormLayout(ctx)
        self._fld_expiry_code = QLineEdit()
        self._fld_und_price   = QLineEdit()
        self._fld_target      = QLineEdit()
        self._fld_target_date = QLineEdit()
        self._fld_uncert_l    = QLineEdit()
        self._fld_uncert_r    = QLineEdit()
        ctx_form.addRow("Expiry code:", self._fld_expiry_code)
        ctx_form.addRow("Underlying price:", self._fld_und_price)
        ctx_form.addRow("Target:", self._fld_target)
        ctx_form.addRow("Target date:", self._fld_target_date)
        ctx_form.addRow("Uncertainty left (bp):", self._fld_uncert_l)
        ctx_form.addRow("Uncertainty right (bp):", self._fld_uncert_r)
        root.addWidget(ctx)

        # ── Number of strategies + populate ────────────────────────────
        nb_row = QHBoxLayout()
        nb_row.addWidget(QLabel("Strategies to include:"))
        self._spn_nb = QSpinBox()
        self._spn_nb.setRange(1, 10)
        self._spn_nb.setValue(3)
        nb_row.addWidget(self._spn_nb)
        btn_populate = QPushButton("Populate from results")
        btn_populate.clicked.connect(self._populate)
        nb_row.addWidget(btn_populate)
        nb_row.addStretch()
        root.addLayout(nb_row)

        # ── Strategy blocks scroll area ────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setSpacing(6)
        self._scroll.setWidget(self._scroll_widget)
        root.addWidget(self._scroll, stretch=1)

        # ── Payoff chart preview ───────────────────────────────────────
        self._chart = ChartWidget(min_height=280)
        root.addWidget(self._chart)

        # ── Action buttons ─────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_outlook = QPushButton("📧 Open in Outlook (HTML + images)")
        btn_pdf     = QPushButton("📄 Export PDF")
        btn_outlook.clicked.connect(self._on_outlook)
        btn_pdf.clicked.connect(self._on_pdf)
        btn_row.addWidget(btn_outlook)
        btn_row.addWidget(btn_pdf)
        btn_row.addStretch()
        root.addLayout(btn_row)

    # ------------------------------------------------------------------ helpers
    def _clear_blocks(self) -> None:
        for b in self._strategy_blocks:
            self._scroll_layout.removeWidget(b)
            b.deleteLater()
        self._strategy_blocks.clear()

    def _populate(self) -> None:
        """Fill forms and strategy blocks from current AppState results."""
        params = self._state.params
        comparisons = self._state.comparisons
        future_data = self._state.future_data
        mixture = self._state.mixture
        filt = self._state.filter

        if not comparisons:
            QMessageBox.information(self, "Email", "No results yet — run a comparison first.")
            return

        # Pre-fill context fields
        ref = (
            f"{future_data.underlying_price:.4f}"
            if future_data and future_data.underlying_price else "N/A"
        )
        self._fld_expiry_code.setText(_expiry_code(params))
        self._fld_und_price.setText(ref)

        if filt:
            self._fld_uncert_l.setText(f"{filt.limit_left}")
            self._fld_uncert_r.setText(f"{filt.limit_right}")

        # Rebuild strategy blocks
        self._clear_blocks()
        nb = min(self._spn_nb.value(), len(comparisons))
        for i, comp in enumerate(comparisons[:nb], start=1):
            block = _StrategyBlock(i, comp, ref)
            self._strategy_blocks.append(block)
            self._scroll_layout.addWidget(block)

        # Payoff chart preview
        if mixture is not None and comparisons:
            from app.widget_payoff import build_payoff_figure
            price = future_data.underlying_price if future_data else 0.0
            try:
                fig = build_payoff_figure(comparisons[:nb], mixture, price)
                self._chart.set_figure(fig)
            except Exception:
                pass

    # ------------------------------------------------------------------ data builders
    def _collect_fields(self) -> dict:
        """Gather all form fields into the dict expected by generate_html_email_from_template."""
        params = self._state.params
        filt = self._state.filter
        stats = self._state.stats

        return {
            "client_name":     self._fld_client.text(),
            "expiry_code":     self._fld_expiry_code.text(),
            "underlying_price": self._fld_und_price.text(),
            "target":          self._fld_target.text() or "XXX",
            "target_date":     self._fld_target_date.text() or "XXX",
            "uncert_left":     self._fld_uncert_l.text() or "XXX",
            "uncert_right":    self._fld_uncert_r.text() or "XXX",
            "tail_left":       f"{filt.max_loss_left:.2f}" if filt else "XXX",
            "tail_right":      f"{filt.max_loss_right:.2f}" if filt else "XXX",
            "limit_left":      f"{filt.limit_left}" if filt else "XXX",
            "limit_right":     f"{filt.limit_right}" if filt else "XXX",
            "open_risk":       (
                f"{filt.ouvert_gauche}ps / {filt.ouvert_droite}cs" if filt else "XXX"
            ),
            "max_legs":        str(params.max_legs) if params else "XXX",
            "price_min":       f"{params.price_min:.4f}" if params else "XXX",
            "price_max":       f"{params.price_max:.4f}" if params else "XXX",
            "price_step":      f"{params.price_step}" if params else "XXX",
            "min_short":       f"{filt.min_premium_sell:.3f}" if filt else "XXX",
            "delta_min":       f"{filt.delta_min * 100:.0f}d" if filt else "XXX",
            "delta_max":       f"{filt.delta_max * 100:+.0f}d" if filt else "XXX",
            "signature":       self._fld_signature.text() or "XXX",
            "nb_screened":     stats.get("nb_strategies_possibles", 0),
        }

    def _collect_strat_data(self) -> list:
        return [b.get_strat_data() for b in self._strategy_blocks]

    def _build_template_data(self):
        """Build an EmailTemplateData from current state."""
        from share_result.email_utils import build_email_template_data
        return build_email_template_data(
            params=self._state.params,
            filter=self._state.filter,
            scoring_weights=(
                self._state.scoring_weights[0]
                if self._state.scoring_weights else {}
            ),
            comparisons=self._state.comparisons,
            future_data=self._state.future_data,
            scenarios=None,
        )

    # ------------------------------------------------------------------ actions
    def _on_outlook(self) -> None:
        """Open Outlook with a professional HTML email + embedded payoff PNGs."""
        if not self._strategy_blocks:
            QMessageBox.information(self, "Email", "Populate the strategies first.")
            return
        try:
            from share_result.email_utils import create_email_with_images

            template_data = self._build_template_data()
            fields = self._collect_fields()
            strat_data = self._collect_strat_data()
            selected = self._state.comparisons[:len(self._strategy_blocks)]

            ok = create_email_with_images(
                template_data=template_data,
                mixture=self._state.mixture,
                comparisons=self._state.comparisons,
                selected_comparisons=selected,
                fields=fields,
                strat_data=strat_data,
                params=self._state.params,
                future_data=self._state.future_data,
            )
            if not ok:
                QMessageBox.warning(
                    self, "Email",
                    "Could not open Outlook.\nFallback: use the mailto link or export PDF.",
                )
        except Exception as exc:
            QMessageBox.warning(self, "Email", f"Error:\n{exc}")

    def _on_pdf(self) -> None:
        """Export a PDF report using share_result.generate_pdf."""
        if not self._strategy_blocks:
            QMessageBox.information(self, "Email", "Populate the strategies first.")
            return
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", "report.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            from share_result.generate_pdf import create_pdf_report

            template_data = self._build_template_data()
            pdf_bytes = create_pdf_report(
                template_data=template_data,
                mixture=self._state.mixture,
                comparisons=self._state.comparisons[:len(self._strategy_blocks)],
            )
            if pdf_bytes:
                with open(path, "wb") as f:
                    f.write(pdf_bytes)
                QMessageBox.information(self, "PDF", f"Saved to {path}")
            else:
                QMessageBox.warning(self, "PDF", "PDF generation returned empty.")
        except Exception as exc:
            QMessageBox.warning(self, "PDF", f"Failed:\n{exc}")
