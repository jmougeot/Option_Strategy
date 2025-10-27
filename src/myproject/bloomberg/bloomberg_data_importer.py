"""
Bloomberg Data Importer for Options Strategy App
=================================================
Importe les données d'options depuis Bloomberg et les convertit directement
en objets Option avec calcul optionnel des surfaces.
"""

from pathlib import Path
from typing import List, Literal, Optional, cast
from datetime import datetime
import json
from myproject.bloomberg.fetcher_batch import fetch_options_batch, extract_best_values
from myproject.bloomberg.ticker_builder import build_option_ticker
from myproject.option.option_class import Option

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


def get_expiration_components(month: str, year: int) -> tuple[MonthCode, int, str]:
    """
    Calcule les composants d'expiration pour une option.
    
    Args:
        month: Code du mois Bloomberg (F, G, H, etc.)
        year: Année sur 1 chiffre (6 = 2026)
        
    Returns:
        (month_code, year, day_str)
    """
    day = MONTH_EXPIRY_DAY.get(month, 18)
    return cast(MonthCode, month), year, str(day)


def create_option_from_bloomberg(
    ticker: str,
    underlying: str,
    strike: float,
    month: str,
    year: int,
    option_type_str: str,
    bloomberg_data: dict,
    position: Literal['long', 'short'] = 'long',
    quantity: int = 1,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    calculate_surfaces: bool = True,
    num_points: int = 200
) -> Option:
    """
    Crée un objet Option directement depuis les données Bloomberg.
    
    Args:
        ticker: Ticker Bloomberg
        underlying: Symbole du sous-jacent
        strike: Prix d'exercice
        month: Code du mois d'expiration
        year: Année d'expiration (1 chiffre)
        option_type_str: "call" ou "put"
        bloomberg_data: Données brutes Bloomberg
        position: 'long' ou 'short'
        quantity: Quantité
        price_min: Prix min pour surfaces
        price_max: Prix max pour surfaces
        calculate_surfaces: Si True, calcule les surfaces
        num_points: Nombre de points pour les surfaces
        
    Returns:
        Objet Option
    """
    try:
        month_code, exp_year, exp_day = get_expiration_components(month, year)
        
        # Créer l'option directement
        option = Option(
            # Obligatoires
            option_type=option_type_str,
            strike=float(strike),
            premium=float(bloomberg_data['premium']),
            expiration_month=month_code,
            expiration_year=exp_year,
            expiration_day=exp_day,
            
            # Position
            quantity=quantity,
            position=position,
            
            # Identification
            ticker=ticker,
            underlying_symbol=underlying,
            bloomberg_ticker=ticker,
            
            # Prix
            bid=float(bloomberg_data['bid']),
            ask=float(bloomberg_data['ask']),
            
            # Greeks
            delta=float(bloomberg_data['delta']),
            gamma=float(bloomberg_data['gamma']),
            vega=float(bloomberg_data['vega']),
            theta=float(bloomberg_data['theta']),
            rho=float(bloomberg_data['rho']),
            
            # Volatilité
            implied_volatility=float(bloomberg_data['implied_volatility']),
            
            # Liquidité
            open_interest=int(bloomberg_data['open_interest']),
            volume=int(bloomberg_data['volume']),
            
            # Sous-jacent
            underlying_price=float(bloomberg_data['underlying_price']),
            
            # Timestamp
            timestamp=datetime.now()
        )
        
        # Calculer les surfaces si demandé
        if calculate_surfaces and price_min is not None and price_max is not None:
            option.profit_surface = option.calcul_profit_surface(price_min, price_max, num_points)
            option.loss_surface = option.calcul_loss_surface(price_min, price_max, num_points)
        
        return option
        
    except Exception as e:
        print(f"⚠️ Erreur création Option: {e}")
        return Option.empyOption()


def import_euribor_options(
    underlying: str = "ER",
    months: List[str] = [],
    years: List[int] = [],
    strikes: List[float] = [],
    suffix: str = "Comdty",
    include_calls: bool = True,
    include_puts: bool = True,
    default_position: Literal['long', 'short'] = 'long',
    default_quantity: int = 1,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    calculate_surfaces: bool = True,
    num_points: int = 200
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
    print("=" * 70)
    print("IMPORT DES OPTIONS DEPUIS BLOOMBERG")
    print("=" * 70)
    print(f"Sous-jacent: {underlying}")
    print(f"Mois: {', '.join(months)}")
    print(f"Années: {', '.join(map(str, years))}")
    print(f"Strikes: {len(strikes)} strikes de {min(strikes)} à {max(strikes)}")
    print(f"Types: {'Calls' if include_calls else ''}{' + ' if include_calls and include_puts else ''}{'Puts' if include_puts else ''}")
    print(f"Calcul surfaces: {'Oui' if calculate_surfaces else 'Non'}")
    if calculate_surfaces and price_min and price_max:
        print(f"Range de prix: ${price_min} - ${price_max}")
    print("=" * 70)
    print()
    
    option_objects: List[Option] = []
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
                # Calls
                if include_calls:
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
                
                # Puts
                if include_puts:
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
    
    print(f"✓ {len(all_tickers)} tickers construits")
    print(f"\n📡 Récupération des données Bloomberg en batch...")
    
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
                        
                        # Créer l'option directement
                        option = create_option_from_bloomberg(
                            ticker=ticker,
                            underlying=meta['underlying'],
                            strike=meta['strike'],
                            month=meta['month'],
                            year=meta['year'],
                            option_type_str=meta['option_type'],
                            bloomberg_data=extracted,
                            position=default_position,
                            quantity=default_quantity,
                            price_min=price_min,
                            price_max=price_max,
                            calculate_surfaces=calculate_surfaces,
                            num_points=num_points
                        )
                        
                        # Vérifier que l'option est valide
                        if option.strike > 0 and option.premium > 0:
                            option_objects.append(option)
                            month_options_count += 1
                            total_success += 1
                            
                            # Afficher un résumé
                            opt_symbol = "C" if option.option_type == "call" else "P"
                            surfaces_info = f", Surf.P={option.profit_surface:.2f}, Surf.L={option.loss_surface:.2f}"
                            
                            print(f"✓ {opt_symbol} {option.strike:6.2f}: "
                                  f"Premium={option.premium:.4f}, "
                                  f"Delta={option.delta:+.4f}, "
                                  f"IV={option.implied_volatility:.2%}"
                                  f"{surfaces_info}")
                
                if month_options_count > 0:
                    print(f"\n   ✓ {month_options_count} options récupérées pour ce mois")
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
    print(f"Succès: {total_success} ({total_success/total_attempts*100:.1f}%)" if total_attempts > 0 else "Succès: 0")
    print(f"Échecs: {total_attempts - total_success}")
    print(f"Options importées: {len(option_objects)}")
    print("=" * 70)
    
    return option_objects


def save_to_json(options: List[Option], filename: str = "bloomberg_options.json"):
    """
    Sauvegarde une liste d'options au format JSON.
    
    Args:
        options: Liste d'objets Option
        filename: Nom du fichier de sortie
    """
    filepath = Path(__file__).parent / filename
    
    # Convertir les objets Option en dictionnaires
    options_dicts = []
    for opt in options:
        opt_dict = {
            "symbol": opt.underlying_symbol,
            "strike": opt.strike,
            "option_type": opt.option_type,
            "premium": opt.premium,
            "expiration_date": f"{2020 + opt.expiration_year}-{opt.expiration_month}-{opt.expiration_day or 15:02d}",
            "underlying_price": opt.underlying_price,
            "bid": opt.bid,
            "ask": opt.ask,
            "volume": opt.volume or 0.0,
            "open_interest": opt.open_interest,
            "implied_volatility": opt.implied_volatility,
            "delta": opt.delta ,
            "gamma": opt.gamma,
            "theta": opt.theta,
            "vega": opt.vega,
            "rho": opt.rho or 0.0,
            "timestamp": datetime.now().isoformat(),
            "bloomberg_ticker": opt.bloomberg_ticker or opt.ticker,
            "month_of_expiration": opt.expiration_month,
            "year_of_expiration": opt.expiration_year,
            "day_of_expiration": opt.expiration_day
        }
        options_dicts.append(opt_dict)
    
    data = {"options": options_dicts}
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Données sauvegardées dans: {filepath}")
    print(f"   {len(options)} options exportées")
