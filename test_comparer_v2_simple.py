"""
Test de StrategyComparerV2
===========================
Test du comparateur avec des stratégies générées par option_generator_v2
"""
import sys
sys.path.insert(0, 'src')

from myproject.option.option_class import Option
from myproject.option.option_generator_v2 import OptionStrategyGeneratorV2
from myproject.option.comparor_v2 import StrategyComparerV2

print("=" * 80)
print("TEST COMPLET: Generation + Comparaison + Ranking")
print("=" * 80)
print()

# Créer des options de test
options = [
    Option(option_type='call', strike=100, premium=5, position='long', delta=0.6, 
           gamma=0.05, vega=0.3, theta=-0.05, implied_volatility=0.25,
           expiration_month='F', expiration_year=6),
    Option(option_type='call', strike=105, premium=3, position='long', delta=0.45,
           gamma=0.04, vega=0.28, theta=-0.04, implied_volatility=0.24,
           expiration_month='F', expiration_year=6),
    Option(option_type='call', strike=110, premium=2, position='long', delta=0.3,
           gamma=0.04, vega=0.25, theta=-0.03, implied_volatility=0.24,
           expiration_month='F', expiration_year=6),
    Option(option_type='put', strike=100, premium=4.5, position='long', delta=-0.4,
           gamma=0.05, vega=0.3, theta=-0.05, implied_volatility=0.26,
           expiration_month='F', expiration_year=6),
    Option(option_type='put', strike=95, premium=3, position='long', delta=-0.3,
           gamma=0.04, vega=0.28, theta=-0.04, implied_volatility=0.27,
           expiration_month='F', expiration_year=6),
    Option(option_type='put', strike=90, premium=1.5, position='long', delta=-0.2,
           gamma=0.03, vega=0.22, theta=-0.02, implied_volatility=0.28,
           expiration_month='F', expiration_year=6),
]

print(f"Options disponibles: {len(options)}")
print()

# Générer toutes les combinaisons
print("Étape 1: Génération des stratégies...")
print("-" * 80)
generator = OptionStrategyGeneratorV2(options)
strategies = generator.generate_all_combinations(
    target_price=102.0,
    price_min=85.0,
    price_max=115.0,
    max_legs=3  # Limiter à 3 legs pour la performance
)
print(f"✅ {len(strategies)} stratégies générées")
print()

# Comparer et classer
print("Étape 2: Comparaison et classement...")
print("-" * 80)
comparer = StrategyComparerV2()
best_strategies = comparer.compare_and_rank(
    strategies=strategies,
    top_n=10
)
print()

# Afficher le résumé
print("Étape 3: Résultats")
print("-" * 80)
comparer.print_summary(best_strategies, top_n=5)

print()
print("✅ Tests terminés avec succès!")
