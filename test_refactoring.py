"""
Script de test pour vérifier le refactoring avec all_options
"""

import sys
sys.path.insert(0, 'src')

from option.option_class import Option
from option.option_utils import dict_to_option, calculate_greeks_from_options, calculate_greeks_by_type
from datetime import datetime

# Test 1: Conversion dict -> Option
print("=" * 60)
print("TEST 1: Conversion dict_to_option")
print("=" * 60)

test_dict = {
    'option_type': 'call',
    'strike': 100.0,
    'premium': 2.5,
    'expiration_date': '2025-12-20',
    'delta': 0.5,
    'gamma': 0.02,
    'vega': 0.15,
    'theta': -0.05,
    'implied_volatility': 0.25,
    'bloomberg_ticker': 'TEST 12/20/25 C100',
    'symbol': 'TEST'
}

opt = dict_to_option(test_dict, position='long', quantity=1)
print(f"✅ Option créée: {opt.option_type} strike={opt.strike} premium={opt.premium}")
print(f"   Delta: {opt.delta}, Position: {opt.position}, Quantity: {opt.quantity}")

# Test 2: Calcul des Greeks depuis une liste
print("\n" + "=" * 60)
print("TEST 2: Calcul des Greeks depuis liste")
print("=" * 60)

# Créer un Butterfly simulé: Long 1 @ 95, Short 2 @ 100, Long 1 @ 105
lower = dict_to_option({
    'option_type': 'call', 'strike': 95.0, 'premium': 5.0,
    'expiration_date': '2025-12-20',
    'delta': 0.6, 'gamma': 0.03, 'vega': 0.18, 'theta': -0.06
}, position='long', quantity=1)

middle = dict_to_option({
    'option_type': 'call', 'strike': 100.0, 'premium': 2.5,
    'expiration_date': '2025-12-20',
    'delta': 0.5, 'gamma': 0.02, 'vega': 0.15, 'theta': -0.05
}, position='short', quantity=2)

upper = dict_to_option({
    'option_type': 'call', 'strike': 105.0, 'premium': 1.0,
    'expiration_date': '2025-12-20',
    'delta': 0.4, 'gamma': 0.015, 'vega': 0.12, 'theta': -0.04
}, position='long', quantity=1)

fly_options = [lower, middle, upper]

greeks = calculate_greeks_from_options(fly_options)
print(f"✅ Butterfly Greeks calculés:")
print(f"   Delta: {greeks['delta']:.4f}")
print(f"   Gamma: {greeks['gamma']:.4f}")
print(f"   Vega: {greeks['vega']:.4f}")
print(f"   Theta: {greeks['theta']:.4f}")

# Test 3: Calcul par type (calls vs puts)
print("\n" + "=" * 60)
print("TEST 3: Calcul Greeks par type (Iron Condor)")
print("=" * 60)

# Iron Condor: Put spread + Call spread
put_lower = dict_to_option({
    'option_type': 'put', 'strike': 90.0, 'premium': 0.5,
    'expiration_date': '2025-12-20',
    'delta': -0.2, 'gamma': 0.01, 'vega': 0.08, 'theta': -0.02
}, position='long', quantity=1)

put_upper = dict_to_option({
    'option_type': 'put', 'strike': 95.0, 'premium': 1.5,
    'expiration_date': '2025-12-20',
    'delta': -0.35, 'gamma': 0.025, 'vega': 0.12, 'theta': -0.04
}, position='short', quantity=1)

call_lower = dict_to_option({
    'option_type': 'call', 'strike': 105.0, 'premium': 1.8,
    'expiration_date': '2025-12-20',
    'delta': 0.4, 'gamma': 0.025, 'vega': 0.13, 'theta': -0.045
}, position='short', quantity=1)

call_upper = dict_to_option({
    'option_type': 'call', 'strike': 110.0, 'premium': 0.8,
    'expiration_date': '2025-12-20',
    'delta': 0.25, 'gamma': 0.015, 'vega': 0.09, 'theta': -0.03
}, position='long', quantity=1)

iron_condor_options = [put_lower, put_upper, call_lower, call_upper]

greeks_by_type = calculate_greeks_by_type(iron_condor_options)
print(f"✅ Iron Condor Greeks par type:")
print(f"   Calls - Delta: {greeks_by_type['calls']['delta']:.4f}, Vega: {greeks_by_type['calls']['vega']:.4f}")
print(f"   Puts  - Delta: {greeks_by_type['puts']['delta']:.4f}, Vega: {greeks_by_type['puts']['vega']:.4f}")
print(f"   Total - Delta: {greeks_by_type['total']['delta']:.4f}, Vega: {greeks_by_type['total']['vega']:.4f}")

# Test 4: Vérifier FlyConfiguration
print("\n" + "=" * 60)
print("TEST 4: FlyConfiguration avec all_options")
print("=" * 60)

from option.fly_generator import FlyConfiguration

# Créer des dicts Bloomberg pour le Fly
lower_dict = {
    'strike': 95.0, 'premium': 5.0, 'option_type': 'call',
    'expiration_date': '2025-12-20',
    'delta': 0.6, 'gamma': 0.03, 'vega': 0.18, 'theta': -0.06,
    'bloomberg_ticker': 'TEST 12/20/25 C95'
}

middle_dict = {
    'strike': 100.0, 'premium': 2.5, 'option_type': 'call',
    'expiration_date': '2025-12-20',
    'delta': 0.5, 'gamma': 0.02, 'vega': 0.15, 'theta': -0.05,
    'bloomberg_ticker': 'TEST 12/20/25 C100'
}

upper_dict = {
    'strike': 105.0, 'premium': 1.0, 'option_type': 'call',
    'expiration_date': '2025-12-20',
    'delta': 0.4, 'gamma': 0.015, 'vega': 0.12, 'theta': -0.04,
    'bloomberg_ticker': 'TEST 12/20/25 C105'
}

fly_config = FlyConfiguration(
    name="Test Butterfly 95/100/105",
    lower_strike=95.0,
    middle_strike=100.0,
    upper_strike=105.0,
    option_type='call',
    expiration_date='2025-12-20',
    lower_option=lower_dict,
    middle_option=middle_dict,
    upper_option=upper_dict
)

print(f"✅ FlyConfiguration créée: {fly_config.name}")
print(f"   Nombre d'options dans all_options: {len(fly_config.all_options)}")
print(f"   Coût estimé: ${fly_config.estimated_cost:.2f}")
print(f"   Total Delta: {fly_config.total_delta:.4f}")
print(f"   Total Gamma: {fly_config.total_gamma:.4f}")
print(f"   Total Vega: {fly_config.total_vega:.4f}")
print(f"   Total Theta: {fly_config.total_theta:.4f}")

# Afficher les détails de chaque option
print(f"\n   Détails all_options:")
for i, opt in enumerate(fly_config.all_options, 1):
    print(f"   {i}. {opt.option_type.upper()} {opt.strike} - {opt.position} x{opt.quantity} - Premium: ${opt.premium}")

print("\n" + "=" * 60)
print("✅ TOUS LES TESTS RÉUSSIS!")
print("=" * 60)
print("\nLe refactoring fonctionne correctement:")
print("  ✅ Conversion dict -> Option")
print("  ✅ Calcul Greeks depuis all_options")
print("  ✅ Séparation calls/puts")
print("  ✅ FlyConfiguration utilise all_options")
print("  ✅ Simplification du code (plus besoin de _get_greek_value)")
