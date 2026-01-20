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
VALID_MONTHS = {"F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"}

# Liste ordonnée des mois Bloomberg pour calcul de l'échéance précédente
# F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
MONTH_ORDER = ["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"]

# Mapping des mois Bloomberg vers les noms complets
MONTH_NAMES = {
    "H": "March",
    "M": "June",
    "U": "September",
    "Z": "December",
}

# Mapping des mois vers les dates d'expiration (3ème mercredi du mois)
MONTH_EXPIRY_DAY = {
    "H": 19,
    "M": 18,
    "U": 17,
    "Z": 16,
}


def get_previous_expiration(month: str, year: int) -> Tuple[str, int]:
    """
    Calcule l'échéance précédente pour un mois/année donné.
    
    Args:
        month: Code mois Bloomberg (F, G, H, J, K, M, N, Q, U, V, X, Z)
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


def get_roll_expiration(current_month: str, current_year: int, 
                        roll_month: Optional[str] = None, roll_year: Optional[int] = None) -> Tuple[str, int, int]:
    """
    Calcule l'échéance pour le roll et le nombre de trimestres de différence.
    
    MONTH_ORDER = ["H", "M", "U", "Z"] → 4 trimestres par an
    
    Args:
        current_month: Mois courant (H, M, U, Z)
        current_year: Année courante
        roll_month: Mois pour le roll (None = trimestre précédent)
        roll_year: Année pour le roll (None = même année ou année précédente)
        
    Returns:
        Tuple (roll_month, roll_year, quarters_diff) où quarters_diff est le nombre de trimestres de différence
    """
    current_idx = MONTH_ORDER.index(current_month)
    
    if roll_month is None:
        # Par défaut: trimestre précédent
        prev_month, prev_year = get_previous_expiration(current_month, current_year)
        return (prev_month, prev_year, 1)
    else:
        # Mois spécifié par l'utilisateur
        roll_idx = MONTH_ORDER.index(roll_month)
        if roll_year is None:
            roll_year = current_year
        
        # Calculer la différence en trimestres
        # 4 trimestres par an (H, M, U, Z)
        if roll_year == current_year:
            quarters_diff = current_idx - roll_idx
        else:
            # Année différente: 4 trimestres par an
            quarters_diff = (current_year - roll_year) * 4 + (current_idx - roll_idx)
        
        return (roll_month, roll_year, abs(quarters_diff))


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
    mixture: Tuple[np.ndarray, np.ndarray, float],
    underlying: str,
    months: List[str] = [],
    years: List[int] = [],
    strikes: List[float] = [],
    suffix: str = "Comdty",
    default_position: Literal["long", "short"] = "long",
    compute_roll: bool = True,
    roll_month: Optional[str] = None,
    roll_year: Optional[int] = None,
) -> List[Option]:
    """
    Importe un ensemble d'options depuis Bloomberg et retourne directement des objets Option.
    Calcule le roll (différence de premium avec l'échéance de roll) si compute_roll=True.

    Args:
        brut_code: Liste de codes Bloomberg bruts (ex: ["ERF6C", "ERF6P"]) ou None pour mode standard
        underlying: Symbole du sous-jacent (ex: "ER" pour Euribor) - ignoré si brut_code
        months: Liste des mois Bloomberg (ex: ['M', 'U', 'Z']) - ignoré si brut_code
        years: Liste des années (ex: [6, 7] pour 2026, 2027) - ignoré si brut_code
        strikes: Liste des strikes à importer
        suffix: Suffixe Bloomberg (ex: "Comdty")
        default_position: Position par défaut ('long' ou 'short')
        mixture: Tuple (prices, probas) pour le calcul des surfaces pondérées
        compute_roll: Si True, importe aussi l'échéance de roll pour calculer le roll
        roll_month: Mois pour le calcul du roll (None = mois précédent automatique)
        roll_year: Année pour le calcul du roll (None = déduit automatiquement)

    Returns:
        Liste d'objets Option directement utilisables
    """
    list_option: List[Option] = []
    total_attempts = 0
    total_success = 0

    # Construire tous les tickers et métadonnées
    all_tickers = []
    ticker_metadata = {}
    
    # Tickers pour l'échéance de roll (custom ou Q-1)
    roll_tickers = []
    roll_ticker_metadata = {}
    
    # Tickers pour le roll Q-1 (toujours le trimestre précédent)
    q1_tickers = []
    q1_ticker_metadata = {}
    
    # Stockage du nombre de trimestres de différence pour normalisation
    quarters_diff_map: dict[Tuple[str, int], int] = {}  # (month, year) -> quarters_diff

    print("\n🔨 Construction des tickers...")

    if brut_code is None:
        # Mode standard: construire à partir de underlying/months/years
        for year in years:
            for month in months:
                month_code = cast(MonthCode, month)
                
                # Calculer l'échéance pour le roll (précédente ou spécifiée)
                r_month, r_year, quarters_diff = get_roll_expiration(month, year, roll_month, roll_year)
                quarters_diff_map[(month, year)] = quarters_diff
                
                # Calculer l'échéance Q-1 (toujours le trimestre précédent)
                q1_month, q1_year, _ = get_roll_expiration(month, year, None, None)
                
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
                    
                    # Ticker pour l'échéance de roll (custom) - CALL
                    if compute_roll:
                        roll_ticker = build_option_ticker(
                            underlying, cast(MonthCode, r_month), r_year, "C", strike, suffix
                        )
                        if roll_ticker not in roll_ticker_metadata:
                            roll_tickers.append(roll_ticker)
                            roll_ticker_metadata[roll_ticker] = {
                                "underlying": underlying,
                                "strike": strike,
                                "option_type": "call",
                                "month": r_month,
                                "year": r_year,
                            }
                        
                        # Ticker pour Q-1 (si différent du custom)
                        if (q1_month, q1_year) != (r_month, r_year):
                            q1_ticker = build_option_ticker(
                                underlying, cast(MonthCode, q1_month), q1_year, "C", strike, suffix
                            )
                            if q1_ticker not in q1_ticker_metadata:
                                q1_tickers.append(q1_ticker)
                                q1_ticker_metadata[q1_ticker] = {
                                    "underlying": underlying,
                                    "strike": strike,
                                    "option_type": "call",
                                    "month": q1_month,
                                    "year": q1_year,
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
                    
                    # Ticker pour l'échéance de roll (custom) - PUT
                    if compute_roll:
                        roll_ticker = build_option_ticker(
                            underlying, cast(MonthCode, r_month), r_year, "P", strike, suffix
                        )
                        if roll_ticker not in roll_ticker_metadata:
                            roll_tickers.append(roll_ticker)
                            roll_ticker_metadata[roll_ticker] = {
                                "underlying": underlying,
                                "strike": strike,
                                "option_type": "put",
                                "month": r_month,
                                "year": r_year,
                            }
                        
                        # Ticker pour Q-1 (si différent du custom)
                        if (q1_month, q1_year) != (r_month, r_year):
                            q1_ticker = build_option_ticker(
                                underlying, cast(MonthCode, q1_month), q1_year, "P", strike, suffix
                            )
                            if q1_ticker not in q1_ticker_metadata:
                                q1_tickers.append(q1_ticker)
                                q1_ticker_metadata[q1_ticker] = {
                                    "underlying": underlying,
                                    "strike": strike,
                                    "option_type": "put",
                                    "month": q1_month,
                                    "year": q1_year,
                                }
    else:
        # Mode brut: parser les codes pour extraire les métadonnées
        for code in brut_code:
            meta = parse_brut_code(code)
            
            # Calculer l'échéance pour le roll (précédente ou spécifiée)
            r_month, r_year, quarters_diff = get_roll_expiration(
                meta["month"], meta["year"], roll_month, roll_year
            )
            quarters_diff_map[(meta["month"], meta["year"])] = quarters_diff
            
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
                
                # Ticker pour l'échéance de roll
                if compute_roll:
                    # Construire le code brut pour l'échéance de roll
                    opt_type_char = "C" if meta["option_type"] == "call" else "P"
                    roll_code = f"{meta['underlying']}{r_month}{r_year}{opt_type_char}"
                    roll_ticker = build_option_ticker_brut(roll_code, strike, suffix)
                    if roll_ticker not in roll_ticker_metadata:
                        roll_tickers.append(roll_ticker)
                        roll_ticker_metadata[roll_ticker] = {
                            "underlying": meta["underlying"],
                            "strike": strike,
                            "option_type": meta["option_type"],
                            "month": r_month,
                            "year": r_year,
                        }

    # FETCH EN BATCH - échéances courantes + roll + Q-1
    try:
        # Fetch des échéances courantes
        print(f"\n📡 Fetch des {len(all_tickers)} options courantes...")
        batch_data = fetch_options_batch(all_tickers, use_overrides=True)
        
        # Fetch des échéances de roll (custom)
        roll_batch_data = {}
        if roll_tickers:
            print(f"📡 Fetch des {len(roll_tickers)} options de roll (custom)...")
            roll_batch_data = fetch_options_batch(roll_tickers, use_overrides=True)
        
        # Fetch des échéances Q-1 (si différentes du custom)
        q1_batch_data = {}
        if q1_tickers:
            print(f"📡 Fetch des {len(q1_tickers)} options Q-1...")
            q1_batch_data = fetch_options_batch(q1_tickers, use_overrides=True)
        
        # Construire un dictionnaire des premiums de l'échéance de roll (custom)
        # Clé: (strike, option_type, roll_month, roll_year) → premium
        roll_premiums: dict[Tuple[float, str, str, int], float] = {}
        
        for roll_ticker, roll_meta in roll_ticker_metadata.items():
            raw_data = roll_batch_data.get(roll_ticker, {})
            if raw_data and not all(v is None for v in raw_data.values()):
                extracted = extract_best_values(raw_data)
                premium = extracted.get("premium")
                if premium is not None and premium > 0:
                    key = (roll_meta["strike"], roll_meta["option_type"], 
                           roll_meta["month"], roll_meta["year"])
                    roll_premiums[key] = premium
        
        # Construire un dictionnaire des premiums Q-1
        # Clé: (strike, option_type, q1_month, q1_year) → premium
        q1_premiums: dict[Tuple[float, str, str, int], float] = {}
        
        for q1_ticker, q1_meta in q1_ticker_metadata.items():
            raw_data = q1_batch_data.get(q1_ticker, {})
            if raw_data and not all(v is None for v in raw_data.values()):
                extracted = extract_best_values(raw_data)
                premium = extracted.get("premium")
                if premium is not None and premium > 0:
                    key = (q1_meta["strike"], q1_meta["option_type"], 
                           q1_meta["month"], q1_meta["year"])
                    q1_premiums[key] = premium

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
            
            # Calculer l'échéance de roll et le nombre de trimestres
            r_month, r_year, quarters_diff = get_roll_expiration(month, year, roll_month, roll_year)

            print(f"\n{month_name} 20{20+year} (roll vs {r_month}{r_year}, {quarters_diff} trimestre(s))")
            print("-" * 70)

            for ticker in all_tickers:
                meta = ticker_metadata[ticker]

                # Filtrer par mois/année
                if meta["month"] != month or meta["year"] != year:
                    continue

                try:
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

                        # Calculer le roll Q-1 (toujours le trimestre précédent)
                        # et le roll custom (si différent)
                        if option.premium is not None and option.premium != 0:
                            try:
                                # Calculer Q-1
                                q1_month_local, q1_year_local, _ = get_roll_expiration(month, year, None, None)
                                q1_key = (meta["strike"], meta["option_type"], q1_month_local, q1_year_local)
                                
                                # Chercher le premium Q-1 (dans q1_premiums ou roll_premiums si c'est le même)
                                q1_premium = q1_premiums.get(q1_key) or roll_premiums.get(q1_key)
                                if q1_premium is not None:
                                    # Roll Q-1 = différence brute (non normalisée)
                                    option.roll_quarterly = q1_premium - option.premium
                                
                                # Calculer le roll custom
                                roll_key = (meta["strike"], meta["option_type"], r_month, r_year)
                                roll_premium = roll_premiums.get(roll_key)
                                if roll_premium is not None:
                                    # Roll = (premium_roll - premium_courant) / nombre_de_trimestres
                                    # Ainsi le roll est normalisé par trimestre
                                    raw_roll = roll_premium - option.premium
                                    option.roll = raw_roll / quarters_diff if quarters_diff > 0 else raw_roll
                            except Exception:
                                # Erreur de calcul du roll, continuer sans
                                pass

                        # Vérifier que l'option est valide
                        if option.strike > 0:
                                list_option.append(option)
                                month_options_count += 1
                                total_success += 1

                                # Afficher un résumé
                                opt_symbol = "C" if option.option_type == "call" else "P"
                                roll_q_str = f", RollQ1={option.roll_quarterly:.4f}" if option.roll_quarterly is not None else ""
                                roll_str = f", Roll={option.roll:.4f}/Q" if option.roll is not None else ""

                                print(
                                    f"✓ {opt_symbol} {option.strike}: "
                                    f"Premium={option.premium}, "
                                    f"Delta={option.delta}, "
                                    f"IV={option.implied_volatility}"
                                    f"{roll_q_str}{roll_str}"
                                )
                except Exception:
                    # Erreur sur cette option, continuer avec les autres
                    continue

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
    if compute_roll:
        print(f"Roll calculé vs: {roll_month or 'mois précédent'}{roll_year or ''}")
    print("=" * 70)

    return list_option
