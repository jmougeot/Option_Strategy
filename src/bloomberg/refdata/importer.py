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
    vol_model: str = "sabr",
) -> Tuple[List[Option], FutureData, List[str], Any]:
    """
    Importe un ensemble d'options depuis Bloomberg et retourne des objets Option.
    Returns:
        Tuple (liste d'objets Option, FutureData, warnings, SABRCalibration or None)
    """    
    # 1. Construction des tickers (mois sélectionné uniquement)
    builder = TickerBuilder(suffix, roll_expiries)

    builder._build_underlying(underlying, months[0], years)

    if brut_code is None:
        builder.build_from_standard(underlying, months, years, strikes)
    else:
        builder.build_from_brut(brut_code, strikes)

    # 1b. Builder séparé pour les expirations voisines (surface SVI)
    surface_builder: Optional[TickerBuilder] = None
    if brut_code is None and vol_model in ("svi", "both"):
        from bloomberg.util.expiry import build_surface_months
        selected = {(m, y) for m in months for y in years}
        extra_pairs = [
            (m, yr) for y in years
            for m, yr in build_surface_months(months[0], y)
            if (m, yr) not in selected
        ]
        if extra_pairs:
            surface_builder = TickerBuilder(suffix, None)
            surface_builder._build_underlying(underlying, months[0], years)
            for m, yr in extra_pairs:
                for strike in strikes:
                    for opt_type in ["call", "put"]:
                        surface_builder.add_option(underlying, m, yr, strike, opt_type)

    # 2. Fetch des données
    future_data = FutureData(None, None)
    options: List[Option] = []
    fetch_warnings: List[str] = []
    sabr_calibration: Any = None
    
    try:
        fetcher = PremiumFetcher(builder)
        fetcher.fetch_all()
        fetch_warnings = fetcher.warnings
        
        # 3. Traitement des options (mois sélectionné)
        processor = OptionProcessor(builder, fetcher, mixture, default_position)
        options = processor.process_all()
        future_data = fetcher.future_data
        time_to_expiry = _time_to_expiry_from_future_data(future_data)

        # 3b. Fetch des expirations voisines pour la surface SVI
        surface_options: List[Option] = []
        if surface_builder is not None:
            try:
                sf = PremiumFetcher(surface_builder)
                sf.fetch_all()
                sp = OptionProcessor(surface_builder, sf, mixture, default_position)
                surface_options = sp.process_all()
            except Exception as exc:
                print(f"  ⚠ Surface fetch échoué: {exc}")
        
        # 3.5. Calibration : SABR/SVI sur le mois sélectionné,
        #       surface SVI sur toutes les expirations
        if options and recalibrate:
            all_for_surface = options + surface_options
            sabr_calibration = Bachelier.compute_volatility(
                all_for_surface,
                time_to_expiry=time_to_expiry,
                future_price=future_data.underlying_price,
                vol_model=vol_model,
            )
        
        if options:
            for option in options:
                option._calcul_all_surface()
        
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()

    # Seules les options du mois sélectionné sont retournées
    return options, future_data, fetch_warnings, sabr_calibration
