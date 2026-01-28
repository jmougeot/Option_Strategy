"""
Workflow Principal - Bloomberg to Strategy Comparison
======================================================
Ce module implÃ©mente le workflow complet :
1. Import des donnÃ©es Bloomberg
2. Conversion en objets Option
3. GÃ©nÃ©ration de toutes les stratÃ©gies possibles
4. Comparaison et ranking des stratÃ©gies

Utilise les fonctions optimisÃ©es des modules :
- option_generator_v2.OptionStrategyGeneratorV2
- comparor_v2.StrategyComparerV2
"""

from typing import List, Dict, Optional, Tuple
from myproject.strategy.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.strategy.scoring.comparer import StrategyComparerV2
from myproject.strategy.strategy_class import StrategyComparison
from myproject.bloomberg.bloomberg_data_importer import import_options
from myproject.app.scenarios_widget import create_mixture_from_scenarios
from myproject.app.scenarios_widget import ScenarioData
from myproject.app.utils import filter_same_strategies
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
    Fonction principale simplifiÃ©e pour Streamlit.
    Importe les options depuis Bloomberg et retourne les meilleures stratÃ©gies + stats.
    """
    stats = {}
    
    # Initialiser le tracker si fourni
    progress_tracker.init_ui()
    progress_tracker.update(ProcessingStep.FETCH_DATA, "Connexion Ã  Bloomberg...")

    mixture = create_mixture_from_scenarios(
        scenarios, price_min, price_max, num_points
    )


    progress_tracker.update(ProcessingStep.FETCH_DATA,
                            "Import des options...")

    # Fetch option from blommberg and return List[Option] with all the calculs done
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

    # tracker of the fecther 
    stats["nb_options"] = len(options)
    stats["underlying_price"] = underlying_price
    progress_tracker.update(ProcessingStep.FETCH_DATA,
                            f"âœ… {len(options)} options rÃ©cupÃ©rÃ©es",stats)

    if not options:
        progress_tracker.error("Aucune option trouvÃ©e")
        return [], stats, mixture, 0

    generator = OptionStrategyGeneratorV2(options)

    # GÃ©nÃ©rer les stratÃ©gies avec suivi de progression
    all_strategies, nb_strategies_possibles = generator.generate_all_combinations(
        price_min=price_min,
        price_max=price_max,
        max_legs=max_legs,
        filter=filter,
        progress_tracker=progress_tracker,
    )

    stats["nb_strategies_totales"] = len(all_strategies)
    stats["nb_strategies_possibles"] = nb_strategies_possibles


    progress_tracker.update(
        ProcessingStep.RANKING, 
        f"Classement de {len(all_strategies)} stratÃ©gies...",
        stats
    )

    comparer = StrategyComparerV2()
    best_strategies = comparer.compare_and_rank(
        strategies=all_strategies, top_n=top_n, weights=scoring_weights)

    # Remove duplicate strategies with identical P&L profiles
    best_strategies = filter_same_strategies(best_strategies)

    stats["nb_strategies_classees"] = len(best_strategies)

    progress_tracker.update(ProcessingStep.DISPLAY, "PrÃ©paration de l'affichage...", stats)

    return best_strategies, stats, mixture, underlying_price

