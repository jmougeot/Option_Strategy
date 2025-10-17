"""
Test du Multi-Structure Comparer dans app.py
=============================================
Vérifie que le nouveau comparateur est correctement intégré.
"""

import sys
from pathlib import Path

# Ajouter le chemin src au PYTHONPATH
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

from option.multi_structure_comparer import MultiStructureComparer
from datetime import datetime


def create_test_data():
    """Crée des données de test simulant Bloomberg"""
    calls = []
    puts = []
    
    strikes = [96.0, 96.5, 97.0, 97.5, 98.0, 98.5, 99.0, 99.5, 100.0, 100.5, 101.0, 101.5, 102.0, 102.5, 103.0]
    expiration = "2025-03-21"
    
    for strike in strikes:
        # Call
        call = {
            'strike': strike,
            'option_type': 'call',
            'premium': max(0.1, 100.0 - strike),
            'expiration_date': expiration,
            'underlying_price': 100.0,
            'bid': max(0.05, 99.8 - strike),
            'ask': max(0.15, 100.2 - strike),
            'volume': 1000,
            'open_interest': 5000,
            'implied_volatility': 0.25,
            'delta': 0.5,
            'gamma': 0.05,
            'theta': -0.03,
            'vega': 0.15,
            'rho': 0.02
        }
        calls.append(call)
        
        # Put
        put = {
            'strike': strike,
            'option_type': 'put',
            'premium': max(0.1, strike - 100.0),
            'expiration_date': expiration,
            'underlying_price': 100.0,
            'bid': max(0.05, strike - 99.8),
            'ask': max(0.15, strike - 100.2),
            'volume': 800,
            'open_interest': 4000,
            'implied_volatility': 0.25,
            'delta': -0.5,
            'gamma': 0.05,
            'theta': -0.03,
            'vega': 0.15,
            'rho': -0.02
        }
        puts.append(put)
    
    return {'calls': calls, 'puts': puts}


def test_integration():
    """Test d'intégration du comparateur"""
    print("=" * 80)
    print("TEST D'INTÉGRATION - Multi-Structure Comparer")
    print("=" * 80)
    print()
    
    # 1. Créer les données
    print("1. Création des données de test...")
    options_data = create_test_data()
    print(f"   ✓ {len(options_data['calls'])} calls")
    print(f"   ✓ {len(options_data['puts'])} puts")
    print()
    
    # 2. Initialiser le comparateur
    print("2. Initialisation du Multi-Structure Comparer...")
    comparer = MultiStructureComparer(options_data)
    print("   ✓ Comparateur initialisé")
    print()
    
    # 3. Comparer toutes les structures
    print("3. Comparaison de toutes les structures...")
    results = comparer.compare_all_structures(
        target_price=100.0,
        strike_min=96.0,
        strike_max=104.0,
        days_to_expiry=30,
        include_flies=True,
        include_condors=True,
        require_symmetric=True,
        top_n=10
    )
    
    print(f"   ✓ {len(results)} structures analysées")
    print()
    
    # 4. Afficher les résultats
    print("4. Affichage des résultats:")
    print()
    comparer.display_comparison(results)
    
    # 5. Vérifier les propriétés
    print("5. Vérification des propriétés StrategyComparison:")
    print("-" * 80)
    if results:
        best = results[0]
        print(f"   Nom: {best.strategy_name}")
        print(f"   Prix cible: ${best.target_price:.2f}")
        print(f"   Crédit net: ${best.net_credit:.4f}")
        print(f"   Max profit: ${best.max_profit:.4f}")
        print(f"   Max loss: ${best.max_loss:.4f}")
        print(f"   Risk/Reward: {best.risk_reward_ratio:.2f}")
        print(f"   Zone de profit: ${best.profit_zone_width:.2f}")
        print(f"   Breakevens: {[f'${be:.2f}' for be in best.breakeven_points]}")
        print(f"   Score: {best.score:.3f}")
        print(f"   Rang: {best.rank}")
    print()
    
    # 6. Résumé
    print("=" * 80)
    print("RÉSUMÉ DU TEST")
    print("=" * 80)
    print()
    if results:
        fly_count = sum(1 for r in results if 'Fly' in r.strategy_name)
        condor_count = sum(1 for r in results if 'Condor' in r.strategy_name)
        
        print(f"✅ Test réussi !")
        print(f"   • {len(results)} structures comparées")
        print(f"   • {fly_count} Butterflies")
        print(f"   • {condor_count} Condors")
        print(f"   • Meilleure structure: {results[0].strategy_name}")
        print(f"   • Score maximum: {results[0].score:.3f}")
    else:
        print("⚠️ Aucune structure générée")
    
    print()
    print("💡 Prêt pour intégration dans app.py !")
    print()


if __name__ == "__main__":
    test_integration()
