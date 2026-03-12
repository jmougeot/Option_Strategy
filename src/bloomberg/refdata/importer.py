"""
Bloomberg Data Importer for Options Strategy App
Importe les données d'options depuis Bloomberg et les convertit en objets Option.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Tuple
import numpy as np
from option.option_class import Option, PositionType
from option.bachelier import Bachelier
from app.data_types import FutureData
from bloomberg.refdata.processor import OptionProcessor
from bloomberg.ticker_builder import TickerBuilder
from bloomberg.refdata.premium import PremiumFetcher


# ============================================================================
# TYPES ET ALIASES
# ============================================================================

TickerMeta = Dict[str, Any]
PremiumKey = Tuple[float, str, str, int]
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


def _parse_expiry_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]

    for fmt in ("%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _time_to_expiry_from_future_data(future_data: FutureData, default: float = 0.25) -> float:
    expiry_date = _parse_expiry_date(future_data.last_tradable_date)
    if expiry_date is None:
        return default

    days_to_expiry = (expiry_date - date.today()).days
    return max(days_to_expiry, 1) / 365.0

# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def import_options(
    mixture: Tuple[np.ndarray, np.ndarray, float],
    underlying: str,
    months: List[str],
    years: List[int],
    strikes: List[float],
    roll_expiries: Optional[List[RollExpiry]] = None,
    brut_code: Optional[List[str]] = None,
    suffix: str = "Comdty",
    default_position: PositionType = "long",
    recalibrate: bool = True,
) -> Tuple[List[Option], FutureData, List[str], Any]:
    """
    Importe un ensemble d'options depuis Bloomberg et retourne des objets Option.
    Returns:
        Tuple (liste d'objets Option, FutureData, warnings, SABRCalibration or None)
    """    
    # 1. Construction des tickers
    builder = TickerBuilder(suffix, roll_expiries)

    builder._build_underlying(underlying, months[0], years)

    if brut_code is None:
        builder.build_from_standard(underlying, months, years, strikes)
    else:
        builder.build_from_brut(brut_code, strikes)


    # 2. Fetch des données
    future_data = FutureData(None, None)
    options: List[Option] = []
    fetch_warnings: List[str] = []
    sabr_calibration: Any = None
    
    try:
        fetcher = PremiumFetcher(builder)
        fetcher.fetch_all()
        fetch_warnings = fetcher.warnings
        
        # 3. Traitement des options
        processor = OptionProcessor(builder, fetcher, mixture, default_position)
        options = processor.process_all()
        future_data = fetcher.future_data
        time_to_expiry = _time_to_expiry_from_future_data(future_data)
        
        # 3.5. Calculer la volatilité Bachelier + SABR (si demandé)
        if options and recalibrate:
            sabr_calibration = Bachelier.compute_volatility(
                options,
                time_to_expiry=time_to_expiry,
                future_price=future_data.underlying_price,
            )
        
        if options:
            for option in options:
                option._calcul_all_surface()
        
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()


    return options, future_data, fetch_warnings, sabr_calibration
