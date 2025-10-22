"""
Test de OptionStrategyGeneratorV2.from_bloomberg_data()
========================================================
Test du générateur créé directement depuis des données Bloomberg
"""
import sys
sys.path.insert(0, 'src')

from myproject.option.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.option.comparor_v2 import StrategyComparerV2

print("=" * 80)
print("TEST: Génération depuis données Bloomberg")
print("=" * 80)
print()

# Données Bloomberg simulées
bloomberg_data = [
    {
        'option_type': 'call',
        'strike': 100.0,
        'premium': 5.0,
        'delta': 0.6,
        'gamma': 0.05,
        'vega': 0.3,
        'theta': -0.05,
        'implied_volatility': 0.25,
        'bloomberg_ticker': 'SPY 250221C100',
        'symbol': 'SPY',
        'underlying_price': 105.0,
        'month_of_expiration': 'F',
        'year_of_expiration': 6
    },
    {
        'option_type': 'call',
        'strike': 105.0,
        'premium': 3.0,
        'delta': 0.45,
        'gamma': 0.04,
        'vega': 0.28,
        'theta': -0.04,
        'implied_volatility': 0.24,
        'bloomberg_ticker': 'SPY 250221C105',
        'symbol': 'SPY',
        'underlying_price': 105.0,
        'month_of_expiration': 'F',
        'year_of_expiration': 6
    },
    {
        'option_type': 'call',
        'strike': 110.0,
        'premium': 2.0,
        'delta': 0.3,
        'gamma': 0.04,
        'vega': 0.25,
        'theta': -0.03,
        'implied_volatility': 0.24,
        'bloomberg_ticker': 'SPY 250221C110',
        'symbol': 'SPY',
        'underlying_price': 105.0,
        'month_of_expiration': 'F',
        'year_of_expiration': 6
    },
    {
        'option_type': 'put',
        'strike': 100.0,
        'premium': 4.5,
        'delta': -0.4,
        'gamma': 0.05,
        'vega': 0.3,
        'theta': -0.05,
        'implied_volatility': 0.26,
        'bloomberg_ticker': 'SPY 250221P100',
        'symbol': 'SPY',
        'underlying_price': 105.0,
        'month_of_expiration': 'F',
        'year_of_expiration': 6
    },
    {
        'option_type': 'put',
        'strike': 95.0,
        'premium': 3.0,
        'delta': -0.3,
        'gamma': 0.04,
        'vega': 0.28,
        'theta': -0.04,
        'implied_volatility': 0.27,
        'bloomberg_ticker': 'SPY 250221P95',
        'symbol': 'SPY',
        'underlying_price': 105.0,
        'month_of_expiration': 'F',
        'year_of_expiration': 6
    },
]

print(f"Données Bloomberg: {len(bloomberg_data)} options")
print()

# Étape 1: Créer le générateur depuis Bloomberg
print("Étape 1: Création du générateur depuis Bloomberg...")
print("-" * 80)
generator = OptionStrategyGeneratorV2.from_bloomberg_data(
    bloomberg_data,
    default_position='long',
    default_quantity=1
)
print()

# Étape 2: Générer les stratégies
print("Étape 2: Génération des stratégies...")
print("-" * 80)
strategies = generator.generate_all_combinations(
    target_price=102.0,
    price_min=85.0,
    price_max=115.0,
    max_legs=4  # Tester jusqu'à 4 legs
)
print()

# Étape 3: Comparer et classer
print("Étape 3: Comparaison et classement...")
print("-" * 80)
comparer = StrategyComparerV2()
best_strategies = comparer.compare_and_rank(strategies, top_n=10)
print()

# Étape 4: Afficher les résultats
print("Étape 4: Résultats")
print("-" * 80)
comparer.print_summary(best_strategies, top_n=5)

print()
print("=" * 80)
print("✅ Test terminé avec succès!")
print("=" * 80)
