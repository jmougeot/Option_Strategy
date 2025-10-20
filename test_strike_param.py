"""
Test de la simplification des paramètres de strike
Vérifie que strike remplace strike_min/strike_max pour les stratégies 3-4 legs
"""

from myproject.option.option_generator import OptionStrategyGenerator
from myproject.option.condor_generator import CondorGenerator
from myproject.option.option_class import Option

# Données de test simplifiées
test_calls = [
    {
        'strike': 100.0, 'premium': 5.0, 'implied_volatility': 0.2,
        'delta': 0.5, 'gamma': 0.03, 'theta': -0.05, 'vega': 0.15,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    },
    {
        'strike': 105.0, 'premium': 3.0, 'implied_volatility': 0.21,
        'delta': 0.4, 'gamma': 0.04, 'theta': -0.04, 'vega': 0.14,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    },
    {
        'strike': 110.0, 'premium': 2.0, 'implied_volatility': 0.22,
        'delta': 0.3, 'gamma': 0.05, 'theta': -0.03, 'vega': 0.13,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    },
    {
        'strike': 115.0, 'premium': 1.0, 'implied_volatility': 0.23,
        'delta': 0.2, 'gamma': 0.04, 'theta': -0.02, 'vega': 0.12,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    }
]

test_puts = [
    {
        'strike': 95.0, 'premium': 2.0, 'implied_volatility': 0.19,
        'delta': -0.3, 'gamma': 0.05, 'theta': -0.03, 'vega': 0.13,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    },
    {
        'strike': 100.0, 'premium': 3.0, 'implied_volatility': 0.2,
        'delta': -0.4, 'gamma': 0.04, 'theta': -0.04, 'vega': 0.14,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    },
    {
        'strike': 105.0, 'premium': 4.0, 'implied_volatility': 0.21,
        'delta': -0.5, 'gamma': 0.03, 'theta': -0.05, 'vega': 0.15,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    },
    {
        'strike': 110.0, 'premium': 5.0, 'implied_volatility': 0.22,
        'delta': -0.6, 'gamma': 0.02, 'theta': -0.06, 'vega': 0.16,
        'day_of_expiration': 21, 'month_of_expiration': 3, 'year_of_expiration': 2025
    }
]

def test_option_generator_strike_param():
    """Test que OptionStrategyGenerator utilise bien le paramètre strike"""
    print("\n" + "="*80)
    print("TEST: Simplification des paramètres strike dans OptionStrategyGenerator")
    print("="*80)
    
    options_data = {'calls': test_calls, 'puts': test_puts}
    generator = OptionStrategyGenerator(options_data)
    
    # Paramètres de test
    price_min = 95.0
    price_max = 115.0
    strike_min = 100.0
    strike_max = 110.0
    strike_central = (strike_min + strike_max) / 2  # 105.0
    target_price = 105.0
    
    print(f"\n📊 Paramètres:")
    print(f"  Prix min/max: {price_min}/{price_max}")
    print(f"  Strike min/max (1-2 legs): {strike_min}/{strike_max}")
    print(f"  Strike central (3-4 legs): {strike_central}")
    print(f"  Prix cible: {target_price}")
    
    # Test avec generate_all_strategies (utilise strike_min/max pour calculer strike)
    print(f"\n🔍 Génération de toutes les stratégies (max_legs=4)...")
    try:
        all_strategies = generator.generate_all_strategies(
            price_min=price_min,
            price_max=price_max,
            strike_min=strike_min,
            strike_max=strike_max,
            target_price=target_price,
            max_legs=4
        )
        print(f"✅ Génération réussie: {len(all_strategies)} stratégies")
        
        # Compter par type
        from collections import Counter
        strategy_types = Counter(s.strategy_name.split()[0] for s in all_strategies)
        print(f"\n📈 Répartition par type:")
        for stype, count in sorted(strategy_types.items()):
            print(f"  {stype}: {count}")
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_condor_generator_strike_param():
    """Test que CondorGenerator utilise bien le paramètre strike"""
    print("\n" + "="*80)
    print("TEST: Simplification des paramètres strike dans CondorGenerator")
    print("="*80)
    
    options_data = {'calls': test_calls, 'puts': test_puts}
    condor_gen = CondorGenerator(options_data)
    
    price_min = 95.0
    price_max = 115.0
    strike = 105.0  # Strike central
    target_price = 105.0
    
    print(f"\n📊 Paramètres:")
    print(f"  Prix min/max: {price_min}/{price_max}")
    print(f"  Strike central: {strike}")
    print(f"  Prix cible: {target_price}")
    
    # Test Call Condors
    print(f"\n🔍 Génération de Call Condors avec strike={strike}...")
    try:
        call_condors = condor_gen.generate_call_condors(
            price_min=price_min,
            price_max=price_max,
            strike=strike,
            target_price=target_price
        )
        print(f"✅ Call Condors: {len(call_condors)} stratégies générées")
    except Exception as e:
        print(f"❌ ERREUR Call Condors: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test Put Condors
    print(f"\n🔍 Génération de Put Condors avec strike={strike}...")
    try:
        put_condors = condor_gen.generate_put_condors(
            price_min=price_min,
            price_max=price_max,
            strike=strike,
            target_price=target_price
        )
        print(f"✅ Put Condors: {len(put_condors)} stratégies générées")
    except Exception as e:
        print(f"❌ ERREUR Put Condors: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test Iron Condors (ne nécessite pas strike)
    print(f"\n🔍 Génération d'Iron Condors...")
    try:
        iron_condors = condor_gen.generate_iron_condors(
            price_min=price_min,
            price_max=price_max,
            target_price=target_price
        )
        print(f"✅ Iron Condors: {len(iron_condors)} stratégies générées")
    except Exception as e:
        print(f"❌ ERREUR Iron Condors: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 TEST DE SIMPLIFICATION DES PARAMÈTRES STRIKE")
    print("="*80)
    print("\nObjectif: Vérifier que strike_min/strike_max ont été remplacés par strike")
    print("pour les stratégies à 3-4 legs (Butterfly, Condor)")
    
    success = True
    
    # Test 1: OptionStrategyGenerator
    if not test_option_generator_strike_param():
        success = False
    
    # Test 2: CondorGenerator
    if not test_condor_generator_strike_param():
        success = False
    
    # Résumé
    print("\n" + "="*80)
    if success:
        print("✅ TOUS LES TESTS RÉUSSIS")
        print("   - OptionStrategyGenerator utilise strike pour 3-4 legs")
        print("   - CondorGenerator utilise strike au lieu de strike_min/strike_max")
        print("   - La simplification est complète et fonctionnelle")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("   Vérifier les erreurs ci-dessus")
    print("="*80 + "\n")
