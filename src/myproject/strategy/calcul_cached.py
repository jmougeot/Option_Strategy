"""
Calcul Ultra-Optimisé des Métriques de Stratégie d'Options
Version avec pré-extraction des données pour éviter les copies répétées

L'idée: extraire toutes les données des options UNE SEULE FOIS au début,
puis réutiliser ces arrays pour toutes les combinaisons.
"""

from typing import List, Optional, Tuple
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
    print("[DEBUG C++] Tentative d'import de strategy_metrics_cpp...")
    print(f"[DEBUG C++] Python: {sys.version}")
    print(f"[DEBUG C++] Executable: {sys.executable}")
    print(f"[DEBUG C++] VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', 'Non défini')}")
    
    # Chercher le fichier .pyd
    import glob
    for path in sys.path[:5]:  # Premiers chemins seulement
        if os.path.isdir(path):
            matches = glob.glob(os.path.join(path, "strategy_metrics_cpp*.pyd"))
            if matches:
                print(f"[DEBUG C++] Fichier trouvé: {matches[0]}")
                print(f"[DEBUG C++] Taille: {os.path.getsize(matches[0]):,} bytes")

try:
    import strategy_metrics_cpp
    CPP_AVAILABLE = True
    print(f"[DEBUG C++] ✓ Import réussi! Module: {strategy_metrics_cpp.__file__}")
except ImportError as e:
    CPP_AVAILABLE = False
    CPP_IMPORT_ERROR = str(e)
    print(f"[DEBUG C++] ✗ Échec de l'import: {e}")
    import traceback
    traceback.print_exc()


class OptionsDataCache:
    """
    Cache pré-extrait des données d'options pour éviter les copies répétées.
    Extrait toutes les données UNE SEULE FOIS, puis on sélectionne par indices.
    """
    
    def __init__(self, options: List[Option]):
        """Pré-extrait toutes les données des options."""
        n = len(options)
        if n == 0:
            self.valid = False
            return
            
        # Vérifier validité
        if options[0].prices is None or options[0].pnl_array is None:
            self.valid = False
            return
            
        self.valid = True
        self.options = options
        self.n = n
        self.prices = options[0].prices
        self.pnl_length = len(options[0].pnl_array)
        
        # Pré-allouer tous les arrays
        self.premiums = np.empty(n, dtype=np.float64)
        self.deltas = np.empty(n, dtype=np.float64)
        self.gammas = np.empty(n, dtype=np.float64)
        self.vegas = np.empty(n, dtype=np.float64)
        self.thetas = np.empty(n, dtype=np.float64)
        self.ivs = np.empty(n, dtype=np.float64)
        self.average_pnls = np.empty(n, dtype=np.float64)
        self.sigma_pnls = np.empty(n, dtype=np.float64)
        self.strikes = np.empty(n, dtype=np.float64)
        self.profit_surfaces = np.empty(n, dtype=np.float64)
        self.loss_surfaces = np.empty(n, dtype=np.float64)
        self.is_calls = np.empty(n, dtype=bool)
        self.pnl_matrix = np.empty((n, self.pnl_length), dtype=np.float64)
        
        # Extraire toutes les données
        for i, opt in enumerate(options):
            if opt.pnl_array is None:
                self.valid = False
                return
            self.premiums[i] = opt.premium
            self.deltas[i] = opt.delta
            self.gammas[i] = opt.gamma
            self.vegas[i] = opt.vega
            self.thetas[i] = opt.theta
            self.ivs[i] = opt.implied_volatility
            self.average_pnls[i] = opt.average_pnl
            self.sigma_pnls[i] = opt.sigma_pnl
            self.strikes[i] = opt.strike
            self.is_calls[i] = opt.option_type.lower() == "call"
            self.pnl_matrix[i] = opt.pnl_array
    
    def get_subset(self, indices: List[int]) -> Tuple:
        """Retourne les données pour un sous-ensemble d'options (par indices)."""
        idx = np.array(indices, dtype=np.intp)
        return (
            self.premiums[idx],
            self.deltas[idx],
            self.gammas[idx],
            self.vegas[idx],
            self.thetas[idx],
            self.ivs[idx],
            self.average_pnls[idx],
            self.sigma_pnls[idx],
            self.strikes[idx],
            self.profit_surfaces[idx],
            self.loss_surfaces[idx],
            self.is_calls[idx],
            self.pnl_matrix[idx],
        )


def create_strategy_from_cache(
    cache: OptionsDataCache,
    indices: List[int],
    signs: np.ndarray,
    max_loss_params: float,
    max_premium_params: float,
    ouvert: bool
) -> Optional[StrategyComparison]:
    """
    Crée une stratégie en utilisant le cache pré-extrait.
    Beaucoup plus rapide car évite l'extraction répétée des données.
    """
    if not cache.valid:
        return None
    
    # Récupérer le sous-ensemble de données
    (premiums, deltas, gammas, vegas, thetas, ivs,
     average_pnls, sigma_pnls, strikes, profit_surfaces,
     loss_surfaces, is_calls, pnl_matrix) = cache.get_subset(indices)
    
    signs_int = signs.astype(np.int32)
    
    # Appel C++
    result = strategy_metrics_cpp.calculate_strategy_metrics( #type: ignore
        premiums, deltas, gammas, vegas, thetas, ivs,
        average_pnls, sigma_pnls, strikes,
        profit_surfaces, loss_surfaces, is_calls,
        signs_int, pnl_matrix, cache.prices,
        max_loss_params, max_premium_params, ouvert
    )
    
    if result is None:
        return None
    
    # Récupérer les options pour cette combinaison
    options = [cache.options[i] for i in indices]
    
    strategy_name = generate_strategy_name(options, signs)
    exp_info = get_expiration_info(options)
    
    try:
        return StrategyComparison(
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
            average_pnl=result["total_average_pnl"],
            sigma_pnl=result["total_sigma_pnl"],
            pnl_array=result["pnl_array"],
            prices=cache.prices,
            total_delta=result["total_delta"],
            total_gamma=result["total_gamma"],
            total_vega=result["total_vega"],
            total_theta=result["total_theta"],
            avg_implied_volatility=result["total_iv"],
            roll=0,
            roll_quarterly=0,
            roll_sum=0,
            profit_at_target=0,
            profit_at_target_pct=0,
            score=0.0,
            rank=0,
        )
    except Exception as e:
        print(f"⚠️ Erreur création stratégie: {e}")
        return None
