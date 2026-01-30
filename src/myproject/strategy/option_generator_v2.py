"""
GÃ©nÃ©rateur V2 de StratÃ©gies d'Options
======================================

GÃ©nÃ¨re toutes les combinaisons de stratÃ©gies d'options via le module C++.
Le traitement est entiÃ¨rement dÃ©lÃ©guÃ© au batch processor C++ pour des performances optimales.
"""

from typing import List, Tuple, Optional, Dict
from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison
from myproject.strategy.batch_processor import process_batch_cpp_with_scoring, init_cpp_cache
from myproject.option.option_filter import sort_options_by_expiration, sort_options_by_strike
from myproject.app.filter_widget import FilterData


class OptionStrategyGeneratorV2:
    """
    Génère toutes les strtégies à partir d'une liste d'options 
    """


    def __init__(self, options: List[Option]):
        """
        Initilisation du générateur 
        """
        # Trier les options par expiration puis par strike croissant
        sorted_by_exp = sort_options_by_expiration(options)
        self.options = sort_options_by_strike(sorted_by_exp)
        init_cpp_cache(options)
    
    def generate_top_strategies(
        self,
        filter: FilterData,
        max_legs: int = 4,
        top_n: int = 10,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> List[StrategyComparison]:
        """
        Génération avec SCORING C++ intégré - RECOMMANDÉ
        
        Génère et score toutes les stratégies en C++, ne retourne que le top_n.
        Beaucoup plus rapide que generate_all_combinations() + scoring Python.
        
        Args:
            filter: Filtres à appliquer
            max_legs: Nombre maximum de legs
            top_n: Nombre de meilleures stratégies à retourner
            progress_tracker: Tracker de progression
            custom_weights: Poids personnalisés pour les métriques (optionnel)
            
        Returns:
            Tuple (liste des top_n stratégies, nombre total de combinaisons)
        """

        strategies = process_batch_cpp_with_scoring(
            max_legs,
            filter,
            top_n=top_n,
            custom_weights=custom_weights
        )
        return strategies

