"""
Bloomberg Data Importer for Options Strategy App
=================================================
Importe les données d'options depuis Bloomberg et les convertit directement
en objets Option avec calcul optionnel des surfaces.
"""

import re
from typing import List, Literal, Optional, cast, Tuple
from myproject.bloomberg.fetcher_batch import fetch_options_batch, extract_best_values
from myproject.bloomberg.ticker_builder import build_option_ticker, build_option_ticker_brut
from myproject.bloomberg.bloomber_to_opt import create_option_from_bloomberg
from myproject.option.option_class import Option
import numpy as np

# Type pour les mois valides
MonthCode = Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]

# Mois Bloomberg valides (codes futures standard)
VALID_MONTHS = {"F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"}

# Liste ordonnée des mois Bloomberg pour calcul de l'échéance précédente
# F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
MONTH_ORDER = ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]

# Mapping des mois Bloomberg vers les noms complets
MONTH_NAMES = {
    "F": "January",
    "G": "February",
    "H": "March",
    "J": "April",
    "K": "May",
    "M": "June",
    "N": "July",
    "Q": "August",
    "U": "September",
    "V": "October",
    "X": "November",
    "Z": "December",
}

# Mapping des mois vers les dates d'expiration (3ème mercredi du mois)
MONTH_EXPIRY_DAY = {
    "F": 15,
    "G": 19,
    "H": 19,
    "J": 16,
    "K": 21,
    "M": 18,
    "N": 16,
    "Q": 20,
    "U": 17,
    "V": 15,
    "X": 19,
    "Z": 17,
}


def get_previous_expiration(month: str, year: int) -> Tuple[str, int]:
    """
    Calcule l'échéance précédente pour un mois/année donné.
    
    Args:
        month: Code mois Bloomberg (F, G, H, K, M, N, Q, U, V, X, Z)
        year: Année sur 1 ou 2 chiffres (ex: 6 pour 2026)
        
    Returns:
        Tuple (month_prev, year_prev)
        
    Examples:
        >>> get_previous_expiration("H", 6)  # Mars 2026
        ('G', 6)  # Février 2026
        >>> get_previous_expiration("F", 6)  # Janvier 2026
        ('Z', 5)  # Décembre 2025
    """
    month_idx = MONTH_ORDER.index(month)
    
    if month_idx == 0:
        # Janvier → Décembre année précédente
        return (MONTH_ORDER[-1], year - 1)
    else:
        return (MONTH_ORDER[month_idx - 1], year)


def parse_brut_code(brut_code: str) -> dict:
    """
    Parse un code brut Bloomberg pour extraire les métadonnées.
    
    Exemples de codes bruts:
    - "ERF6C" → underlying="ER", month="F", year=6, option_type="call"
    - "RXWF26P" → underlying="RXW", month="F", year=26, option_type="put"
    - "ERF6P2" → underlying="ER", month="F", year=6, option_type="put"
    
    Args:
        brut_code: Code Bloomberg sans strike ni suffix (ex: "ERF6C", "RXWF26P")
        
    Returns:
        Dict avec underlying, month, year, option_type
    """
    code = brut_code.upper().strip()
    
    # Trouver le type C ou P dans toute la chaîne (pas seulement à la fin)
    if "C" in code:
        option_type = "call"
        # Retirer le C de la chaîne pour parser le reste
        code_without_type = code.replace("C", "", 1)  # Remplacer seulement le premier C
    elif "P" in code:
        option_type = "put"
        code_without_type = code.replace("P", "", 1)
    else:
        # Pas de type explicite, par défaut call
        option_type = "call"
        code_without_type = code
    
    # Trouver l'année (1 ou 2 chiffres à la fin)
    match = re.search(r'(\d{1,2})$', code_without_type)
    if match:
        year = int(match.group(1))
        code_without_year = code_without_type[:match.start()]
    else:
        year = 6  # Défaut
        code_without_year = code_without_type
    
    # Trouver le mois (dernière lettre valide)
    month = ""  # Défaut
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


def import_euribor_options(
    brut_code: Optional[List[str]],
    underlying: str = "",
    months: List[str] = [],
    years: List[int] = [],
    strikes: List[float] = [],
    suffix: str = "Comdty",
    default_position: Literal["long", "short"] = "long",
    mixture: Optional[Tuple[np.ndarray, np.ndarray]] = None,
    compute_roll: bool = True,
) -> List[Option]:
    """
    Importe un ensemble d'options depuis Bloomberg et retourne directement des objets Option.
    Calcule le roll (différence de premium avec l'échéance précédente) si compute_roll=True.

    Args:
        brut_code: Liste de codes Bloomberg bruts (ex: ["ERF6C", "ERF6P"]) ou None pour mode standard
        underlying: Symbole du sous-jacent (ex: "ER" pour Euribor) - ignoré si brut_code
        months: Liste des mois Bloomberg (ex: ['M', 'U', 'Z']) - ignoré si brut_code
        years: Liste des années (ex: [6, 7] pour 2026, 2027) - ignoré si brut_code
        strikes: Liste des strikes à importer
        suffix: Suffixe Bloomberg (ex: "Comdty")
        default_position: Position par défaut ('long' ou 'short')
        mixture: Tuple (prices, probas) pour le calcul des surfaces pondérées
        compute_roll: Si True, importe aussi l'échéance précédente pour calculer le roll

    Returns:
        Liste d'objets Option directement utilisables
    """
    list_option: List[Option] = []
    total_attempts = 0
    total_success = 0

    # Construire tous les tickers et métadonnées
    all_tickers = []
    ticker_metadata = {}
    
    # Tickers pour l'échéance précédente (pour le calcul du roll)
    prev_tickers = []
    prev_ticker_metadata = {}

    print("\n🔨 Construction des tickers...")

    if brut_code is None:
        # Mode standard: construire à partir de underlying/months/years
        for year in years:
            for month in months:
                month_code = cast(MonthCode, month)
                
                # Calculer l'échéance précédente pour le roll
                prev_month, prev_year = get_previous_expiration(month, year)
                
                for strike in strikes:
                    # Ticker pour l'échéance courante - CALL
                    ticker = build_option_ticker(
                        underlying, month_code, year, "C", strike, suffix
                    )
                    all_tickers.append(ticker)
                    ticker_metadata[ticker] = {
                        "underlying": underlying,
                        "strike": strike,
                        "option_type": "call",
                        "month": month,
                        "year": year,
                    }
                    total_attempts += 1
                    
                    # Ticker pour l'échéance précédente - CALL (pour roll)
                    if compute_roll:
                        prev_ticker = build_option_ticker(
                            underlying, cast(MonthCode, prev_month), prev_year, "C", strike, suffix
                        )
                        if prev_ticker not in prev_ticker_metadata:
                            prev_tickers.append(prev_ticker)
                            prev_ticker_metadata[prev_ticker] = {
                                "underlying": underlying,
                                "strike": strike,
                                "option_type": "call",
                                "month": prev_month,
                                "year": prev_year,
                            }

                    # Ticker pour l'échéance courante - PUT
                    ticker = build_option_ticker(
                        underlying, month_code, year, "P", strike, suffix
                    )
                    all_tickers.append(ticker)
                    ticker_metadata[ticker] = {
                        "underlying": underlying,
                        "strike": strike,
                        "option_type": "put",
                        "month": month,
                        "year": year,
                    }
                    total_attempts += 1
                    
                    # Ticker pour l'échéance précédente - PUT (pour roll)
                    if compute_roll:
                        prev_ticker = build_option_ticker(
                            underlying, cast(MonthCode, prev_month), prev_year, "P", strike, suffix
                        )
                        if prev_ticker not in prev_ticker_metadata:
                            prev_tickers.append(prev_ticker)
                            prev_ticker_metadata[prev_ticker] = {
                                "underlying": underlying,
                                "strike": strike,
                                "option_type": "put",
                                "month": prev_month,
                                "year": prev_year,
                            }
    else:
        # Mode brut: parser les codes pour extraire les métadonnées
        for code in brut_code:
            meta = parse_brut_code(code)
            
            # Calculer l'échéance précédente pour le roll
            prev_month, prev_year = get_previous_expiration(meta["month"], meta["year"])
            
            for strike in strikes:
                ticker = build_option_ticker_brut(code, strike, suffix)
                all_tickers.append(ticker)
                ticker_metadata[ticker] = {
                    "underlying": meta["underlying"],
                    "strike": strike,
                    "option_type": meta["option_type"],
                    "month": meta["month"],
                    "year": meta["year"],
                }
                total_attempts += 1
                
                # Ticker pour l'échéance précédente (pour roll)
                if compute_roll:
                    # Construire le code brut pour l'échéance précédente
                    opt_type_char = "C" if meta["option_type"] == "call" else "P"
                    prev_code = f"{meta['underlying']}{prev_month}{prev_year}{opt_type_char}"
                    prev_ticker = build_option_ticker_brut(prev_code, strike, suffix)
                    if prev_ticker not in prev_ticker_metadata:
                        prev_tickers.append(prev_ticker)
                        prev_ticker_metadata[prev_ticker] = {
                            "underlying": meta["underlying"],
                            "strike": strike,
                            "option_type": meta["option_type"],
                            "month": prev_month,
                            "year": prev_year,
                        }

    # FETCH EN BATCH - échéances courantes + précédentes
    try:
        # Fetch des échéances courantes
        print(f"\n📡 Fetch des {len(all_tickers)} options courantes...")
        batch_data = fetch_options_batch(all_tickers, use_overrides=True)
        
        # Fetch des échéances précédentes pour le roll
        prev_batch_data = {}
        if compute_roll and prev_tickers:
            print(f"📡 Fetch des {len(prev_tickers)} options précédentes (pour roll)...")
            prev_batch_data = fetch_options_batch(prev_tickers, use_overrides=True)
        
        # Construire un dictionnaire des premiums de l'échéance précédente
        # Clé: (strike, option_type, prev_month, prev_year) → premium
        prev_premiums: dict[Tuple[float, str, str, int], float] = {}
        
        for prev_ticker, prev_meta in prev_ticker_metadata.items():
            raw_data = prev_batch_data.get(prev_ticker, {})
            if raw_data and not all(v is None for v in raw_data.values()):
                extracted = extract_best_values(raw_data)
                premium = extracted.get("premium")
                if premium is not None and premium > 0:
                    key = (prev_meta["strike"], prev_meta["option_type"], 
                           prev_meta["month"], prev_meta["year"])
                    prev_premiums[key] = premium

        # Collecter les mois/années uniques depuis les métadonnées
        if brut_code is not None:
            # Extraire les mois/années uniques des codes bruts
            unique_periods = set()
            for meta in ticker_metadata.values():
                unique_periods.add((meta["year"], meta["month"]))
            periods = sorted(unique_periods)
        else:
            # Utiliser les années/mois fournis
            periods = [(year, month) for year in years for month in months]

        # Traiter les résultats par mois
        for year, month in periods:
            month_options_count = 0
            month_name = MONTH_NAMES.get(month, month)
            
            # Calculer l'échéance précédente
            prev_month, prev_year = get_previous_expiration(month, year)

            print(f"\n📅 {month_name} 20{20+year}")
            print("-" * 70)

            for ticker in all_tickers:
                meta = ticker_metadata[ticker]

                # Filtrer par mois/année
                if meta["month"] != month or meta["year"] != year:
                    continue

                # Récupérer les données brutes
                raw_data = batch_data.get(ticker, {})

                if raw_data and not all(v is None for v in raw_data.values()):
                    # Extraire les meilleures valeurs
                    extracted = extract_best_values(raw_data)

                    # Créer l'option directement (les surfaces sont calculées dans create_option_from_bloomberg)
                    option = create_option_from_bloomberg(
                        ticker=ticker,
                        underlying=meta["underlying"],
                        strike=meta["strike"],
                        month=meta["month"],
                        year=meta["year"],
                        option_type_str=meta["option_type"],
                        bloomberg_data=extracted,
                        position=default_position,
                        mixture=mixture,
                    )

                    # Calculer le roll si possible
                    if compute_roll and option.premium is not None:
                        prev_key = (meta["strike"], meta["option_type"], prev_month, prev_year)
                        prev_premium = prev_premiums.get(prev_key)
                        if prev_premium is not None:
                            # Roll = premium courant - premium précédent
                            option.roll = prev_premium - option.premium 

                    # Vérifier que l'option est valide
                    if option.strike > 0:
                            list_option.append(option)
                            month_options_count += 1
                            total_success += 1

                            # Afficher un résumé
                            opt_symbol = "C" if option.option_type == "call" else "P"
                            roll_str = f", Roll={option.roll:.4f}" if option.roll is not None else ""

                            print(
                                f"✓ {opt_symbol} {option.strike}: "
                                f"Premium={option.premium}, "
                                f"Delta={option.delta}, "
                                f"IV={option.implied_volatility}"
                                f"{roll_str}"
                            )

    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)
    print("RÉSUMÉ DE L'IMPORT")
    print("=" * 70)
    print(f"Total tentatives: {total_attempts}")
    print(
        f"Succès: {total_success} ({total_success/total_attempts*100:.1f}%)"
        if total_attempts > 0
        else "Succès: 0"
    )
    print(f"Échecs: {total_attempts - total_success}")
    print("=" * 70)

    return list_option
