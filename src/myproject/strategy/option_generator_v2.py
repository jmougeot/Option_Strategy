"""
Générateur V2 de Stratégies d'Options
======================================
Version simplifiée qui prend une liste d'objets Option et génère toutes les
combinaisons possibles (1 à 4 options) pour créer des StrategyComparison.

Utilise itertools.combinations pour générer efficacement toutes les combinaisons.
"""

from itertools import product
from typing import List, Optional
from itertools import combinations_with_replacement
import numpy as np
from myproject.option.option_class import Option
from myproject.strategy.comparison_class import StrategyComparison
from myproject.strategy.calcul_linear_metrics import create_strategy_fast_with_signs
from myproject.option.option_filter import sort_options_by_expiration


class OptionStrategyGeneratorV2:
    """
    Génère toutes les stratégies possibles à partir d'une liste d'options.
    Teste toutes les combinaisons de 1 à 4 options avec différentes positions (long/short).
    """

    def __init__(self, options: List[Option]):
        """
        Initialise le générateur avec une liste d'options triées par expiration.

        Args:
            options: Liste d'objets Option récupérés depuis Bloomberg
        """
        # Trier les options par expiration une seule fois au début
        self.options = sort_options_by_expiration(options)
        self.price_min = None
        self.price_max = None

    def generate_all_combinations(
        self, target_price: float, price_min: float, price_max: float, max_legs: int = 4
    ) -> List[StrategyComparison]:
        """
        Génère toutes les combinaisons possibles d'options (1 à max_legs).
        """
        self.price_min = price_min
        self.price_max = price_max
        all_strategies = []

        for n_legs in range(1, max_legs + 1):
            print(f"🔄 Génération des stratégies à {n_legs} leg(s)...")

            # Générer toutes les combinaisons de n_legs options
            for combo in combinations_with_replacement(self.options, n_legs):
                # Pour chaque combinaison, tester différentes configurations de positions
                strategies = self._generate_position_variants(
                    list(combo),
                    target_price,
                )
                all_strategies.extend(strategies)

        print(f"{len(all_strategies)} stratégies générées au total")
        return all_strategies

    def _generate_position_variants(
        self,
        options: List[Option],
        target_price: float,
    ) -> List[StrategyComparison]:
        """
        Génère les variantes de positions pour une combinaison d'options.
        Teste long/short selon include_long/include_short.

        Note: Les options sont déjà triées par expiration dans __init__.
        On vérifie simplement que la première et la dernière ont la même date.
        """
        n = len(options)
        if n == 0:
            return []

        # Comme les options sont triées, si première == dernière, toutes sont identiques
        if n > 1:
            first, last = options[0], options[-1]
            # Vérifier année, mois, semaine ET jour
            if (
                first.expiration_year != last.expiration_year
                or first.expiration_month != last.expiration_month
                or first.expiration_week != last.expiration_week
                or first.expiration_day != last.expiration_day
            ):
                return []

        n = len(options)
        if n == 0:
            return []

        sign_space = list(product((-1, 1), repeat=n))
        strategies: List[StrategyComparison] = []

        # ===== Génération des stratégies =====
        for signs in sign_space:
            positions: List[str] = ["long" if s == -1 else "short" for s in signs]
            strat = self._create_strategy(options, positions, target_price)
            if strat:
                strategies.append(strat)
        return strategies

    def _create_strategy(
        self, options: List[Option], positions: List[str], target_price: float
    ) -> Optional[StrategyComparison]:
        """
        Crée un StrategyComparison à partir d'une combinaison d'options et de positions.

        OPTIMISÉ : Pas de copie ! Utilise les signes directement dans les calculs.

        Args:
            options: Liste d'options (peut contenir des doublons)
            positions: Liste des positions correspondantes ('long' ou 'short')
            target_price: Prix cible

        Returns:
            StrategyComparison ou None si la stratégie est invalide
        """
        try:
            # Convertir positions en signes numpy (+1 pour long, -1 pour short)
            signs = np.array(
                [1.0 if pos == "long" else -1.0 for pos in positions], dtype=np.float64
            )

            # Créer la stratégie SANS copier les options !
            strategy = create_strategy_fast_with_signs(options, signs, target_price)

            return strategy

        except Exception as e:
            print(f"⚠️ Erreur création stratégie: {e}")
            return None
