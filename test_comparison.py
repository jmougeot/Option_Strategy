"""
Script de Test - Comparaison de Stratégies
==========================================
Teste la comparaison de stratégies centrées autour d'un prix cible
"""

from strategy_comparison import StrategyComparer, StrategyComparison
from datetime import datetime, timedelta
import json

def test_strategy_comparison():
    """Test complet de comparaison de stratégies"""
    
    print("\n" + "="*80)
    print("TEST DE COMPARAISON DES STRATÉGIES SHORT VOLATILITY")
    print("="*80)
    
    # 1. Charger les données d'options
    print("\n📂 Chargement des données...")
    try:
        with open('calls_export.json', 'r') as f:
            data = json.load(f)
        print(f"✓ {len(data['options'])} options chargées")
    except FileNotFoundError:
        print("❌ Fichier calls_export.json non trouvé. Générez d'abord la base de données.")
        return
    
    # 2. Préparer les données (séparer calls et puts)
    calls = [opt for opt in data['options'] if opt['option_type'] == 'call']
    puts = [opt for opt in data['options'] if opt['option_type'] == 'put']
    
    options_data = {
        'calls': calls,
        'puts': puts
    }
    
    print(f"✓ Calls: {len(calls)}, Puts: {len(puts)}")
    
    if len(puts) == 0:
        print("⚠️  ATTENTION: Aucun put trouvé! Régénérez la base avec generate_full_database.py")
        return
    
    # 3. Initialiser le comparateur
    comparer = StrategyComparer(options_data)
    
    # 4. Définir les paramètres de comparaison
    print("\n⚙️  Paramètres de comparaison:")
    target_price = 100.0  # Prix actuel du sous-jacent
    days_to_expiry = 30   # Échéance à 30 jours
    
    print(f"   • Prix cible: ${target_price:.2f}")
    print(f"   • Jours jusqu'à expiration: {days_to_expiry}")
    
    # 5. Liste des stratégies à tester
    strategies_to_test = [
        'iron_condor',
        'iron_butterfly', 
        'short_strangle',
        'short_straddle'
    ]
    
    print(f"   • Stratégies testées: {', '.join(strategies_to_test)}")
    
    # 6. Poids pour le scoring
    weights = {
        'max_profit': 0.30,          # 30% - Profit maximum
        'risk_reward': 0.30,         # 30% - Ratio risque/rendement
        'profit_zone': 0.20,         # 20% - Largeur zone profitable
        'target_performance': 0.20   # 20% - Performance au prix cible
    }
    
    print("\n📊 Poids du scoring:")
    for metric, weight in weights.items():
        print(f"   • {metric}: {weight*100:.0f}%")
    
    # 7. Lancer la comparaison
    print("\n🔄 Comparaison en cours...")
    results = comparer.compare_strategies(
        target_price=target_price,
        days_to_expiry=days_to_expiry,
        strategies_to_compare=strategies_to_test,
        weights=weights
    )
    
    # 8. Afficher les résultats
    if not results:
        print("\n❌ Aucune stratégie n'a pu être construite.")
        print("💡 Conseil: Vérifiez que vous avez des options pour ~30 jours d'expiration")
        return
    
    print(f"\n✓ {len(results)} stratégies comparées avec succès!\n")
    
    # 9. Afficher le tableau de comparaison
    comparer.display_comparison(results)
    
    # 10. Analyse détaillée du gagnant
    print("\n" + "="*80)
    print("🏆 ANALYSE DÉTAILLÉE - STRATÉGIE GAGNANTE")
    print("="*80)
    
    winner = results[0]
    print(f"\nStratégie: {winner.strategy_name}")
    print(f"Score global: {winner.score:.4f}")
    print(f"\n📈 MÉTRIQUES FINANCIÈRES:")
    print(f"   • Crédit net reçu: ${winner.net_credit:.2f}")
    print(f"   • Profit maximum: ${winner.max_profit:.2f}")
    
    if winner.max_loss != -999999.0:
        print(f"   • Perte maximale: ${abs(winner.max_loss):.2f}")
        print(f"   • Ratio Risque/Rendement: {winner.risk_reward_ratio:.2f}:1")
    else:
        print(f"   • Perte maximale: Illimitée ⚠️")
        print(f"   • Ratio Risque/Rendement: Illimité")
    
    print(f"\n📍 POINTS DE BREAKEVEN:")
    if winner.breakeven_points:
        for i, be in enumerate(winner.breakeven_points, 1):
            print(f"   {i}. ${be:.2f}")
    
    print(f"\n🎯 ZONE PROFITABLE:")
    if winner.profit_zone_width != float('inf'):
        print(f"   • Largeur: ${winner.profit_zone_width:.2f}")
        print(f"   • Range: ${winner.profit_range[0]:.2f} - ${winner.profit_range[1]:.2f}")
    else:
        print(f"   • Range: Illimitée")
    
    print(f"\n💰 PERFORMANCE AU PRIX CIBLE (${target_price:.2f}):")
    print(f"   • P&L: ${winner.profit_at_target:.2f}")
    print(f"   • % du max profit: {winner.profit_at_target_pct:.1f}%")
    
    # 11. Comparaison des 3 meilleures
    if len(results) >= 3:
        print("\n" + "="*80)
        print("📊 TOP 3 DES STRATÉGIES")
        print("="*80)
        
        for i, comp in enumerate(results[:3], 1):
            print(f"\n{i}. {comp.strategy_name} (Score: {comp.score:.4f})")
            print(f"   Crédit: ${comp.net_credit:.2f} | P&L@Target: ${comp.profit_at_target:.2f}")
            
            if comp.max_loss != -999999.0:
                print(f"   Max Profit: ${comp.max_profit:.2f} | Max Loss: ${abs(comp.max_loss):.2f}")
            else:
                print(f"   Max Profit: ${comp.max_profit:.2f} | Max Loss: Illimité")
    
    # 12. Tester différents prix spot
    print("\n" + "="*80)
    print("📉 SIMULATION P&L À DIFFÉRENTS PRIX")
    print("="*80)
    
    test_prices = [
        target_price * 0.90,  # -10%
        target_price * 0.95,  # -5%
        target_price,         # Prix cible
        target_price * 1.05,  # +5%
        target_price * 1.10   # +10%
    ]
    
    print(f"\n{'Prix Spot':<12} ", end="")
    for comp in results[:3]:
        print(f"{comp.strategy_name[:15]:<18}", end="")
    print()
    print("-" * 70)
    
    for price in test_prices:
        pct_change = ((price - target_price) / target_price) * 100
        print(f"${price:<7.2f} ({pct_change:+.0f}%)  ", end="")
        
        for comp in results[:3]:
            pnl = comp.strategy.profit_at_expiry(price)
            print(f"${pnl:<10.2f}       ", end="")
        print()
    
    # 13. Recommandations
    print("\n" + "="*80)
    print("💡 RECOMMANDATIONS")
    print("="*80)
    
    winner = results[0]
    
    if "Condor" in winner.strategy_name or "Butterfly" in winner.strategy_name:
        print("\n✓ Stratégie à risque défini recommandée pour:")
        print("  • Marché range-bound attendu")
        print("  • Volatilité faible à moyenne")
        print("  • Exposition au risque contrôlée")
    elif "Straddle" in winner.strategy_name or "Strangle" in winner.strategy_name:
        print("\n⚠️  Stratégie à risque illimité - Prudence:")
        print("  • Nécessite surveillance active")
        print("  • Risque élevé si mouvement brusque")
        print("  • Considérer des stops ou ajustements")
    
    print("\n📋 Actions suggérées:")
    print(f"  1. Vérifier la liquidité des options pour {winner.strategy_name}")
    print(f"  2. Calculer la marge requise")
    print(f"  3. Définir un plan d'ajustement si le prix sort de la zone [{winner.profit_range[0]:.2f}, {winner.profit_range[1]:.2f}]")
    print(f"  4. Monitorer la volatilité implicite")
    
    print("\n" + "="*80)
    print("✅ TEST TERMINÉ")
    print("="*80)


if __name__ == "__main__":
    test_strategy_comparison()
