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

from typing import List, Dict, Optional, Literal
from myproject.option.option_class import Option
from myproject.option.dic_to_option import bloomberg_data_to_options
from myproject.option.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.option.comparor_v2 import StrategyComparerV2
from myproject.option.comparison_class import StrategyComparison


def run_complete_workflow(
    bloomberg_data: List[Dict],
    target_price: float,
    price_min: float,
    price_max: float,
    max_legs: int = 4,
    top_n: int = 10,
    default_position: Literal['long', 'short'] = 'long',
    scoring_weights: Optional[Dict[str, float]] = None
) -> List[StrategyComparison]:
    """
    Exécute le workflow complet Bloomberg → Options → Stratégies → Ranking
    
    Args:
        bloomberg_data: Liste de dictionnaires avec les données Bloomberg
        target_price: Prix cible du sous-jacent
        price_min: Prix minimum pour le calcul des surfaces
        price_max: Prix maximum pour le calcul des surfaces
        max_legs: Nombre maximum d'options dans une combinaison (1-4)
        top_n: Nombre de meilleures stratégies à retourner
        default_position: Position par défaut ('long' ou 'short')
        scoring_weights: Poids personnalisés pour le scoring (optionnel)
    
    Returns:
        Liste des top_n meilleures stratégies, classées par score
    
    Example:
        >>> from myproject.bloomberg_data_importer import import_euribor_options
        >>> data = import_euribor_options(
        ...     underlying='EURIBOR',
        ...     months=['F', 'G', 'H'],
        ...     years=[2025],
        ...     strikes=[95.0, 100.0, 105.0]
        ... )
        >>> best_strategies = run_complete_workflow(
        ...     bloomberg_data=data['options'],
        ...     target_price=100.0,
        ...     price_min=85.0,
        ...     price_max=115.0,
        ...     max_legs=4,
        ...     top_n=10
        ... )
        >>> for s in best_strategies[:5]:
        ...     print(f"#{s.rank}: {s.strategy_name} - Score: {s.score:.3f}")
    """
    print("=" * 80)
    print("🚀 WORKFLOW COMPLET BLOOMBERG → STRATÉGIES")
    print("=" * 80)
    
    # ===== ÉTAPE 1 : CONVERSION BLOOMBERG → OPTIONS =====
    print("\n📥 ÉTAPE 1 : Conversion des données Bloomberg en Options")
    print("-" * 80)
    
    options = bloomberg_data_to_options(
        bloomberg_data=bloomberg_data,
        default_position=default_position,
        default_quantity=1,
        price_min=price_min,
        price_max=price_max,
        calculate_surfaces=False  # Les surfaces seront calculées par le générateur
    )
    
    if not options:
        print("❌ Aucune option valide après conversion")
        return []
    
    print(f"✅ {len(options)} options converties avec succès")
    
    # ===== ÉTAPE 2 : GÉNÉRATION DES STRATÉGIES =====
    print("\n🔄 ÉTAPE 2 : Génération de toutes les combinaisons de stratégies")
    print("-" * 80)
    print(f"   Paramètres:")
    print(f"   - Options disponibles: {len(options)}")
    print(f"   - Legs maximum: {max_legs}")
    print(f"   - Prix cible: ${target_price:.2f}")
    print(f"   - Intervalle prix: ${price_min:.2f} - ${price_max:.2f}")
    
    generator = OptionStrategyGeneratorV2(options)
    
    all_strategies = generator.generate_all_combinations(
        target_price=target_price,
        price_min=price_min,
        price_max=price_max,
        max_legs=max_legs,
        include_long=True,
        include_short=True
    )
    
    if not all_strategies:
        print("❌ Aucune stratégie générée")
        return []
    
    print(f"✅ {len(all_strategies)} stratégies générées au total")
    
    # ===== ÉTAPE 3 : COMPARAISON ET RANKING =====
    print("\n📊 ÉTAPE 3 : Comparaison et ranking des stratégies")
    print("-" * 80)
    
    comparer = StrategyComparerV2()
    
    best_strategies = comparer.compare_and_rank(
        strategies=all_strategies,
        top_n=top_n,
        weights=scoring_weights
    )
    
    if not best_strategies:
        print("❌ Aucune stratégie classée")
        return []
    
    # ===== AFFICHAGE DES RÉSULTATS =====
    print("\n" + "=" * 80)
    print(f"🏆 TOP {len(best_strategies)} STRATÉGIES")
    print("=" * 80)
    
    for strat in best_strategies[:5]:
        print(f"\n#{strat.rank} - {strat.strategy_name}")
        print(f"   Score: {strat.score:.4f}")
        print(f"   Max Profit: ${strat.max_profit:.2f} | Max Loss: ${strat.max_loss:.2f}")
        print(f"   Risk/Reward: {strat.risk_reward_ratio:.2f}")
        if strat.profit_zone_width != float('inf'):
            print(f"   Profit Zone: ${strat.profit_zone_width:.2f}")
        print(f"   P&L @ Target: ${strat.profit_at_target:.2f} ({strat.profit_at_target_pct:.1f}%)")
        
        if strat.surface_loss > 0:
            pl_ratio = strat.surface_profit / strat.surface_loss
            print(f"   Surf. Profit: {strat.surface_profit:.2f} | Surf. Loss: {strat.surface_loss:.2f} | Ratio: {pl_ratio:.2f}")
        
        print(f"   Greeks - Delta: {strat.total_delta:.3f} | Gamma: {strat.total_gamma:.3f} | Vega: {strat.total_vega:.3f}")
    
    print("\n" + "=" * 80)
    print(f"✅ Workflow terminé avec succès!")
    print(f"   {len(options)} options → {len(all_strategies)} stratégies → Top {len(best_strategies)} classées")
    print("=" * 80)
    
    return best_strategies


def run_workflow_with_target_prices(
    bloomberg_data: List[Dict],
    target_prices: List[float],
    price_min: float,
    price_max: float,
    max_legs: int = 4,
    top_n: int = 10,
    default_position: Literal['long', 'short'] = 'long',
    scoring_weights: Optional[Dict[str, float]] = None
) -> Dict[float, List[StrategyComparison]]:
    """
    Exécute le workflow pour plusieurs prix cibles et retourne les meilleures stratégies par prix.
    
    Args:
        bloomberg_data: Liste de dictionnaires avec les données Bloomberg
        target_prices: Liste des prix cibles à tester
        price_min: Prix minimum pour le calcul des surfaces
        price_max: Prix maximum pour le calcul des surfaces
        max_legs: Nombre maximum d'options dans une combinaison (1-4)
        top_n: Nombre de meilleures stratégies à retourner par prix
        default_position: Position par défaut ('long' ou 'short')
        scoring_weights: Poids personnalisés pour le scoring (optionnel)
    
    Returns:
        Dictionnaire {target_price: [stratégies classées]}
    """
    print("=" * 80)
    print("🚀 WORKFLOW MULTI-PRIX")
    print("=" * 80)
    print(f"   Nombre de prix cibles: {len(target_prices)}")
    print(f"   Intervalle: ${min(target_prices):.2f} - ${max(target_prices):.2f}")
    print("=" * 80 + "\n")
    
    results = {}
    
    for i, target_price in enumerate(target_prices, 1):
        print(f"\n{'=' * 80}")
        print(f"Prix cible {i}/{len(target_prices)}: ${target_price:.2f}")
        print(f"{'=' * 80}")
        
        best_strategies = run_complete_workflow(
            bloomberg_data=bloomberg_data,
            target_price=target_price,
            price_min=price_min,
            price_max=price_max,
            max_legs=max_legs,
            top_n=top_n,
            default_position=default_position,
            scoring_weights=scoring_weights
        )
        
        results[target_price] = best_strategies
    
    # Résumé global
    print("\n" + "=" * 80)
    print("📊 RÉSUMÉ GLOBAL - MEILLEURES STRATÉGIES PAR PRIX CIBLE")
    print("=" * 80)
    
    for target_price, strategies in results.items():
        if strategies:
            best = strategies[0]
            print(f"\n💰 Target: ${target_price:.2f}")
            print(f"   🏆 Meilleure: {best.strategy_name} (Score: {best.score:.4f})")
            print(f"   📈 Max Profit: ${best.max_profit:.2f} | R/R: {best.risk_reward_ratio:.2f}")
    
    print("\n" + "=" * 80)
    
    return results


if __name__ == "__main__":
    """
    Exemple d'utilisation du workflow complet
    """
    # Exemple avec des données de test
    print("🧪 Mode Test - Exemple d'utilisation\n")
    
    # Données Bloomberg simulées pour le test
    test_bloomberg_data = [
        {
            'option_type': 'call',
            'strike': 95.0,
            'premium': 7.5,
            'delta': 0.70,
            'gamma': 0.03,
            'vega': 0.25,
            'theta': -0.05,
            'implied_volatility': 0.25,
            'month_of_expiration': 3,
            'year_of_expiration': 2025,
            'symbol': 'TEST'
        },
        {
            'option_type': 'call',
            'strike': 100.0,
            'premium': 5.0,
            'delta': 0.50,
            'gamma': 0.04,
            'vega': 0.30,
            'theta': -0.06,
            'implied_volatility': 0.24,
            'month_of_expiration': 3,
            'year_of_expiration': 2025,
            'symbol': 'TEST'
        },
        {
            'option_type': 'call',
            'strike': 105.0,
            'premium': 3.0,
            'delta': 0.30,
            'gamma': 0.03,
            'vega': 0.25,
            'theta': -0.04,
            'implied_volatility': 0.23,
            'month_of_expiration': 3,
            'year_of_expiration': 2025,
            'symbol': 'TEST'
        },
        {
            'option_type': 'put',
            'strike': 95.0,
            'premium': 2.5,
            'delta': -0.25,
            'gamma': 0.03,
            'vega': 0.25,
            'theta': -0.04,
            'implied_volatility': 0.26,
            'month_of_expiration': 3,
            'year_of_expiration': 2025,
            'symbol': 'TEST'
        },
        {
            'option_type': 'put',
            'strike': 100.0,
            'premium': 4.5,
            'delta': -0.50,
            'gamma': 0.04,
            'vega': 0.30,
            'theta': -0.06,
            'implied_volatility': 0.25,
            'month_of_expiration': 3,
            'year_of_expiration': 2025,
            'symbol': 'TEST'
        }
    ]
    
    # Exécuter le workflow
    best_strategies = run_complete_workflow(
        bloomberg_data=test_bloomberg_data,
        target_price=100.0,
        price_min=85.0,
        price_max=115.0,
        max_legs=3,  # Limité à 3 pour le test
        top_n=10
    )
    
    print(f"\n✅ Test terminé : {len(best_strategies)} stratégies retournées")
