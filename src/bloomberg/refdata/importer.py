"""
Bloomberg Data Importer for Options Strategy App
Importe les données d'options depuis Bloomberg et les convertit en objets Option.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple
import numpy as np
from option.option_class import Option
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
PositionType = Literal["long", "short"]
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
    use_sabr: bool = True,
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
        
        # 3.5. Calculer la volatilité Bachelier + SABR pour TOUTES les options
        if options:
            if use_sabr:
                sabr_calibration = Bachelier.compute_volatility(options, time_to_expiry=0.25, future_price=future_data.underlying_price)
            else:
                # Bachelier IV sans calibration SABR
                F = future_data.underlying_price
                T = 0.25
                if F:
                    for opt in options:
                        opt.underlying_price = F
                        if opt.status and opt.premium > 0:
                            opt.implied_volatility = Bachelier(F, opt.strike, 0.0, T, opt.is_call(), opt.premium).implied_vol()
                        opt.delta = Bachelier(F, opt.strike, opt.implied_volatility or 0.0, T, opt.is_call()).delta()
                        opt.gamma = Bachelier(F, opt.strike, opt.implied_volatility or 0.0, T, opt.is_call()).gamma()
                        opt.theta = Bachelier(F, opt.strike, opt.implied_volatility or 0.0, T, opt.is_call()).theta()

            for option in options:
                option._calcul_all_surface()
        
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()


    return options, future_data, fetch_warnings, sabr_calibration
