"""
Script de Debug pour les Surfaces
==================================
Vérifie que les surfaces profit/loss sont correctement calculées
"""

from myproject.option.option_class import Option
from myproject.option.dic_to_option import dict_to_option_with_calcul, bloomberg_data_to_options

def test_surface_single_option():
    """Test du calcul de surface sur une seule option"""
    print("\n" + "="*80)
    print("TEST 1: Surface d'une option simple")
    print("="*80)
    
    # Créer une option call long simple
    option = Option(
        option_type='call',
        strike=100.0,
        premium=2.5,
        position='long',
        quantity=1,
        expiration_month='M',
        expiration_year=6
    )
    
    price_min = 95.0
    price_max = 105.0
    
    # Calculer les surfaces
    profit_surface = option.calcul_profit_surface(price_min, price_max, num_points=200)
    loss_surface = option.calcul_loss_surface(price_min, price_max, num_points=200)
    
    print(f"\n📊 Option: Long Call Strike={option.strike}, Premium={option.premium}")
    print(f"   Prix range: ${price_min} - ${price_max}")
    print(f"   ✅ Surface Profit: {profit_surface:.2f}")
    print(f"   ✅ Surface Loss: {loss_surface:.2f}")
    
    if profit_surface == 0 and loss_surface == 0:
        print("   ❌ ERREUR: Les deux surfaces sont nulles!")
        return False
    else:
        print("   ✅ SUCCÈS: Les surfaces sont calculées")
        return True

def test_surface_dict_conversion():
    """Test du calcul de surface via dict_to_option_with_calcul"""
    print("\n" + "="*80)
    print("TEST 2: Surface via conversion dictionnaire")
    print("="*80)
    
    # Créer un dictionnaire d'option (format Bloomberg)
    option_dict = {
        'option_type': 'put',
        'strike': 98.0,
        'premium': 1.5,
        'bloomberg_ticker': 'TEST',
        'delta': -0.4,
        'gamma': 0.05,
        'vega': 0.2,
        'theta': -0.05,
        'implied_volatility': 0.25,
        'month_of_expiration': 'M',
        'year_of_expiration': 6,
        'day_of_expiration': '15'
    }
    
    price_min = 95.0
    price_max = 100.0
    
    # Convertir avec calcul des surfaces
    option = dict_to_option_with_calcul(
        option_dict,
        position='long',
        quantity=1,
        price_min=price_min,
        price_max=price_max,
        num_points=200
    )
    
    print(f"\n📊 Option: Long Put Strike={option.strike}, Premium={option.premium}")
    print(f"   Prix range: ${price_min} - ${price_max}")
    print(f"   ✅ Surface Profit: {option.profit_surface:.2f}")
    print(f"   ✅ Surface Loss: {option.loss_surface:.2f}")
    
    if option.profit_surface == 0 and option.loss_surface == 0:
        print("   ❌ ERREUR: Les deux surfaces sont nulles!")
        return False
    else:
        print("   ✅ SUCCÈS: Les surfaces sont calculées")
        return True

def test_surface_batch_conversion():
    """Test du calcul de surfaces sur une liste d'options"""
    print("\n" + "="*80)
    print("TEST 3: Surface via conversion batch Bloomberg")
    print("="*80)
    
    # Créer plusieurs options
    bloomberg_data = [
        {
            'option_type': 'call',
            'strike': 97.5,
            'premium': 2.0,
            'delta': 0.6,
            'gamma': 0.08,
            'vega': 0.3,
            'theta': -0.03,
            'implied_volatility': 0.22,
            'month_of_expiration': 'M',
            'year_of_expiration': 6,
            'day_of_expiration': '15'
        },
        {
            'option_type': 'put',
            'strike': 98.5,
            'premium': 1.8,
            'delta': -0.35,
            'gamma': 0.06,
            'vega': 0.25,
            'theta': -0.02,
            'implied_volatility': 0.24,
            'month_of_expiration': 'M',
            'year_of_expiration': 6,
            'day_of_expiration': '15'
        }
    ]
    
    price_min = 95.0
    price_max = 100.0
    
    # Convertir avec calcul des surfaces
    options = bloomberg_data_to_options(
        bloomberg_data,
        default_position='long',
        price_min=price_min,
        price_max=price_max,
        calculate_surfaces=True,
        num_points=200
    )
    
    print(f"\n📊 {len(options)} options converties")
    print(f"   Prix range: ${price_min} - ${price_max}")
    
    success = True
    for i, opt in enumerate(options, 1):
        print(f"\n   Option {i}: {opt.option_type.upper()} Strike={opt.strike}, Premium={opt.premium}")
        print(f"      Surface Profit: {opt.profit_surface:.2f}")
        print(f"      Surface Loss: {opt.loss_surface:.2f}")
        
        if opt.profit_surface == 0 and opt.loss_surface == 0:
            print(f"      ❌ ERREUR: Les deux surfaces sont nulles!")
            success = False
    
    if success:
        total_profit = sum(opt.profit_surface or 0 for opt in options)
        total_loss = sum(opt.loss_surface or 0 for opt in options)
        print(f"\n   ✅ SUCCÈS: Toutes les surfaces sont calculées")
        print(f"   📊 Total: Profit={total_profit:.2f}, Loss={total_loss:.2f}")
    
    return success

if __name__ == "__main__":
    print("\n🔍 TESTS DE DEBUG DES SURFACES")
    print("="*80)
    
    results = []
    
    # Test 1
    results.append(("Surface option simple", test_surface_single_option()))
    
    # Test 2
    results.append(("Surface via dict", test_surface_dict_conversion()))
    
    # Test 3
    results.append(("Surface via batch", test_surface_batch_conversion()))
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    for test_name, success in results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        print(f"  {status}: {test_name}")
    
    all_success = all(success for _, success in results)
    
    if all_success:
        print("\n🎉 TOUS LES TESTS RÉUSSIS!")
        print("   Les surfaces sont correctement calculées.")
    else:
        print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("   Vérifier le calcul des surfaces dans Option.calcul_profit_surface()")
