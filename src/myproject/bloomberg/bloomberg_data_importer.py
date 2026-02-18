"""
Bloomberg Data Importer for Options Strategy App
=================================================
Importe les données d'options depuis Bloomberg et les convertit en objets Option.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, cast
from git import Reference
import numpy as np

from myproject.bloomberg.expiry_utils import MONTH_NAMES
from myproject.bloomberg.fetcher_batch import fetch_options_batch, extract_best_values
from myproject.bloomberg.ticker_builder import (
    build_option_ticker, build_option_ticker_brut, parse_brut_code, MonthCode)
from myproject.bloomberg.bloomber_to_opt import create_option_from_bloomberg
from myproject.option.option_class import Option
from myproject.app.data_types import FutureData


# ============================================================================
# TYPES ET ALIASES
# ============================================================================

TickerMeta = Dict[str, Any]
PremiumKey = Tuple[float, str, str, int]  # (strike, option_type, month, year)
OptionTypeChar = Literal["C", "P"]
PositionType = Literal["long", "short"]
RollExpiry = Tuple[str, int]  # (month, year)


# ============================================================================
# CLASSES INTERNES
# ============================================================================

class TickerBuilder:
    """Construit les tickers et leurs métadonnées pour l'import."""
    
    def __init__(self, suffix: str, roll_expiries: Optional[List[RollExpiry]] = None):
        self.suffix = suffix
        self.roll_expiries = roll_expiries
        
        # Collections
        self.main_tickers: List[str] = []
        self.main_metadata: Dict[str, TickerMeta] = {}
        self.roll_tickers: List[str] = []
        self.roll_metadata: Dict[str, TickerMeta] = {}
        self.underlying_ticker: str =""

    def _build_underlying(self, underlying, months, years):
        month=months[0]
        year=years[0]
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
        
        # Tickers de roll
        self._add_roll_tickers(underlying, strike, option_type, opt_char)
    
    def build_from_standard(self, underlying: str, months: List[str], 
                            years: List[int], strikes: List[float]):
        """Construit les tickers en mode standard."""
        for year in years:
            for month in months:
                for strike in strikes:
                    for opt_type in ["call", "put"]:
                        self.add_option(underlying, month, year, strike, opt_type)
    
    def build_from_brut(self, brut_codes: List[str], strikes: List[float]):
        """Construit les tickers à partir de codes bruts."""
        for code in brut_codes:
            meta = parse_brut_code(code)
            for strike in strikes:
                self.add_option(
                    meta["underlying"], meta["month"], meta["year"],
                    strike, meta["option_type"], use_brut=True, brut_code=code
                )


class PremiumFetcher:
    """Récupère les premiums depuis Bloomberg en batch."""
    
    def __init__(self, builder: TickerBuilder):
        self.builder = builder
        self.main_data: Dict[str, Any] = {}
        self.roll_premiums: Dict[PremiumKey, float] = {}
        self.future_data: FutureData = FutureData(None, None)
        self.warnings: List[str] = []
    
    def fetch_all(self):
        """Fetch toutes les données en batch."""
        self.main_data, self.future_data, warnings = fetch_options_batch(
            self.builder.main_tickers, 
            underlyings=self.builder.underlying_ticker
        )
        self.warnings.extend(warnings)
        
        if self.builder.roll_tickers:
            roll_data, _, roll_warnings = fetch_options_batch(self.builder.roll_tickers, use_overrides=True)
            self.warnings.extend(roll_warnings)
            self._extract_premiums(roll_data, self.builder.roll_metadata)
    
    def _extract_premiums(self, batch_data: Dict, metadata: Dict[str, TickerMeta]):
        """Extrait les premiums d'un batch de données."""
        for ticker, meta in metadata.items():
            raw = batch_data.get(ticker, {})
            if raw and not all(v is None for v in raw.values()):
                premium = extract_best_values(raw).get("premium")
                if premium is not None and premium > 0:
                    key: PremiumKey = (meta["strike"], meta["option_type"], 
                                       meta["month"], meta["year"])
                    self.roll_premiums[key] = premium


class OptionProcessor:
    """Traite les données Bloomberg pour créer les objets Option."""
    
    def __init__(self, builder: TickerBuilder, fetcher: PremiumFetcher,
                 mixture: Tuple[np.ndarray, np.ndarray, float],
                 default_position: PositionType):
        self.builder = builder
        self.fetcher = fetcher
        self.mixture = mixture
        self.default_position: PositionType = default_position
    
    def _compute_roll(self, option: Option, meta: TickerMeta):
        """Calcule le roll pour une option."""
        if option.premium is None or option.premium == 0:
            return
        
        roll_expiries = self.builder.roll_expiries or []
        if not roll_expiries:
            return
        
        try:
            # Calculer le roll pour chaque échéance fournie
            rolls: List[float] = []
            rolls_detail: Dict[str, float] = {}
            
            for r_month, r_year in roll_expiries:
                roll_key: PremiumKey = (meta["strike"], meta["option_type"], r_month, r_year)
                roll_premium = self.fetcher.roll_premiums.get(roll_key)
                if roll_premium is not None:
                    roll_value = roll_premium - option.premium
                    rolls.append(roll_value)
                    # Label comme "H6", "M6", etc.
                    label = f"{r_month}{r_year}"
                    rolls_detail[label] = roll_value
            
            if rolls:
                # Roll = série complète dans l'ordre des expiries fournies par l'utilisateur
                option.roll = rolls
                option.rolls_detail = rolls_detail
                
        except Exception as e:
            print(f"  ⚠️ Erreur calcul roll: {e}")
    
    def process_all(self) -> List[Option]:
        """Traite toutes les options et retourne la liste."""
        options: List[Option] = []
        
        # Collecter les périodes uniques
        periods = sorted({(m["year"], m["month"]) for m in self.builder.main_metadata.values()})
        
        for year, month in periods:
            for ticker in self.builder.main_tickers:
                meta = self.builder.main_metadata[ticker]
                if meta["month"] != month or meta["year"] != year:
                    continue
                
                option = self._process_single(ticker, meta)
                if option:
                    options.append(option)
        
        return options
    
    def _process_single(self, ticker: str, meta: TickerMeta) -> Optional[Option]:
        """Traite une seule option."""
        try:
            raw_data = self.fetcher.main_data.get(ticker, {})
            if not raw_data or all(v is None for v in raw_data.values()):
                return None
            
            extracted = extract_best_values(raw_data)
            option = create_option_from_bloomberg(
                ticker=ticker,
                underlying=meta["underlying"],
                strike=meta["strike"],
                month=meta["month"],
                year=meta["year"],
                option_type_str=meta["option_type"],
                bloomberg_data=extracted,
                position=self.default_position,
                mixture=self.mixture,
            )
            
            self._compute_roll(option, meta)
            
            if option.strike > 0:
                self._print_option(option)
                return option
        except Exception:
            pass
        return None
    
    @staticmethod
    def _print_option(option: Option):
        """Affiche le résumé d'une option."""
        sym = "C" if option.option_type == "call" else "P"
        roll = f", Roll0={option.roll[0]:.4f}" if option.roll else ""
        print(f"✓ {sym} {option.strike}: Premium={option.premium}, "
              f"Delta={option.delta}, IV={option.implied_volatility}{roll}")


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
) -> Tuple[List[Option], FutureData, List[str]]:
    """
    Importe un ensemble d'options depuis Bloomberg et retourne des objets Option.
    Returns:
        Tuple (liste d'objets Option, FutureData avec prix et date, warnings)
    """
    print("\n🔨 Construction des tickers...")
    
    # 1. Construction des tickers
    builder = TickerBuilder(suffix, roll_expiries)

    builder._build_underlying(underlying, months, years)

    if brut_code is None:
        builder.build_from_standard(underlying, months, years, strikes)
    else:
        builder.build_from_brut(brut_code, strikes)


    # 2. Fetch des données
    future_data = FutureData(None, None)
    options: List[Option] = []
    fetch_warnings: List[str] = []
    
    try:
        fetcher = PremiumFetcher(builder)
        fetcher.fetch_all()
        fetch_warnings = fetcher.warnings
        
        # 3. Traitement des options
        processor = OptionProcessor(builder, fetcher, mixture, default_position)
        options = processor.process_all()
        future_data = fetcher.future_data
        
        # 4. Calculer les prix intra-vie pour toutes les options (avec Bachelier)
        if options:
            # Estimer le temps jusqu'à expiration (en années)
            time_to_expiry = 0.25  # ~3 mois par défaut
            for option in options:
                option.calculate_all_intra_life(all_options=options, time_to_expiry=time_to_expiry)
            print(f"  • Prix intra-vie calculés pour {len(options)} options")
        
        print(f"📊 Future: price={future_data.underlying_price}, last_trade={future_data.last_tradable_date}")
        
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()


    return options, future_data, fetch_warnings
