"""
Exemple d'utilisation : Options EURIBOR
========================================
Script de démonstration pour récupérer et analyser des options EURIBOR via Bloomberg.

EURIBOR = Euro Interbank Offered Rate
Options sur futures de taux EURIBOR 3 mois sur Eurex.

Cas d'usage:
1. Récupérer une option EURIBOR spécifique
2. Scanner toutes les expiries pour un strike donné
3. Analyser la structure de terme de la volatilité
4. Calculer les payoffs à différents scénarios de taux

Prérequis:
- Bloomberg Terminal lancé et connecté
- Module blpapi installé (pip install blpapi)

Auteur: BGC Trading Desk
Date: 2026-10-16
"""

from datetime import date
from fetcher import BloombergOptionFetcher
from formatters import (
        format_euribor_option,
        format_option_table,
        format_term_structure
    )
from models import EuriborOptionData


def example_1_single_euribor_option():
    """
    Exemple 1: Récupérer une option EURIBOR spécifique.
    
    On cherche un CALL sur le future EURIBOR Mars 2026, strike 98.00
    (ce qui correspond à un taux implicite de 2.50%)
    """
    print("\n" + "="*80)
    print("EXEMPLE 1: Option EURIBOR spécifique")
    print("="*80)
    
    print("[DEBUG] Création du BloombergOptionFetcher...")
    try:
        with BloombergOptionFetcher() as fetcher:
            print("[DEBUG] ✓ Fetcher créé et connexion établie")
            
            # Option: CALL Mars 2026, strike 98.00
            # Ticker Bloomberg: "ER H5 C98.00 Comdty"
            print("[DEBUG] Requête option EURIBOR:")
            print("[DEBUG]   - Underlying: ER")
            print("[DEBUG]   - Expiry: 2026-03-15")
            print("[DEBUG]   - Type: CALL")
            print("[DEBUG]   - Strike: 98.00")
            print("[DEBUG]   - is_euribor: True")
            
            option = fetcher.get_option_data(
                underlying="ER",
                expiry=date(2026, 3, 15),  # Mars 2026
                option_type="C",            # CALL
                strike=98.00,               # Strike = 98.00 → taux implicite 2.50%
                is_euribor=True
            )
            
            print(f"[DEBUG] Option retournée: {option}")
            print(f"[DEBUG] Type de l'option: {type(option)}")
            print(f"[DEBUG] Est EuriborOptionData? {isinstance(option, EuriborOptionData)}")
            
            if option and isinstance(option, EuriborOptionData):
                print("[DEBUG] ✓ Option EURIBOR valide trouvée")
                print(format_euribor_option(option))
                print(f"\nDétails:")
                print(f"  - Ticker Bloomberg: {option.ticker}")
                print(f"  - Taux implicite: {option.implied_rate:.2f}%")
                print(f"  - Valeur du tick: €{option.tick_value:.2f}")
                
                if option.last:
                    print(f"  - Dernier prix: ${option.last:.2f}")
                    print(f"  - Valeur notionnelle: €{option.last * option.contract_size:.2f}")
                else:
                    print("[DEBUG] ⚠️ Pas de dernier prix disponible")
            elif option:
                print(f"[DEBUG] ⚠️ Option trouvée mais n'est pas EuriborOptionData (type: {type(option)})")
            else:
                print("[DEBUG] ✗ Option non trouvée (retour None)")
                print("❌ Option non trouvée. Vérifiez:")
                print("  - Bloomberg Terminal est lancé")
                print("  - La date d'expiry existe (contrats trimestriels)")
                print("  - Le ticker est correct")
                
    except Exception as e:
        print(f"[DEBUG] ✗ Exception dans example_1: {type(e).__name__}: {e}")
        raise  # Re-lever l'exception pour la gérer dans main()


def example_2_euribor_term_structure():
    """
    Exemple 2: Analyser la structure de terme de la volatilité EURIBOR.
    
    On scanne toutes les expiries disponibles pour un strike donné (ex: 98.00)
    et on affiche comment la volatilité implicite évolue dans le temps.
    """
    print("\n" + "="*80)
    print("EXEMPLE 2: Structure de terme - Volatilité EURIBOR")
    print("="*80)
    
    with BloombergOptionFetcher() as fetcher:
        # Lister toutes les expiries EURIBOR disponibles
        print("Récupération des dates d'expiration EURIBOR...")
        expiries = fetcher.list_expiries("ER", is_euribor=True)
        
        if expiries:
            print(f"✓ {len(expiries)} expiries trouvées")
            print(f"  Première: {expiries[0]}")
            print(f"  Dernière: {expiries[-1]}")
            
            # Scanner toutes les options CALL à strike 98.00
            print("\nRécupération des options CALL strike 98.00...")
            options = fetcher.get_options_by_strike(
                underlying="ER",
                strike=98.00,
                option_type="C",
                expiries=expiries[:6],  # Limiter aux 6 premières pour l'exemple
                is_euribor=True
            )
            
            if options:
                print(f"✓ {len(options)} options récupérées\n")
                
                # Afficher la structure de terme de la volatilité
                print(format_term_structure(options, "implied_volatility"))
                
                # Afficher aussi le tableau complet
                print(format_option_table(options, "EURIBOR CALLs Strike 98.00"))
            else:
                print("❌ Aucune option récupérée")
        else:
            print("❌ Aucune expiry trouvée")


def example_3_euribor_payoff_scenarios():
    """
    Exemple 3: Calculer les payoffs d'une option EURIBOR sous différents scénarios.
    
    On prend une position (ex: CALL strike 98.00) et on calcule le P&L
    selon différents scénarios de taux EURIBOR à l'expiration.
    """
    print("\n" + "="*80)
    print("EXEMPLE 3: Scénarios de payoff EURIBOR")
    print("="*80)
    
    with BloombergOptionFetcher() as fetcher:
        # Récupérer une option CALL
        option = fetcher.get_option_data(
            underlying="ER",
            expiry=date(2026, 3, 15),
            option_type="C",
            strike=98.00,  # Taux implicite: 2.50%
            is_euribor=True
        )
        
        if not option:
            print("❌ Option non trouvée")
            return
        
        # Vérifier que c'est bien un EuriborOptionData
        if not isinstance(option, EuriborOptionData):
            print("❌ Erreur: option n'est pas de type EuriborOptionData")
            return
        
        print(f"Position: LONG {option.ticker}")
        print(f"Strike: {option.strike} (Taux implicite: {option.implied_rate:.2f}%)")
        
        if option.last:
            premium_paid = option.last * option.contract_size
            print(f"Prime payée: ${option.last:.2f} × €{option.contract_size:.0f} = €{premium_paid:.2f}")
        else:
            premium_paid = 0
            print("⚠️ Prix non disponible, on suppose prime = 0 pour l'exemple")
        
        print("\nScénarios de taux EURIBOR à l'expiration:")
        print("-" * 60)
        
        # Tester différents scénarios de taux
        rate_scenarios = [2.00, 2.25, 2.50, 2.75, 3.00, 3.25, 3.50]
        
        for rate in rate_scenarios:
            payoff = option.payoff_at_rate(rate)
            pnl = payoff - premium_paid
            
            print(f"Taux final: {rate:.2f}% → Payoff: €{payoff:>8.2f} | P&L: €{pnl:>8.2f}")
        
        print("-" * 60)
        print("\nInterprétation:")
        print(f"  - Strike 98.00 = Taux implicite {option.implied_rate:.2f}%")
        print(f"  - CALL profitable si taux final < {option.implied_rate:.2f}%")
        print(f"  - Perte limitée à la prime payée: €{premium_paid:.2f}")


def example_4_euribor_spread_strategy():
    """
    Exemple 4: Analyser un spread sur EURIBOR (Bull Call Spread).
    
    Stratégie:
    - Acheter CALL strike 98.00 (taux implicite 2.50%)
    - Vendre CALL strike 98.00 (taux implicite 2.00%)
    
    C'est un pari que les taux vont baisser (prix du future monte).
    """
    print("\n" + "="*80)
    print("EXEMPLE 4: Bull Call Spread EURIBOR")
    print("="*80)
    
    with BloombergOptionFetcher() as fetcher:
        # Jambe longue: BUY CALL 98.00
        long_call = fetcher.get_option_data(
            underlying="ER",
            expiry=date(2026, 3, 15),
            option_type="C",
            strike=98.00,
            is_euribor=True
        )
        
        # Jambe courte: SELL CALL 98.00
        short_call = fetcher.get_option_data(
            underlying="ER",
            expiry=date(2026, 3, 15),
            option_type="C",
            strike=98.00,
            is_euribor=True
        )
        
        if not long_call or not short_call:
            print("❌ Options non trouvées")
            return
        
        # Vérifier que ce sont bien des EuriborOptionData
        if not isinstance(long_call, EuriborOptionData) or not isinstance(short_call, EuriborOptionData):
            print("❌ Erreur: les options ne sont pas de type EuriborOptionData")
            return
        
        print("Stratégie: Bull Call Spread")
        print(f"  Jambe 1: BUY  {long_call.ticker}")
        print(f"  Jambe 2: SELL {short_call.ticker}")
        
        # Calculer le coût du spread
        if long_call.last and short_call.last:
            net_premium = (long_call.last - short_call.last) * long_call.contract_size
            max_profit = (short_call.strike - long_call.strike) * long_call.contract_size - net_premium
            max_loss = net_premium
            
            print(f"\nCoût net du spread: €{net_premium:.2f}")
            print(f"Profit maximum: €{max_profit:.2f}")
            print(f"Perte maximum: €{max_loss:.2f}")
            print(f"Break-even rate: {100 - (long_call.strike + net_premium / long_call.contract_size):.2f}%")
        else:
            print("\n⚠️ Prix non disponibles pour calculer le spread")
        
        print("\nGreeks combinés:")
        if long_call.delta and short_call.delta:
            net_delta = long_call.delta - short_call.delta
            print(f"  Net Delta: {net_delta:.3f}")
        
        if long_call.vega and short_call.vega:
            net_vega = long_call.vega - short_call.vega
            print(f"  Net Vega: {net_vega:.3f} (exposition à la volatilité)")


def main():
    """
    Fonction principale - exécute tous les exemples.
    """
    print("\n" + "="*80)
    print("EXEMPLES D'UTILISATION: OPTIONS EURIBOR VIA BLOOMBERG")
    print("="*80)
    print("\nCes exemples démontrent comment:")
    print("  1. Récupérer des données d'options EURIBOR individuelles")
    print("  2. Analyser la structure de terme de la volatilité")
    print("  3. Calculer des payoffs sous différents scénarios de taux")
    print("  4. Construire et analyser des spreads sur taux")
    
    try:
        print("\n[DEBUG] Démarrage des exemples...")
        
        # Exécuter chaque exemple
        print("[DEBUG] Exécution de l'exemple 1: Option EURIBOR spécifique")
        example_1_single_euribor_option()
        
        # Décommenter pour exécuter les autres exemples
        # print("[DEBUG] Exécution de l'exemple 2: Structure de terme")
        # example_2_euribor_term_structure()
        # print("[DEBUG] Exécution de l'exemple 3: Scénarios de payoff")
        # example_3_euribor_payoff_scenarios()
        # print("[DEBUG] Exécution de l'exemple 4: Bull Call Spread")
        # example_4_euribor_spread_strategy()
        
        print("\n" + "="*80)
        print("✓ Exemples terminés avec succès")
        print("="*80)
        
    except ImportError as e:
        print(f"\n❌ ERREUR D'IMPORT: {e}")
        print("\n[DEBUG] Type d'erreur: ImportError")
        print("[DEBUG] Détails de l'erreur:")
        import traceback
        traceback.print_exc()
        print("\nSolution:")
        print("  - Installez le module manquant: pip install blpapi")
        
    except ConnectionError as e:
        print(f"\n❌ ERREUR DE CONNEXION BLOOMBERG: {e}")
        print("\n[DEBUG] Type d'erreur: ConnectionError")
        print("[DEBUG] Détails de l'erreur:")
        import traceback
        traceback.print_exc()
        print("\nSolution:")
        print("  - Vérifiez que Bloomberg Terminal est lancé")
        print("  - Vérifiez que vous êtes connecté (login Bloomberg)")
        print("  - Redémarrez Bloomberg Terminal si nécessaire")
        
    except AttributeError as e:
        print(f"\n❌ ERREUR D'ATTRIBUT: {e}")
        print("\n[DEBUG] Type d'erreur: AttributeError")
        print("[DEBUG] Cela arrive souvent quand l'option retournée n'est pas du bon type")
        print("[DEBUG] Détails de l'erreur:")
        import traceback
        traceback.print_exc()
        print("\nSolution:")
        print("  - Vérifiez que is_euribor=True est bien passé")
        print("  - Vérifiez que le ticker EURIBOR existe pour cette date")
        
    except Exception as e:
        print(f"\n❌ ERREUR INATTENDUE: {e}")
        print(f"\n[DEBUG] Type d'erreur: {type(e).__name__}")
        print("[DEBUG] Stack trace complet:")
        import traceback
        traceback.print_exc()
        print("\nInformations de debug:")
        print(f"  - Type d'exception: {type(e).__module__}.{type(e).__name__}")
        print(f"  - Message: {str(e)}")
        print("\nVérifications à faire:")
        print("  - Bloomberg Terminal est lancé et connecté")
        print("  - Le module blpapi est installé (pip install blpapi)")
        print("  - Vous avez accès aux données EURIBOR sur votre abonnement")
        print("  - Les dates d'expiry sont correctes (contrats trimestriels)")


if __name__ == "__main__":
    main()
