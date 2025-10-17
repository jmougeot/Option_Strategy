"""
Recherche Delta d'un Call EURIBOR
==================================
Script simple pour récupérer le delta d'une option Call EURIBOR depuis Bloomberg.

Usage:
    python get_delta_euribor.py

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from fetcher import BloombergOptionFetcher


def get_euribor_call_delta():
    """
    Récupère le delta d'un Call EURIBOR spécifique
    """
    print("="*70)
    print(" RECHERCHE DELTA - CALL EURIBOR")
    print("="*70)
    print()
    
    # Configuration de l'option à rechercher
    underlying = "ER"           # EURIBOR
    expiry_month = 'H'          # Mars (H)
    expiry_year = 5             # 2025
    option_type = 'C'           # Call
    strike = 97.50              # Strike 97.50
    
    # Afficher les informations
    print("Option recherchée:")
    print(f"  Sous-jacent: EURIBOR (ER)")
    print(f"  Expiration: Mars 2025 (H5)")
    print(f"  Type: Call (C)")
    print(f"  Strike: {strike}")
    print(f"  Ticker Bloomberg: ERH5C {strike} Comdty")
    print()
    print("-"*70)
    print()
    
    try:
        # Se connecter à Bloomberg et récupérer les données
        print("Connexion à Bloomberg Terminal...")
        with BloombergOptionFetcher() as fetcher:
            print("✓ Connecté")
            print()
            print("Récupération des données...")
            
            option = fetcher.get_option_data(
                underlying=underlying,
                expiry_month=expiry_month,
                expiry_year=expiry_year,
                option_type=option_type,
                strike=strike
            )
            
            if option:
                print("✓ Données récupérées avec succès!")
                print()
                print("="*70)
                print(" RÉSULTATS")
                print("="*70)
                print()
                
                # Afficher le delta
                if option.delta is not None:
                    print(f"🎯 DELTA: {option.delta:.4f}")
                    print()
                    print(f"   Interprétation:")
                    prob_itm = abs(option.delta) * 100
                    print(f"   - Probabilité d'être ITM (In-The-Money): ~{prob_itm:.1f}%")
                    print(f"   - Pour 1€ de hausse du sous-jacent, l'option gagne ~{option.delta:.4f}€")
                else:
                    print("⚠️  DELTA: Non disponible")
                
                print()
                print("-"*70)
                print()
                
                # Afficher les autres données disponibles
                print("Autres données récupérées:")
                print()
                
                if option.last is not None:
                    print(f"  Prix (Last):     {option.last:.4f}")
                if option.bid is not None and option.ask is not None:
                    print(f"  Bid/Ask:         {option.bid:.4f} / {option.ask:.4f}")
                if option.mid is not None:
                    print(f"  Mid:             {option.mid:.4f}")
                
                print()
                
                # Greeks
                if option.gamma is not None:
                    print(f"  Gamma:           {option.gamma:.4f}")
                if option.vega is not None:
                    print(f"  Vega:            {option.vega:.4f}")
                if option.theta is not None:
                    print(f"  Theta:           {option.theta:.4f}")
                if option.rho is not None:
                    print(f"  Rho:             {option.rho:.4f}")
                
                print()
                
                # Volatilité
                if option.implied_volatility is not None:
                    print(f"  Vol. Implicite:  {option.implied_volatility:.2f}%")
                
                print()
                print("="*70)
                return True
            else:
                print("✗ Aucune donnée retournée par Bloomberg")
                print()
                print("Causes possibles:")
                print("  - Le ticker ERH5C 97.5 Comdty n'existe pas ou a expiré")
                print("  - Vous n'avez pas les droits d'accès aux données EURIBOR")
                print("  - Erreur de connexion Bloomberg")
                return False
                
    except ConnectionError as e:
        print(f"✗ Erreur de connexion Bloomberg: {e}")
        print()
        print("Vérifiez que:")
        print("  - Bloomberg Terminal est ouvert")
        print("  - Vous êtes connecté")
        print("  - Le Terminal est complètement chargé")
        return False
        
    except Exception as e:
        print(f"✗ Erreur inattendue: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """Point d'entrée principal"""
    print()
    print("Ce script récupère le delta d'un Call EURIBOR depuis Bloomberg")
    print()
    print("Pré-requis:")
    print("  ✓ Bloomberg Terminal ouvert et connecté")
    print("  ✓ Droits d'accès aux données EURIBOR")
    print()
    input("Appuyez sur Entrée pour continuer...")
    print()
    
    success = get_euribor_call_delta()
    
    if success:
        print()
        print("✓ Récupération terminée avec succès!")
        return 0
    else:
        print()
        print("✗ Échec de la récupération")
        return 1


if __name__ == "__main__":
    sys.exit(main())
