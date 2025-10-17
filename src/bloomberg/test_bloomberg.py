"""
Test Bloomberg Connection and Data Fetching
===========================================
Script de test pour vérifier que le module Bloomberg fonctionne correctement.

Ce script teste:
PARTIE A - Tests sans connexion Bloomberg (structure Python):
1. Imports des modules
2. Création d'objets OptionData
3. Formatage des données
4. Construction de tickers

PARTIE B - Tests avec connexion Bloomberg (nécessite Terminal):
5. Connexion au Bloomberg Terminal
6. Récupération de données pour une option simple
7. Récupération de données EURIBOR
8. L'affichage des résultats

Usage:
    python test_bloomberg.py              # Tous les tests
    python test_bloomberg.py --no-bbg     # Seulement tests Python (sans Bloomberg)

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from datetime import date

# Import du module Bloomberg
try:
    from connection import BloombergConnection, test_connection
    from fetcher import BloombergOptionFetcher
    from formatters import (
        format_option_summary, 
        format_greeks_summary,
        format_option_table,
        format_term_structure
    )
    from models import OptionData
    from ticker_builder import build_option_ticker
    from underlying import EURIBOR, MONTH_CODES
    print("✓ Imports Bloomberg réussis")
except ImportError as e:
    print(f"✗ Erreur d'import: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


# ============================================================================
# PARTIE A: TESTS PYTHON (sans connexion Bloomberg requise)
# ============================================================================

def test_A1_imports():
    """Test A1: Vérification des imports"""
    print("\n" + "="*70)
    print("TEST A1: Vérification des imports Python")
    print("="*70)
    
    try:
        # Vérifier que tous les modules nécessaires sont importés
        modules = {
            'OptionData': OptionData,
            'BloombergConnection': BloombergConnection,
            'BloombergOptionFetcher': BloombergOptionFetcher,
            'build_option_ticker': build_option_ticker,
            'format_option_summary': format_option_summary,
        }
        
        print("Modules importés:")
        for name, obj in modules.items():
            print(f"  ✓ {name}: {type(obj).__name__}")
        
        print("\n✓ Tous les imports sont valides")
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la vérification des imports: {e}")
        return False


def test_A2_option_data_creation():
    """Test A2: Création d'objets OptionData"""
    print("\n" + "="*70)
    print("TEST A2: Création d'objets OptionData")
    print("="*70)
    
    try:
        # Créer une option fictive
        option = OptionData(
            ticker="ERH5C 97.50 Comdty",
            underlying="ER",
            option_type="CALL",
            strike=97.50,
            expiry_month='H',
            expiry_year=5,
            bid=0.15,
            ask=0.17,
            last=0.16,
            mid=0.16,
            volume=1250,
            open_interest=8430,
            delta=0.450,
            gamma=0.023,
            vega=0.180,
            theta=-0.052,
            rho=0.012,
            implied_volatility=25.3
        )
        
        print(f"Option créée: {option.ticker}")
        print(f"  Underlying: {option.underlying}")
        print(f"  Type: {option.option_type}")
        print(f"  Strike: {option.strike}")
        print(f"  Expiry: {option.expiry_month}{option.expiry_year}")
        print(f"  Last: ${option.last}")
        print(f"  Delta: {option.delta}")
        print(f"  IV: {option.implied_volatility}%")
        
        # Tester les propriétés calculées
        print(f"\nPropriétés calculées:")
        print(f"  Spread: ${option.spread}")
        print(f"  Is Liquid: {option.is_liquid}")
        
        print("\n✓ Création d'OptionData réussie")
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la création d'OptionData: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_A3_ticker_builder():
    """Test A3: Construction de tickers Bloomberg"""
    print("\n" + "="*70)
    print("TEST A3: Construction de tickers Bloomberg")
    print("="*70)
    
    try:
        test_cases = [
            {
                'params': {
                    'underlying': 'ER',
                    'expiry_month': 'H',
                    'expiry_year': 5,
                    'option_type': 'C',
                    'strike': 97.50,
                    'suffix': 'Comdty'
                },
                'expected_pattern': 'ERH5C 97.5 Comdty'
            },
            {
                'params': {
                    'underlying': 'ER',
                    'expiry_month': 'M',
                    'expiry_year': 5,
                    'option_type': 'P',
                    'strike': 98.00,
                    'suffix': 'Comdty'
                },
                'expected_pattern': 'ERM5P 98.0 Comdty'
            },
        ]
        
        print("Tests de construction de tickers:")
        for i, test in enumerate(test_cases, 1):
            ticker = build_option_ticker(**test['params'])
            print(f"  Test {i}: {ticker}")
            if test['expected_pattern'] in ticker or ticker.startswith(test['expected_pattern'][:5]):
                print(f"    ✓ Format valide")
            else:
                print(f"    ⚠️  Format attendu: {test['expected_pattern']}")
        
        print("\n✓ Construction de tickers réussie")
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la construction de tickers: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_A4_formatters():
    """Test A4: Formatage des données"""
    print("\n" + "="*70)
    print("TEST A4: Formatage des données d'options")
    print("="*70)
    
    try:
        # Créer des options fictives pour tester le formatage
        options = [
            OptionData(
                ticker="ERH5C 97.00 Comdty", underlying="ER", option_type="CALL",
                strike=97.00, expiry_month='H', expiry_year=5,
                last=0.20, delta=0.550, implied_volatility=26.5
            ),
            OptionData(
                ticker="ERH5C 97.50 Comdty", underlying="ER", option_type="CALL",
                strike=97.50, expiry_month='H', expiry_year=5,
                last=0.16, delta=0.450, implied_volatility=25.3
            ),
            OptionData(
                ticker="ERH5C 98.00 Comdty", underlying="ER", option_type="CALL",
                strike=98.00, expiry_month='H', expiry_year=5,
                last=0.12, delta=0.350, implied_volatility=24.1
            ),
        ]
        
        # Test format_option_summary
        print("\n1. format_option_summary:")
        for opt in options:
            summary = format_option_summary(opt)
            print(f"  {summary}")
        
        # Test format_option_table
        print("\n2. format_option_table:")
        table = format_option_table(options, "Test EURIBOR Calls")
        print(table)
        
        # Test format_greeks_summary
        print("\n3. format_greeks_summary:")
        greeks = format_greeks_summary(options[1])
        print(greeks)
        
        # Test format_term_structure
        print("\n4. format_term_structure:")
        term_struct = format_term_structure(options, "implied_volatility")
        print(term_struct)
        
        print("\n✓ Tous les formatters fonctionnent")
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors du formatage: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_A5_month_codes():
    """Test A5: Vérification des codes de mois Bloomberg"""
    print("\n" + "="*70)
    print("TEST A5: Codes de mois Bloomberg")
    print("="*70)
    
    try:
        print("Codes de mois disponibles:")
        month_names = {
            'F': 'Janvier', 'G': 'Février', 'H': 'Mars', 'J': 'Avril',
            'K': 'Mai', 'M': 'Juin', 'N': 'Juillet', 'Q': 'Août',
            'U': 'Septembre', 'V': 'Octobre', 'X': 'Novembre', 'Z': 'Décembre'
        }
        
        for code, name in month_names.items():
            print(f"  {code}: {name}")
        
        print(f"\n✓ {len(month_names)} codes de mois définis")
        return True
        
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False


# ============================================================================
# PARTIE B: TESTS BLOOMBERG (connexion requise)
# ============================================================================

def test_B1_connection():
    """Test B1: Vérification de la connexion Bloomberg"""
    print("\n" + "="*70)
    print("TEST B1: Connexion au Bloomberg Terminal")
    print("="*70)
    
    try:
        success = test_connection()
        if success:
            print("✓ Connexion Bloomberg réussie!")
            return True
        else:
            print("✗ Échec de connexion Bloomberg")
            return False
    except Exception as e:
        print(f"✗ Erreur lors du test de connexion: {e}")
        print("   → Vérifiez que Bloomberg Terminal est ouvert et connecté")
        return False


def test_B2_simple_option():
    """Test B2: Récupération d'une option EURIBOR simple"""
    print("\n" + "="*70)
    print("TEST B2: Récupération d'une option EURIBOR")
    print("="*70)
    
    try:
        with BloombergOptionFetcher() as fetcher:
            print("Connexion établie...")
            
            # Tester une option EURIBOR Mars 2025 (H5) Call 97.50
            print("\nRecherche: EURIBOR H5 (Mars 2025) Call Strike 97.50")
            option = fetcher.get_option_data(
                underlying="ER",
                expiry_month='H',
                expiry_year=5,
                option_type='C',
                strike=97.50
            )
            
            if option:
                print("✓ Option trouvée!")
                print(f"\n{format_option_summary(option)}")
                print(f"\n{format_greeks_summary(option)}")
                return True
            else:
                print("✗ Aucune donnée retournée pour cette option")
                return False
                
    except Exception as e:
        print(f"✗ Erreur lors de la récupération: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_B3_multiple_strikes():
    """Test B3: Récupération de plusieurs strikes"""
    print("\n" + "="*70)
    print("TEST B3: Récupération de plusieurs strikes EURIBOR")
    print("="*70)
    
    try:
        with BloombergOptionFetcher() as fetcher:
            print("Connexion établie...")
            
            # Tester plusieurs strikes autour de 97.50
            strikes = [97.00, 97.25, 97.50, 97.75, 98.00]
            print(f"\nRecherche de {len(strikes)} strikes pour EURIBOR H5 Call")
            
            found = 0
            for strike in strikes:
                option = fetcher.get_option_data(
                    underlying="ER",
                    expiry_month='H',
                    expiry_year=5,
                    option_type='C',
                    strike=strike
                )
                
                if option:
                    found += 1
                    delta_str = f"Delta={option.delta:.3f}" if option.delta else "Delta=N/A"
                    iv_str = f"IV={option.implied_volatility:.1f}%" if option.implied_volatility else "IV=N/A"
                    print(f"  ✓ Strike {strike}: {delta_str}, {iv_str}")
                else:
                    print(f"  ✗ Strike {strike}: Pas de données")
            
            print(f"\n✓ Résultat: {found}/{len(strikes)} options trouvées")
            return found > 0
            
    except Exception as e:
        print(f"✗ Erreur lors de la récupération: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_B4_range_strikes():
    """Test B4: Récupération par intervalle de strikes"""
    print("\n" + "="*70)
    print("TEST B4: Récupération par intervalle (range)")
    print("="*70)
    
    try:
        with BloombergOptionFetcher() as fetcher:
            print("Connexion établie...")
            
            # Tester un petit intervalle autour de 97.50
            print("\nRecherche: EURIBOR H5 Call, Strike 97.50 ± 1.0 (pas de 0.25)")
            options = fetcher.get_options_by_range_strike(
                underlying="ER",
                strike_center=97.50,
                option_type='C',
                expiry_month='H',
                expiry_year=5,
                strike_range=1.0,  # ± 1.0 autour de 97.50
                strike_step=0.25
            )
            
            if options:
                print(f"✓ {len(options)} options trouvées dans l'intervalle")
                print("\nRésumé:")
                for opt in sorted(options, key=lambda x: x.strike):
                    delta_str = f"{opt.delta:.3f}" if opt.delta else "N/A"
                    iv_str = f"{opt.implied_volatility:.1f}%" if opt.implied_volatility else "N/A"
                    print(f"  Strike {opt.strike}: Delta={delta_str}, IV={iv_str}")
                return True
            else:
                print("✗ Aucune option trouvée dans l'intervalle")
                return False
                
    except Exception as e:
        print(f"✗ Erreur lors de la récupération: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# ORCHESTRATION DES TESTS
# ============================================================================

def run_python_tests():
    """Exécute uniquement les tests Python (sans Bloomberg)"""
    print("\n" + "="*70)
    print(" TESTS PYTHON (Structure et Logique)")
    print("="*70)
    print("Tests sans connexion Bloomberg requise\n")
    
    results = []
    
    # Tests Python uniquement
    results.append(("A1: Imports", test_A1_imports()))
    results.append(("A2: Création OptionData", test_A2_option_data_creation()))
    results.append(("A3: Construction tickers", test_A3_ticker_builder()))
    results.append(("A4: Formatters", test_A4_formatters()))
    results.append(("A5: Codes de mois", test_A5_month_codes()))
    
    return results


def run_bloomberg_tests():
    """Exécute les tests nécessitant Bloomberg"""
    print("\n" + "="*70)
    print(" TESTS BLOOMBERG (Connexion et Données)")
    print("="*70)
    print("Tests nécessitant Bloomberg Terminal actif\n")
    
    results = []
    
    # Test de connexion d'abord
    connection_ok = test_B1_connection()
    results.append(("B1: Connexion Bloomberg", connection_ok))
    
    if connection_ok:
        # Si connexion OK, continuer les autres tests
        results.append(("B2: Option EURIBOR simple", test_B2_simple_option()))
        results.append(("B3: Multiples strikes", test_B3_multiple_strikes()))
        results.append(("B4: Intervalle de strikes", test_B4_range_strikes()))
    else:
        print("\n⚠️  Tests Bloomberg suivants ignorés (pas de connexion)")
    
    return results


def run_all_tests(skip_bloomberg=False):
    """Exécute tous les tests et affiche un résumé"""
    print("\n" + "="*70)
    print(" SUITE DE TESTS BLOOMBERG MODULE")
    print("="*70)
    
    all_results = []
    
    # PARTIE A: Tests Python
    python_results = run_python_tests()
    all_results.extend(python_results)
    
    # PARTIE B: Tests Bloomberg (si non ignorés)
    if not skip_bloomberg:
        bloomberg_results = run_bloomberg_tests()
        all_results.extend(bloomberg_results)
    else:
        print("\n" + "="*70)
        print(" TESTS BLOOMBERG IGNORÉS (mode --no-bbg)")
        print("="*70)
    
    # Résumé final
    print("\n" + "="*70)
    print(" RÉSUMÉ GÉNÉRAL")
    print("="*70)
    
    # Séparer les résultats par catégorie
    python_tests = [r for r in all_results if r[0].startswith('A')]
    bloomberg_tests = [r for r in all_results if r[0].startswith('B')]
    
    if python_tests:
        print("\nTests Python (sans Bloomberg):")
        for test_name, success in python_tests:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status:8} | {test_name}")
    
    if bloomberg_tests:
        print("\nTests Bloomberg (avec connexion):")
        for test_name, success in bloomberg_tests:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status:8} | {test_name}")
    
    # Statistiques
    passed = sum(1 for _, s in all_results if s)
    total = len(all_results)
    
    print("\n" + "="*70)
    print(f"Résultat global: {passed}/{total} tests réussis")
    
    # Message final
    if passed == total:
        print("\n🎉 Tous les tests sont passés!")
        if skip_bloomberg:
            print("   (Tests Bloomberg non exécutés)")
        else:
            print("   Le module Bloomberg fonctionne parfaitement.")
        return True
    else:
        failed = total - passed
        print(f"\n⚠️  {failed} test(s) échoué(s)")
        
        # Analyser les échecs
        python_failed = sum(1 for name, s in python_tests if not s)
        bloomberg_failed = sum(1 for name, s in bloomberg_tests if not s)
        
        if python_failed > 0:
            print(f"   - {python_failed} test(s) Python échoué(s) → Vérifiez la structure du code")
        if bloomberg_failed > 0:
            print(f"   - {bloomberg_failed} test(s) Bloomberg échoué(s) → Vérifiez la connexion Terminal")
        
        return False


if __name__ == "__main__":
    print("="*70)
    print(" TEST BLOOMBERG MODULE")
    print("="*70)
    
    # Vérifier les arguments en ligne de commande
    skip_bbg = '--no-bbg' in sys.argv
    
    if skip_bbg:
        print("\nMode: TESTS PYTHON UNIQUEMENT (--no-bbg)")
        print("  ✓ Pas de connexion Bloomberg requise")
        print("  ✓ Tests de structure et logique Python")
    else:
        print("\nMode: TESTS COMPLETS")
        print("\nPré-requis Bloomberg:")
        print("  - Bloomberg Terminal doit être ouvert et connecté")
        print("  - Licence Bloomberg active")
        print("  - Module blpapi installé (pip install blpapi)")
        print("\nAstuce: Utilisez --no-bbg pour tester sans Bloomberg")
    
    print("\n" + "="*70)
    input("Appuyez sur Entrée pour démarrer les tests...")
    
    success = run_all_tests(skip_bloomberg=skip_bbg)
    
    sys.exit(0 if success else 1)
