"""
Test Complet Bloomberg Fetcher V2
==================================
Test de toutes les fonctionnalités du fetcher_v2 incluant:
- Tous les Greeks possibles (DELTA, GAMMA, VEGA, THETA, RHO)
- Volatilité implicite
- Différents formats de champs Bloomberg

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bloomberg.fetcher_v2 import bbg_fetch, bbg_fetch_multi, bdp


def print_header(title):
    """Affiche un en-tête formaté"""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70 + "\n")


def print_section(title):
    """Affiche un titre de section"""
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70)


def test_single_field():
    """Test 1: Récupération d'un seul champ"""
    print_section("TEST 1: Récupération d'un seul champ (DELTA_MID)")
    
    ticker = "ERF6C 97.5 Comdty"
    field = "DELTA_MID"
    
    try:
        print(f"Ticker: {ticker}")
        print(f"Champ: {field}")
        print()
        
        delta = bbg_fetch(ticker, field)
        
        print(f"✓ Résultat: {delta}")
        print(f"  Type: {type(delta).__name__}")
        
        return True
    except Exception as e:
        print(f"✗ Erreur: {type(e).__name__}: {e}")
        return False


def test_all_greeks():
    """Test 2: Tous les Greeks possibles"""
    print_section("TEST 2: Tous les Greeks possibles + Volatilité Implicite")
    
    ticker = "ERF6C 97.5 Comdty"
    
    # Liste complète de tous les champs Greeks possibles
    greek_fields = [
        # Champs globaux Greeks
        "GREEK_MID",          # Tous les Greeks ensemble (si disponible)
        "OPT_GREEK",          # Alternatif pour tous les Greeks
        
        # Format _MID (recommandé)
        "DELTA_MID",
        "GAMMA_MID", 
        "VEGA_MID",
        "THETA_MID",
        "RHO_MID",
        
        # Format sans préfixe (court)
        "DELTA",
        "GAMMA",
        "VEGA",
        "THETA",
        "RHO",
        
        # Format OPT_ (alternatif)
        "OPT_DELTA",
        "OPT_GAMMA",
        "OPT_VEGA",
        "OPT_THETA",
        "OPT_RHO",
        
        # Bid/Ask Greeks
        "OPT_DELTA_BID",
        "OPT_DELTA_ASK",
        "OPT_GAMMA_BID",
        "OPT_GAMMA_ASK",
        "OPT_VEGA_BID",
        "OPT_VEGA_ASK",
        
        # Volatilité implicite (tous les formats)
        "OPT_IMP_VOL",        # Volatilité implicite mid
        "OPT_IVOL_MID",       # Alternative
        "OPT_IVOL_BID",       # Vol implicite bid
        "OPT_IVOL_ASK",       # Vol implicite ask
        "IVOL_MID",           # Format court
        "IVOL_BID",
        "IVOL_ASK",
        "IMP_VOL",            # Format court sans préfixe
        "IMPL_VOL",           # Autre variante
        
        # Prix pour contexte
        "PX_LAST",
        "PX_BID",
        "PX_ASK",
        "PX_MID",
    ]
    
    try:
        print(f"Ticker: {ticker}")
        print(f"Nombre de champs demandés: {len(greek_fields)}")
        print()
        
        data = bbg_fetch(ticker, greek_fields)
        
        # Compter les champs retournés
        fields_returned = {k: v for k, v in data.items() if v is not None}
        fields_missing = {k: v for k, v in data.items() if v is None}
        
        print(f"✓ Requête réussie!")
        print(f"  Champs retournés: {len(fields_returned)}/{len(greek_fields)}")
        print(f"  Champs manquants: {len(fields_missing)}")
        print()
        
        # Afficher les champs globaux Greeks d'abord
        print("CHAMPS GLOBAUX GREEKS:")
        for field in ["GREEK_MID", "OPT_GREEK"]:
            value = data.get(field)
            status = "✓" if value is not None else "✗"
            print(f"  {status} {field:20} = {value}")
        
        # Afficher les Greeks par catégorie
        print("\nGREEKS (format _MID):")
        for field in ["DELTA_MID", "GAMMA_MID", "VEGA_MID", "THETA_MID", "RHO_MID"]:
            value = data.get(field)
            status = "✓" if value is not None else "✗"
            print(f"  {status} {field:20} = {value}")
        
        print("\nGREEKS (format court - sans préfixe):")
        for field in ["DELTA", "GAMMA", "VEGA", "THETA", "RHO"]:
            value = data.get(field)
            status = "✓" if value is not None else "✗"
            print(f"  {status} {field:20} = {value}")
        
        print("\nGREEKS (format OPT_):")
        for field in ["OPT_DELTA", "OPT_GAMMA", "OPT_VEGA", "OPT_THETA", "OPT_RHO"]:
            value = data.get(field)
            status = "✓" if value is not None else "✗"
            print(f"  {status} {field:20} = {value}")
        
        print("\nGREEKS BID/ASK:")
        for field in ["OPT_DELTA_BID", "OPT_DELTA_ASK", "OPT_GAMMA_BID", "OPT_GAMMA_ASK", 
                      "OPT_VEGA_BID", "OPT_VEGA_ASK"]:
            value = data.get(field)
            status = "✓" if value is not None else "✗"
            print(f"  {status} {field:20} = {value}")
        
        print("\nVOLATILITÉ IMPLICITE:")
        for field in ["OPT_IMP_VOL", "OPT_IVOL_MID", "OPT_IVOL_BID", "OPT_IVOL_ASK",
                      "IVOL_MID", "IVOL_BID", "IVOL_ASK", "IMP_VOL", "IMPL_VOL"]:
            value = data.get(field)
            status = "✓" if value is not None else "✗"
            print(f"  {status} {field:20} = {value}")
        
        print("\nPRIX:")
        for field in ["PX_LAST", "PX_BID", "PX_ASK", "PX_MID"]:
            value = data.get(field)
            status = "✓" if value is not None else "✗"
            print(f"  {status} {field:20} = {value}")
        
        # Afficher tous les champs manquants
        if fields_missing:
            print("\nCHAMPS NON RETOURNÉS PAR BLOOMBERG:")
            for field in sorted(fields_missing.keys()):
                print(f"  • {field}")
        
        return True
    except Exception as e:
        print(f"✗ Erreur: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_minimal_greeks():
    """Test 3: Configuration minimale recommandée"""
    print_section("TEST 3: Configuration minimale recommandée (Greeks + Vol)")
    
    ticker = "ERF6C 97.5 Comdty"
    
    # Configuration minimale mais complète
    essential_fields = [
        # Champs globaux Greeks
        "GREEK_MID",
        "OPT_GREEK",
        
        # Prix
        "PX_LAST",
        "PX_BID", 
        "PX_ASK",
        
        # Greeks (essayer les deux formats)
        "DELTA_MID",
        "DELTA",
        "OPT_DELTA",
        "GAMMA_MID",
        "GAMMA",
        "OPT_GAMMA",
        "VEGA_MID",
        "VEGA",
        "OPT_VEGA",
        "THETA_MID",
        "THETA",
        "OPT_THETA",
        
        # Volatilité
        "OPT_IMP_VOL",
        
        # Informations contrat
        "OPT_STRIKE_PX",
        "OPT_UNDL_PX",
    ]
    
    try:
        print(f"Ticker: {ticker}")
        print(f"Champs essentiels: {len(essential_fields)}")
        print()
        
        data = bbg_fetch(ticker, essential_fields)
        
        print("✓ Données récupérées:\n")
        
        for field, value in data.items():
            if value is not None:
                print(f"  {field:20} = {value}")
            else:
                print(f"  {field:20} = (non disponible)")
        
        return True
    except Exception as e:
        print(f"✗ Erreur: {type(e).__name__}: {e}")
        return False


def test_multiple_tickers():
    """Test 4: Plusieurs tickers (Call et Put)"""
    print_section("TEST 4: Comparaison Call vs Put (même strike)")
    
    tickers = [
        "ERF6C 97.5 Comdty",  # Call
        "ERF6P 97.5 Comdty",  # Put
    ]
    
    fields = [
        "PX_LAST",
        "GREEK_MID",
        "OPT_GREEK",
        "DELTA_MID",
        "DELTA",
        "OPT_DELTA",
        "GAMMA_MID",
        "GAMMA",
        "VEGA_MID",
        "VEGA",
        "OPT_IMP_VOL",
        "IMP_VOL",
    ]
    
    try:
        print(f"Tickers: {len(tickers)}")
        for t in tickers:
            print(f"  - {t}")
        print()
        
        data = bbg_fetch_multi(tickers, fields)
        
        print("✓ Résultats:\n")
        
        for ticker, ticker_data in data.items():
            print(f"{ticker}:")
            for field, value in ticker_data.items():
                status = "✓" if value is not None else "✗"
                print(f"  {status} {field:20} = {value}")
            print()
        
        # Comparaison Delta
        call_delta = data[tickers[0]].get("DELTA_MID") or data[tickers[0]].get("DELTA") or data[tickers[0]].get("OPT_DELTA")
        put_delta = data[tickers[1]].get("DELTA_MID") or data[tickers[1]].get("DELTA") or data[tickers[1]].get("OPT_DELTA")
        
        if call_delta is not None and put_delta is not None:
            print("ANALYSE:")
            print(f"  Delta Call: {call_delta:+.4f}")
            print(f"  Delta Put:  {put_delta:+.4f}")
            print(f"  Vérification Put-Call: {call_delta + put_delta:.4f} (devrait ≈ 1.0 pour ATM)")
        
        return True
    except Exception as e:
        print(f"✗ Erreur: {type(e).__name__}: {e}")
        return False


def test_bdp_alias():
    """Test 5: Alias bdp (style Excel)"""
    print_section("TEST 5: Test alias bdp() - Style Excel =BDP()")
    
    ticker = "ERF6C 97.5 Comdty"
    
    try:
        print(f"Syntaxe: bdp('{ticker}', 'DELTA_MID')")
        print()
        
        delta = bdp(ticker, "DELTA_MID")
        
        print(f"✓ Delta: {delta}")
        print()
        print("Note: bdp() est un alias de bbg_fetch() pour rappeler")
        print("      la fonction Excel =BDP() (Bloomberg Data Point)")
        
        return True
    except Exception as e:
        print(f"✗ Erreur: {type(e).__name__}: {e}")
        return False


def test_with_custom_overrides():
    """Test 6: Overrides personnalisés"""
    print_section("TEST 6: Test avec overrides personnalisés")
    
    ticker = "ERF6C 97.5 Comdty"
    fields = ["DELTA_MID", "PX_LAST", "OPT_IMP_VOL"]
    
    # Overrides personnalisés
    custom_overrides = {
        "PRICING_SOURCE": "BGNE",
        "SETTLEMENT_DATE": "20260120",  # Date spécifique
    }
    
    try:
        print(f"Ticker: {ticker}")
        print(f"Overrides personnalisés:")
        for k, v in custom_overrides.items():
            print(f"  {k} = {v}")
        print()
        
        data = bbg_fetch(ticker, fields, use_overrides=True, overrides=custom_overrides)
        
        print("✓ Résultats avec overrides:\n")
        for field, value in data.items():
            print(f"  {field:20} = {value}")
        
        return True
    except Exception as e:
        print(f"✗ Erreur: {type(e).__name__}: {e}")
        return False


def main():
    """Fonction principale - exécute tous les tests"""
    print_header("TEST COMPLET BLOOMBERG FETCHER V2")
    print("Test de toutes les fonctionnalités incluant:")
    print("  • Tous les Greeks (DELTA, GAMMA, VEGA, THETA, RHO)")
    print("  • Volatilité implicite (tous formats)")
    print("  • Plusieurs tickers")
    print("  • Alias bdp() style Excel")
    print("  • Overrides personnalisés")
    
    # Exécuter tous les tests
    tests = [
        ("Un seul champ", test_single_field),
        ("Tous les Greeks + Vol", test_all_greeks),
        ("Configuration minimale", test_minimal_greeks),
        ("Plusieurs tickers", test_multiple_tickers),
        ("Alias bdp()", test_bdp_alias),
        ("Overrides personnalisés", test_with_custom_overrides),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            print(f"\n✗ Erreur inattendue dans {test_name}: {e}")
            results[test_name] = False
    
    # Résumé final
    print_header("RÉSUMÉ DES TESTS")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    print()
    print("=" * 70)
    print(f"TOTAL: {passed}/{total} tests réussis ({failed} échecs)")
    print("=" * 70)
    
    if failed == 0:
        print("\n🎉 Tous les tests sont passés avec succès!")
    else:
        print(f"\n⚠️  {failed} test(s) ont échoué - vérifiez les détails ci-dessus")


if __name__ == "__main__":
    main()
