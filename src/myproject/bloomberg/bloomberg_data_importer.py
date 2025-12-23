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

# Mois Bloomberg valides
VALID_MONTHS = {"F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"}

# Mapping des mois Bloomberg vers les noms complets
MONTH_NAMES = {
    "F": "January",
    "G": "February",
    "H": "March",
    "K": "April",
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
    "K": 16,
    "M": 18,
    "N": 16,
    "Q": 20,
    "U": 17,
    "V": 15,
    "X": 19,
    "Z": 17,
}


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
) -> List[Option]:
    """
    Importe un ensemble d'options depuis Bloomberg et retourne directement des objets Option.

    Args:
        brut_code: Liste de codes Bloomberg bruts (ex: ["ERF6C", "ERF6P"]) ou None pour mode standard
        underlying: Symbole du sous-jacent (ex: "ER" pour Euribor) - ignoré si brut_code
        months: Liste des mois Bloomberg (ex: ['M', 'U', 'Z']) - ignoré si brut_code
        years: Liste des années (ex: [6, 7] pour 2026, 2027) - ignoré si brut_code
        strikes: Liste des strikes à importer
        suffix: Suffixe Bloomberg (ex: "Comdty")
        default_position: Position par défaut ('long' ou 'short')
        mixture: Tuple (prices, probas) pour le calcul des surfaces pondérées

    Returns:
        Liste d'objets Option directement utilisables
    """
    list_option: List[Option] = []
    total_attempts = 0
    total_success = 0

    # Construire tous les tickers et métadonnées
    all_tickers = []
    ticker_metadata = {}

    print("\n🔨 Construction des tickers...")

    if brut_code is None:
        # Mode standard: construire à partir de underlying/months/years
        for year in years:
            for month in months:
                month_code = cast(MonthCode, month)
                for strike in strikes:
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
    else:
        # Mode brut: parser les codes pour extraire les métadonnées
        for code in brut_code:
            meta = parse_brut_code(code)
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

    # FETCH EN BATCH
    import os
    TEST_MODE = os.environ.get("TEST_BBG_IMPORT", "0") == "1"

    try:
        if TEST_MODE:
            print("\n⚡ Mode TEST_BBG_IMPORT=1 : génération de données random pour chaque ticker")
            batch_data = {}
            rng = np.random.default_rng()
            for ticker in all_tickers:
                batch_data[ticker] = {
                    "PX_LAST": float(rng.uniform(90, 110)),
                    "BID": float(rng.uniform(0.1, 2.0)),
                    "ASK": float(rng.uniform(0.1, 2.0)),
                    "IVOL_MID": float(rng.uniform(0.1, 0.5)),
                    "DELTA": float(rng.uniform(-1, 1)),
                    "GAMMA": float(rng.uniform(0, 0.1)),
                    "THETA": float(rng.uniform(-0.1, 0)),
                    "VEGA": float(rng.uniform(0, 0.2)),
                    "PREMIUM": float(rng.uniform(0.1, 2.0)),
                }
        else:
            batch_data = fetch_options_batch(all_tickers, use_overrides=True)

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

                    # Vérifier que l'option est valide
                    if option.strike > 0:
                            list_option.append(option)
                            month_options_count += 1
                            total_success += 1

                            # Afficher un résumé
                            opt_symbol = "C" if option.option_type == "call" else "P"

                            print(
                                f"✓ {opt_symbol} {option.strike}: "
                                f"Premium={option.premium}, "
                                f"Delta={option.delta}, "
                                f"IV={option.implied_volatility}"
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
