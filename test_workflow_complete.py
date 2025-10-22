"""
Test du Workflow Complet - Bloomberg to Strategies
==================================================
Ce script teste le workflow complet intégré dans main.py
"""

from myproject.option.main import run_complete_workflow

# Données Bloomberg de test (simulées)
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
        'symbol': 'EURIBOR'
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
        'symbol': 'EURIBOR'
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
        'symbol': 'EURIBOR'
    },
    {
        'option_type': 'call',
        'strike': 110.0,
        'premium': 1.5,
        'delta': 0.15,
        'gamma': 0.02,
        'vega': 0.20,
        'theta': -0.03,
        'implied_volatility': 0.22,
        'month_of_expiration': 3,
        'year_of_expiration': 2025,
        'symbol': 'EURIBOR'
    },
    {
        'option_type': 'put',
        'strike': 90.0,
        'premium': 1.5,
        'delta': -0.15,
        'gamma': 0.02,
        'vega': 0.20,
        'theta': -0.03,
        'implied_volatility': 0.27,
        'month_of_expiration': 3,
        'year_of_expiration': 2025,
        'symbol': 'EURIBOR'
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
        'symbol': 'EURIBOR'
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
        'symbol': 'EURIBOR'
    },
    {
        'option_type': 'put',
        'strike': 105.0,
        'premium': 7.0,
        'delta': -0.70,
        'gamma': 0.03,
        'vega': 0.25,
        'theta': -0.05,
        'implied_volatility': 0.24,
        'month_of_expiration': 3,
        'year_of_expiration': 2025,
        'symbol': 'EURIBOR'
    }
]

if __name__ == "__main__":
    print("🧪 TEST DU WORKFLOW COMPLET")
    print("=" * 80)
    print("Configuration du test:")
    print(f"  - Options: {len(test_bloomberg_data)} (4 calls, 4 puts)")
    print(f"  - Prix cible: 100.0")
    print(f"  - Intervalle: 80.0 - 120.0")
    print(f"  - Max legs: 4")
    print(f"  - Top N: 10")
    print("=" * 80 + "\n")
    
    # Exécuter le workflow
    best_strategies = run_complete_workflow(
        bloomberg_data=test_bloomberg_data,
        target_price=100.0,
        price_min=80.0,
        price_max=120.0,
        max_legs=4,
        top_n=10
    )
    
    # Affichage détaillé du Top 3
    print("\n" + "=" * 80)
    print("🏆 DÉTAILS DU TOP 3")
    print("=" * 80)
    
    for i, strat in enumerate(best_strategies[:3], 1):
        print(f"\n{'─' * 80}")
        print(f"#{i} - {strat.strategy_name}")
        print(f"{'─' * 80}")
        print(f"📊 Score Global: {strat.score:.4f}")
        print(f"\n💰 Métriques Financières:")
        print(f"   • Max Profit: ${strat.max_profit:.2f}")
        print(f"   • Max Loss: ${strat.max_loss:.2f}")
        print(f"   • Risk/Reward: {strat.risk_reward_ratio:.2f}")
        print(f"   • P&L @ Target: ${strat.profit_at_target:.2f} ({strat.profit_at_target_pct:.1f}%)")
        
        if strat.profit_zone_width != float('inf'):
            print(f"   • Profit Zone Width: ${strat.profit_zone_width:.2f}")
        
        if strat.breakeven_points:
            be_str = ", ".join([f"${be:.2f}" for be in strat.breakeven_points])
            print(f"   • Breakeven Points: {be_str}")
        
        print(f"\n📈 Surfaces:")
        print(f"   • Profit Surface: {strat.surface_profit:.2f}")
        print(f"   • Loss Surface: {strat.surface_loss:.2f}")
        if strat.surface_loss > 0:
            pl_ratio = strat.surface_profit / strat.surface_loss
            print(f"   • P/L Ratio: {pl_ratio:.2f}")
        
        print(f"\n🔢 Greeks:")
        print(f"   • Delta: {strat.total_delta:.3f}")
        print(f"   • Gamma: {strat.total_gamma:.3f}")
        print(f"   • Vega: {strat.total_vega:.3f}")
        print(f"   • Theta: {strat.total_theta:.3f}")
        
        print(f"\n📋 Composition:")
        for j, opt in enumerate(strat.all_options, 1):
            print(f"   {j}. {opt.position.upper()} {opt.option_type.upper()} @ ${opt.strike:.2f} (Premium: ${opt.premium:.2f})")
    
    print("\n" + "=" * 80)
    print(f"✅ Test terminé avec succès!")
    print(f"   {len(best_strategies)} stratégies ont été classées")
    print("=" * 80)
