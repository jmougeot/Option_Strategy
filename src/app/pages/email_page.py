"""
Email page — PyQt6.
Compose a trade-recommendation email from current session results.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from PyQt6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from app.app_state import AppState
from app.chart_widget import PlotlyChart

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


class _StrategyBlock(QGroupBox):
    """One editable block per recommended strategy."""

    def __init__(self, idx: int, comp: Any, ref: str, parent=None):
        super().__init__(f"Strategy {idx}", parent)
        self._build(comp, ref)

    def _build(self, comp, ref: str) -> None:
        form = QFormLayout(self)

        def _line(val: str) -> QLineEdit:
            w = QLineEdit(val)
            return w

        prem = abs(comp.premium or 0.0)
        sign = "BUY" if (comp.premium or 0) >= 0 else "SELL"
        delta = getattr(comp, "total_delta", 0.0)

        self._summary = _line(f"{sign} {comp.strategy_name}, mkt={prem:.4f}, ref={ref}, Δ={delta:+.3f}")
        self._comment = QTextEdit()
        self._comment.setFixedHeight(60)
        self._comment.setPlaceholderText("Add a comment…")

        form.addRow("Summary:", self._summary)
        form.addRow("Comment:", self._comment)

    def get_data(self) -> dict:
        return {
            "summary": self._summary.text(),
            "comment": self._comment.toPlainText(),
        }


class EmailPage(QWidget):
    """Draft and send a structured trade recommendation email."""

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

        # Header form
        hdr = QGroupBox("Header")
        hdr_form = QFormLayout(hdr)
        self._fld_date    = QLineEdit(datetime.now().strftime("%B %d, %Y"))
        self._fld_to      = QLineEdit()
        self._fld_from    = QLineEdit()
        self._fld_subject = QLineEdit()
        self._fld_expiry  = QLineEdit()
        self._fld_ref     = QLineEdit()
        hdr_form.addRow("Date:", self._fld_date)
        hdr_form.addRow("To:", self._fld_to)
        hdr_form.addRow("From:", self._fld_from)
        hdr_form.addRow("Subject:", self._fld_subject)
        hdr_form.addRow("Expiry:", self._fld_expiry)
        hdr_form.addRow("Reference:", self._fld_ref)
        root.addWidget(hdr)

        # Number of strategies to include
        nb_row = QHBoxLayout()
        nb_row.addWidget(QLabel("Number of strategies:"))
        self._spn_nb = QSpinBox()
        self._spn_nb.setRange(1, 10)
        self._spn_nb.setValue(3)
        nb_row.addWidget(self._spn_nb)
        btn_populate = QPushButton("Populate from results")
        btn_populate.clicked.connect(self._populate)
        nb_row.addWidget(btn_populate)
        nb_row.addStretch()
        root.addLayout(nb_row)

        # Strategy blocks scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setSpacing(6)
        self._scroll.setWidget(self._scroll_widget)
        root.addWidget(self._scroll, stretch=1)

        # Payoff chart
        self._chart = PlotlyChart(min_height=300)
        root.addWidget(self._chart)

        # Actions
        btn_row = QHBoxLayout()
        btn_email = QPushButton("📧 Open in email client")
        btn_pdf   = QPushButton("📄 Export PDF")
        btn_email.clicked.connect(self._on_email)
        btn_pdf.clicked.connect(self._on_pdf)
        btn_row.addWidget(btn_email)
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
        """Fill the header and strategy blocks from current AppState results."""
        params = self._state.params
        comparisons = self._state.comparisons
        future_data = self._state.future_data
        mixture = self._state.mixture

        if not comparisons:
            QMessageBox.information(self, "Email", "No results yet — run a comparison first.")
            return

        # Pre-fill header
        expiry = _expiry_label(params)
        ref = (
            f"{future_data.underlying_price:.4f}" if future_data and future_data.underlying_price
            else "N/A"
        )
        self._fld_expiry.setText(expiry)
        self._fld_ref.setText(ref)
        subject = f"Trade recommendation — {expiry}" if expiry else "Trade recommendation"
        self._fld_subject.setText(subject)

        # Rebuild strategy blocks
        self._clear_blocks()
        nb = min(self._spn_nb.value(), len(comparisons))
        for i, comp in enumerate(comparisons[:nb], start=1):
            block = _StrategyBlock(i, comp, ref)
            self._strategy_blocks.append(block)
            self._scroll_layout.addWidget(block)

        # Payoff chart
        if mixture is not None and comparisons:
            from app.widget_payoff import build_payoff_figure
            price = future_data.underlying_price if future_data else 0.0
            try:
                fig = build_payoff_figure(comparisons[:nb], mixture, price)
                self._chart.set_figure(fig)
            except Exception:
                pass

    def _on_email(self) -> None:
        try:
            from share_result.email_utils import create_email_with_images
            # Build minimal template data from fields + strategy blocks
            strategies_data = [b.get_data() for b in self._strategy_blocks]
            # Open default mail client using mailto
            import urllib.parse, webbrowser
            body = "\n\n".join(
                f"{s['summary']}\n{s['comment']}" for s in strategies_data
            )
            url = f"mailto:{self._fld_to.text()}?subject={urllib.parse.quote(self._fld_subject.text())}&body={urllib.parse.quote(body)}"
            webbrowser.open(url)
        except Exception as exc:
            QMessageBox.warning(self, "Email", f"Could not open email client:\n{exc}")

    def _on_pdf(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "report.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            from share_result.generate_pdf import create_pdf_report
            strategies_data = [b.get_data() for b in self._strategy_blocks]
            create_pdf_report(
                strategies=self._state.comparisons[:len(self._strategy_blocks)],
                mixture=self._state.mixture,
                output_path=path,
            )
            QMessageBox.information(self, "PDF", f"Saved to {path}")
        except Exception as exc:
            QMessageBox.warning(self, "PDF", f"Failed:\n{exc}")
