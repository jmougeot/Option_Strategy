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
from myproject.option.bachelier import bachelier_implied_vol, bachelier_price, bachelier_delta, bachelier_gamma, bachelier_theta
from myproject.option.sabr import SABRCalibration, sabr_vol as _sabr_vol
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

    F = future_price
    if not F:
        return

    # ── 1. Calcul IV individuelle + construction de datas ───────────────────
    datas: List[Tuple[float, Option, Option]] = []
    for j in range(len(options) // 2):
        call = options[2 * j]       # "call" < "put" alphabétiquement → call en premier
        put  = options[2 * j + 1]
        call.underlying_price = F
        put.underlying_price  = F

        call.implied_volatility = (bachelier_implied_vol(F, call.strike, call.premium, time_to_expiry, True)
            if call.status and call.premium > 0 else 0.0)
        
        put.implied_volatility = (bachelier_implied_vol(F, put.strike, put.premium, time_to_expiry, False)
            if put.status and put.premium > 0 else 0.0)
        
        datas.append((call.strike, call, put))

    n = len(datas)
    if n == 0:
        return

    # ── 2. Fusion call+put → iv_merged par strike ───────────────────────────
    IV_DIVERGENCE_THRESHOLD = 0.30

    def _neighbor_avg(iv_list: List[float], idx: int) -> Optional[float]:
        neighbors = [iv_list[j] for j in (idx - 1, idx + 1) if 0 <= j < n and iv_list[j] > 0]
        return sum(neighbors) / len(neighbors) if neighbors else None

    iv_c = [d[1].implied_volatility for d in datas]
    iv_p = [d[2].implied_volatility for d in datas]
    iv_merged: List[float] = []

    for i, (_, call, put) in enumerate(datas):
        ic, ip = iv_c[i], iv_p[i]
        if ic > 0 and ip > 0:
            if abs(ic - ip) <= IV_DIVERGENCE_THRESHOLD:
                iv_merged.append((ic + ip) / 2.0)
            else:
                # Garder celui le plus cohérent avec ses voisins
                err_c = abs(ic - _neighbor_avg(iv_c, i)) if _neighbor_avg(iv_c, i) is not None else float("inf")
                err_p = abs(ip - _neighbor_avg(iv_p, i)) if _neighbor_avg(iv_p, i) is not None else float("inf")
                if err_c <= err_p:
                    put.status = False
                    put.implied_volatility = 0.0
                    iv_merged.append(ic)
                else:
                    call.status = False
                    call.implied_volatility = 0.0
                    iv_merged.append(ip)
        elif ic > 0:
            iv_merged.append(ic)
        elif ip > 0:
            iv_merged.append(ip)
        else:
            iv_merged.append(0.0)

    # ── 3. Suppression des clusters trop petits ──────────────────────────────
    MIN_CLUSTER_SIZE = 3

    valid_indices = [i for i in range(n) if iv_merged[i] > 0]
    clusters: List[List[int]] = []
    for idx in valid_indices:
        if clusters and idx == clusters[-1][-1] + 1:
            clusters[-1].append(idx)
        else:
            clusters.append([idx])

    to_remove = {idx for cluster in clusters if len(cluster) < MIN_CLUSTER_SIZE for idx in cluster}

    for i in to_remove:
        _, call, put = datas[i]
        call.status = False
        put.status  = False
        call.implied_volatility = 0.0
        put.implied_volatility  = 0.0
        iv_merged[i] = 0.0

    # ── 4. Slopes sur iv_merged + extrapolation ──────────────────────────────
    def _slope(a: float, b: float) -> Optional[float]:
        return a - b if a > 0 and b > 0 else None

    sl: List[Optional[float]] = [0.0 if i == 0     else _slope(iv_merged[i - 1], iv_merged[i]) for i in range(n)]
    sr: List[Optional[float]] = [0.0 if i == n - 1 else _slope(iv_merged[i], iv_merged[i + 1]) for i in range(n)]

    # Propagation forward (left_slope manquant)
    for i in range(1, n):
        if sl[i] is None:
            sl[i] = sl[i - 1]
    # Propagation backward (right_slope manquant)
    for i in range(n - 2, -1, -1):
        if sr[i] is None:
            sr[i] = sr[i + 1]

    # Extrapolation backward (strikes bas)
    for i in range(n - 2, -1, -1):
        if iv_merged[i] <= 0 and iv_merged[i + 1] > 0 and sr[i] is not None:
            iv_merged[i] = iv_merged[i + 1] + sr[i]
    # Extrapolation forward (strikes hauts)
    for i in range(1, n):
        if iv_merged[i] <= 0 and iv_merged[i - 1] > 0 and sl[i] is not None:
            iv_merged[i] = iv_merged[i - 1] - sl[i]

    # ── 5. Application iv_merged + premium extrapolé + greeks ───────────────
    for i, (_, call, put) in enumerate(datas):
        iv = max(iv_merged[i], 0.0)
        for opt in (call, put):
            opt.left_slope  = sl[i]
            opt.right_slope = sr[i]
            if iv > 0:
                was_missing = opt.implied_volatility <= 0
                opt.implied_volatility = iv
                if was_missing or opt.premium <= 0:
                    opt.premium = bachelier_price(F, opt.strike, iv, time_to_expiry, opt.is_call())
                    sym = "C" if opt.is_call() else "P"
                    print(f"  Extrapole {sym} K={opt.strike}: IV={iv:.4f}  Premium={opt.premium:.6f}")
                opt.delta = bachelier_delta(F, opt.strike, iv, time_to_expiry, opt.is_call())
                opt.gamma = bachelier_gamma(F, opt.strike, iv, time_to_expiry)
                opt.theta = bachelier_theta(F, opt.strike, iv, time_to_expiry)

# ============================================================================
# CALIBRATION SABR SUR LE SMILE BLOOMBERG
# ============================================================================

def _compute_sabr_volatility(
    options: List[Option],
    time_to_expiry: float = 0.25,
    future_price: Optional[float] = None,
    anomaly_threshold: float = 1.5,
) -> Optional[SABRCalibration]:
    """
    Calibre le modele SABR (beta=0, pure normal) sur le smile Bloomberg
    et enrichit chaque Option avec :
      - sabr_volatility  : vol SABR predite au strike
      - sabr_residual    : IV_mkt - IV_SABR (en memes unites)
      - sabr_z_score     : |residual| / RMSE de calibration
      - sabr_is_anomaly  : True si le point est identifie comme aberrant

    Parameters
    ----------
    options            : liste d'Options avec implied_volatility deja calcule
    time_to_expiry     : temps a expiration en annees
    future_price       : prix forward du sous-jacent
    anomaly_threshold  : multiplicateur de RMSE pour flaguer une anomalie

    Returns
    -------
    SABRCalibration calibree, ou None en cas d'echec
    """
    F = future_price
    if not F:
        print("[SABR] Pas de prix future disponible, calibration annulee.")
        return None

    # --- Grouper les IV valides par strike (moyenne call + put) ---
    from collections import defaultdict
    by_strike: dict = defaultdict(list)
    for o in options:
        if o.implied_volatility > 0 and o.strike > 0:
            by_strike[round(o.strike, 6)].append(o.implied_volatility)

    if len(by_strike) < 3:
        print(f"[SABR] Pas assez de strikes valides ({len(by_strike)} < 3), calibration annulee.")
        return None

    strikes = np.array(sorted(by_strike.keys()))
    sigmas  = np.array([float(np.mean(by_strike[K])) for K in strikes])

    print(f"\n[SABR] Calibration sur {len(strikes)} strikes | F={F:.4f} | T={time_to_expiry:.4f}a")

    try:
        # ── Boucle itérative : corriger une anomalie à la fois puis recalibrer ──
        # sigmas_work est la copie de travail corrigée au fil des itérations
        sigmas_work     = sigmas.copy()
        corrected_set: dict[float, float] = {}   # strike → ancienne IV originale
        MAX_ITER = len(strikes)                  # ne può corriger plus de points qu'il n'y en a

        calib  = SABRCalibration(F=float(F), T=time_to_expiry, beta=0.0)
        result = calib.fit(strikes, sigmas_work)

        for iteration in range(MAX_ITER):
            anoms = calib.anomalies(threshold=anomaly_threshold)
            if not anoms:
                break  # plus d'anomalie → on s'arrête

            # Prendre uniquement le pire point (résidu absolu le plus grand)
            worst = anoms[0]
            K_bad = worst["strike"]

            # Trouver l'index dans strikes
            idx = np.argmin(np.abs(strikes - K_bad))
            old_iv   = sigmas_work[idx]
            new_iv   = worst["sigma_model"]   # vol SABR du modèle courant

            print(
                f"[SABR] Iter {iteration+1} — correction K={K_bad:.4f}: "
                f"{old_iv*1e4:.1f}bp → {new_iv*1e4:.1f}bp "
                f"(Δ={worst['residual_bps']:+.1f}bp  z={worst['z_score']:.2f})"
            )

            corrected_set[round(K_bad, 4)] = old_iv
            sigmas_work[idx] = new_iv

            # Recalibrer SABR sur les données corrigées (minimum 3 points)
            if len(strikes) < 3:
                break
            calib  = SABRCalibration(F=float(F), T=time_to_expiry, beta=0.0)
            result = calib.fit(strikes, sigmas_work)

        print(f"[SABR] Calibration finale ({len(corrected_set)} point(s) corrigé(s))")
        print(calib.summary())

        # ── Enrichir chaque Option avec la calibration finale ────────────────
        for opt in options:
            if opt.strike <= 0:
                continue
            opt.sabr_volatility = _sabr_vol(
                float(F), opt.strike, time_to_expiry,
                result.alpha, result.beta, result.rho, result.nu,
            )
            if opt.implied_volatility > 0:
                K_rounded = round(opt.strike, 4)
                if K_rounded in corrected_set:
                    # Ce strike a été corrigé : mettre à jour IV et premium
                    opt.sabr_is_anomaly = True
                    opt.sabr_corrected  = True
                    opt.implied_volatility = opt.sabr_volatility
                    opt.sabr_residual      = 0.0
                    opt.sabr_z_score       = 0.0
                    opt.premium = bachelier_price(
                        float(F), opt.strike, opt.sabr_volatility, time_to_expiry, opt.is_call()
                    )
                else:
                    opt.sabr_is_anomaly = False
                    opt.sabr_corrected  = False
                    opt.sabr_residual   = opt.implied_volatility - opt.sabr_volatility
                    opt.sabr_z_score    = (
                        abs(opt.sabr_residual) / result.rmse if result.rmse > 0 else 0.0
                    )
            else:
                opt.sabr_residual   = 0.0
                opt.sabr_z_score    = 0.0
                opt.sabr_is_anomaly = False
                opt.sabr_corrected  = False

        return calib

    except Exception as e:
        print(f"[SABR] Erreur de calibration : {e}")
        import traceback
        traceback.print_exc()
        return None


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
             _compute_sabr_volatility(options, time_to_expiry=0.25, future_price=future_data.underlying_price)

             for option in options:
                option._calcul_all_surface()
        
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()


    return options, future_data, fetch_warnings
