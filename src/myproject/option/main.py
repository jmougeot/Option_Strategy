"""
Workflow Principal - Bloomberg to Strategy Comparison
======================================================
Ce module implémente le workflow complet :
1. Import des données Bloomberg
2. Conversion en objets Option
3. Génération de toutes les stratégies possibles
4. Comparaison et ranking des stratégies

Utilise les fonctions optimisées des modules :
- dic_to_option.bloomberg_data_to_options()
- option_generator_v2.OptionStrategyGeneratorV2
- comparor_v2.StrategyComparerV2
"""

from typing import List, Dict, Optional, Tuple
from myproject.option.dic_to_option import bloomberg_data_to_options
from myproject.option.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.option.comparor_v2 import StrategyComparerV2
from myproject.option.comparison_class import StrategyComparison


def process_bloomberg_to_strategies(
    bloomberg_data: List[Dict],
    target_price: float,
    price_min: float,
    price_max: float,
    max_legs: int = 4,
    top_n: int = 10,
    scoring_weights: Optional[Dict[str, float]] = None,
    verbose: bool = False
) -> Tuple[List[StrategyComparison], Dict]:
    """
    Fonction principale simplifiée pour Streamlit.
    Prend les données Bloomberg et retourne les meilleures stratégies + stats.
    """
    stats = {}
    
    # ÉTAPE 1 : Conversion Bloomberg → Options
    if verbose:
        print("📥 Conversion des données Bloomberg...")
    
    options = bloomberg_data_to_options(
        bloomberg_data=bloomberg_data,
        default_position='long',
        price_min=price_min,
        price_max=price_max,
        num_points=200
    )
    
    stats['nb_options'] = len(options)
    
    if not options:
        return [], stats
    
    # ÉTAPE 2 : Génération des stratégies
    if verbose:
        print(f"🔄 Génération des stratégies (max {max_legs} legs)...")
    
    generator = OptionStrategyGeneratorV2(options)
    
    all_strategies = generator.generate_all_combinations(
        target_price=target_price,
        price_min=price_min,
        price_max=price_max,
        max_legs=max_legs,
        include_long=True,
        include_short=True
    )
    
    stats['nb_strategies_totales'] = len(all_strategies)
    
    if not all_strategies:
        return [], stats
    
    # ÉTAPE 3 : Comparaison et ranking
    if verbose:
        print(f"📊 Comparaison et ranking (top {top_n})...")
    
    comparer = StrategyComparerV2()
    best_strategies = comparer.compare_and_rank(
        strategies=all_strategies,
        top_n=top_n,
        weights=scoring_weights
    )
    
    stats['nb_strategies_classees'] = len(best_strategies)
    
    if verbose:
        print(f"✅ Terminé : {stats['nb_options']} options → {stats['nb_strategies_totales']} stratégies → Top {stats['nb_strategies_classees']}")
    
    return best_strategies, stats
