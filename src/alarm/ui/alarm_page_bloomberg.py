"""Mixin — Bloomberg price updates and local analytics refresh."""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Optional

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QTableWidget

from alarm.models.strategy import Strategy, normalize_ticker
from alarm.ui.columns import (
    C_DELTA, C_FUT, C_GAMMA, C_IV, C_PRICE, C_THETA,
)
from app import theme

if TYPE_CHECKING:
    from bloomberg.realtime import BloombergService


class BloombergMixin:
    """Handles Bloomberg connection status, price and greeks updates."""

    _bbg_lbl: QLabel
    _table: QTableWidget
    _pages: list[dict]
    _cur: int
    _bbg: BloombergService

    if TYPE_CHECKING:
        def _update_dot(self, row: Optional[int], s: Strategy) -> None: ...

    # ── Bloomberg status ──────────────────────────────────────────────────────
    def _on_bbg_status(self, connected: bool, message: str) -> None:
        if connected:
            self._bbg_lbl.setText("Bloomberg: ⬤ connecté")
            self._bbg_lbl.setStyleSheet(theme.BBG_OK)
            self._subscribe_all_tickers()
            self._bbg.resubscribe_all()
        else:
            self._bbg_lbl.setText("Bloomberg: ⬤ déconnecté")
            self._bbg_lbl.setStyleSheet(theme.BBG_ERR)

    def _subscribe_all_tickers(self) -> None:
        """(Re)subscribe all tickers across every page."""
        for page in self._pages:
            for s in page["strategies"]:
                for t in s.get_all_tickers():
                    self._bbg.subscribe(t)
                    fut = self._future_ticker_from_option(normalize_ticker(t))
                    if fut:
                        self._bbg.subscribe(fut)

    # ── Bloomberg price updates ───────────────────────────────────────────────
    def _on_price_updated(self, ticker: str, last: float, bid: float, ask: float) -> None:
        ticker_n = normalize_ticker(ticker)
        for page_index, page in enumerate(self._pages):
            for row, s in enumerate(page["strategies"]):
                visible_row = row if page_index == self._cur else None
                option_tickers = {normalize_ticker(t) for t in s.get_all_tickers()}
                if ticker_n in option_tickers:
                    strategy_changed = False
                    for leg in s.legs:
                        if normalize_ticker(leg.ticker or "") == ticker_n:
                            leg.update_price(last, bid, ask)
                            strategy_changed = True
                    if strategy_changed:
                        s.recalculate_market_analytics()
                    if visible_row is not None:
                        self._refresh_price_cell(visible_row, s.calculate_strategy_price())
                        self._refresh_greeks_cells(visible_row, s)
                    self._update_dot(visible_row, s)
                else:
                    # Check if this is the underlying future for this strategy
                    for opt_t in s.get_all_tickers():
                        fut = self._future_ticker_from_option(normalize_ticker(opt_t))
                        if fut and normalize_ticker(fut) == ticker_n:
                            price = last if last >= 0 else (
                                (bid + ask) / 2 if bid >= 0 and ask >= 0 else None
                            )
                            if price is not None:
                                s.future_price = price
                                s.recalculate_market_analytics()
                                if visible_row is not None:
                                    self._refresh_greeks_cells(visible_row, s)
                            break

    def _refresh_price_cell(self, row: int, price: Optional[float]) -> None:
        item = self._table.item(row, C_PRICE)
        if item is None:
            return
        if price is None:
            item.setText("--")
            item.setForeground(QColor("#888888"))
        elif price >= 0:
            item.setText(f"{price:.4f}")
            item.setForeground(QColor("#008800"))
        else:
            item.setText(f"{price:.4f}")
            item.setForeground(QColor("#cc2200"))

    def _refresh_greeks_cells(self, row: int, s: Strategy) -> None:
        """Update the 5 analytic cells for the given row."""
        def _set(col: int, val: Optional[float], fmt: str,
                 signed_color: bool = False) -> None:
            item = self._table.item(row, col)
            if item is None:
                return
            if val is None or (isinstance(val, float) and math.isnan(val)):
                item.setText("--")
                item.setForeground(QColor("#888888"))
                return
            item.setText(fmt.format(val))
            if signed_color:
                item.setForeground(QColor("#006600") if val >= 0 else QColor("#cc2200"))
            else:
                item.setForeground(QColor("#333333"))

        _set(C_DELTA, s.get_total_delta(), "{:+.4f}", signed_color=True)
        _set(C_GAMMA, s.get_total_gamma(), "{:+.5f}")
        _set(C_THETA, s.get_total_theta(), "{:+.4f}", signed_color=True)
        _set(C_IV,    s.get_average_ivol(), "{:.2%}")
        _set(C_FUT,   s.future_price,       "{:.4f}")

    # ── static helpers ────────────────────────────────────────────────────────
    @staticmethod
    def _future_ticker_from_option(option_ticker: str) -> Optional[str]:
        """Derive the underlying future ticker from a Bloomberg option ticker.

        Example: "SFRH6C 98.0 COMDTY" → "SFRH6 COMDTY"
        """
        m = re.match(r'^([A-Z]+[FGHJKMNQUVXZ]\d+)[CP]\s', option_ticker.strip().upper())
        return f"{m.group(1)} COMDTY" if m else None
