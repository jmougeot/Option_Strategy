"""
Workflow Principal - Bloomberg to Strategy Comparison
======================================================
Ce module implémente le workflow complet :
1. Import des données Bloomberg
2. Conversion en objets Option
3. Génération de toutes les stratégies possibles
4. Comparaison et ranking des stratégies

Utilise les fonctions optimisées des modules :
- option_generator_v2.OptionStrategyGeneratorV2
- comparor_v2.StrategyComparerV2
"""

from typing import List, Dict, Optional, Tuple
import numpy as np
from myproject.strategy.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.strategy.comparor_v2 import StrategyComparerV2
from myproject.strategy.comparison_class import StrategyComparison
from myproject.bloomberg.bloomberg_data_importer import import_euribor_options
from myproject.app.widget import ScenarioData
from myproject.mixture.mixture_gaussienne import mixture
from myproject.mixture.gauss import gaussian


def create_mixture_from_scenarios(
    scenarios: ScenarioData,
    price_min: float,
    price_max: float,
    num_points: int = 500
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crée une mixture gaussienne à partir des scénarios définis par l'utilisateur.
    
    Utilise les fonctions du module mixture_gaussienne pour créer une distribution
    de probabilité à partir de plusieurs gaussiennes pondérées.
    
    Args:
        scenarios: ScenarioData avec centers, std_devs, weights
        price_min: Prix minimum de la grille
        price_max: Prix maximum de la grille
        num_points: Nombre de points dans la grille
        
    Returns:
        (prices, mixture_normalized): Grille de prix et mixture gaussienne normalisée
    """
    if not scenarios or not scenarios.centers:
        # Retourner une mixture uniforme par défaut
        prices = np.linspace(price_min, price_max, num_points)
        uniform_mixture = np.ones_like(prices) / num_points
        return prices, uniform_mixture
    
    # Extraire les paramètres des scénarios
    centers = scenarios.centers
    std_devs = scenarios.std_devs
    weights = scenarios.weights
    
    # Normaliser les poids pour qu'ils somment à 1
    total_weight = sum(weights)
    if total_weight > 0:
        proba = [w / total_weight for w in weights]
    else:
        # Poids égaux si tous sont à 0
        proba = [1.0 / len(weights)] * len(weights)
    
    # Utiliser la fonction mixture du module mixture_gaussienne
    prices, mix = mixture(
        price_min=price_min,
        price_max=price_max,
        num_points=num_points,
        proba=proba,
        mus=centers,
        sigmas=std_devs,
        f=gaussian  # Fonction gaussienne du module gauss
    )
    
    # Normaliser la mixture pour que l'intégrale soit 1
    norm = float(np.trapz(mix, prices))
    if norm > 0:
        mix = mix / norm
    
    return prices, mix


def process_bloomberg_to_strategies(
    underlying: str = "ER",
    months: List[str] = [],
    years: List[int] = [],
    strikes: List[float] = [],
    target_price: float = 0.0,
    price_min: float = 0.0,
    price_max: float = 100.0,
    max_legs: int = 4,
    top_n: int = 10,
    scoring_weights: Optional[Dict[str, float]] = None,
    verbose: bool = False
) -> Tuple[List[StrategyComparison], Dict]:
    """
    Fonction principale simplifiée pour Streamlit.
    Importe les options depuis Bloomberg et retourne les meilleures stratégies + stats.
    
    Args:
        underlying: Symbole du sous-jacent (ex: "ER")
        months: Liste des mois Bloomberg (ex: ['M', 'U'])
        years: Liste des années (ex: [6, 7])
        strikes: Liste des strikes
        target_price: Prix cible
        price_min: Prix minimum
        price_max: Prix maximum
        max_legs: Nombre max de legs par stratégie
        top_n: Nombre de meilleures stratégies à retourner
        scoring_weights: Poids personnalisés pour le scoring
        verbose: Affichage détaillé
    """
    stats = {}
    
    # ÉTAPE 1 : Import Bloomberg → Options
    if verbose:
        print("📥 Import des options depuis Bloomberg...")
    
    options = import_euribor_options(
        underlying=underlying,
        months=months,
        years=years,
        strikes=strikes,
        default_position='long',
        default_quantity=1,
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
