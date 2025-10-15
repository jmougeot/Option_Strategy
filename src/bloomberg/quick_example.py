"""
Exemple Rapide - Bloomberg Option Fetcher
==========================================
Exemples d'utilisation courante du module

Pour exécuter:
    python3 src/bloomberg/quick_example.py
"""

import sys
from pathlib import Path

# Ajouter src/ au path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from bloomberg import BloombergOptionFetcher, format_option_table
from datetime import datetime, timedelta


def example_1_single_option():
    """Exemple 1: Récupérer une option SPY CALL"""
    print("\n" + "="*80)
    print("📌 EXEMPLE 1: Option SPY CALL unique")
    print("="*80)
    
    with BloombergOptionFetcher() as fetcher:
        option = fetcher.get_option_data(
            underlying='SPY',
            option_type='CALL',
            strike=450.0,
            expiration='2024-12-20'
        )
        
        if option:
            print(f"\n✅ Option: {option.ticker}")
            print(f"   Prix: ${option.last:.2f}")
            print(f"   Delta: {option.delta:.4f}")
            print(f"   IV: {option.implied_volatility:.2f}%")


def example_2_option_chain():
    """Exemple 2: Chaîne d'options autour de l'ATM"""
    print("\n" + "="*80)
    print("📌 EXEMPLE 2: Chaîne d'options SPY")
    print("="*80)
    
    # Date d'expiration: dans 30 jours
    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Strikes autour de 450
    strikes = [440, 445, 450, 455, 460]
    
    with BloombergOptionFetcher() as fetcher:
        options = fetcher.get_option_chain(
            underlying='SPY',
            expiration=exp_date,
            strikes=strikes,
            option_types=['CALL', 'PUT']
        )
        
        if options:
            print(format_option_table(options))


def example_3_compare_greeks():
    """Exemple 3: Comparer les Greeks de plusieurs options"""
    print("\n" + "="*80)
    print("📌 EXEMPLE 3: Comparaison de Greeks")
    print("="*80)
    
    strikes = [445, 450, 455]
    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    with BloombergOptionFetcher() as fetcher:
        print(f"\n{'Strike':<10} {'Delta':<10} {'Gamma':<10} {'Vega':<10} {'Theta':<10}")
        print("-" * 50)
        
        for strike in strikes:
            option = fetcher.get_option_data('SPY', 'CALL', strike, exp_date)
            
            if option:
                print(f"${strike:<9.2f} "
                      f"{option.delta:<10.4f} "
                      f"{option.gamma:<10.6f} "
                      f"{option.vega:<10.4f} "
                      f"{option.theta:<10.4f}")


def example_4_implied_vol_smile():
    """Exemple 4: Smile de volatilité implicite"""
    print("\n" + "="*80)
    print("📌 EXEMPLE 4: Smile de volatilité implicite")
    print("="*80)
    
    strikes = [430, 435, 440, 445, 450, 455, 460, 465, 470]
    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    with BloombergOptionFetcher() as fetcher:
        print(f"\n{'Strike':<10} {'Call IV':<12} {'Put IV':<12}")
        print("-" * 40)
        
        for strike in strikes:
            call = fetcher.get_option_data('SPY', 'CALL', strike, exp_date)
            put = fetcher.get_option_data('SPY', 'PUT', strike, exp_date)
            
            if call and put:
                call_iv = f"{call.implied_volatility:.2f}%" if call.implied_volatility else "N/A"
                put_iv = f"{put.implied_volatility:.2f}%" if put.implied_volatility else "N/A"
                print(f"${strike:<9.2f} {call_iv:<12} {put_iv:<12}")


def example_5_vertical_spread():
    """Exemple 5: Analyser un Bull Call Spread"""
    print("\n" + "="*80)
    print("📌 EXEMPLE 5: Bull Call Spread")
    print("="*80)
    
    long_strike = 445
    short_strike = 455
    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    with BloombergOptionFetcher() as fetcher:
        long_call = fetcher.get_option_data('SPY', 'CALL', long_strike, exp_date)
        short_call = fetcher.get_option_data('SPY', 'CALL', short_strike, exp_date)
        
        if long_call and short_call:
            net_debit = long_call.last - short_call.last
            max_profit = (short_strike - long_strike) - net_debit
            max_loss = net_debit
            breakeven = long_strike + net_debit
            net_delta = long_call.delta - short_call.delta
            
            print(f"\n📊 Bull Call Spread SPY")
            print(f"   Long  ${long_strike} CALL @ ${long_call.last:.2f}")
            print(f"   Short ${short_strike} CALL @ ${short_call.last:.2f}")
            print(f"\n   ───────────────────────────────")
            print(f"   Net Debit:   ${net_debit:.2f}")
            print(f"   Max Profit:  ${max_profit:.2f}")
            print(f"   Max Loss:    ${max_loss:.2f}")
            print(f"   Breakeven:   ${breakeven:.2f}")
            print(f"   Net Delta:   {net_delta:.4f}")
            print(f"   Risk/Reward: {max_loss/max_profit:.2f}")


def main():
    """Exécute tous les exemples"""
    print("\n🚀 " + "="*76)
    print("🚀 EXEMPLES D'UTILISATION - Bloomberg Option Fetcher")
    print("🚀 " + "="*76)
    
    examples = [
        example_1_single_option,
        example_2_option_chain,
        example_3_compare_greeks,
        example_4_implied_vol_smile,
        example_5_vertical_spread,
    ]
    
    for i, example in enumerate(examples, 1):
        try:
            example()
        except Exception as e:
            print(f"\n❌ Erreur dans l'exemple {i}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("✅ Exemples terminés!")
    print("="*80 + "\n")


if __name__ == "__main__":
    print("\n⚠️  Assurez-vous que Bloomberg Terminal est ouvert et connecté!\n")
    
    response = input("Continuer? (o/n): ").strip().lower()
    
    if response == 'o':
        main()
    else:
        print("❌ Exemples annulés")
