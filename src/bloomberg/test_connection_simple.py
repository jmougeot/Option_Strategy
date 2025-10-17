"""
Test Simple - Connexion Bloomberg
==================================
Test minimal pour vérifier:
1. Connexion au Bloomberg Terminal
2. Capacité à récupérer des données réelles

Usage:
    python test_connection_simple.py

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from connection import BloombergConnection, test_connection
from fetcher import BloombergOptionFetcher


def test_connexion_et_recuperation():
    """
    Test simple: connexion + récupération d'une option EURIBOR
    """
    print("="*70)
    print(" TEST CONNEXION BLOOMBERG - VERSION SIMPLE")
    print("="*70)
    print()
    
    # ÉTAPE 1: Test de connexion
    print("ÉTAPE 1/2: Test de connexion au Bloomberg Terminal")
    print("-" * 70)
    
    try:
        connexion_ok = test_connection()
        
        if not connexion_ok:
            print("✗ ÉCHEC: Impossible de se connecter à Bloomberg")
            print()
            print("Vérifiez que:")
            print("  - Bloomberg Terminal est ouvert")
            print("  - Vous êtes connecté avec vos identifiants")
            print("  - Le Terminal est complètement chargé")
            return False
        
        print("✓ SUCCÈS: Connexion Bloomberg établie")
        print()
        
    except Exception as e:
        print(f"✗ ERREUR lors de la connexion: {e}")
        return False
    
    # ÉTAPE 2: Test de récupération de données
    print("ÉTAPE 2/2: Récupération d'une option EURIBOR de test")
    print("-" * 70)
    
    try:
        with BloombergOptionFetcher() as fetcher:
            # Tester avec une option EURIBOR standard
            # ERH5C 97.5 = EURIBOR Mars 2025 Call Strike 97.5
            print("Recherche: EURIBOR Mars 2025 (H5) Call Strike 97.50")
            print("Ticker Bloomberg: ERH5C 97.5 Comdty")
            print()
            
            option = fetcher.get_option_data(
                underlying="ER",
                expiry_month='H',
                expiry_year=5,
                option_type='C',
                strike=97.50
            )
            
            if option:
                print("✓ SUCCÈS: Données récupérées depuis Bloomberg!")
                print()
                print("Résumé des données reçues:")
                print(f"  Ticker: {option.ticker}")
                print(f"  Strike: {option.strike}")
                print(f"  Last Price: ${option.last}" if option.last else "  Last Price: N/A")
                print(f"  Delta: {option.delta:.3f}" if option.delta is not None else "  Delta: N/A")
                print(f"  Implied Volatility: {option.implied_volatility:.1f}%" if option.implied_volatility else "  Implied Volatility: N/A")
                print(f"  Volume: {option.volume}" if option.volume else "  Volume: N/A")
                print()
                return True
            else:
                print("✗ ÉCHEC: Aucune donnée retournée par Bloomberg")
                print()
                print("Causes possibles:")
                print("  - Le ticker ERH5C 97.5 Comdty n'existe pas")
                print("  - Vous n'avez pas les droits d'accès à EURIBOR")
                print("  - L'option a expiré ou n'est plus disponible")
                return False
                
    except Exception as e:
        print(f"✗ ERREUR lors de la récupération: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """Point d'entrée principal"""
    print()
    print("Ce test vérifie simplement que:")
    print("  1. Vous pouvez vous connecter à Bloomberg Terminal")
    print("  2. Vous pouvez récupérer des données d'options")
    print()
    print("Pré-requis:")
    print("  ✓ Bloomberg Terminal ouvert et connecté")
    print("  ✓ Module blpapi installé (pip install blpapi)")
    print()
    input("Appuyez sur Entrée pour lancer le test...")
    print()
    
    # Exécuter le test
    resultat = test_connexion_et_recuperation()
    
    # Résumé final
    print("="*70)
    if resultat:
        print("✓ TEST RÉUSSI: Votre connexion Bloomberg fonctionne!")
        print()
        print("Vous pouvez maintenant utiliser le module Bloomberg pour:")
        print("  - Récupérer des données d'options")
        print("  - Analyser les Greeks")
        print("  - Construire des stratégies")
        print("="*70)
        return 0
    else:
        print("✗ TEST ÉCHOUÉ: Problème de connexion ou de récupération")
        print()
        print("Actions recommandées:")
        print("  1. Vérifiez que Bloomberg Terminal est bien ouvert")
        print("  2. Assurez-vous d'être connecté")
        print("  3. Testez manuellement le ticker ERH5C 97.5 Comdty dans Bloomberg")
        print("  4. Vérifiez vos droits d'accès aux données EURIBOR")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
