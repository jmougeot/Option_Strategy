"""
Test du MultiStructureComparer avec affichage du ticker et de l'expiration
"""
from src.myproject.option.multi_structure_comparer import MultiStructureComparer

# Données fictives pour le test
test_options_data = {
    'calls': [
        {'ticker': 'SPY', 'strike': 95.0, 'premium': 8.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 100.0, 'premium': 5.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 105.0, 'premium': 3.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 110.0, 'premium': 2.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 115.0, 'premium': 1.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
    ],
    'puts': [
        {'ticker': 'SPY', 'strike': 85.0, 'premium': 1.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 90.0, 'premium': 2.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 95.0, 'premium': 3.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 100.0, 'premium': 5.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
        {'ticker': 'SPY', 'strike': 105.0, 'premium': 8.0, 'day_of_expiration': 21, 'month_of_expiration': 'H', 'year_of_expiration': 2025},
    ]
}

def test_comparer():
    print("="*80)
    print("TEST: MultiStructureComparer avec affichage Ticker/Expiration")
    print("="*80)
    
    try:
        # Créer le comparateur
        comparer = MultiStructureComparer(test_options_data)
        
        # Générer des stratégies
        print("\n🔄 Génération des stratégies...")
        strategies = comparer.compare_all_structures(
            target_price=100.0,
            strike_min=90.0,
            strike_max=110.0,
            include_flies=True,
            include_condors=True,
            include_spreads=True,
            include_straddles=True,
            include_single_legs=False,
            top_n=10,
            max_legs=4
        )
        
        print(f"\n✅ {len(strategies)} stratégies générées")
        
        # Afficher les résultats
        comparer.display_comparison(strategies)
        
        print("\n✅ TEST RÉUSSI!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_comparer()
