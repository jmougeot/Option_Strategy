"""
Bloomberg Data Importer for Options Strategy App
=================================================
Importe les données d'options depuis Bloomberg et les convertit directement
en objets Option avec calcul optionnel des surfaces.
"""

from pathlib import Path
from typing import List, Literal, Optional, cast, Tuple 
from datetime import datetime
import json
from myproject.bloomberg.fetcher_batch import fetch_options_batch, extract_best_values
from myproject.bloomberg.ticker_builder import build_option_ticker
from myproject.bloomberg.bloomber_to_opt import create_option_from_bloomberg
from myproject.option.option_class import Option
import numpy as np

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


def import_euribor_options(
    underlying: str = "ER",
    months: List[str] = [],
    years: List[int] = [] ,
    strikes: List[float] = [],
    suffix: str = "Comdty",
    default_position: Literal['long', 'short'] = 'long',
    mixture: Optional[Tuple[np.ndarray, np.ndarray]] = None ,
) -> List[Option]:
    """
    Importe un ensemble d'options depuis Bloomberg et retourne directement des objets Option.
    
    Args:
        underlying: Symbole du sous-jacent (ex: "ER" pour Euribor)
        months: Liste des mois Bloomberg (ex: ['M', 'U', 'Z'])
        years: Liste des années (ex: [6, 7] pour 2026, 2027)
        strikes: Liste des strikes à importer
        suffix: Suffixe Bloomberg (ex: "Comdty")
        include_calls: Inclure les calls
        include_puts: Inclure les puts
        default_position: Position par défaut ('long' ou 'short')
        default_quantity: Quantité par défaut
        price_min: Prix minimum pour le calcul des surfaces
        price_max: Prix maximum pour le calcul des surfaces
        calculate_surfaces: Si True, calcule profit_surface et loss_surface
        num_points: Nombre de points pour le calcul des surfaces

    Returns:
        Liste d'objets Option directement utilisables
    """ 
    list_option: List[Option] = []
    total_attempts = 0
    total_success = 0
    
    # Construire tous les tickers et métadonnées
    all_tickers = []
    ticker_metadata = {}
    
    print("\n🔨 Construction des tickers...")
    for year in years:
        for month in months:
            month_code = cast(MonthCode, month)
            for strike in strikes:
                    ticker = build_option_ticker(underlying, month_code, year, 'C', strike, suffix)
                    all_tickers.append(ticker)
                    ticker_metadata[ticker] = {
                        'underlying': underlying,
                        'strike': strike,
                        'option_type': 'call',
                        'month': month,
                        'year': year
                    }
                    total_attempts += 1

                    ticker = build_option_ticker(underlying, month_code, year, 'P', strike, suffix)
                    all_tickers.append(ticker)
                    ticker_metadata[ticker] = {
                        'underlying': underlying,
                        'strike': strike,
                        'option_type': 'put',
                        'month': month,
                        'year': year
                    }
                    total_attempts += 1
        
    # FETCH EN BATCH
    try:
        batch_data = fetch_options_batch(all_tickers, use_overrides=True)
        
        # Traiter les résultats par mois
        for year in years:
            for month in months:
                month_options_count = 0
                
                print(f"\n📅 {MONTH_NAMES[month]} 20{20+year}")
                print("-" * 70)
                
                for ticker in all_tickers:
                    meta = ticker_metadata[ticker]
                    
                    # Filtrer par mois/année
                    if meta['month'] != month or meta['year'] != year:
                        continue
                    
                    # Récupérer les données brutes
                    raw_data = batch_data.get(ticker, {})
                    
                    if raw_data and not all(v is None for v in raw_data.values()):
                        # Extraire les meilleures valeurs
                        extracted = extract_best_values(raw_data)
                        
                        # Créer l'option directement (les surfaces sont calculées dans create_option_from_bloomberg)
                        option = create_option_from_bloomberg(
                            ticker=ticker,
                            underlying=meta['underlying'],
                            strike=meta['strike'],
                            month=meta['month'],
                            year=meta['year'],
                            option_type_str=meta['option_type'],
                            bloomberg_data=extracted,
                            position=default_position,
                            mixture = mixture,    
                        )
                        
                        # Vérifier que l'option est valide
                        if option.strike > 0 :
                            list_option.append(option)
                            month_options_count += 1
                            total_success += 1
                            
                            # Afficher un résumé
                            opt_symbol = "C" if option.option_type == "call" else "P"
                            surfaces_info = f", Surf.P={option.profit_surface_ponderated:.2f}, Surf.L={option.loss_surface_ponderated:.2f}"
                            
                            print(f"✓ {opt_symbol} {option.strike}: "
                                  f"Premium={option.premium}, "
                                  f"Delta={option.delta}, "
                                  f"IV={option.implied_volatility}")
    
    except Exception as e:
        print(f"\n✗ Erreur lors du fetch batch: {e}")
        import traceback
        traceback.print_exc()
    

    print("\n" + "=" * 70)
    print("RÉSUMÉ DE L'IMPORT")
    print("=" * 70)
    print(f"Total tentatives: {total_attempts}")
    print(f"Succès: {total_success} ({total_success/total_attempts*100:.1f}%)" if total_attempts > 0 else "Succès: 0")
    print(f"Échecs: {total_attempts - total_success}")
    print("=" * 70)
    
    return list_option