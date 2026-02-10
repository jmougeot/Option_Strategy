"""
SFR (SOFR) Option Ticker Builder
=================================
Construction des tickers Bloomberg pour options SOFR.

Format Bloomberg:
    SFR{MONTH}{YEAR}{C/P} {STRIKE} Comdty

Exemples:
    SFRH5C 96.00 Comdty  → Call SOFR Mars 2025, strike 96.00
    SFRH5P 95.50 Comdty  → Put  SOFR Mars 2025, strike 95.50
"""

from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

from src.backtesting.config import SFRConfig


OptionType = Literal["C", "P"]


@dataclass
class TickerMeta:
    """Métadonnées associées à un ticker Bloomberg."""
    ticker: str
    underlying: str
    expiry_month: str
    expiry_year: int
    option_type: str     # "call" ou "put"
    strike: float
    suffix: str

    @property
    def type_char(self) -> OptionType:
        return "C" if self.option_type == "call" else "P"

    @property
    def display_name(self) -> str:
        sym = self.type_char
        return f"SFR {self.expiry_month}{self.expiry_year} {sym} {self.strike:.2f}"


class SFRTickerBuilder:
    """
    Construit la liste des tickers Bloomberg pour les options SFR
    (calls et puts) sur une plage de strikes.

    Usage:
        builder = SFRTickerBuilder(config)
        builder.build()
        print(builder.call_tickers)
        print(builder.put_tickers)
    """

    def __init__(self, config: SFRConfig):
        self.config = config
        self.call_tickers: List[str] = []
        self.put_tickers: List[str] = []
        self.all_tickers: List[str] = []
        self.metadata: Dict[str, TickerMeta] = {}
        self.underlying_ticker: str = ""

    def _build_ticker(self, strike: float, opt_char: OptionType) -> str:
        """
        Construit un ticker Bloomberg pour une option SFR.

        Args:
            strike: Prix d'exercice
            opt_char: 'C' pour Call, 'P' pour Put

        Returns:
            Ticker formaté, ex: "SFRH5C 96.00 Comdty"
        """
        c = self.config
        # Format: SFR + H + 5 + C + " " + 96.00 + " " + Comdty
        strike_fmt = f"{strike:.2f}"
        return f"{c.underlying}{c.expiry_month}{c.expiry_year}{opt_char} {strike_fmt} {c.suffix}"

    def _build_underlying_ticker(self) -> str:
        """
        Construit le ticker du sous-jacent (future SOFR).

        Returns:
            ex: "SFRH5 Comdty"
        """
        c = self.config
        return f"{c.underlying}{c.expiry_month}{c.expiry_year} {c.suffix}"

    def build(self) -> "SFRTickerBuilder":
        """
        Construit tous les tickers calls et puts pour chaque strike.
        Retourne self pour permettre le chainage.
        """
        self.call_tickers.clear()
        self.put_tickers.clear()
        self.all_tickers.clear()
        self.metadata.clear()

        self.underlying_ticker = self._build_underlying_ticker()

        for strike in self.config.strikes:
            for opt_type_str, opt_char in [("call", "C"), ("put", "P")]:
                ticker = self._build_ticker(strike, opt_char)  # type: ignore

                meta = TickerMeta(
                    ticker=ticker,
                    underlying=self.config.underlying,
                    expiry_month=self.config.expiry_month,
                    expiry_year=self.config.expiry_year,
                    option_type=opt_type_str,
                    strike=strike,
                    suffix=self.config.suffix,
                )
                self.metadata[ticker] = meta
                self.all_tickers.append(ticker)

                if opt_char == "C":
                    self.call_tickers.append(ticker)
                else:
                    self.put_tickers.append(ticker)

        n_calls = len(self.call_tickers)
        n_puts = len(self.put_tickers)
        print(f"[TickerBuilder] {n_calls} calls + {n_puts} puts = "
              f"{len(self.all_tickers)} tickers construits "
              f"(strikes {self.config.strike_min}–{self.config.strike_max}, "
              f"step={self.config.strike_step})")

        return self

    def get_tickers_by_type(self, option_type: str) -> List[str]:
        """Retourne les tickers filtrés par type ('call' ou 'put')."""
        return [t for t, m in self.metadata.items() if m.option_type == option_type]

    def get_strike_for_ticker(self, ticker: str) -> float:
        """Retourne le strike associé à un ticker."""
        return self.metadata[ticker].strike
