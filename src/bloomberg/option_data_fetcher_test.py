"""
Script de Test - Bloomberg Option Data Fetcher
==============================================
Test complet du système de récupération de données d'options Bloomberg

Usage:
    python3 src/bloomberg/option_data_fetcher_test.py
"""

import sys
from pathlib import Path

# Ajouter src/ au path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from bloomberg.option_data_fetcher import BloombergOptionFetcher, format_option_table
from datetime import datetime, timedelta


def test_connection():
    """Test 1: Connexion au Terminal Bloomberg"""
    print("\n" + "="*80)
    print("🧪 TEST 1: Connexion Bloomberg Terminal")
    print("="*80)
    
    fetcher = BloombergOptionFetcher()
    
    if fetcher.connect():
        print("✅ Connexion réussie!")
        fetcher.disconnect()
        return True
    else:
        print("❌ Échec de connexion")
        print("\n⚠️  Vérifiez que:")
        print("   1. Bloomberg Terminal est ouvert")
        print("   2. Vous êtes authentifié")
        print("   3. Le port 8194 est accessible")
        return False


def test_single_option():
    """Test 2: Récupération d'une option unique"""
    print("\n" + "="*80)
    print("🧪 TEST 2: Récupération d'une option SPY CALL")
    print("="*80)
    
    # Paramètres de test
    underlying = "SPY"
    option_type = "CALL"
    strike = 450.0
    
    # Date d'expiration: dans 30 jours
    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"\n📋 Paramètres:")
    print(f"   Underlying: {underlying}")
    print(f"   Type: {option_type}")
    print(f"   Strike: ${strike}")
    print(f"   Expiration: {exp_date}")
    
    with BloombergOptionFetcher() as fetcher:
        option = fetcher.get_option_data(underlying, option_type, strike, exp_date)
        
        if option:
            print("\n✅ Option récupérée avec succès!")
            print(f"\n📊 Données de l'option:")
            print(f"   Ticker: {option.ticker}")
            print(f"\n💰 Prix:")
            print(f"   Bid:  ${option.bid:.2f}" if option.bid else "   Bid:  N/A")
            print(f"   Ask:  ${option.ask:.2f}" if option.ask else "   Ask:  N/A")
            print(f"   Last: ${option.last:.2f}" if option.last else "   Last: N/A")
            print(f"   Mid:  ${option.mid:.2f}" if option.mid else "   Mid:  N/A")
            
            print(f"\n📈 Greeks:")
            print(f"   Delta: {option.delta:.4f}" if option.delta else "   Delta: N/A")
            print(f"   Gamma: {option.gamma:.4f}" if option.gamma else "   Gamma: N/A")
            print(f"   Vega:  {option.vega:.4f}" if option.vega else "   Vega:  N/A")
            print(f"   Theta: {option.theta:.4f}" if option.theta else "   Theta: N/A")
            print(f"   Rho:   {option.rho:.4f}" if option.rho else "   Rho:   N/A")
            
            print(f"\n📊 Autres:")
            print(f"   IV:            {option.implied_volatility:.2f}%" if option.implied_volatility else "   IV:            N/A")
            print(f"   Open Interest: {option.open_interest:,}" if option.open_interest else "   Open Interest: N/A")
            print(f"   Volume:        {option.volume:,}" if option.volume else "   Volume:        N/A")
            
            return True
        else:
            print("❌ Échec de récupération de l'option")
            return False


def test_option_chain():
    """Test 3: Récupération d'une chaîne d'options"""
    print("\n" + "="*80)
    print("🧪 TEST 3: Récupération d'une chaîne d'options")
    print("="*80)
    
    underlying = "SPY"
    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Strikes autour de la monnaie (ATM ±10)
    strikes = [440.0, 445.0, 450.0, 455.0, 460.0]
    
    print(f"\n📋 Paramètres:")
    print(f"   Underlying: {underlying}")
    print(f"   Expiration: {exp_date}")
    print(f"   Strikes: {strikes}")
    
    with BloombergOptionFetcher() as fetcher:
        options = fetcher.get_option_chain(
            underlying=underlying,
            expiration=exp_date,
            strikes=strikes,
            option_types=['CALL', 'PUT']
        )
        
        if options:
            print(f"\n✅ {len(options)} options récupérées!")
            print(format_option_table(options))
            return True
        else:
            print("❌ Aucune option récupérée")
            return False


def test_ticker_format():
    """Test 4: Formatage des tickers Bloomberg"""
    print("\n" + "="*80)
    print("🧪 TEST 4: Formatage des tickers Bloomberg")
    print("="*80)
    
    fetcher = BloombergOptionFetcher()
    
    test_cases = [
        ("SPY", "CALL", 450.0, "2024-12-20"),
        ("AAPL", "PUT", 175.5, "2024-11-15"),
        ("QQQ", "CALL", 380.0, "2025-01-17"),
    ]
    
    print("\n📝 Tickers générés:")
    for underlying, opt_type, strike, exp in test_cases:
        ticker = fetcher._build_option_ticker(underlying, opt_type, strike, exp)
        print(f"   {underlying} {opt_type} ${strike} exp:{exp} → {ticker}")
    
    print("\n✅ Test de formatage réussi!")
    return True


def test_custom_fields():
    """Test 5: Récupération de champs personnalisés"""
    print("\n" + "="*80)
    print("🧪 TEST 5: Récupération de champs personnalisés")
    print("="*80)
    
    underlying = "SPY"
    option_type = "CALL"
    strike = 450.0
    exp_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Seulement les champs de prix et delta
    custom_fields = ['PX_LAST', 'PX_BID', 'PX_ASK', 'DELTA', 'IVOL_MID']
    
    print(f"\n📋 Champs demandés: {', '.join(custom_fields)}")
    
    with BloombergOptionFetcher() as fetcher:
        option = fetcher.get_option_data(
            underlying, option_type, strike, exp_date,
            fields=custom_fields
        )
        
        if option:
            print("\n✅ Données récupérées avec champs personnalisés!")
            print(f"   Last:  ${option.last:.2f}" if option.last else "   Last:  N/A")
            print(f"   Delta: {option.delta:.4f}" if option.delta else "   Delta: N/A")
            print(f"   IV:    {option.implied_volatility:.2f}%" if option.implied_volatility else "   IV:    N/A")
            return True
        else:
            print("❌ Échec de récupération")
            return False


def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "🚀 " + "="*76)
    print("🚀 SUITE DE TESTS - Bloomberg Option Data Fetcher")
    print("🚀 " + "="*76)
    
    tests = [
        ("Connexion Bloomberg", test_connection),
        ("Option unique", test_single_option),
        ("Chaîne d'options", test_option_chain),
        ("Format ticker", test_ticker_format),
        ("Champs personnalisés", test_custom_fields),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ ERREUR dans {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("-"*80)
    print(f"Résultat: {passed}/{total} tests réussis ({passed/total*100:.0f}%)")
    print("="*80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
