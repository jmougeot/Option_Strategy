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
    from bloomberg.fetcher_batch import fetch_options_batch, extract_best_values
    from bloomberg.ticker_builder import build_option_ticker
except ImportError:
    # Fallback pour imports directs
    import os
    bloomberg_dir = os.path.join(os.path.dirname(__file__), 'bloomberg')
    sys.path.insert(0, bloomberg_dir)
    from fetcher_batch import fetch_options_batch, extract_best_values
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


def build_ticker_info(
    underlying: str,
    month: MonthCode,
    year: int,
    option_type: Literal['C', 'P'],
    strike: float,
    suffix: str = "Comdty"
) -> tuple[str, str, str]:
    """
    Construit le ticker et les métadonnées.
    
    Returns:
        (ticker, expiration_date, option_type_str)
    """
    ticker = build_option_ticker(underlying, month, year, option_type, strike, suffix)
    expiration_date = get_expiration_date(month, year)
    option_type_str = "call" if option_type == 'C' else "put"
    
    return ticker, expiration_date, option_type_str


def convert_to_option_dict(
    ticker: str,
    underlying: str,
    strike: float,
    expiration_date: str,
    option_type_str: str,
    bloomberg_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convertit les données Bloomberg brutes en format attendu par l'app.
    
    Args:
        ticker: Ticker Bloomberg
        underlying: Symbole du sous-jacent
        strike: Prix d'exercice
        expiration_date: Date d'expiration
        option_type_str: "call" ou "put"
        bloomberg_data: Données extraites de Bloomberg
        
    Returns:
        Dictionnaire formaté pour l'app
    """
    return {
        "symbol": underlying,
        "strike": float(strike),
        "option_type": option_type_str,
        "premium": float(bloomberg_data['premium']),
        "expiration_date": expiration_date,
        "underlying_price": float(bloomberg_data['underlying_price']),
        "bid": float(bloomberg_data['bid']),
        "ask": float(bloomberg_data['ask']),
        "volume": int(bloomberg_data['volume']),
        "open_interest": int(bloomberg_data['open_interest']),
        "implied_volatility": float(bloomberg_data['implied_volatility']),
        "delta": float(bloomberg_data['delta']),
        "gamma": float(bloomberg_data['gamma']),
        "theta": float(bloomberg_data['theta']),
        "vega": float(bloomberg_data['vega']),
        "rho": float(bloomberg_data['rho']),
        "timestamp": datetime.now().isoformat(),
        "bloomberg_ticker": ticker
    }


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
    
    # OPTIMISATION: Construire tous les tickers d'abord, puis fetch en batch
    all_tickers = []
    ticker_metadata = {}  # Stocke les métadonnées pour chaque ticker
    
    print("\n🔨 Construction des tickers...")
    for year in years:
        for month in months:
            month_code = cast(MonthCode, month)
            
            for strike in strikes:
                # Calls
                if include_calls:
                    ticker, exp_date, opt_type = build_ticker_info(underlying, month_code, year, 'C', strike, suffix)
                    all_tickers.append(ticker)
                    ticker_metadata[ticker] = {
                        'underlying': underlying,
                        'strike': strike,
                        'expiration_date': exp_date,
                        'option_type': opt_type,
                        'month': month,
                        'year': year
                    }
                    total_attempts += 1
                
                # Puts
                if include_puts:
                    ticker, exp_date, opt_type = build_ticker_info(underlying, month_code, year, 'P', strike, suffix)
                    all_tickers.append(ticker)
                    ticker_metadata[ticker] = {
                        'underlying': underlying,
                        'strike': strike,
                        'expiration_date': exp_date,
                        'option_type': opt_type,
                        'month': month,
                        'year': year
                    }
                    total_attempts += 1
    
    print(f"✓ {len(all_tickers)} tickers construits")
    print(f"\n📡 Récupération des données Bloomberg en batch...")
    print(f"   (UN SEUL appel pour TOUS les tickers - beaucoup plus rapide!)")
    
    # FETCH EN BATCH - UN SEUL APPEL BLOOMBERG POUR TOUS LES TICKERS
    try:
        batch_data = fetch_options_batch(all_tickers, use_overrides=True)
        
        # Traiter les résultats par mois pour l'affichage
        for year in years:
            for month in months:
                month_options = []
                
                print(f"\n📅 {MONTH_NAMES[month]} 20{20+year}")
                print("-" * 70)
                
                for ticker in all_tickers:
                    meta = ticker_metadata[ticker]
                    
                    # Filtrer par mois/année courant
                    if meta['month'] != month or meta['year'] != year:
                        continue
                    
                    # Récupérer les données brutes
                    raw_data = batch_data.get(ticker, {})
                    
                    if raw_data and not all(v is None for v in raw_data.values()):
                        # Extraire les meilleures valeurs
                        extracted = extract_best_values(raw_data)
                        
                        # Convertir au format attendu
                        option_dict = convert_to_option_dict(
                            ticker=ticker,
                            underlying=meta['underlying'],
                            strike=meta['strike'],
                            expiration_date=meta['expiration_date'],
                            option_type_str=meta['option_type'],
                            bloomberg_data=extracted
                        )
                        
                        options.append(option_dict)
                        month_options.append(option_dict)
                        total_success += 1
                        
                        # Afficher un résumé
                        opt_symbol = "C" if option_dict['option_type'] == "call" else "P"
                        print(f"✓ {opt_symbol} {option_dict['strike']:6.2f}: "
                              f"Premium={option_dict['premium']:.4f}, "
                              f"Delta={option_dict['delta']:+.4f}, "
                              f"IV={option_dict['implied_volatility']:.2%}")
                
                if month_options:
                    print(f"\n   ✓ {len(month_options)} options récupérées pour ce mois")
                else:
                    print(f"\n   ⚠️  Aucune option récupérée pour ce mois")
    
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()
    
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
