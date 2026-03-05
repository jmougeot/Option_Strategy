"""
Bloomberg Ticker Builder
=========================
Construction et parsing des tickers Bloomberg pour options sur futures.

Fonctions standalone :
    build_option_ticker(...)       → ticker standard
    build_option_ticker_brut(...)  → ticker à partir d'un code brut
    parse_brut_code(brut_code)     → dict {underlying, month, year, option_type}

Classe :
    TickerBuilder      → gère une grille complète de tickers (main + roll)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Literal, Optional, Tuple, cast

# ── types ──────────────────────────────────────────────────────────────────────
TickerMeta     = Dict[str, Any]
OptionTypeChar = Literal["C", "P"]
RollExpiry     = Tuple[str, int]
MonthCode      = Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]
VALID_MONTHS   = {"F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"}

# ── mappings ────────────────────────────────────────────────────────────────────
# Mois option → mois du future de référence trimestriel
UNDERLYING_REF: Dict[str, str] = {
    "F": "H", "G": "H", "H": "H",
    "J": "M", "K": "M", "M": "M",
    "N": "U", "Q": "U", "U": "U",
    "V": "Z", "X": "Z", "Z": "Z",
}

# Suffixe produit pour les mid-curves
MID_CURVE: Dict[str, str] = {
    "R": "ER",
    "N": "SFI",
    "Q": "SFR",
}


# ── standalone helpers ──────────────────────────────────────────────────────────
def parse_brut_code(brut_code: str) -> dict:
    """Parse un code brut Bloomberg pour extraire les métadonnées.

    Format : ``[UNDERLYING][MONTH][YEAR][C/P][SUFFIX?]``  ex: ``RXW F 26 C 2``
    Returns dict avec ``underlying``, ``month``, ``year``, ``option_type``.
    """
    code = brut_code.upper().strip()
    match = re.match(r'^([A-Z]+)([FGHJKMNQUVXZ])(\d{1,2})([CP])(\d*)$', code)
    if match:
        return {
            "underlying":  match.group(1),
            "month":       match.group(2),
            "year":        int(match.group(3)),
            "option_type": "call" if match.group(4) == "C" else "put",
        }

    # Fallback : ancien parsing
    if "C" in code:
        option_type, code = "call", code.replace("C", "", 1)
    elif "P" in code:
        option_type, code = "put", code.replace("P", "", 1)
    else:
        option_type = "call"

    m = re.search(r'(\d{1,2})', code)
    if m:
        year, code = int(m.group(1)), code[:m.start()]
    else:
        year = 6

    month = underlying = ""
    if code and code[-1].upper() in VALID_MONTHS:
        month, underlying = code[-1].upper(), code[:-1]
    else:
        underlying = code

    return {"underlying": underlying, "month": month, "year": year, "option_type": option_type}


def build_option_ticker(
    underlying: str,
    expiry_month: MonthCode,
    expiry_year: int,
    option_type: OptionTypeChar,
    strike: float,
    suffix: Optional[str] = None,
) -> str:
    """Construit un ticker Bloomberg pour option sur future.

    Format : ``[UNDERLYING][MONTH][YEAR][TYPE] [STRIKE] [SUFFIX]``
    """
    strike_r = round(strike, 5)
    t = f"{underlying.upper()}{expiry_month}{expiry_year}{option_type} {strike_r}"
    return f"{t} {suffix}" if suffix else t


def build_option_ticker_brut(brut_code: str, strike: float, suffix: str) -> str:
    """Construit un ticker à partir d'un code brut Bloomberg."""
    return f"{brut_code} {round(strike, 5)} {suffix}"


# ── TickerBuilder ───────────────────────────────────────────────────────────────
class TickerBuilder:
    """Construit la grille de tickers (main + roll) pour un import Bloomberg."""

    def __init__(self, suffix: str, roll_expiries: Optional[List[RollExpiry]] = None) -> None:
        self.suffix = suffix
        self.roll_expiries = roll_expiries
        self.main_tickers:   List[str]           = []
        self.main_metadata:  Dict[str, TickerMeta] = {}
        self.roll_tickers:   List[str]           = []
        self.roll_metadata:  Dict[str, TickerMeta] = {}
        self.underlying_ticker: str = ""

    def _build_underlying(self, underlying: str, months: str, years: List[int]) -> None:
        if underlying[0] == "0":
            year, month, underlying = years[0] + 1, UNDERLYING_REF[months[0]], MID_CURVE[underlying[1]]
        elif underlying[0] == "2":
            year, month, underlying = years[0] + 2, UNDERLYING_REF[months[0]], MID_CURVE[underlying[1]]
        else:
            year, month = years[0], UNDERLYING_REF[months[0]]
        self.underlying_ticker = f"{underlying}{month}{year} {self.suffix}"

    def _add_roll_tickers(self, underlying: str, strike: float,
                          option_type: str, opt_char: OptionTypeChar) -> None:
        for r_month, r_year in (self.roll_expiries or []):
            roll_code   = f"{underlying}{r_month}{r_year}{opt_char}"
            roll_ticker = build_option_ticker_brut(roll_code, strike, self.suffix)
            if roll_ticker not in self.roll_metadata:
                self.roll_tickers.append(roll_ticker)
                self.roll_metadata[roll_ticker] = {
                    "underlying": underlying, "strike": strike,
                    "option_type": option_type, "month": r_month, "year": r_year,
                }

    def add_option(self, underlying: str, month: str, year: int,
                   strike: float, option_type: str,
                   use_brut: bool = False, brut_code: Optional[str] = None) -> None:
        opt_char: OptionTypeChar = "C" if option_type == "call" else "P"
        if use_brut and brut_code:
            ticker = build_option_ticker_brut(brut_code, strike, self.suffix)
        else:
            ticker = build_option_ticker(
                underlying, cast(MonthCode, month), year, opt_char, strike, self.suffix
            )
        self.main_tickers.append(ticker)
        self.main_metadata[ticker] = {
            "underlying": underlying, "strike": strike,
            "option_type": option_type, "month": month, "year": year,
        }
        self._add_roll_tickers(underlying, strike, option_type, opt_char)

    def build_from_standard(self, underlying: str, months: List[str],
                            years: List[int], strikes: List[float]) -> None:
        for year in years:
            for month in months:
                for strike in strikes:
                    for opt_type in ["call", "put"]:
                        self.add_option(underlying, month, year, strike, opt_type)

    def build_from_brut(self, brut_codes: List[str], strikes: List[float]) -> None:
        for code in brut_codes:
            meta = parse_brut_code(code)
            for strike in strikes:
                self.add_option(
                    meta["underlying"], meta["month"], meta["year"],
                    strike, meta["option_type"], use_brut=True, brut_code=code,
                )
