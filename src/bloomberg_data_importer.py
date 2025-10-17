"""
Bloomberg Data Importer for Options Strategy App
=================================================
Importe les données d'options depuis Bloomberg et les convertit au format
JSON attendu par app.py

Structure de données attendue:
{
    "options": [
        {
            "symbol": "ER",
            "strike": 97.5,
            "option_type": "call" ou "put",
            "premium": 0.5625,
            "expiration_date": "2026-01-20",
            "underlying_price": 98.065,
            "bid": 0.55,
            "ask": 0.575,
            "volume": 1000,
            "open_interest": 5000,
            "implied_volatility": 0.15,
            "delta": 0.62,
            "gamma": 0.05,
            "theta": -0.02,
            "vega": 0.10,
            "rho": 0.03,
            "timestamp": "2025-10-17T10:00:00"
        },
        ...
    ]
}

Usage:
    from bloomberg_data_importer import import_euribor_options
    
    # Importer toutes les options EURIBOR disponibles
    data = import_euribor_options(
        underlying="ER",
        months=["F", "G", "H"],  # Jan, Feb, Mar
        years=[6, 7],  # 2026, 2027
        strikes=[96.0, 96.5, 97.0, 97.5, 98.0, 98.5, 99.0]
    )
    
    # Sauvegarder en JSON
    save_to_json(data, "euribor_options.json")

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Literal, Optional, cast
from datetime import datetime
import json
import os

# Add parent directory and bloomberg directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent))
sys.path.insert(0, str(current_dir))

# Import depuis le répertoire bloomberg
try:
    from bloomberg.fetcher_v2 import bbg_fetch
    from bloomberg.ticker_builder import build_option_ticker
except ImportError:
    # Fallback pour imports directs
    import os
    bloomberg_dir = os.path.join(os.path.dirname(__file__), 'bloomberg')
    sys.path.insert(0, bloomberg_dir)
    from fetcher_v2 import bbg_fetch
    from ticker_builder import build_option_ticker

# Type pour les mois valides
MonthCode = Literal['F', 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']


# Mapping des mois Bloomberg vers les noms complets
MONTH_NAMES = {
    'F': 'January', 'G': 'February', 'H': 'March', 'K': 'April',
    'M': 'June', 'N': 'July', 'Q': 'August', 'U': 'September',
    'V': 'October', 'X': 'November', 'Z': 'December'
}

# Mapping des mois vers les dates d'expiration (3ème mercredi du mois)
MONTH_EXPIRY_DAY = {
    'F': 15, 'G': 19, 'H': 19, 'K': 16,
    'M': 18, 'N': 16, 'Q': 20, 'U': 17,
    'V': 15, 'X': 19, 'Z': 17
}


def get_expiration_date(month: str, year: int) -> str:
    """
    Calcule la date d'expiration (3ème mercredi du mois)
    
    Args:
        month: Code du mois (F, G, H, etc.)
        year: Année sur 1 chiffre (6 = 2026)
        
    Returns:
        Date au format ISO "YYYY-MM-DD"
    """
    # Convertir l'année
    full_year = 2020 + year
    
    # Obtenir le numéro du mois
    month_number = list(MONTH_NAMES.keys()).index(month) + 1
    if month_number > 12:
        month_number = month_number - 12
        full_year += 1
    
    # Approximation du 3ème mercredi (jour 15-21 généralement)
    day = MONTH_EXPIRY_DAY.get(month, 18)
    
    return f"{full_year:04d}-{month_number:02d}-{day:02d}"


def fetch_option_data(
    underlying: str,
    month: MonthCode,
    year: int,
    option_type: Literal['C', 'P'],
    strike: float,
    suffix: str = "Comdty"
) -> Optional[Dict[str, Any]]:
    """
    Récupère les données d'une option depuis Bloomberg
    
    Args:
        underlying: Code du sous-jacent (ex: "ER" pour EURIBOR)
        month: Mois d'expiration (F, G, H, etc.)
        year: Année sur 1 chiffre (6 = 2026)
        option_type: 'C' pour Call, 'P' pour Put
        strike: Prix d'exercice
        suffix: Suffixe Bloomberg (défaut: "Comdty")
        
    Returns:
        Dictionnaire avec les données de l'option ou None si erreur
    """
    # Construire le ticker
    ticker = build_option_ticker(underlying, month, year, option_type, strike, suffix)
    
    # Champs à récupérer
    fields = [
        "PX_LAST",           # Prix (premium)
        "PX_BID",            # Bid
        "PX_ASK",            # Ask
        "PX_MID",            # Mid
        "DELTA_MID",         # Delta
        "DELTA",             # Delta alternatif
        "OPT_DELTA",         # Delta alternatif 2
        "GAMMA_MID",         # Gamma
        "GAMMA",
        "OPT_GAMMA",
        "VEGA_MID",          # Vega
        "VEGA",
        "OPT_VEGA",
        "THETA_MID",         # Theta
        "THETA",
        "OPT_THETA",
        "RHO_MID",           # Rho
        "RHO",
        "OPT_RHO",
        "OPT_IMP_VOL",       # Volatilité implicite
        "IMP_VOL",
        "IVOL_MID",
        "OPT_UNDL_PX",       # Prix du sous-jacent
        "OPT_STRIKE_PX",     # Strike
        "OPEN_INT",          # Open interest
        "VOLUME",            # Volume
        "PX_VOLUME",         # Volume alternatif
    ]
    
    try:
        # Récupérer les données
        data = bbg_fetch(ticker, fields)
        
        if not data or all(v is None for v in data.values()):
            print(f"⚠️  Aucune donnée pour {ticker}")
            return None
        
        # Extraire le prix (premium) - essayer plusieurs champs
        premium = data.get('PX_LAST') or data.get('PX_MID') or 0.0
        bid = data.get('PX_BID') or premium * 0.98
        ask = data.get('PX_ASK') or premium * 1.02
        
        # Greeks - essayer plusieurs formats
        delta = data.get('DELTA_MID') or data.get('DELTA') or data.get('OPT_DELTA') or 0.0
        gamma = data.get('GAMMA_MID') or data.get('GAMMA') or data.get('OPT_GAMMA') or 0.0
        vega = data.get('VEGA_MID') or data.get('VEGA') or data.get('OPT_VEGA') or 0.0
        theta = data.get('THETA_MID') or data.get('THETA') or data.get('OPT_THETA') or 0.0
        rho = data.get('RHO_MID') or data.get('RHO') or data.get('OPT_RHO') or 0.0
        
        # Volatilité implicite
        iv = data.get('OPT_IMP_VOL') or data.get('IMP_VOL') or data.get('IVOL_MID') or 0.15
        
        # Prix du sous-jacent
        underlying_price = data.get('OPT_UNDL_PX') or strike
        
        # Volume et Open Interest
        volume = data.get('VOLUME') or data.get('PX_VOLUME') or 0
        open_interest = data.get('OPEN_INT') or 0
        
        # Calculer la date d'expiration
        expiration_date = get_expiration_date(month, year)
        
        # Convertir le type d'option
        option_type_str = "call" if option_type == 'C' else "put"
        
        # Construire le dictionnaire de données
        option_data = {
            "symbol": underlying,
            "strike": float(strike),
            "option_type": option_type_str,
            "premium": float(premium) if premium else 0.0,
            "expiration_date": expiration_date,
            "underlying_price": float(underlying_price) if underlying_price else strike,
            "bid": float(bid) if bid else 0.0,
            "ask": float(ask) if ask else 0.0,
            "volume": int(volume) if volume else 0,
            "open_interest": int(open_interest) if open_interest else 0,
            "implied_volatility": float(iv) if iv else 0.15,
            "delta": float(delta) if delta else 0.0,
            "gamma": float(gamma) if gamma else 0.0,
            "theta": float(theta) if theta else 0.0,
            "vega": float(vega) if vega else 0.0,
            "rho": float(rho) if rho else 0.0,
            "timestamp": datetime.now().isoformat(),
            "bloomberg_ticker": ticker
        }
        
        print(f"✓ {ticker}: Premium={premium:.4f}, Delta={delta:.4f}, IV={iv:.2%}")
        
        return option_data
        
    except Exception as e:
        print(f"✗ Erreur pour {ticker}: {e}")
        return None


def import_euribor_options(
    underlying: str = "ER",
    months: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    strikes: Optional[List[float]] = None,
    suffix: str = "Comdty",
    include_calls: bool = True,
    include_puts: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Importe un ensemble d'options EURIBOR depuis Bloomberg
    
    Args:
        underlying: Code du sous-jacent (défaut: "ER")
        months: Liste des mois (défaut: ["F", "G", "H"] - Jan, Feb, Mar)
        years: Liste des années (défaut: [6, 7] - 2026, 2027)
        strikes: Liste des strikes (défaut: range de 96.0 à 99.0 par 0.5)
        suffix: Suffixe Bloomberg (défaut: "Comdty")
        include_calls: Importer les calls (défaut: True)
        include_puts: Importer les puts (défaut: True)
        
    Returns:
        Dictionnaire avec clé "options" contenant la liste des options
    """
    # Valeurs par défaut
    if months is None:
        months = ["F", "G", "H", "K", "M", "N"]  # Jan à Jul
    
    if years is None:
        years = [6, 7]  # 2026, 2027
    
    if strikes is None:
        # Strikes de 96.0 à 99.0 par pas de 0.25
        strikes = [round(96.0 + i * 0.25, 2) for i in range(13)]  # 96.0 à 99.0
    
    print("=" * 70)
    print("IMPORT DES OPTIONS DEPUIS BLOOMBERG")
    print("=" * 70)
    print(f"Sous-jacent: {underlying}")
    print(f"Mois: {', '.join(months)}")
    print(f"Années: {', '.join(map(str, years))}")
    print(f"Strikes: {len(strikes)} strikes de {min(strikes)} à {max(strikes)}")
    print(f"Types: {'Calls' if include_calls else ''}{' + ' if include_calls and include_puts else ''}{'Puts' if include_puts else ''}")
    print("=" * 70)
    print()
    
    options = []
    total_attempts = 0
    total_success = 0
    
    # Boucler sur toutes les combinaisons
    for year in years:
        for month in months:
            # Cast month to MonthCode for type safety
            month_code = cast(MonthCode, month)
            
            print(f"\n📅 {MONTH_NAMES[month]} 20{20+year}")
            print("-" * 70)
            
            for strike in strikes:
                # Calls
                if include_calls:
                    total_attempts += 1
                    call_data = fetch_option_data(underlying, month_code, year, 'C', strike, suffix)
                    if call_data:
                        options.append(call_data)
                        total_success += 1
                
                # Puts
                if include_puts:
                    total_attempts += 1
                    put_data = fetch_option_data(underlying, month_code, year, 'P', strike, suffix)
                    if put_data:
                        options.append(put_data)
                        total_success += 1
    
    print("\n" + "=" * 70)
    print("RÉSUMÉ DE L'IMPORT")
    print("=" * 70)
    print(f"Total tentatives: {total_attempts}")
    print(f"Succès: {total_success} ({total_success/total_attempts*100:.1f}%)")
    print(f"Échecs: {total_attempts - total_success}")
    print(f"Options importées: {len(options)}")
    print("=" * 70)
    
    return {"options": options}


def save_to_json(data: Dict, filename: str = "bloomberg_options.json"):
    """
    Sauvegarde les données au format JSON
    
    Args:
        data: Dictionnaire avec les données
        filename: Nom du fichier de sortie
    """
    filepath = Path(__file__).parent / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Données sauvegardées dans: {filepath}")
    print(f"   {len(data.get('options', []))} options exportées")


def main():
    """
    Fonction principale - exemple d'utilisation
    """
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "BLOOMBERG DATA IMPORTER" + " " * 30 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\n")
    
    # Configuration de l'import
    print("📋 Configuration de l'import:")
    print("   • Sous-jacent: EURIBOR (ER)")
    print("   • Mois: Janvier à Juillet (F, G, H, K, M, N)")
    print("   • Années: 2026, 2027")
    print("   • Strikes: 96.0 à 99.0 par 0.25")
    print("   • Types: Calls et Puts")
    print()
    
    input("Appuyez sur Entrée pour démarrer l'import...")
    print()
    
    # Importer les données
    data = import_euribor_options(
        underlying="ER",
        months=["F", "G", "H", "K", "M", "N"],  # Jan à Jul
        years=[6, 7],  # 2026, 2027
        strikes=[round(96.0 + i * 0.25, 2) for i in range(13)],  # 96.0 à 99.0
        include_calls=True,
        include_puts=True
    )
    
    # Sauvegarder
    save_to_json(data, "bloomberg_euribor_options.json")
    
    # Statistiques
    options = data.get('options', [])
    if options:
        calls = [o for o in options if o['option_type'] == 'call']
        puts = [o for o in options if o['option_type'] == 'put']
        
        print("\n📊 STATISTIQUES:")
        print(f"   • Total options: {len(options)}")
        print(f"   • Calls: {len(calls)}")
        print(f"   • Puts: {len(puts)}")
        
        if options:
            avg_iv = sum(o.get('implied_volatility', 0) for o in options) / len(options)
            print(f"   • Vol implicite moyenne: {avg_iv:.2%}")
    
    print("\n✅ Import terminé!")
    print(f"   Utilisez 'bloomberg_euribor_options.json' dans app.py")
    print()


if __name__ == "__main__":
    main()
