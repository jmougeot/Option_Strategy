"""
Help page — PyQt6.
Static documentation rendered in a QTextBrowser.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget


HELP_HTML = """
<h1>Complete Guide</h1>
<p>This guide explains all parameters, filters and scoring criteria.</p>

<h2 id="scenarios">1 — Market Scenarios</h2>
<p>Scenarios define your price expectations at expiration, modeled as a Gaussian mixture.</p>
<ul>
<li><b>Target Price</b>: center of the distribution for this scenario.</li>
<li><b>σ left / σ right</b>: downside / upside uncertainty (std dev).</li>
<li><b>Probability weight</b>: relative weight (automatically normalized).</li>
</ul>

<h2 id="params">2 — Search Parameters</h2>
<ul>
<li><b>Underlying</b>: Bloomberg code (e.g. ER = EURIBOR, RX = Bund).</li>
<li><b>Year(s)</b>: last digit(s) of the year (6 = 2026, comma-separated for multi-year).</li>
<li><b>Month</b>: expiry month code (H=Mar, M=Jun, U=Sep, Z=Dec).</li>
<li><b>Price Step</b>: tick size for generating strikes.</li>
<li><b>Roll months</b>: extra expiries to include (format: M1Y1, M2Y2).</li>
<li><b>Max legs</b>: maximum number of options per strategy (1–9).</li>
<li><b>Leg penalty</b>: cost subtracted per leg from the effective premium.</li>
<li><b>Bachelier</b>: if checked, options with missing prices are priced via the Bachelier model.</li>
<li><b>SABR calibration</b>: fit SABR to the Bloomberg smile to correct anomalous vols.</li>
</ul>

<h2 id="filters">3 — Strategy Filters</h2>
<ul>
<li><b>Risk Premium only</b>: accept strategies where the only risk is the initial premium paid.</li>
<li><b>Max loss ↓ / ↑</b>: maximum tolerated loss on the downside / upside (premium included).</li>
<li><b>Starting from</b>: price level beyond which the loss constraint applies.</li>
<li><b>Max premium</b>: maximum cost of the strategy (absolute value).</li>
<li><b>Min short price</b>: minimum price required to sell an option leg.</li>
<li><b>PUT/CALL short-long</b>: maximum imbalance between sold and bought legs.</li>
<li><b>Delta min/max</b>: net delta constraint for the strategy.</li>
</ul>

<h2 id="scoring">4 — Scoring Criteria</h2>
<ul>
<li><b>Leverage (avg_pnl_levrage)</b>: expected P&amp;L divided by premium paid (risk-adjusted return).</li>
<li><b>Roll</b>: carry / time-value capture of the strategy.</li>
<li><b>Expected Gain (average_pnl)</b>: expected P&amp;L under the Gaussian mixture.</li>
<li><b>Premium</b>: absolute cost of the strategy.</li>
<li><b>Theta</b>: daily time decay of the strategy.</li>
<li><b>Gamma</b>: sensitivity of delta to price moves.</li>
<li><b>Delta Height</b>: maximum delta exposure across the price range.</li>
</ul>

<h2 id="presets">5 — Ranking Presets</h2>
<ul>
<li><b>R1 — Leverage</b>: sort by risk-adjusted return only.</li>
<li><b>R2 — Roll</b>: sort by carry only.</li>
<li><b>R3 — Balanced</b>: 50% Leverage + 50% Roll.</li>
<li><b>R4 — Roll + Leverage</b>: equivalent to R3.</li>
</ul>
<p>You can activate multiple presets simultaneously; a Meta Ranking tab will appear showing
the consensus across all active rankings.</p>
<p>Custom weight sets let you define your own linear combination of criteria.</p>
"""


class HelpPage(QWidget):
    """Static help content rendered in a QTextBrowser."""

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        browser = QTextBrowser()
        browser.setHtml(HELP_HTML)
        browser.setOpenExternalLinks(True)
        root.addWidget(browser)
