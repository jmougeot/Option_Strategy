"""
Test Bloomberg avec build_option_ticker
========================================
Test d'utilisation de la fonction build_option_ticker pour construire 
un ticker EURIBOR et récupérer les données incluant les Greeks.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.bloomberg.ticker_builder import build_option_ticker
from src.bloomberg.connection import BloombergConnection
from src.bloomberg.fetcher import BloombergOptionFetcher


def test_ticker_builder():
    """Test de construction de ticker avec build_option_ticker"""
    print("=" * 70)
    print("TEST 1: Construction du ticker")
    print("=" * 70)
    
    # Paramètres spécifiés par l'utilisateur
    underlying = "ER"
    expiry_month = "F"
    expiry_year = 6
    option_type = "C"
    strike = 97.5
    suffix = "Comdty"
    
    # Construction du ticker
    ticker = build_option_ticker(
        underlying=underlying,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        option_type=option_type,
        strike=strike,
        suffix=suffix
    )
    
    print(f"\nParamètres:")
    print(f"  Underlying: {underlying}")
    print(f"  Expiry Month: {expiry_month}")
    print(f"  Expiry Year: {expiry_year}")
    print(f"  Option Type: {option_type}")
    print(f"  Strike: {strike}")
    print(f"  Suffix: {suffix}")
    print(f"\nTicker construit: {ticker}")
    print(f"✓ Format attendu: ERF6C 97.5 Comdty")
    
    return ticker


def test_bloomberg_data(ticker):
    """Test de récupération des données Bloomberg incluant GREEK_MID"""
    print("\n" + "=" * 70)
    print("TEST 2: Connexion Bloomberg et récupération des données")
    print("=" * 70)
    
    fetcher = None
    try:
        # Liste des champs incluant les Greeks individuels
        fields = [
            "PX_LAST",
            "PX_BID",
            "PX_ASK",
            "PX_MID",
            "DELTA_MID",          # Delta
            "GAMMA_MID",          # Gamma
            "VEGA_MID",           # Vega
            "THETA_MID",          # Theta
            "RHO_MID",            # Rho
            "OPT_DELTA",          # Alternatif Delta
            "OPT_GAMMA",          # Alternatif Gamma
            "OPT_VEGA",           # Alternatif Vega
            "OPT_THETA",          # Alternatif Theta
            "OPT_RHO",            # Alternatif Rho
            "OPT_STRIKE_PX",
            "OPT_UNDL_PX",
            "OPT_PUT_CALL",
            "OPEN_INT",
            "VOLUME"
        ]
        
        # Créer le fetcher avec les champs personnalisés
        print("\n[1/2] Initialisation du fetcher...")
        fetcher = BloombergOptionFetcher(fields=fields)
        
        # Établir la connexion Bloomberg
        print("\n[2/2] Connexion à Bloomberg Terminal...")
        if not fetcher.connect():
            print("✗ Échec de connexion à Bloomberg Terminal")
            print("  Assurez-vous que Bloomberg Terminal est ouvert et connecté")
            return False
        print("✓ Connexion établie")
        
        print("\n✓ Fetcher initialisé")
        print(f"\nChamps demandés ({len(fields)}):")
        for field in fields:
            print(f"  - {field}")
        
        print(f"\nNote: Les overrides PRICING_SOURCE=BGNE et REFERENCE_DATE=TODAY")
        print(f"      sont automatiquement ajoutés par le fetcher")
        
        # Récupérer les données - utiliser l'API correcte
        # Extraire les paramètres du ticker ERF6C 97.5 Comdty
        print(f"\nRécupération des données pour {ticker}...")
        option_data = fetcher.get_option_data(
            underlying="ER",
            expiry_month="F",
            expiry_year=6,
            option_type="C",
            strike=97.5
        )
        
        # Récupérer également les données brutes pour voir GREEK_MID
        print(f"\nRécupération des données brutes incluant GREEK_MID...")
        raw_data = fetcher._send_request(ticker, fields)
        
        # Afficher les résultats
        print("\n" + "=" * 70)
        print("RÉSULTATS")
        print("=" * 70)
        
        if option_data:
            print(f"\n✓ Données récupérées avec succès pour {ticker}\n")
            
            # Prix
            print("PRIX:")
            print(f"  PX_LAST:     {option_data.last or 'N/A'}")
            print(f"  PX_BID:      {option_data.bid or 'N/A'}")
            print(f"  PX_ASK:      {option_data.ask or 'N/A'}")
            print(f"  PX_MID:      {option_data.mid or 'N/A'}")
            if option_data.spread:
                print(f"  SPREAD:      {option_data.spread:.4f}")
            
            # Greeks - Formats _MID
            print("\nGREEKS (format _MID):")
            delta_mid = raw_data.get('DELTA_MID', 'N/A')
            gamma_mid = raw_data.get('GAMMA_MID', 'N/A')
            vega_mid = raw_data.get('VEGA_MID', 'N/A')
            theta_mid = raw_data.get('THETA_MID', 'N/A')
            rho_mid = raw_data.get('RHO_MID', 'N/A')
            print(f"  DELTA_MID:   {delta_mid}")
            print(f"  GAMMA_MID:   {gamma_mid}")
            print(f"  VEGA_MID:    {vega_mid}")
            print(f"  THETA_MID:   {theta_mid}")
            print(f"  RHO_MID:     {rho_mid}")
            
            # Greeks - Individuels (depuis OptionData)
            print("\nGREEKS (format OPT_ - via OptionData):")
            print(f"  Delta:       {option_data.delta or 'N/A'} (depuis OPT_DELTA)")
            print(f"  Gamma:       {option_data.gamma or 'N/A'} (depuis OPT_GAMMA)")
            print(f"  Vega:        {option_data.vega or 'N/A'} (depuis OPT_VEGA)")
            print(f"  Theta:       {option_data.theta or 'N/A'} (depuis OPT_THETA)")
            print(f"  Rho:         {option_data.rho or 'N/A'} (depuis OPT_RHO)")
            
            # Informations du contrat
            print("\nINFORMATIONS CONTRAT:")
            print(f"  Ticker:      {option_data.ticker}")
            print(f"  Strike:      {option_data.strike}")
            print(f"  Type:        {option_data.option_type}")
            print(f"  Expiry:      {option_data.expiry_month}{option_data.expiry_year}")
            print(f"  Underlying:  {option_data.underlying}")
            
            # Volatilité implicite
            print("\nVOLATILITÉ:")
            print(f"  IV:          {option_data.implied_volatility or 'N/A'}")
            
            # Volume & Open Interest
            print("\nVOLUME & OPEN INTEREST:")
            print(f"  Volume:      {option_data.volume or 'N/A'}")
            print(f"  Open Int:    {option_data.open_interest or 'N/A'}")
            print(f"  Liquidité:   {'✓ Liquide' if option_data.is_liquid else '✗ Peu liquide'}")
            
            # Résumé des champs bruts retournés
            print("\n" + "-" * 70)
            print(f"Total des champs bruts retournés: {len(raw_data)}/{len(fields)}")
            
            if len(raw_data) < len(fields):
                missing = set(fields) - set(raw_data.keys())
                print(f"Champs non retournés ({len(missing)}): {', '.join(sorted(missing))}")
            
            # Afficher tous les champs bruts reçus
            print(f"\nChamps bruts disponibles:")
            for field_name, field_value in sorted(raw_data.items()):
                print(f"  {field_name}: {field_value}")
            
            return True
        else:
            print(f"\n✗ Aucune donnée retournée pour {ticker}")
            print("  Vérifiez que le ticker est valide et que l'option existe")
            return False
            
    except Exception as e:
        print(f"\n✗ Erreur lors de la récupération des données:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Fermer la connexion via le fetcher
        if 'fetcher' in locals() and fetcher:
            fetcher.disconnect()
            print("\n✓ Connexion Bloomberg fermée")


def main():
    """Fonction principale"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "TEST BLOOMBERG TICKER BUILDER" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")
    
    # Test 1: Construction du ticker
    ticker = test_ticker_builder()
    
    # Test 2: Récupération des données Bloomberg
    input("\nAppuyez sur Entrée pour continuer avec le test Bloomberg...")
    success = test_bloomberg_data(ticker)
    
    # Résumé final
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"Ticker construit: {ticker}")
    print(f"Test Bloomberg: {'✓ SUCCÈS' if success else '✗ ÉCHEC'}")
    print("\n")


if __name__ == "__main__":
    main()
