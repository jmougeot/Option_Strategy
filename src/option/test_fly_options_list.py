"""
Test de la génération de liste d'options pour les Butterflies
==============================================================
Démontre l'utilisation de get_options_list() pour obtenir directement
une liste d'options standardisée prête à utiliser.
"""

from fly_generator import FlyGenerator
from datetime import datetime


def create_test_data():
    """Crée des données de test simulant Bloomberg"""
    calls = []
    puts = []
    
    # Strikes de 95.0 à 105.0 par pas de 0.25
    strikes = [95.0 + i * 0.25 for i in range(41)]  # 41 strikes
    expiration = "2025-03-21"
    
    for strike in strikes:
        # Call option
        call = {
            'symbol': f'TEST{strike}C',
            'strike': strike,
            'option_type': 'call',
            'premium': max(0.1, 100.0 - strike + (strike - 100) * 0.3),  # Simulation
            'expiration_date': expiration,
            'underlying_price': 100.0,
            'bid': max(0.05, 99.5 - strike),
            'ask': max(0.15, 100.5 - strike),
            'volume': 1000,
            'open_interest': 5000,
            'implied_volatility': 0.25,
            'delta': min(1.0, max(0.0, 0.5 + (100 - strike) * 0.02)),
            'gamma': 0.05,
            'theta': -0.03,
            'vega': 0.15,
            'rho': 0.02,
            'timestamp': datetime.now()
        }
        calls.append(call)
        
        # Put option
        put = {
            'symbol': f'TEST{strike}P',
            'strike': strike,
            'option_type': 'put',
            'premium': max(0.1, strike - 100.0 + (100 - strike) * 0.3),
            'expiration_date': expiration,
            'underlying_price': 100.0,
            'bid': max(0.05, strike - 99.5),
            'ask': max(0.15, strike - 100.5),
            'volume': 800,
            'open_interest': 4000,
            'implied_volatility': 0.25,
            'delta': max(-1.0, min(0.0, -0.5 + (100 - strike) * 0.02)),
            'gamma': 0.05,
            'theta': -0.03,
            'vega': 0.15,
            'rho': -0.02,
            'timestamp': datetime.now()
        }
        puts.append(put)
    
    return {'calls': calls, 'puts': puts}


def test_get_options_list():
    """Test principal: obtenir une liste d'options"""
    print("=" * 80)
    print("TEST: get_options_list() - Retour d'une liste d'options standardisée")
    print("=" * 80)
    print()
    
    # 1. Créer les données de test
    print("1. Création des données de test...")
    options_data = create_test_data()
    print(f"   ✓ {len(options_data['calls'])} calls")
    print(f"   ✓ {len(options_data['puts'])} puts")
    print()
    
    # 2. Initialiser le générateur
    print("2. Initialisation du générateur...")
    generator = FlyGenerator(options_data)
    print("   ✓ FlyGenerator initialisé")
    print()
    
    # 3. Obtenir la liste d'options pour les Flies
    print("3. Génération de la liste d'options (Call Butterflies)...")
    options_list = generator.get_options_list(
        price_min=99.0,
        price_max=101.0,
        strike_min=97.0,
        strike_max=103.0,
        option_type='call',
        require_symmetric=True,
        min_wing_width=0.5,
        max_wing_width=2.0
    )
    
    print(f"   ✓ {len(options_list)} options générées")
    print()
    
    # 4. Analyser le contenu
    print("4. Analyse du contenu de la liste d'options:")
    print("-" * 80)
    
    if options_list:
        # Afficher les premières options
        print(f"\n   Aperçu des {min(5, len(options_list))} premières options:\n")
        for i, opt in enumerate(options_list[:5], 1):
            print(f"   Option {i}:")
            print(f"      Strike: {opt['strike']}")
            print(f"      Premium: {opt['premium']:.4f}")
            print(f"      Type: {opt['option_type']}")
            print(f"      Expiration: {opt['expiration_date']}")
            print(f"      Delta: {opt.get('delta', 'N/A')}")
            print(f"      IV: {opt.get('implied_volatility', 'N/A')}")
            print()
        
        # Statistiques
        print("   Statistiques de la liste:")
        strikes = sorted(set(opt['strike'] for opt in options_list))
        print(f"      Nombre total d'options: {len(options_list)}")
        print(f"      Strikes uniques: {len(strikes)}")
        print(f"      Strike min: {min(strikes)}")
        print(f"      Strike max: {max(strikes)}")
        print(f"      Premium moyen: {sum(opt['premium'] for opt in options_list) / len(options_list):.4f}")
    else:
        print("   ⚠️ Aucune option générée")
    
    print()
    print("-" * 80)
    print()
    
    # 5. Test avec Put Butterflies
    print("5. Génération pour Put Butterflies...")
    put_options = generator.get_options_list(
        price_min=99.0,
        price_max=101.0,
        strike_min=97.0,
        strike_max=103.0,
        option_type='put',
        require_symmetric=False,  # Tous les Flies (symétriques et asymétriques)
        min_wing_width=0.25,
        max_wing_width=3.0
    )
    
    print(f"   ✓ {len(put_options)} options put générées")
    print()
    
    # 6. Comparaison dédupliquée vs non-dédupliquée
    print("6. Test de déduplication:")
    non_dedup = generator.get_options_list(
        price_min=99.0,
        price_max=101.0,
        strike_min=97.0,
        strike_max=103.0,
        option_type='call',
        deduplicate=False
    )
    
    dedup = generator.get_options_list(
        price_min=99.0,
        price_max=101.0,
        strike_min=97.0,
        strike_max=103.0,
        option_type='call',
        deduplicate=True
    )
    
    print(f"   Sans déduplication: {len(non_dedup)} options")
    print(f"   Avec déduplication: {len(dedup)} options")
    print(f"   Réduction: {len(non_dedup) - len(dedup)} options éliminées")
    print()
    
    # 7. Validation du format
    print("7. Validation du format standardisé:")
    required_fields = ['strike', 'premium', 'expiration_date', 'option_type']
    if options_list:
        sample = options_list[0]
        missing = [field for field in required_fields if field not in sample]
        
        if not missing:
            print("   ✓ Tous les champs obligatoires présents")
            print(f"   ✓ Champs disponibles: {', '.join(sample.keys())}")
        else:
            print(f"   ⚠️ Champs manquants: {missing}")
    
    print()
    print("=" * 80)
    print("TEST TERMINÉ")
    print("=" * 80)
    print()
    print("💡 UTILISATION:")
    print("   Cette liste d'options peut être utilisée directement avec:")
    print("   - StrategyComparer(options_list)")
    print("   - Analyse de stratégies complexes")
    print("   - Export vers Excel/CSV")
    print("   - Intégration avec d'autres modules")
    print()
    
    return options_list


if __name__ == "__main__":
    test_get_options_list()
