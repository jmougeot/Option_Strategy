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
        
        # Compteurs pour statistiques
        total_combos_tested = 0
        total_combos_filtered = 0

        for n_legs in range(1, max_legs + 1):
            print(f"🔄 Génération des stratégies à {n_legs} leg(s)...")
            combos_this_level = 0
            filtered_this_level = 0

            # Générer toutes les combinaisons de n_legs options
            for combo in combinations_with_replacement(self.options, n_legs):
                combos_this_level += 1
                # Pour chaque combinaison, tester différentes configurations de positions
                strategies = self._generate_position_variants(
                    list(combo),
                    target_price,
                )
                if not strategies:
                    filtered_this_level += 1
                all_strategies.extend(strategies)
            
            total_combos_tested += combos_this_level
            total_combos_filtered += filtered_this_level
            print(f"  ✓ {combos_this_level:,} combos testées, {filtered_this_level:,} filtrées ({filtered_this_level/combos_this_level*100:.1f}%)")

        print(f"\n📊 Résumé:")
        print(f"  • Total combos testées: {total_combos_tested:,}")
        print(f"  • Total combos filtrées: {total_combos_filtered:,} ({total_combos_filtered/total_combos_tested*100:.1f}%)")
        print(f"  • Stratégies générées: {len(all_strategies):,}")
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

        # OPTIMISATION CRITIQUE: Pré-filtrage des combinaisons impossibles
        # Calculer les Greeks totaux pour vérifier les limites AVANT de générer les positions
        # Extraire les valeurs une seule fois
        premiums = [opt.premium for opt in options]
        deltas = [opt.delta for opt in options]
        gammas = [opt.gamma for opt in options]
        average_pnls = [opt.average_pnl for opt in options]
        profit_surfaces = [opt.profit_surface_ponderated for opt in options]
        loss_surfaces = [opt.loss_surface_ponderated for opt in options]
        
        # Calculer les limites min/max (tous long vs tous short)
        total_premium_max = sum(premiums)  # Tous long (+1)
        total_premium_min = -total_premium_max  # Tous short (-1)
        
        # Filtre 1: Premium - Si AUCUNE combinaison de signes ne peut satisfaire
        if total_premium_min > 0.05 or total_premium_max < -0.1:
            return []
        
        # Filtre 2: Delta - Maximum absolu possible
        total_delta_max = sum(abs(d) for d in deltas)
        if total_delta_max > 1:
            return []
        
        # Filtre 3: Gamma - Maximum absolu possible
        total_gamma_max = sum(abs(g) for g in gammas)
        if total_gamma_max > 50:
            return []
        
        # Filtre 4: Average PnL - Le meilleur cas doit être positif
        total_average_pnl_max = sum(abs(a) for a in average_pnls)
        # Si même dans le meilleur cas (tout combiné positivement) c'est négatif
        if total_average_pnl_max < 0:
            return []
        
        # Filtre 5: Surfaces - Maximum absolu possible
        total_surface_max = sum(abs(p) + abs(l) for p, l in zip(profit_surfaces, loss_surfaces))
        if total_surface_max > 1000:
            return []

        # Générer directement les signes numpy (+1/-1) au lieu de strings "long"/"short"
        sign_space = list(product((-1.0, 1.0), repeat=n))
        strategies: List[StrategyComparison] = []

        # ===== Génération des stratégies =====
        for signs_tuple in sign_space:
            signs = np.array(signs_tuple, dtype=np.float64)
            strat = create_strategy_fast_with_signs(options, signs, target_price)
            if strat:
                strategies.append(strat)
        return strategies
