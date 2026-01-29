"""
GÃ©nÃ©rateur V2 de StratÃ©gies d'Options
======================================

GÃ©nÃ¨re toutes les combinaisons de stratÃ©gies d'options via le module C++.
Le traitement est entiÃ¨rement dÃ©lÃ©guÃ© au batch processor C++ pour des performances optimales.
"""

from typing import List, Tuple
from myproject.option.option_class import Option
from myproject.strategy.strategy_class import StrategyComparison
from myproject.strategy.batch_processor import generate_all_strategies_batch
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

    def generate_all_combinations(
        self, 
        filter: FilterData, 
        max_legs: int = 4,
        progress_tracker=None,
    ) -> Tuple[List[StrategyComparison], int]:
        """
        GÃ©nÃ¨re toutes les combinaisons possibles d'options (1 Ã  max_legs).
        
        DÃ©lÃ¨gue le traitement au batch processor C++ pour des performances optimales.
        
        Args:
            price_min: Prix minimum pour le range (non utilisÃ© - dÃ©fini dans les options)
            price_max: Prix maximum pour le range (non utilisÃ© - dÃ©fini dans les options)
            filter: Filtres Ã  appliquer aux stratÃ©gies
            max_legs: Nombre maximum de legs par stratÃ©gie (1 Ã  4)
            progress_tracker: Tracker de progression optionnel
            
        Returns:
            Tuple[List[StrategyComparison], int]: 
                - Liste des stratÃ©gies valides
                - Nombre total de combinaisons testÃ©es
        """        
        strategies, grand_total = generate_all_strategies_batch(
            progress_tracker,
            self.options, 
            filter, 
            max_legs
        )
        return strategies, grand_total

