"""
Bloomberg Data Importer for Options Strategy App
=================================================
Importe les données d'options depuis Bloomberg et les convertit en objets Option.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, cast
import numpy as np

from myproject.bloomberg.fetcher_batch import fetch_options_batch, extract_best_values
from myproject.bloomberg.ticker_builder import (build_option_ticker, build_option_ticker_brut, parse_brut_code, MonthCode)
from myproject.bloomberg.bloomber_to_opt import create_option_from_bloomberg
from myproject.option.option_class import Option
from myproject.option.bachelier import bachelier_implied_vol, bachelier_price
from myproject.app.data_types import FutureData


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



# Class por créer des options depuis les données blommberg : calcul de roll 
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
            has_warning = raw_data.get("_warning", False)
            
            if not has_warning:
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
                warning=has_warning,
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
        warn = " ⚠️" if not option.status else ""
        print(f"✓ {sym} {option.strike}: Premium={option.premium}, "
              f"Delta={option.delta}, IV={option.implied_volatility}{roll}{warn}")


# ============================================================================
# CALCUL DE LA VOLATILITÉ BACHELIER POUR TOUTES LES OPTIONS
# ============================================================================

def _compute_bachelier_volatility(options: List[Option], time_to_expiry: float = 0.25, future_price: Optional[float] = None) -> None:
    """
    Calcule la volatilité Bachelier pour TOUTES les options.
    """
    options.sort(key=lambda x: (x.strike, x.option_type))

    F = future_price or FutureData.underlying_price
    if not F:
        print("[_compute_bachelier_volatility] Pas de prix future disponible, abandon.")
        return
    print(f"[_compute_bachelier_volatility] Appel avec F={F}, {len(options)} options")
    for o in options:
        if not o.status or o.premium <= 0:
            sym = "C" if o.is_call() else "P"
            print(f"  [DEBUG] {sym} K={o.strike} | premium={o.premium} | status={o.status} | IV_entree={o.implied_volatility:.4f}")
    datas: List[Tuple[float, Option, Option]] = []

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _calc_slope(iv_a: float, iv_b: float) -> Optional[float]:
        """Retourne iv_a - iv_b si les deux IV sont valides, sinon None."""
        return iv_a - iv_b if iv_a > 0 and iv_b > 0 else None

    def _assign_slopes(call: Option, put: Option,
                       left_c: Optional[float], right_c: Optional[float],
                       left_p: Optional[float], right_p: Optional[float]) -> None:
        """Assigne left/right slope avec fallback call↔put si l'un est None."""
        call.left_slope  = left_c  if left_c  is not None else left_p
        call.right_slope = right_c if right_c is not None else right_p
        put.left_slope   = left_p  if left_p  is not None else left_c
        put.right_slope  = right_p if right_p is not None else right_c

    # ── 1. Construction de datas + calcul IV de base ──────────────────────────
    for j in range(len(options) // 2):
        opt1 = options[2 * j]       # call  (sort: "call" < "put")
        opt2 = options[2 * j + 1]   # put
        opt1.underlying_price = F
        opt2.underlying_price = F

        # Reset IV des options sans premium : l'IV Bloomberg est dans des unités
        if not opt1.status or opt1.premium <= 0:
            opt1.implied_volatility = 0.0
        if not opt2.status or opt2.premium <= 0:
            opt2.implied_volatility = 0.0

        if opt1.status and opt1.premium > 0:
            opt1.implied_volatility = bachelier_implied_vol(F, opt1.strike, opt1.premium, time_to_expiry, opt1.is_call())
        if opt2.status and opt2.premium > 0:
            opt2.implied_volatility = bachelier_implied_vol(F, opt2.strike, opt2.premium, time_to_expiry, opt2.is_call())

        datas.append((opt1.strike, opt1, opt2))

    # ── 2. Calcul des slopes (après que datas est complet) ───────────────────
    n = len(datas)
    iv_c = [d[1].implied_volatility for d in datas]
    iv_p = [d[2].implied_volatility for d in datas]

    for i, data in enumerate(datas):
        call, put = data[1], data[2]
        left_c  = 0.0 if i == 0     else _calc_slope(iv_c[i - 1], iv_c[i])
        right_c = 0.0 if i == n - 1 else _calc_slope(iv_c[i], iv_c[i + 1])
        left_p  = 0.0 if i == 0     else _calc_slope(iv_p[i - 1], iv_p[i])
        right_p = 0.0 if i == n - 1 else _calc_slope(iv_p[i], iv_p[i + 1])
        _assign_slopes(call, put, left_c, right_c, left_p, right_p)

    # ── 3. Propagation des slopes si encore None ─────────────────────────────
    for i in range(1, n):
        call, put = datas[i][1], datas[i][2]
        prev_call, prev_put = datas[i - 1][1], datas[i - 1][2]
        if call.left_slope is None:
            call.left_slope = prev_call.left_slope
        if put.left_slope is None:
            put.left_slope = prev_put.left_slope

    # Backward : right_slope hérite du strike supérieur
    for i in range(n - 2, -1, -1):
        call, put = datas[i][1], datas[i][2]
        next_call, next_put = datas[i + 1][1], datas[i + 1][2]
        if call.right_slope is None:
            call.right_slope = next_call.right_slope
        if put.right_slope is None:
            put.right_slope = next_put.right_slope

    # ── 4. Extrapolation des IV manquantes ────────────────────────────────────
    # Backward (droite→gauche) : strikes bas dont IV=0 → iv[i] = iv[i+1] + right_slope
    for i in range(n - 2, -1, -1):
        call, put = datas[i][1], datas[i][2]
        next_call, next_put = datas[i + 1][1], datas[i + 1][2]
        if call.implied_volatility <= 0 and next_call.implied_volatility > 0 and call.right_slope is not None:
            call.implied_volatility = next_call.implied_volatility + call.right_slope
        if put.implied_volatility <= 0 and next_put.implied_volatility > 0 and put.right_slope is not None:
            put.implied_volatility = next_put.implied_volatility + put.right_slope

    # Forward (gauche→droite) : strikes hauts dont IV=0 → iv[i] = iv[i-1] - left_slope
    for i in range(1, n):
        call, put = datas[i][1], datas[i][2]
        prev_call, prev_put = datas[i - 1][1], datas[i - 1][2]
        if call.implied_volatility <= 0 and prev_call.implied_volatility > 0 and call.left_slope is not None:
            call.implied_volatility = prev_call.implied_volatility - call.left_slope
        if put.implied_volatility <= 0 and prev_put.implied_volatility > 0 and put.left_slope is not None:
            put.implied_volatility = prev_put.implied_volatility - put.left_slope

    # ── 5. Recalcul du premium pour les options extrapolées (premium=0, IV extrapolée) ──
    print("\n--- Corrections IV/Premium (extrapolation par slope) ---")
    for _, call, put in datas:
        for opt in (call, put):
            if opt.premium <= 0 and opt.implied_volatility > 0:
                opt.premium = bachelier_price(F, opt.strike, opt.implied_volatility, time_to_expiry, opt.is_call())
                sym = "C" if opt.is_call() else "P"
                print(f"  Corrige {sym} K={opt.strike}: IV={opt.implied_volatility:.4f}  Premium={opt.premium:.6f}")




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
    
    try:
        fetcher = PremiumFetcher(builder)
        fetcher.fetch_all()
        fetch_warnings = fetcher.warnings
        
        # 3. Traitement des options
        processor = OptionProcessor(builder, fetcher, mixture, default_position)
        options = processor.process_all()
        future_data = fetcher.future_data
        
        # 3.5. Calculer la volatilité Bachelier pour TOUTES les options
        if options:
            _compute_bachelier_volatility(options, time_to_expiry=0.25, future_price=future_data.underlying_price)
            for option in options:
                option._calcul_all_surface()

        # 4. Calculer les prix intra-vie pour toutes les options (avec Bachelier)
        if options:
            time_to_expiry = 0.25
            for option in options:
                option.calculate_all_intra_life(all_options=options, time_to_expiry=time_to_expiry)
        
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()


    return options, future_data, fetch_warnings
