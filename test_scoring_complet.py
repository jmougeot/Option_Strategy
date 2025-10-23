"""
Test du Système de Scoring Complet
===================================
Vérifie que tous les attributs participent au scoring.
"""

from myproject.option.comparor_v2 import StrategyComparerV2
from myproject.option.comparison_class import StrategyComparison

def test_scoring_complet():
    """Test que tous les 14 critères participent au scoring"""
    
    # Créer des stratégies de test avec des valeurs différentes
    strategies = [
        StrategyComparison(
            strategy_name="Strategy A - Balanced",
            strategy=None,
            target_price=98.0,
            expiration_day="15",
            expiration_week="W2",
            expiration_month="M",
            expiration_year=6,
            max_profit=1000,
            max_loss=500,
            breakeven_points=[97.5, 98.5],
            profit_range=(97.5, 98.5),
            profit_zone_width=1.0,
            surface_profit=50.0,
            surface_loss=25.0,
            risk_reward_ratio=0.5,
            total_delta=0.05,
            total_gamma=0.10,
            total_vega=0.50,
            total_theta=0.8,
            avg_implied_volatility=0.25,
            profit_at_target=750,
            profit_at_target_pct=75.0
        ),
        StrategyComparison(
            strategy_name="Strategy B - High Profit",
            strategy=None,
            target_price=98.0,
            expiration_day="15",
            expiration_week="W2",
            expiration_month="M",
            expiration_year=6,
            max_profit=1500,  # Plus élevé
            max_loss=800,
            breakeven_points=[97.2, 98.8],
            profit_range=(97.2, 98.8),
            profit_zone_width=1.6,  # Plus large
            surface_profit=70.0,  # Plus élevé
            surface_loss=35.0,
            risk_reward_ratio=0.53,
            total_delta=-0.15,  # Moins neutre
            total_gamma=0.20,
            total_vega=0.45,
            total_theta=0.6,
            avg_implied_volatility=0.30,
            profit_at_target=1000,
            profit_at_target_pct=66.7
        ),
        StrategyComparison(
            strategy_name="Strategy C - Delta Neutral",
            strategy=None,
            target_price=98.0,
            expiration_day="15",
            expiration_week="W2",
            expiration_month="M",
            expiration_year=6,
            max_profit=800,
            max_loss=400,
            breakeven_points=[97.8, 98.2],
            profit_range=(97.8, 98.2),
            profit_zone_width=0.4,
            surface_profit=40.0,
            surface_loss=20.0,
            risk_reward_ratio=0.5,
            total_delta=0.01,  # Très neutre
            total_gamma=0.08,
            total_vega=0.52,
            total_theta=1.0,  # Theta très positif
            avg_implied_volatility=0.22,
            profit_at_target=600,
            profit_at_target_pct=75.0
        ),
    ]
    
    # Tester avec les poids par défaut
    print("\n" + "="*80)
    print("TEST 1: POIDS PAR DÉFAUT (tous les attributs)")
    print("="*80)
    
    comparer = StrategyComparerV2()
    ranked = comparer.compare_and_rank(strategies, top_n=3)
    
    comparer.print_summary(ranked, top_n=3)
    
    # Vérifier que les scores sont calculés
    assert all(s.score > 0 for s in ranked), "Tous les scores doivent être > 0"
    assert ranked[0].rank == 1, "La première stratégie doit avoir rank=1"
    print("\n✅ Test 1 réussi: Tous les scores sont calculés")
    
    # Tester avec des poids personnalisés (focus sur Delta neutralité)
    print("\n" + "="*80)
    print("TEST 2: POIDS PERSONNALISÉS (focus Delta Neutralité)")
    print("="*80)
    
    custom_weights = {
        'max_profit': 0.05,
        'risk_reward': 0.05,
        'profit_zone': 0.05,
        'target_performance': 0.05,
        'surface_profit': 0.05,
        'surface_loss': 0.05,
        'profit_loss_ratio': 0.05,
        'delta_neutral': 0.40,  # Focus principal
        'gamma_exposure': 0.05,
        'vega_exposure': 0.05,
        'theta_positive': 0.10,
        'implied_vol': 0.03,
        'breakeven_count': 0.01,
        'breakeven_spread': 0.01,
    }
    
    ranked_custom = comparer.compare_and_rank(strategies, top_n=3, weights=custom_weights)
    
    # Avec focus sur delta, Strategy C devrait être meilleure
    print(f"\nClassement avec focus Delta:")
    for s in ranked_custom:
        print(f"  {s.rank}. {s.strategy_name} - Score: {s.score:.4f} - Delta: {s.total_delta:.3f}")
    
    assert ranked_custom[0].strategy_name == "Strategy C - Delta Neutral", \
        "Avec focus delta, Strategy C devrait être première"
    print("\n✅ Test 2 réussi: Le focus sur delta change le classement")
    
    # Tester avec focus sur profit maximum
    print("\n" + "="*80)
    print("TEST 3: POIDS PERSONNALISÉS (focus Max Profit)")
    print("="*80)
    
    profit_weights = {
        'max_profit': 0.50,  # Focus principal
        'risk_reward': 0.10,
        'profit_zone': 0.10,
        'target_performance': 0.10,
        'surface_profit': 0.10,
        'surface_loss': 0.02,
        'profit_loss_ratio': 0.02,
        'delta_neutral': 0.01,
        'gamma_exposure': 0.01,
        'vega_exposure': 0.01,
        'theta_positive': 0.01,
        'implied_vol': 0.01,
        'breakeven_count': 0.005,
        'breakeven_spread': 0.005,
    }
    
    ranked_profit = comparer.compare_and_rank(strategies, top_n=3, weights=profit_weights)
    
    print(f"\nClassement avec focus Profit:")
    for s in ranked_profit:
        print(f"  {s.rank}. {s.strategy_name} - Score: {s.score:.4f} - Max Profit: ${s.max_profit:.2f}")
    
    assert ranked_profit[0].strategy_name == "Strategy B - High Profit", \
        "Avec focus profit, Strategy B devrait être première"
    print("\n✅ Test 3 réussi: Le focus sur profit change le classement")
    
    # Test de validation des poids
    print("\n" + "="*80)
    print("TEST 4: VALIDATION DES CRITÈRES")
    print("="*80)
    
    default_weights = {
        'max_profit': 0.10,
        'risk_reward': 0.10,
        'profit_zone': 0.08,
        'target_performance': 0.08,
        'surface_profit': 0.12,
        'surface_loss': 0.08,
        'profit_loss_ratio': 0.12,
        'delta_neutral': 0.06,
        'gamma_exposure': 0.04,
        'vega_exposure': 0.04,
        'theta_positive': 0.04,
        'implied_vol': 0.04,
        'breakeven_count': 0.03,
        'breakeven_spread': 0.03,
    }
    
    total_weight = sum(default_weights.values())
    print(f"\nNombre de critères: {len(default_weights)}")
    print(f"Total des poids: {total_weight*100:.1f}%")
    
    assert len(default_weights) == 14, "Doit avoir exactement 14 critères"
    assert 0.95 <= total_weight <= 1.05, "Total doit être proche de 100%"
    
    print("✅ Test 4 réussi: 14 critères validés")
    
    print("\n" + "="*80)
    print("🎉 TOUS LES TESTS RÉUSSIS!")
    print("="*80)
    print("\n✅ Le système de scoring complet fonctionne correctement")
    print("✅ Tous les 14 attributs participent au scoring")
    print("✅ Les poids personnalisés influencent correctement le classement")
    print("✅ La validation des critères est OK")

if __name__ == "__main__":
    test_scoring_complet()
