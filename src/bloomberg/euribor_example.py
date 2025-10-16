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
Date: 2025-10-16
"""

from datetime import date
from bloomberg import (
    BloombergOptionFetcher,
    format_euribor_option,
    format_option_table,
    format_term_structure
)


def example_1_single_euribor_option():
    """
    Exemple 1: Récupérer une option EURIBOR spécifique.
    
    On cherche un CALL sur le future EURIBOR Mars 2025, strike 97.50
    (ce qui correspond à un taux implicite de 2.50%)
    """
    print("\n" + "="*80)
    print("EXEMPLE 1: Option EURIBOR spécifique")
    print("="*80)
    
    with BloombergOptionFetcher() as fetcher:
        # Option: CALL Mars 2025, strike 97.50
        # Ticker Bloomberg: "ER H5 C97.50 Comdty"
        option = fetcher.get_option_data(
            underlying="ER",
            expiry=date(2025, 3, 15),  # Mars 2025
            option_type="C",            # CALL
            strike=97.50,               # Strike = 97.50 → taux implicite 2.50%
            is_euribor=True
        )
        
        if option:
            print(format_euribor_option(option))
            print(f"\nDétails:")
            print(f"  - Ticker Bloomberg: {option.ticker}")
            print(f"  - Taux implicite: {option.implied_rate:.2f}%")
            print(f"  - Valeur du tick: €{option.tick_value:.2f}")
            
            if option.last:
                print(f"  - Dernier prix: ${option.last:.2f}")
                print(f"  - Valeur notionnelle: €{option.last * option.contract_size:.2f}")
        else:
            print("❌ Option non trouvée. Vérifiez:")
            print("  - Bloomberg Terminal est lancé")
            print("  - La date d'expiry existe (contrats trimestriels)")
            print("  - Le ticker est correct")


def example_2_euribor_term_structure():
    """
    Exemple 2: Analyser la structure de terme de la volatilité EURIBOR.
    
    On scanne toutes les expiries disponibles pour un strike donné (ex: 97.50)
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
            
            # Scanner toutes les options CALL à strike 97.50
            print("\nRécupération des options CALL strike 97.50...")
            options = fetcher.get_options_by_strike(
                underlying="ER",
                strike=97.50,
                option_type="C",
                expiries=expiries[:6],  # Limiter aux 6 premières pour l'exemple
                is_euribor=True
            )
            
            if options:
                print(f"✓ {len(options)} options récupérées\n")
                
                # Afficher la structure de terme de la volatilité
                print(format_term_structure(options, "implied_volatility"))
                
                # Afficher aussi le tableau complet
                print(format_option_table(options, "EURIBOR CALLs Strike 97.50"))
            else:
                print("❌ Aucune option récupérée")
        else:
            print("❌ Aucune expiry trouvée")


def example_3_euribor_payoff_scenarios():
    """
    Exemple 3: Calculer les payoffs d'une option EURIBOR sous différents scénarios.
    
    On prend une position (ex: CALL strike 97.50) et on calcule le P&L
    selon différents scénarios de taux EURIBOR à l'expiration.
    """
    print("\n" + "="*80)
    print("EXEMPLE 3: Scénarios de payoff EURIBOR")
    print("="*80)
    
    with BloombergOptionFetcher() as fetcher:
        # Récupérer une option CALL
        option = fetcher.get_option_data(
            underlying="ER",
            expiry=date(2025, 3, 15),
            option_type="C",
            strike=97.50,  # Taux implicite: 2.50%
            is_euribor=True
        )
        
        if not option:
            print("❌ Option non trouvée")
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
        print(f"  - Strike 97.50 = Taux implicite {option.implied_rate:.2f}%")
        print(f"  - CALL profitable si taux final < {option.implied_rate:.2f}%")
        print(f"  - Perte limitée à la prime payée: €{premium_paid:.2f}")


def example_4_euribor_spread_strategy():
    """
    Exemple 4: Analyser un spread sur EURIBOR (Bull Call Spread).
    
    Stratégie:
    - Acheter CALL strike 97.50 (taux implicite 2.50%)
    - Vendre CALL strike 98.00 (taux implicite 2.00%)
    
    C'est un pari que les taux vont baisser (prix du future monte).
    """
    print("\n" + "="*80)
    print("EXEMPLE 4: Bull Call Spread EURIBOR")
    print("="*80)
    
    with BloombergOptionFetcher() as fetcher:
        # Jambe longue: BUY CALL 97.50
        long_call = fetcher.get_option_data(
            underlying="ER",
            expiry=date(2025, 3, 15),
            option_type="C",
            strike=97.50,
            is_euribor=True
        )
        
        # Jambe courte: SELL CALL 98.00
        short_call = fetcher.get_option_data(
            underlying="ER",
            expiry=date(2025, 3, 15),
            option_type="C",
            strike=98.00,
            is_euribor=True
        )
        
        if not long_call or not short_call:
            print("❌ Options non trouvées")
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
        # Exécuter chaque exemple
        example_1_single_euribor_option()
        
        # Décommenter pour exécuter les autres exemples
        # example_2_euribor_term_structure()
        # example_3_euribor_payoff_scenarios()
        # example_4_euribor_spread_strategy()
        
        print("\n" + "="*80)
        print("✓ Exemples terminés")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        print("\nVérifiez que:")
        print("  - Bloomberg Terminal est lancé et connecté")
        print("  - Le module blpapi est installé (pip install blpapi)")
        print("  - Vous avez accès aux données EURIBOR sur votre abonnement")


if __name__ == "__main__":
    main()
