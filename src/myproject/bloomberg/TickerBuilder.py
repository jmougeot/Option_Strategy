"""
Bloomberg Ticker Builder
"""

from typing import Dict, Tuple, Optional, Any, Literal, List, cast
import re 

# =========================================
# Type et Dict 
# =========================================

TickerMeta = Dict[str, Any]
OptionTypeChar = Literal["C", "P"]
RollExpiry = Tuple[str, int] 

UNDERLYING_REF = {
    "F" : "H",
    "G" : "H",
    "H" : "H",
    "J":"M",
    "K":"M",
    "M":"M",
    "N":"U",
    "Q":"U",
    "U":"U",
    "V":"Z",
    "X":"Z",
    "Z":"Z"}

MID_CURVE = {
    "R":"ER",
    "N":"SFI",
    "Q":"SFR"}

# Type pour les mois valides
MonthCode = Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]
VALID_MONTHS = {"F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"}


def parse_brut_code(brut_code: str) -> dict:
    """
    Parse un code brut Bloomberg pour extraire les métadonnées.
    Format: [UNDERLYING][MONTH][YEAR][C/P][SUFFIX?]
    Returns:
        Dict avec underlying, month, year, option_type
    """
    code = brut_code.upper().strip()
    
    # Pattern: lettres + mois (une lettre valide) + année (1-2 chiffres) + C/P + suffix optionnel
    # Ex: RXW F 26 C 2 ou ER H 6 C
    pattern = r'^([A-Z]+)([FGHJKMNQUVXZ])(\d{1,2})([CP])(\d*)$'
    match = re.match(pattern, code)
    
    if match:
        underlying = match.group(1)
        month = match.group(2)
        year = int(match.group(3))
        option_type = "call" if match.group(4) == "C" else "put"
    else:
        # Fallback: ancien parsing
        if "C" in code:
            option_type = "call"
            code_without_type = code.replace("C", "", 1)
        elif "P" in code:
            option_type = "put"
            code_without_type = code.replace("P", "", 1)
        else:
            option_type = "call"
            code_without_type = code
        
        match_year = re.search(r'(\d{1,2})', code_without_type)
        if match_year:
            year = int(match_year.group(1))
            code_without_year = code_without_type[:match_year.start()]
        else:
            year = 6
            code_without_year = code_without_type
        
        month = ""
        underlying = code_without_year
        if code_without_year:
            last_char = code_without_year[-1].upper()
            if last_char in VALID_MONTHS:
                month = last_char
                underlying = code_without_year[:-1]
    
    return {
        "underlying": underlying,
        "month": month,
        "year": year,
        "option_type": option_type,
    }


def build_option_ticker(
    underlying: str,
    expiry_month: Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"],
    expiry_year: int,
    option_type: Literal["C", "P"],
    strike: float,
    suffix: Optional[str] = None,
) -> str:
    """
    Construit un ticker Bloomberg pour options EURIBOR.
    Format Bloomberg: [UNDERLYING][MONTH][YEAR][TYPE] [STRIKE] [SUFFIX]
    """

    strike_rounded = round(strike, 5)  # 5 décimales suffisent pour les options
    
    ticker = f"{underlying.upper()}{expiry_month}{expiry_year}{option_type} {strike_rounded}"

    if suffix:
        ticker = f"{ticker} {suffix}"

    return ticker

def build_option_ticker_brut(
        brut_code:str,
        strike: float,
        suffix: str
    ) -> str :
    """
    Construit un ticket avec le code brut
    """
    # Arrondir le strike pour éviter les problèmes de précision flottante
    strike_rounded = round(strike, 5)
    ticker=f"{brut_code} {strike_rounded} {suffix}"
    
    return ticker



class TickerBuilder:
    """Construit les tickers et leurs métadonnées pour l'import."""
    
    def __init__(self, suffix: str, roll_expiries: Optional[List[RollExpiry]] = None):
        self.suffix = suffix
        self.roll_expiries = roll_expiries
        self.main_tickers: List[str] = []
        self.main_metadata: Dict[str, TickerMeta] = {}
        self.roll_tickers: List[str] = []
        self.roll_metadata: Dict[str, TickerMeta] = {}
        self.underlying_ticker: str =""

    def _build_underlying(self, underlying:str, months:str, years:List[int]):
        if underlying[0] == "0":
            year = years[0] + 1
            month=UNDERLYING_REF[months[0]]
            underlying = MID_CURVE[underlying[1]] 

        elif underlying[0] == "2":
            year = years[0] + 2
            month=UNDERLYING_REF[months[0]]
            underlying = MID_CURVE[underlying[1]]

        else: 
            month=UNDERLYING_REF[months[0]]
            year= years[0]

        self.underlying_ticker = f"{underlying}{month}{year} {self.suffix}"

    
    def _add_roll_tickers(self, underlying: str, strike: float, 
                          option_type: str, opt_char: OptionTypeChar):
        """Ajoute les tickers de roll pour une option."""
        expiries = self.roll_expiries or []
        
        for r_month, r_year in expiries:
            roll_code = f"{underlying}{r_month}{r_year}{opt_char}"
            roll_ticker = build_option_ticker_brut(roll_code, strike, self.suffix)
            
            if roll_ticker not in self.roll_metadata:
                self.roll_tickers.append(roll_ticker)
                self.roll_metadata[roll_ticker] = {
                    "underlying": underlying, "strike": strike,
                    "option_type": option_type, "month": r_month, "year": r_year
                }


    # Ajoute une option avec son roll dans le Builder
    def add_option(self, underlying: str, month: str, year: int, 
                   strike: float, option_type: str, 
                   use_brut: bool = False, brut_code: Optional[str] = None):
        """Ajoute une option et ses tickers de roll."""
        opt_char: OptionTypeChar = "C" if option_type == "call" else "P"
        
        # Ticker principal
        if use_brut and brut_code:
            ticker = build_option_ticker_brut(brut_code, strike, self.suffix)
        else:
            ticker = build_option_ticker(
                underlying, cast(MonthCode, month), year, opt_char, strike, self.suffix
            )
        
        self.main_tickers.append(ticker)
        self.main_metadata[ticker] = {
            "underlying": underlying, "strike": strike,
            "option_type": option_type, "month": month, "year": year
        }
        self._add_roll_tickers(underlying, strike, option_type, opt_char)
    

    
    # Construit les tickers en mode standard.
    def build_from_standard(self, underlying: str, months: List[str], 
                            years: List[int], strikes: List[float]):
        """Construit les tickers en mode standard."""
        for year in years:
            for month in months:
                for strike in strikes:
                    for opt_type in ["call", "put"]:
                        self.add_option(underlying, month, year, strike, opt_type)
    

    # Construit les tickers à partir de codes bruts.
    def build_from_brut(self, brut_codes: List[str], strikes: List[float]):
        """Construit les tickers à partir de codes bruts."""
        for code in brut_codes:
            meta = parse_brut_code(code)
            for strike in strikes:
                self.add_option(
                    meta["underlying"], meta["month"], meta["year"],
                    strike, meta["option_type"], use_brut=True, brut_code=code
                )

