"""
Workflow Principal - Bloomberg to Strategy Comparison
======================================================

Ce module implemente le workflow complet :
1. Import des donnees Bloomberg (ou simulation offline)
2. Conversion en objets Option
3. Generation de toutes les strategies possibles avec SCORING C++
4. Les stratégies sont déjà scorées et classées (pas besoin de comparer.py)

Mode Offline:
    Definir OFFLINE_MODE=true dans l'environnement pour utiliser des donnees simulees.

Utilise les fonctions optimisees des modules :
- option_generator_v2.OptionStrategyGeneratorV2 (avec scoring C++ intégré)
"""

from typing import List, Dict, Optional, Tuple
from myproject.strategy.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.strategy.strategy_class import StrategyComparison
from myproject.bloomberg.bloomberg_data_importer import import_options
from myproject.bloomberg.bloomberg_data_importer_offline import (
    import_options_offline, 
    is_offline_mode
)
from myproject.app.scenarios_widget import create_mixture_from_scenarios
from myproject.app.scenarios_widget import ScenarioData
from myproject.app.filter_widget import FilterData
from myproject.app.progress_tracker import ProgressTracker, ProcessingStep
import numpy as np


def process_bloomberg_to_strategies(
    filter: FilterData,
    scenarios: ScenarioData,
    progress_tracker: ProgressTracker,
    underlying: str = "ER",
    months: List[str] = [],
    years: List[int] = [],
    strikes: List[float] = [],
    price_min: float = 0.0,
    price_max: float = 100.0,
    max_legs: int = 4,
    top_n: int = 10,
    scoring_weights: Optional[Dict[str, float]] = None,
    num_points: int = 200,
    brut_code: Optional[List[str]] = None,
    roll_expiries: Optional[List[Tuple[str, int]]] = None,
) -> Tuple[List[StrategyComparison], Dict, Tuple[np.ndarray, np.ndarray, float], float]:
    """
    Fonction principale simplifiee pour Streamlit.
    Importe les options depuis Bloomberg (ou simulation offline) et retourne les meilleures strategies + stats.
    """
    stats = {}
    
    # Initialiser le tracker
    progress_tracker.init_ui()
    
    # Verifier le mode offline
    offline = is_offline_mode()
    if offline:
        progress_tracker.update(ProcessingStep.FETCH_DATA, "MODE OFFLINE - Simulation...")
    else:
        progress_tracker.update(ProcessingStep.FETCH_DATA, "Connexion a Bloomberg...")

    # Creer la mixture de scenarios
    mixture = create_mixture_from_scenarios(
        scenarios, price_min, price_max, num_points
    )

    progress_tracker.update(ProcessingStep.FETCH_DATA, "Import des options...")

    # Fetch options: Bloomberg ou Simulation selon OFFLINE_MODE
    if offline:
        options, underlying_price = import_options_offline(
            mixture=mixture,
            underlying=underlying,
            months=months,
            years=years,
            strikes=strikes,
            default_position="long",
        )
    else:
        options, underlying_price = import_options(
            mixture=mixture,
            underlying=underlying,
            months=months,
            years=years,
            strikes=strikes,
            roll_expiries=roll_expiries,
            brut_code=brut_code,
            default_position="long",
        )

    # Tracker du fetch
    stats["nb_options"] = len(options)
    stats["underlying_price"] = underlying_price
    progress_tracker.update(
        ProcessingStep.FETCH_DATA,
        f"{len(options)} options recuperees",
        stats
    )

    if not options:
        progress_tracker.error("Aucune option trouvee")
        return [], stats, mixture, 0

    # Generer les strategies avec SCORING C++ intégré
    generator = OptionStrategyGeneratorV2(options)
    

    best_strategies = generator.generate_top_strategies(
        filter=filter,
        max_legs=max_legs,
        top_n=top_n,
        custom_weights=scoring_weights)

    stats["nb_strategies_possibles"] = (len(options*4)**max_legs)
    
    progress_tracker.update(
        ProcessingStep.RANKING, 
        f"Stratégies déjà scorées et filtrées en C++ - {len(best_strategies)} résultats",
        stats
    )
    
    stats["nb_strategies_classees"] = len(best_strategies)

    progress_tracker.update(ProcessingStep.DISPLAY, "Preparation de l'affichage...", stats)

    return best_strategies, stats, mixture, underlying_price

