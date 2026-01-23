"""
Calcul Optimisé des Métriques de Stratégie d'Options
Version hybride Python/C++ pour performance maximale

Python: Génération des combinaisons, filtrage par expiration, création finale
C++: Tous les calculs numériques, filtres, validations
"""

from typing import List, Optional
from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.strategy_naming_v2 import generate_strategy_name
from myproject.option.option_utils_v2 import get_expiration_info
import numpy as np
import sys
import os

# Import du module C++ avec debug détaillé
CPP_AVAILABLE = False
CPP_IMPORT_ERROR = None

def _debug_cpp_import():
    """Affiche des informations de debug pour l'import C++."""
    print("[DEBUG C++ linear] Tentative d'import de strategy_metrics_cpp...")
    print(f"[DEBUG C++ linear] Python: {sys.version}")
    print(f"[DEBUG C++ linear] Executable: {sys.executable}")
    print(f"[DEBUG C++ linear] VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', 'Non défini')}")
    
    # Chercher le fichier .pyd
    import glob
    for path in sys.path[:5]:  # Premiers chemins seulement
        if os.path.isdir(path):
            matches = glob.glob(os.path.join(path, "strategy_metrics_cpp*.pyd"))
            if matches:
                print(f"[DEBUG C++ linear] Fichier trouvé: {matches[0]}")
                print(f"[DEBUG C++ linear] Taille: {os.path.getsize(matches[0]):,} bytes")

try:
    _debug_cpp_import()
    import strategy_metrics_cpp
    CPP_AVAILABLE = True
    print(f"[DEBUG C++ linear] ✓ Import réussi! Module: {strategy_metrics_cpp.__file__}")
except ImportError as e:
    CPP_AVAILABLE = False
    CPP_IMPORT_ERROR = str(e)
    print(f"[DEBUG C++ linear] ✗ Échec de l'import: {e}")
    print("⚠️ Module C++ non disponible, utilisation du fallback Python")
    import traceback
    traceback.print_exc()


def create_strategy_fast_with_signs_cpp(
    options: List[Option], 
    signs: np.ndarray, 
    max_loss_params: float, 
    max_premium_params: float, 
    ouvert_gauche: int,
    ouvert_droite: int,
    min_premium_sell: float
) -> Optional[StrategyComparison]:
    """
    Version ultra-optimisée avec calculs C++.
    
    Le C++ gère:
      - Tous les calculs numériques
      - Tous les filtres (retourne None si invalide)
      - Le calcul des métriques
    
    Python gère:
      - Extraction des données des objets Option
      - Génération du nom de stratégie
      - Création de l'objet StrategyComparison final
    
    Args:
        options: Liste d'options
        signs: Array NumPy des signes (+1 pour long, -1 pour short)
        max_loss_params: Perte maximale autorisée
        max_premium_params: Premium maximum autorisé
        ouvert_gauche: Nombre de short puts - long puts autorisé
        ouvert_droite: Nombre de short calls - long calls autorisé
        min_premium_sell: Premium minimum pour vendre une option
        
    Returns:
        StrategyComparison complète ou None si invalide
    """
    if not options or len(options) != len(signs):
        return None
    
    # Vérification préalable rapide
    if options[0].prices is None or options[0].pnl_array is None:
        return None
    
    if options[0].mixture is None:
        return None
    
    n_options = len(options)
    prices = options[0].prices
    mixture = options[0].mixture  # Mixture est la même pour toutes les options
    pnl_length = len(options[0].pnl_array)
    
    # ========== EXTRACTION VECTORISÉE DES DONNÉES ==========
    # (Cette partie reste en Python car elle accède aux objets Option)
    
    premiums = np.empty(n_options, dtype=np.float64)
    deltas = np.empty(n_options, dtype=np.float64)
    gammas = np.empty(n_options, dtype=np.float64)
    vegas = np.empty(n_options, dtype=np.float64)
    thetas = np.empty(n_options, dtype=np.float64)
    ivs = np.empty(n_options, dtype=np.float64)
    average_pnls = np.empty(n_options, dtype=np.float64)
    sigma_pnls = np.empty(n_options, dtype=np.float64)
    strikes = np.empty(n_options, dtype=np.float64)
    profit_surfaces = np.empty(n_options, dtype=np.float64)
    loss_surfaces = np.empty(n_options, dtype=np.float64)
    is_calls = np.empty(n_options, dtype=bool)
    pnl_matrix = np.empty((n_options, pnl_length), dtype=np.float64)
    
    for i, opt in enumerate(options):
        if opt.pnl_array is None:
            return None
        premiums[i] = opt.premium
        deltas[i] = opt.delta
        gammas[i] = opt.gamma
        vegas[i] = opt.vega
        thetas[i] = opt.theta
        ivs[i] = opt.implied_volatility
        average_pnls[i] = opt.average_pnl
        sigma_pnls[i] = opt.sigma_pnl
        strikes[i] = opt.strike
        is_calls[i] = opt.option_type.lower() == "call"
        pnl_matrix[i] = opt.pnl_array
    
    # Convertir signs en int32 pour C++
    signs_int = signs.astype(np.int32)
    
    # S'assurer que mixture est en float64
    mixture_arr = np.asarray(mixture, dtype=np.float64)
    
    # ========== APPEL DU MODULE C++ ==========
    # Tous les calculs et filtres sont faits en C++
    
    result = strategy_metrics_cpp.calculate_strategy_metrics(
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes, 
        profit_surfaces, loss_surfaces, is_calls,
        signs_int, pnl_matrix, prices, mixture_arr,
        max_loss_params, max_premium_params, ouvert_gauche, ouvert_droite, min_premium_sell
    )
    
    # C++ retourne None si stratégie invalide
    if result is None:
        return None
    
    # ========== CRÉATION FINALE (Python) ==========
    # Nom de stratégie et expiration (dépendent des objets Option)
    
    strategy_name = generate_strategy_name(options, signs)
    exp_info = get_expiration_info(options)
    
    try:
        strategy = StrategyComparison(
            strategy_name=strategy_name,
            strategy=None,
            premium=result["total_premium"],
            all_options=options,
            signs=signs,
            call_count=result["call_count"],
            put_count=result["put_count"],
            expiration_day=exp_info.get("expiration_day"),
            expiration_week=exp_info.get("expiration_week"),
            expiration_month=exp_info.get("expiration_month", "F"),
            expiration_year=exp_info.get("expiration_year", 6),
            max_profit=result["max_profit"],
            max_loss=result["max_loss"],
            breakeven_points=result["breakeven_points"],
            profit_range=(result["min_profit_price"], result["max_profit_price"]),
            profit_zone_width=result["profit_zone_width"],
            surface_profit=result["surface_profit"],
            surface_loss=result["surface_loss"],
            average_pnl=result["total_average_pnl"],
            sigma_pnl=result["total_sigma_pnl"],
            pnl_array=result["pnl_array"],
            prices=prices,
            risk_reward_ratio=0,
            risk_reward_ratio_ponderated=0,
            total_delta=result["total_delta"],
            total_gamma=result["total_gamma"],
            total_vega=result["total_vega"],
            total_theta=result["total_theta"],
            avg_implied_volatility=result["total_iv"],
            profit_at_target=0,
            profit_at_target_pct=0,
            rolls_detail= 0,
            score=0.0,
            rank=0,
        )
        return strategy
    except Exception as e:
        print(f"⚠️ Erreur création stratégie: {e}")
        return None


# ============================================================================
# FONCTION PRINCIPALE AVEC FALLBACK AUTOMATIQUE
# ============================================================================

def create_strategy_fast_with_signs(
    options: List[Option], 
    signs: np.ndarray, 
    filter_data
) -> Optional[StrategyComparison]:
    """
    Fonction principale avec sélection automatique C++/Python.
    
    Args:
        options: Liste d'options
        signs: Array NumPy des signes (+1 pour long, -1 pour short)
        filter_data: FilterData avec max_loss_left/right, max_premium, etc.
        
    Returns:
        StrategyComparison complète ou None si invalide
    """
    # Toujours utiliser l'implémentation Python (la plus à jour)
    # Le C++ batch processor est utilisé séparément via batch_processor.py
    from myproject.strategy.calcul_linear_metrics import (
        create_strategy_fast_with_signs as python_impl
    )
    return python_impl(options, signs, filter_data)
