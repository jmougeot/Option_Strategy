# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

from typing import Dict, List
from myproject.strategy.strategy_class import StrategyComparison
from myproject.option.option_class import Option


def prepare_options_data(options: List[Option]) -> Dict[str, List[Option]]:
    """SÃ©pare les calls et puts."""
    calls = [opt for opt in options if opt.option_type == "call"]
    puts = [opt for opt in options if opt.option_type == "put"]

    return {"calls": calls, "puts": puts}


def format_currency(value: float) -> str:
    """Formats a value as currency."""
    if value == float("inf"):
        return "Unlimited"
    return f"{value:.2f}"


def format_percentage(value: float) -> str:
    """Formats a percentage."""
    return f"{value:.1f}%"


def format_expiration_date(month: str, year: int) -> str:
    """
    Formate la date d'expiration Ã  partir du mois Bloomberg et de l'annÃ©e.

    Args:
        month: Code du mois Bloomberg (F, G, H, K, M, N, Q, U, V, X, Z)
        year: AnnÃ©e (6 = 2026)

    Returns:
        Date formatÃ©e (ex: "Jun 2026")
    """
    month_names = {
        "F": "Jan",
        "G": "Feb",
        "H": "Mar",
        "K": "Apr",
        "M": "Jun",
        "N": "Jul",
        "Q": "Aug",
        "U": "Sep",
        "V": "Oct",
        "X": "Nov",
        "Z": "Dec",
    }

    month_name = month_names.get(month, month)
    full_year = 2020 + year

    return f"{month_name} {full_year}"

def strike_list(strike_min: float, strike_max: float, step: float) -> List[float]:
    """
    GÃ©nÃ¨re une liste de strikes avec un step dÃ©fini
    """
    # Calculer le nombre de steps nÃ©cessaires
    num_steps = int(round((strike_max - strike_min) / step)) + 1
    
    # GÃ©nÃ©rer les strikes par multiplication pour Ã©viter l'accumulation d'erreurs
    strike_list = [round(strike_min + i * step, 10) for i in range(num_steps)]
    
    return strike_list

def filter_same_strategies(comparisons: List[StrategyComparison], decimals: int = 4) -> List[StrategyComparison]:
    """
    Filtre les stratÃ©gies ayant le mÃªme profil P&L.
    
    Args:
        comparisons: Liste de StrategyComparison Ã  filtrer
        decimals: Nombre de dÃ©cimales pour l'arrondi (4 = tolÃ©rance 0.0001)
        
    Returns:
        Liste sans doublons (conserve la premiÃ¨re occurrence)
    """
    import numpy as np
    
    vues = set()
    uniques = []
    duplicates_info = []
    
    for i, comp in enumerate(comparisons):
        # Signature = tuple du pnl_array arrondi
        sig = tuple(np.round(comp.pnl_array, decimals))
        if sig not in vues:
            vues.add(sig)
            uniques.append(comp)
        else:
            # Trouver l'original
            orig_idx = next(j for j, c in enumerate(uniques) if tuple(np.round(c.pnl_array, decimals)) == sig)
            duplicates_info.append((i, orig_idx, comp, uniques[orig_idx]))
    
    n = len(comparisons) - len(uniques)
    if n > 0:
        print(f"  🔍 {n} doublons éliminés (même profil P&L)")
        if len(duplicates_info) > 0:
            print(f"  🔍 DEBUG doublons - Premiers exemples:")
            for dup_idx, orig_idx, dup, orig in duplicates_info[:3]:
                dup_strikes = [f"{opt.strike:.1f}" for opt in dup.all_options]
                orig_strikes = [f"{opt.strike:.1f}" for opt in orig.all_options]
                dup_types = [opt.option_type[0].upper() for opt in dup.all_options]
                orig_types = [opt.option_type[0].upper() for opt in orig.all_options]
                dup_signs = ['+' if s > 0 else '-' for s in dup.signs]
                orig_signs = ['+' if s > 0 else '-' for s in orig.signs]
                print(f"    Dup #{dup_idx}: {''.join([f'{s}{t}@{k}' for s,t,k in zip(dup_signs, dup_types, dup_strikes)])}")
                print(f"    Orig #{orig_idx}: {''.join([f'{s}{t}@{k}' for s,t,k in zip(orig_signs, orig_types, orig_strikes)])}")
                # Comparer quelques valeurs du P&L
                step = max(1, len(dup.pnl_array)//5)
                pnl_sample_dup = dup.pnl_array[::step][:5]
                pnl_sample_orig = orig.pnl_array[::step][:5]
                print(f"      P&L dup (échantillon): {[f'{x:.2f}' for x in pnl_sample_dup]}")
                print(f"      P&L orig (échantillon): {[f'{x:.2f}' for x in pnl_sample_orig]}")
    
    return uniques




