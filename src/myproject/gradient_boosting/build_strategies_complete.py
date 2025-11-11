"""
Script complet pour parser Trade_monitor.csv et construire des StrategyComparison
"""

import pandas as pd
import re
from typing import List, Tuple, Optional


def normalize_and_export_mapping(
    trade_csv_path: str, output_mapping_path: Optional[str] = None
):
    """
    Crée le fichier Strategy_mapping.csv à partir de Trade_monitor.csv
    """
    print("=" * 80)
    print("ÉTAPE 1: NORMALISATION DES STRATÉGIES")
    print("=" * 80)

    # Lire Trade_monitor.csv
    df = pd.read_csv(trade_csv_path, encoding="latin1")
    print(f"Lignes lues: {len(df)}")

    # Analyser chaque stratégie
    results = []

    for idx, row in df.iterrows():
        strategy_str = str(row.get("STRATEGY", ""))

        if not strategy_str or strategy_str.strip() == "" or strategy_str == "nan":
            continue

        # Extraire toutes les colonnes additionnelles depuis Trade_monitor.csv
        ref_o = row.get("REF O", "")
        ref_c = row.get("REF C", "")
        delta = row.get("DELTA", "")
        what_is_closed = row.get("what is closed", "")
        close_size = row.get("CLOSE SIZE", "")
        close_price = row.get("CLOSE PRICE", "")
        close_date = row.get("CLOSE DATE", "")
        pnl = row.get("P&L (ticks)", "")
        premium = row.get("OPENING PRICE", "")

        # Convertir les valeurs manquantes en chaîne vide
        def safe_str(val):
            return "" if pd.isna(val) else str(val)

        # Traiter toutes les stratégies de la même manière (VS ou non)
        result = {
            "original": strategy_str,
            "underlying": "",
            "month_expiracy": "",
            "year_expiray": "",
            "normalized": "",
            "strategy_type": "unknown",
            "option_type": "call",
            "strikes": [],
            "REF O": safe_str(ref_o),
            "REF C": safe_str(ref_c),
            "DELTA": safe_str(delta),
            "what is closed": safe_str(what_is_closed),
            "CLOSE SIZE": safe_str(close_size),
            "CLOSE PRICE": safe_str(close_price),
            "CLOSE DATE": safe_str(close_date),
            "P&L": safe_str(pnl),
            "call_count": None,
            "average_pnl": safe_str(pnl),
            "num_breakevens": None,
            "max_profit": None,
            "max_loss": None,
            "premium": safe_str(premium),
            "profit_at_target": None,
            "profit_range_min": None,
            "profit_range_max": None,
            "sigma_pnl": None,
            "surface_loss_ponderated": None,
            "surface_profit_ponderated": None,
            "surface_loss": None,
            "surface_profit": None,
            "risk_reward_ratio": None,
            "total_delta": None,
            "total_theta": None,
            "total_gamma": None,
            "total_vega": None,
            "profit_zone_width": None,
            "max_loss_penalty": None,
            "IV": None,
            "is_trade_monitor_data": True,
        }

        # Extraire les strikes (gère automatiquement les VS)
        strikes = extract_strikes_simple(strategy_str)
        result["strikes"] = strikes

        # Détecter le type
        strategy_type, option_type = detect_strategy_type_simple(
            strategy_str, len(strikes)
        )
        result["strategy_type"] = strategy_type
        result["option_type"] = option_type

        # Normaliser si possible
        if strikes and strategy_type != "unknown":
            normalized, underlying, month_expiry, year_expiry = normalize_simple(
                strategy_str, strikes, option_type, strategy_type
            )
            if normalized:
                result["normalized"] = normalized
                result["underlying"] = underlying
                result["month_expiracy"] = month_expiry
                result["year_expiray"] = year_expiry
                result["confidence"] = "high"

        results.append(result)

    mapping_df = pd.DataFrame(results)

    # Calculer les scores pour chaque stratégie
    scores = []
    for result in results:
        pnl_str = result.get("P&L", "")
        try:
            pnl_val = float(pnl_str) if pnl_str and pnl_str != "" else None
        except (ValueError, TypeError):
            pnl_val = None

        score = scoring_system(pnl_val)
        scores.append(score)

    # Ajouter les scores au DataFrame
    mapping_df["score"] = scores

    # Supprimer la colonne P&L après avoir calculé les scores
    if "P&L" in mapping_df.columns:
        mapping_df = mapping_df.drop(columns=["P&L"])

    if output_mapping_path is not None:
        mapping_df.to_csv(output_mapping_path, index=False)

    return mapping_df, scores


def scoring_system(pnl: Optional[float]) -> float:
    # Normalize input and handle missing/invalid values
    if pnl is None:
        return 50.0
    try:
        val = float(pnl)
    except Exception:
        return 50.0

    if val == 0:
        return 50.0
    if val <= 0:
        return 50.0 - val
    return 50.0 + val


def extract_strikes_simple(strategy_str: str) -> List[float]:
    """Extraction avancée des strikes - gère tous les formats"""
    strikes = []

    # Nettoyer: retirer codes produit au début (ERJ4, SFRM4, etc.)
    cleaned_str = re.sub(r"^\s*[A-Z]{2,5}\d\s+", "", strategy_str, flags=re.IGNORECASE)

    # Chercher d'abord les séquences avec / (priorité)
    # Pattern: nombres séparés par / (avec ou sans décimales)
    slash_pattern = r"(\d{2,3}\.?\d{0,5}(?:/\d{1,5}\.?\d{0,5})+)"
    slash_sequences = re.findall(slash_pattern, cleaned_str)

    for sequence in slash_sequences:
        parts = sequence.split("/")
        first = parts[0]

        if "." in first:
            # Format avec décimales: 106.4/106.8/107 ou 95.06/12/18
            base = first.split(".")[0]

            # Premier élément
            try:
                strike = float(first)
                if 50 < strike < 200:
                    strikes.append(strike)
            except:
                pass

            # Éléments suivants
            for part in parts[1:]:
                if "." in part:
                    # Décimale complète: 106.8, 95.125
                    try:
                        strike = float(part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                elif len(part) <= 2:
                    # Suffixe 2 chiffres: "12" → 95.12
                    try:
                        strike = float(base + "." + part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                elif len(part) == 3:
                    # 3 chiffres: probablement entier "107"
                    try:
                        strike = float(part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                else:
                    # 4+ chiffres: format collé "9712"
                    try:
                        strike = float(part[:2] + "." + part[2:])
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass

        elif len(first) == 2:
            # Format: 95/95.06/95.125/95.18 (premier = 2 chiffres)
            base = first
            try:
                strike = float(first)
                if 50 < strike < 200:
                    strikes.append(strike)
            except:
                pass

            for part in parts[1:]:
                if "." in part:
                    try:
                        strike = float(part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
                elif len(part) <= 2:
                    try:
                        strike = float(base + "." + part)
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass

        elif len(first) == 4:
            # Format collé 4 chiffres: 9712/9737/9750 ou 9540/50/60/70
            base = first[:2]

            if all(len(p) == 4 for p in parts):
                # Tous 4 chiffres: 9712/9737/9750
                for part in parts:
                    try:
                        strike = float(part[:2] + "." + part[2:])
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass
            else:
                # Format mixte: 9540/50/60/70
                try:
                    strike = float(first[:2] + "." + first[2:])
                    if 50 < strike < 200:
                        strikes.append(strike)
                except:
                    pass
                for part in parts[1:]:
                    if len(part) == 2:
                        try:
                            strike = float(base + "." + part)
                            if 50 < strike < 200:
                                strikes.append(strike)
                        except:
                            pass

        elif len(first) == 6:
            # Format 6 chiffres: 949375/948125
            for part in parts:
                if len(part) >= 4:
                    try:
                        strike = float(part[:2] + "." + part[2:])
                        if 50 < strike < 200:
                            strikes.append(strike)
                    except:
                        pass

    # Si pas de séquence trouvée, extraction simple
    if not strikes:
        simple_pattern = r"\b(\d{2,3}\.?\d{0,5})\b"
        matches = re.findall(simple_pattern, cleaned_str)
        for match in matches:
            try:
                strike = float(match)
                if 50 < strike < 200:
                    strikes.append(strike)
            except:
                pass

    # Dédupliquer et trier
    return sorted(list(set(strikes)))


def detect_strategy_type_simple(strategy_str: str, num_strikes: int) -> Tuple[str, str]:
    """Détection simple du type de stratégie"""
    strategy_lower = strategy_str.lower()

    # Déterminer si call ou put
    if "put" in strategy_lower or " p " in strategy_lower or " ps" in strategy_lower:
        option_type = "put"
    else:
        option_type = "call"

    # Détecter le type basé sur les mots-clés et le nombre de strikes
    if "fly" in strategy_lower:
        if (
            "broken" in strategy_lower
            or "brk" in strategy_lower
            or "bkn" in strategy_lower
        ):
            return f"broken_{option_type}_fly", option_type
        return f"{option_type}_fly", option_type
    elif "condor" in strategy_lower:
        return f"{option_type}_condor", option_type
    elif (
        "spread" in strategy_lower or " cs" in strategy_lower or " ps" in strategy_lower
    ):
        return f"{option_type}_spread", option_type
    elif num_strikes == 2:
        return f"{option_type}_spread", option_type
    elif num_strikes == 3:
        return f"{option_type}_fly", option_type
    elif num_strikes == 4:
        return f"{option_type}_condor", option_type

    return "unknown", option_type


def normalize_simple(
    strategy_str: str, strikes: List[float], option_type: str, strategy_type: str
) -> Tuple[str, str, str, str]:
    """Normalisation simple avec long/short correct

    Returns:
        Tuple[str, str, str, str]: (normalized_name, underlying, month_expiry, year_expiry)
    """
    # Extraire underlying et expiry
    pattern = r"\b([A-Z]{2,4})([FGHJKMNQUVXZ]\d)\b"
    match = re.search(pattern, strategy_str, re.IGNORECASE)

    if match:
        underlying = match.group(1).upper()
        expiry = match.group(2).upper()
        # Extraire le mois (lettre) et l'année (chiffre)
        month_expiry = expiry[0]  # Première lettre (F, G, H, etc.)
        year_expiry = expiry[1]  # Chiffre (0-9)
    else:
        return "", "", "", ""

    # Construire le nom normalisé
    opt_type = "C" if option_type == "call" else "P"
    parts = []

    # Définir les signes selon le type de stratégie
    if "fly" in strategy_type and len(strikes) == 3:
        # Fly: +strike1 -2×strike2 +strike3
        signs = ["+", "-2x", "+"]
    elif "condor" in strategy_type and len(strikes) == 4:
        # Condor: +strike1 -strike2 -strike3 +strike4
        signs = ["+", "-", "-", "+"]
    elif "spread" in strategy_type and len(strikes) == 2:
        # Spread: +strike1 -strike2
        signs = ["+", "-"]
    else:
        # Par défaut: tous long
        signs = ["+"] * len(strikes)

    for i, strike in enumerate(strikes):
        sign = signs[i] if i < len(signs) else "+"
        parts.append(f"{sign}{underlying}{expiry} {strike}{opt_type}")

    return " ".join(parts), underlying, month_expiry, year_expiry
