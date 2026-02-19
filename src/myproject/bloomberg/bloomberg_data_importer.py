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
    
    Méthode:
    1. Pour les options avec un premium valide: calcul direct de σ_n via bachelier_implied_vol
    2. Pour les options sans premium (warning): interpolation via slope linéaire σ(K) = a·K + b
    3. Pour les options interpolées: recalcul du premium via bachelier_price
    
    Args:
        options: Liste complète d'options
        time_to_expiry: Temps jusqu'à expiration (en années)
        future_price: Prix du futures (utilisé si OPT_UNDL_PX absent des options)
    """
    if not options:
        return
    
    # Forward price: depuis les options, sinon fallback sur le futures récupéré
    F = next((opt.underlying_price for opt in options if opt.underlying_price and opt.underlying_price > 0), None)
    if F is None and future_price and future_price > 0:
        F = future_price
        print(f"  ℹ OPT_UNDL_PX absent des options → utilisation du prix futures: {F:.4f}")
    if F is None:
        print("Pas de prix sous-jacent disponible pour le calcul Bachelier")
        return
    
    # Propager le prix sous-jacent aux options qui ne l'ont pas
    for opt in options:
        if not opt.underlying_price or opt.underlying_price <= 0:
            opt.underlying_price = F
    
    print(f"\n📐 Calcul volatilité Bachelier (F={F:.2f}, T={time_to_expiry:.3f})")
    
    # 1. Première passe: calculer σ_n pour toutes les options avec premium valide et status OK
    call_raw: List[Tuple[float, float, Option]] = []
    put_raw: List[Tuple[float, float, Option]] = []
    needs_interpolation: List[Option] = []  # status=False → premium + IV recalculés
    needs_iv_only: List[Option] = []        # status=True mais σ_n pas fiable → IV seule interpolée
    
    for opt in options:
        # Assurer le underlying_price
        if not opt.underlying_price or opt.underlying_price <= 0:
            opt.underlying_price = F
        
        # Options avec warning (status=False) -> premium à recalculer par interpolation
        if not opt.status:
            needs_interpolation.append(opt)
        elif opt.premium and opt.premium > 0:
            # status=True avec premium valide: calcul direct de σ_n
            sigma_n = bachelier_implied_vol(F, opt.strike, opt.premium, time_to_expiry, opt.is_call())
            if sigma_n > 0:
                if opt.is_call():
                    call_raw.append((opt.strike, sigma_n, opt))
                else:
                    put_raw.append((opt.strike, sigma_n, opt))
            else:
                # σ_n ≤ 0: IV à interpoler mais premium conservé
                needs_iv_only.append(opt)
        else:
            # status=True mais pas de premium: IV à interpoler, premium conservé
            needs_iv_only.append(opt)
    
    # 2. Filtrer les σ_n aberrantes (deep ITM → σ ≈ 0, pas fiable)
    #    On rejette les σ_n < 20% de la médiane du même type
    call_data: List[Tuple[float, float]] = []
    put_data: List[Tuple[float, float]] = []
    
    for raw_list, data_list, label in [
        (call_raw, call_data, "calls"),
        (put_raw, put_data, "puts"),
    ]:
        if not raw_list:
            continue
        sigmas = [s for _, s, _ in raw_list]
        median_sigma = float(np.median(sigmas))
        threshold = median_sigma * 0.20  # 20% de la médiane
        
        for strike, sigma_n, opt in raw_list:
            if sigma_n >= threshold:
                opt.implied_volatility = (sigma_n / F) * 100.0 if F > 0 else 0.0
                data_list.append((strike, sigma_n))
            else:
                # σ_n trop basse → deep ITM, pas fiable → IV à interpoler (premium conservé)
                needs_iv_only.append(opt)
                print(f"  ⚠ {label[:-1].title()} K={strike}: σ_n={sigma_n:.6f} < seuil {threshold:.6f} → IV interpolée")
    
    print(f"  • {len(call_data)} calls + {len(put_data)} puts avec σ_n fiable (médiane filtrée)")
    
    # 3. Si des options nécessitent interpolation, interpolation locale par différence finie
    all_to_interpolate = needs_interpolation + needs_iv_only
    if all_to_interpolate:

        def _local_slope_interp(K_target: float, data: List[Tuple[float, float]]) -> Optional[float]:
            """
            Interpole σ_n(K_target) via pente locale entre voisins.

            Pour chaque K cible, on cherche les voisins K_{n-1} < K_target < K_{n+1}
            dans les données connues (triées par strike).
            - Pente locale: a = (σ_{n+1} - σ_{n-1}) / (K_{n+1} - K_{n-1})
            - Ancrage sur le voisin le plus proche: σ = σ_voisin + a * (K - K_voisin)
            - Si K hors intervalle (extrapolation): même logique avec les 2 points extrêmes.
            """
            if not data:
                return None
            
            # Trier par strike
            sorted_data = sorted(data, key=lambda x: x[0])
            strikes = [d[0] for d in sorted_data]
            sigmas  = [d[1] for d in sorted_data]
            n = len(sorted_data)
            
            if n == 1:
                # Un seul point connu → σ constante
                return sigmas[0]
            
            # Trouver les voisins encadrants
            # idx_right = premier indice dont le strike > K_target
            idx_right = next((i for i, k in enumerate(strikes) if k > K_target), n)
            idx_left  = idx_right - 1

            if idx_right == 0:
                # K_target < tous les strikes connus → extrapolation gauche avec les 2 premiers
                K_n_minus = strikes[0]; s_n_minus = sigmas[0]
                K_n_plus  = strikes[1]; s_n_plus  = sigmas[1]
            elif idx_right == n:
                # K_target > tous les strikes connus → extrapolation droite avec les 2 derniers
                K_n_minus = strikes[-2]; s_n_minus = sigmas[-2]
                K_n_plus  = strikes[-1]; s_n_plus  = sigmas[-1]
            else:
                # Interpolation: voisins gauche et droite
                K_n_minus = strikes[idx_left];  s_n_minus = sigmas[idx_left]
                K_n_plus  = strikes[idx_right]; s_n_plus  = sigmas[idx_right]
            
            # Pente locale par différence finie
            dK = K_n_plus - K_n_minus
            if abs(dK) < 1e-10:
                return s_n_minus  # strikes identiques → σ constante

            a = (s_n_plus - s_n_minus) / dK
            
            # Ancrage sur le voisin le plus proche
            if abs(K_target - K_n_minus) <= abs(K_target - K_n_plus):
                return s_n_minus + a * (K_target - K_n_minus)
            else:
                return s_n_plus + a * (K_target - K_n_plus)

        # Fallback: si call_data ou put_data vide, on emprunte l'autre
        effective_call_data = call_data if call_data else put_data
        effective_put_data  = put_data  if put_data  else call_data

        # 4. Interpoler
        fixed_count = 0
        iv_only_count = 0
        needs_iv_only_set = set(id(o) for o in needs_iv_only)
        
        for opt in all_to_interpolate:
            data_ref = effective_call_data if opt.is_call() else effective_put_data
            if not data_ref:
                continue
            
            sigma_interp = _local_slope_interp(opt.strike, data_ref)
            if sigma_interp is None:
                continue
            sigma_interp = max(sigma_interp, 1e-6)
            opt.implied_volatility = (sigma_interp / F) * 100.0 if F > 0 else 0.0
            
            sym = "C" if opt.is_call() else "P"
            
            if id(opt) in needs_iv_only_set:
                # status=True, deep ITM: on garde le premium Bloomberg, juste IV interpolée
                iv_only_count += 1
                print(f"  ✓ IV interpolée {sym} K={opt.strike}: σ_n={sigma_interp:.4f}, IV≈{opt.implied_volatility:.2f}% (premium conservé={opt.premium:.6f})")
            else:
                # status=False (warning): recalculer le premium avec Bachelier
                new_premium = bachelier_price(F, opt.strike, sigma_interp, time_to_expiry, opt.is_call())
                opt.premium = new_premium
                opt._calcul_all_surface()
                fixed_count += 1
                print(f"  ✓ Corrigé {sym} K={opt.strike}: σ_n={sigma_interp:.4f}, Premium={new_premium:.6f}, IV≈{opt.implied_volatility:.2f}%")
        
        if fixed_count > 0:
            print(f"  • {fixed_count}/{len(needs_interpolation)} options warning corrigées (premium recalculé)")
        if iv_only_count > 0:
            print(f"  • {iv_only_count}/{len(needs_iv_only)} options deep ITM: IV interpolée, premium conservé")


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
            _compute_bachelier_volatility(options, time_to_expiry=0.25, future_price=future_data.price)
        
        # 4. Calculer les prix intra-vie pour toutes les options (avec Bachelier)
        if options:
            # Estimer le temps jusqu'à expiration (en années)
            time_to_expiry = 0.25  # ~3 mois par défaut
            for option in options:
                option.calculate_all_intra_life(all_options=options, time_to_expiry=time_to_expiry)
        
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()


    return options, future_data, fetch_warnings
