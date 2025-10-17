"""
Test du Générateur de Butterflies avec Bloomberg
=================================================
Test avec données réelles Bloomberg pour SOFR options (SFR)

Exemple: SFRH6C = 3-Month SOFR, March 2026, Call
         H = March (8ème lettre de l'année)
         6 = 2026
         C = Call

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.Strategy.fly_generator import FlyGenerator
from src.bloomberg_data_importer import import_euribor_options


def test_with_bloomberg_sofr():
    """Test avec données Bloomberg SOFR réelles"""
    
    print("=" * 70)
    print("TEST GÉNÉRATEUR DE BUTTERFLIES - DONNÉES BLOOMBERG SOFR")
    print("=" * 70)
    print()
    
    # Configuration de l'import
    print("📋 Configuration de l'import Bloomberg:")
    print("   • Sous-jacent: SFR (3-Month SOFR Futures)")
    print("   • Mois: Mars 2026 (H)")
    print("   • Année: 2026 (6)")
    print("   • Strikes: 95.0 à 100.0 par 0.25")
    print()
    
    input("Appuyez sur Entrée pour lancer l'import Bloomberg...")
    print()
    
    # Import depuis Bloomberg
    print("1. Import des données depuis Bloomberg...")
    try:
        data = import_euribor_options(
            underlying="SFR",
            months=["H"],  # March
            years=[6],     # 2026
            strikes=[round(95.0 + i * 0.25, 2) for i in range(21)],  # 95.0 à 100.0
            include_calls=True,
            include_puts=True
        )
        
        calls = [opt for opt in data['options'] if opt['option_type'] == 'call']
        puts = [opt for opt in data['options'] if opt['option_type'] == 'put']
        
        print(f"   ✓ {len(calls)} calls importés")
        print(f"   ✓ {len(puts)} puts importés")
        print(f"   ✓ Total: {len(data['options'])} options")
        
        if calls:
            strikes = sorted(set(c['strike'] for c in calls))
            print(f"   ✓ Strikes disponibles: {strikes[0]} à {strikes[-1]}")
            print(f"   ✓ Nombre de strikes: {len(strikes)}")
        
    except Exception as e:
        print(f"   ✗ ERREUR lors de l'import Bloomberg: {e}")
        print()
        print("⚠️  Assurez-vous que:")
        print("   1. Bloomberg Terminal est ouvert")
        print("   2. Vous êtes connecté à Bloomberg")
        print("   3. Les options SOFR sont disponibles")
        return
    
    # Préparer les données
    print("\n2. Préparation des données...")
    options_data = {'calls': calls, 'puts': puts}
    print(f"   ✓ Données préparées")
    
    # Initialiser le générateur
    print("\n3. Initialisation du générateur de Butterflies...")
    generator = FlyGenerator(options_data)
    
    call_strikes = generator.get_available_strikes('call')
    put_strikes = generator.get_available_strikes('put')
    expirations = generator.get_available_expirations('call')
    
    print(f"   ✓ Strikes calls disponibles: {len(call_strikes)}")
    print(f"   ✓ Strikes puts disponibles: {len(put_strikes)}")
    print(f"   ✓ Dates d'expiration: {len(expirations)}")
    
    if call_strikes:
        print(f"\n   Strikes disponibles:")
        print(f"   {call_strikes}")
    
    # Paramètres de génération
    print("\n4. Paramètres de génération des Butterflies:")
    
    # Utiliser le prix moyen comme centre
    if call_strikes:
        price_center = (min(call_strikes) + max(call_strikes)) / 2
        price_min = price_center - 1.0
        price_max = price_center + 1.0
        strike_min = min(call_strikes)
        strike_max = max(call_strikes)
    else:
        price_min = 96.0
        price_max = 99.0
        strike_min = 95.0
        strike_max = 100.0
    
    print(f"   • Tête du Fly (middle strike): {price_min:.2f} à {price_max:.2f}")
    print(f"   • Jambes (lower/upper strikes): {strike_min:.2f} à {strike_max:.2f}")
    print(f"   • Largeur d'aile min: 0.25")
    print(f"   • Largeur d'aile max: 3.0")
    
    # Générer les Call Butterflies
    print("\n5. Génération des CALL BUTTERFLIES...")
    
    call_flies = generator.generate_all_flies(
        price_min=price_min,
        price_max=price_max,
        strike_min=strike_min,
        strike_max=strike_max,
        option_type='call',
        require_symmetric=False,
        min_wing_width=0.25,
        max_wing_width=3.0
    )
    
    print(f"   ✓ {len(call_flies)} Call Butterflies générés")
    
    if call_flies:
        print("\n   Top 10 Call Butterflies:")
        print(f"   {'#':>3} {'Strikes':^20} {'Lower Wing':>12} {'Upper Wing':>12} {'Coût':>10} {'Sym':>4}")
        print("   " + "-" * 66)
        
        for i, fly in enumerate(call_flies[:10], 1):
            sym = "✓" if fly.is_symmetric else "✗"
            print(f"   {i:3d} {fly.strikes_str:^20} {fly.wing_width_lower:12.2f} {fly.wing_width_upper:12.2f} ${fly.estimated_cost:9.4f} {sym:>4}")
        
        if len(call_flies) > 10:
            print(f"\n   ... et {len(call_flies) - 10} autres Call Flies")
    
    # Filtrer les symétriques
    print("\n6. Filtrage: CALL BUTTERFLIES SYMÉTRIQUES uniquement...")
    symmetric_call_flies = generator.filter_flies(call_flies, symmetric_only=True)
    print(f"   ✓ {len(symmetric_call_flies)} Call Flies symétriques")
    
    if symmetric_call_flies:
        print("\n   Call Flies Symétriques:")
        print(f"   {'#':>3} {'Strikes':^20} {'Wing Width':>12} {'Coût':>10}")
        print("   " + "-" * 50)
        
        for i, fly in enumerate(symmetric_call_flies[:10], 1):
            print(f"   {i:3d} {fly.strikes_str:^20} {fly.wing_width_lower:12.2f} ${fly.estimated_cost:9.4f}")
    
    # Générer les Put Butterflies
    print("\n7. Génération des PUT BUTTERFLIES...")
    
    put_flies = generator.generate_all_flies(
        price_min=price_min,
        price_max=price_max,
        strike_min=strike_min,
        strike_max=strike_max,
        option_type='put',
        require_symmetric=False,
        min_wing_width=0.25,
        max_wing_width=3.0
    )
    
    print(f"   ✓ {len(put_flies)} Put Butterflies générés")
    
    if put_flies:
        print("\n   Top 10 Put Butterflies:")
        print(f"   {'#':>3} {'Strikes':^20} {'Lower Wing':>12} {'Upper Wing':>12} {'Coût':>10} {'Sym':>4}")
        print("   " + "-" * 66)
        
        for i, fly in enumerate(put_flies[:10], 1):
            sym = "✓" if fly.is_symmetric else "✗"
            print(f"   {i:3d} {fly.strikes_str:^20} {fly.wing_width_lower:12.2f} {fly.wing_width_upper:12.2f} ${fly.estimated_cost:9.4f} {sym:>4}")
    
    # Statistiques globales
    print("\n8. STATISTIQUES GLOBALES:")
    
    all_flies = call_flies + put_flies
    stats = generator.generate_statistics(all_flies)
    
    print(f"\n   📊 Statistiques combinées (Calls + Puts):")
    print(f"   {'─' * 50}")
    print(f"   Total généré           : {stats['total']:>6}")
    print(f"   Symétriques            : {stats['symmetric']:>6} ({stats['symmetric']/stats['total']*100 if stats['total'] > 0 else 0:.1f}%)")
    print(f"   Call Flies             : {stats['call_flies']:>6}")
    print(f"   Put Flies              : {stats['put_flies']:>6}")
    print(f"   {'─' * 50}")
    print(f"   Coût moyen             : ${stats['avg_cost']:>8.4f}")
    print(f"   Coût minimum           : ${stats['min_cost']:>8.4f}")
    print(f"   Coût maximum           : ${stats['max_cost']:>8.4f}")
    print(f"   {'─' * 50}")
    print(f"   Largeur aile moyenne   : {stats['avg_wing_width']:>8.2f}")
    print(f"   Largeur aile min       : {stats['min_wing_width']:>8.2f}")
    print(f"   Largeur aile max       : {stats['max_wing_width']:>8.2f}")
    print(f"   {'─' * 50}")
    print(f"   Middle strikes uniques : {stats['unique_middle_strikes']:>6}")
    print(f"   Expirations uniques    : {stats['unique_expirations']:>6}")
    
    # Meilleurs Flies par critère
    print("\n9. SÉLECTION DES MEILLEURS BUTTERFLIES:")
    
    # Par coût (plus économique)
    print("\n   🏆 Top 5 par COÛT (plus économique):")
    best_by_cost = generator.get_best_flies(all_flies, criterion='cost', top_n=5)
    for i, fly in enumerate(best_by_cost, 1):
        type_str = "CALL" if fly.option_type.lower() == 'call' else "PUT "
        sym = "SYM" if fly.is_symmetric else "ASY"
        print(f"   {i}. [{type_str}] {fly.strikes_str:^20} ${fly.estimated_cost:+9.4f} [{sym}]")
    
    # Par symétrie (plus symétrique)
    print("\n   🏆 Top 5 par SYMÉTRIE (plus équilibré):")
    best_by_sym = generator.get_best_flies(all_flies, criterion='symmetric', top_n=5)
    for i, fly in enumerate(best_by_sym, 1):
        type_str = "CALL" if fly.option_type.lower() == 'call' else "PUT "
        diff = abs(fly.wing_width_lower - fly.wing_width_upper)
        print(f"   {i}. [{type_str}] {fly.strikes_str:^20} Diff: {diff:.4f} | Coût: ${fly.estimated_cost:+9.4f}")
    
    # Par largeur d'aile (plus serré)
    print("\n   🏆 Top 5 par LARGEUR D'AILE (plus serré):")
    best_by_wing = generator.get_best_flies(all_flies, criterion='wing_width', top_n=5)
    for i, fly in enumerate(best_by_wing, 1):
        type_str = "CALL" if fly.option_type.lower() == 'call' else "PUT "
        avg_wing = (fly.wing_width_lower + fly.wing_width_upper) / 2
        print(f"   {i}. [{type_str}] {fly.strikes_str:^20} Avg Wing: {avg_wing:.2f} | Coût: ${fly.estimated_cost:+9.4f}")
    
    # Exemples détaillés
    print("\n10. EXEMPLES DÉTAILLÉS:")
    
    if call_flies:
        print("\n   📝 Détail d'un Call Butterfly:")
        fly = call_flies[0]
        print(f"   {'─' * 60}")
        print(f"   Nom            : {fly.name}")
        print(f"   Strikes        : {fly.strikes_str}")
        print(f"   Type           : {fly.option_type.upper()}")
        print(f"   Expiration     : {fly.expiration_date}")
        print(f"   {'─' * 60}")
        print(f"   Lower Strike   : {fly.lower_strike:.2f}")
        print(f"   Middle Strike  : {fly.middle_strike:.2f}")
        print(f"   Upper Strike   : {fly.upper_strike:.2f}")
        print(f"   {'─' * 60}")
        print(f"   Lower Wing     : {fly.wing_width_lower:.2f}")
        print(f"   Upper Wing     : {fly.wing_width_upper:.2f}")
        print(f"   Symétrique     : {'Oui ✓' if fly.is_symmetric else 'Non ✗'}")
        print(f"   {'─' * 60}")
        print(f"   Coût estimé    : ${fly.estimated_cost:+.4f}")
        print(f"   {'─' * 60}")
        
        if fly.lower_option and fly.middle_option and fly.upper_option:
            print(f"\n   Primes des options:")
            print(f"   • Lower  ({fly.lower_strike:.2f}):  ${fly.lower_option['premium']:.4f}")
            print(f"   • Middle ({fly.middle_strike:.2f}): ${fly.middle_option['premium']:.4f} (x2)")
            print(f"   • Upper  ({fly.upper_strike:.2f}):  ${fly.upper_option['premium']:.4f}")
            print(f"\n   Structure du Fly:")
            print(f"   • Long  1x Lower  @ {fly.lower_strike:.2f}  : -${fly.lower_option['premium']:.4f}")
            print(f"   • Short 2x Middle @ {fly.middle_strike:.2f} : +${2 * fly.middle_option['premium']:.4f}")
            print(f"   • Long  1x Upper  @ {fly.upper_strike:.2f}  : -${fly.upper_option['premium']:.4f}")
            print(f"   {'-' * 60}")
            print(f"   Net (débit/crédit)                  : ${fly.estimated_cost:+.4f}")
    
    print("\n" + "=" * 70)
    print("✅ TEST TERMINÉ AVEC SUCCÈS!")
    print("=" * 70)
    print()
    print(f"💡 Résumé:")
    print(f"   • {len(all_flies)} Butterflies générés au total")
    print(f"   • {len(symmetric_call_flies)} Call Flies symétriques")
    print(f"   • Prêt à être intégré dans app.py")
    print()


def main():
    """Point d'entrée principal"""
    try:
        test_with_bloomberg_sofr()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
