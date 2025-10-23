"""
Conversion de Dictionnaires en Objets Option
=============================================

Ce module fournit deux fonctions pour convertir des dictionnaires (format Bloomberg)
en objets Option:

1. dict_to_option(): Conversion simple, rapide
2. dict_to_option_with_calcul(): Conversion + calcul des métriques de surface
   - Utilise les méthodes calcul_profit_surface() et calcul_loss_surface() de la classe Option
   - Permet de pré-calculer les surfaces pour éviter de les recalculer plusieurs fois
"""

from typing import Dict, Literal, Optional, List
from myproject.option.option_class import Option

def dict_to_option(option_dict: Dict, position: Literal['long', 'short'] = 'long', quantity: int = 1) -> Option:
    """
    Convertit un dictionnaire d'option (format Bloomberg) en objet Option.
    
    Args:
        option_dict: Dictionnaire avec les données de l'option
        position: 'long' ou 'short'
        quantity: Quantité
    
    Returns:
        Objet Option ou None si données invalides
    """
    try:
        # Extraire la date d'expiration
        expiration_day = option_dict.get('day_of_expiration')
        expiration_month = option_dict.get('month_of_expiration', 1)
        expiration_year = option_dict.get('year_of_expiration', 2025)

        
        return Option(
            # Obligatoires
            option_type=option_dict.get('option_type', 'call'),
            strike=float(option_dict.get('strike', 0.0)),
            premium=float(option_dict.get('premium', 0.0)),
            expiration_month= expiration_month,
            expiration_year=expiration_year,
            expiration_day= expiration_day,

            # Position
            quantity=quantity,
            position=position,
            
            # Identification
            ticker=option_dict.get('bloomberg_ticker'),
            underlying_symbol=option_dict.get('symbol'),
            
            # Prix
            bid=option_dict.get('bid'),
            ask=option_dict.get('ask'),
            last=option_dict.get('last'),
            mid=option_dict.get('mid'),
            
            # Greeks
            delta=option_dict.get('delta'),
            gamma=option_dict.get('gamma'),
            vega=option_dict.get('vega'),
            theta=option_dict.get('theta'),
            rho=option_dict.get('rho'),
            
            # Volatilité
            implied_volatility=option_dict.get('implied_volatility'),
            
            # Liquidité
            open_interest=option_dict.get('open_interest'),
            volume=option_dict.get('volume'),
            
            # Sous-jacent
            underlying_price=option_dict.get('underlying_price'),
            
            # Bloomberg
            bloomberg_ticker=option_dict.get('bloomberg_ticker'),
            timestamp=option_dict.get('timestamp')
        )
    except Exception as e:
        print(f"⚠️ Erreur conversion dict->Option: {e}")
        return Option.empyOption()

def dict_to_option_with_calcul(option_dict: Dict, 
                              position: Literal['long', 'short'] = 'long', 
                              quantity: int = 1,
                              price_min: Optional[float] = None,
                              price_max: Optional[float] = None,
                              num_points: int = 200) -> Option:
    """
    Convertit un dictionnaire d'option (format Bloomberg) en objet Option
    et calcule les métriques de surface (profit/loss surfaces).
    """
    try:
        # Extraire la date d'expiration
        expiration_day = option_dict.get('day_of_expiration')
        expiration_month = option_dict.get('month_of_expiration', 1)
        expiration_year = option_dict.get('year_of_expiration', 2025)

        # Créer l'option
        option = Option(
            # Obligatoires
            option_type=option_dict.get('option_type', 'call'),
            strike=float(option_dict.get('strike', 0.0)),
            premium=float(option_dict.get('premium', 0.0)),
            expiration_month= expiration_month,
            expiration_year=expiration_year,
            expiration_day= expiration_day,

            # Position
            quantity=quantity,
            position=position,

            # Identification
            ticker=option_dict.get('bloomberg_ticker'),
            underlying_symbol=option_dict.get('symbol'),
            
            # Prix
            bid=option_dict.get('bid'),
            ask=option_dict.get('ask'),
            last=option_dict.get('last'),
            mid=option_dict.get('mid'),
            
            # Greeks
            delta=option_dict.get('delta'),
            gamma=option_dict.get('gamma'),
            vega=option_dict.get('vega'),
            theta=option_dict.get('theta'),
            rho=option_dict.get('rho'),
            
            # Volatilité
            implied_volatility=option_dict.get('implied_volatility'),
            
            # Liquidité
            open_interest=option_dict.get('open_interest'),
            volume=option_dict.get('volume'),
            
            # Sous-jacent
            underlying_price=option_dict.get('underlying_price'),
            
            # Bloomberg
            bloomberg_ticker=option_dict.get('bloomberg_ticker'),
            timestamp=option_dict.get('timestamp')
        )
        
        # Calculer les métriques de surface si les prix sont fournis
        if price_min is not None and price_max is not None:
            try:
                option.profit_surface = option.calcul_profit_surface(price_min, price_max, num_points)
                option.loss_surface = option.calcul_loss_surface(price_min, price_max, num_points)
            except Exception as e:
                print(f"⚠️ Erreur calcul surfaces: {e}")
                option.profit_surface = 0.0
                option.loss_surface = 0.0
        
        return option
        
    except Exception as e:
        print(f"⚠️ Erreur conversion dict->Option: {e}")
        return Option.empyOption()

def bloomberg_data_to_options(bloomberg_data: List[Dict],
                              default_position: Literal['long', 'short'] = 'long',
                              default_quantity: int = 1,
                              price_min: Optional[float] = None,
                              price_max: Optional[float] = None,
                              num_points: int = 200,) -> List[Option]:
    """
    Convertit une liste complète de données Bloomberg en liste d'objets Option.
    Utilise dict_to_option_with_calcul pour calculer automatiquement les surfaces.
    """
    if not bloomberg_data:
        print("⚠️ Aucune donnée Bloomberg fournie")
        return []
    
    options = []
    errors = 0
    
    for i, option_dict in enumerate(bloomberg_data):
        try:
            # Extraire position et quantity si présents dans les données
            position = option_dict.get('position', default_position)
            quantity = option_dict.get('quantity', default_quantity)
            option = dict_to_option_with_calcul(
            option_dict,
            position=position,
            quantity=quantity,
            price_min=price_min,
            price_max=price_max,
            num_points=num_points
            )

            
            # Ajouter uniquement les options valides (non-empty)
            if option.strike > 0 and option.premium > 0:
                options.append(option)
            else:
                errors += 1
                print(f"⚠️ Option {i+1} invalide (strike ou premium = 0)")
                
        except Exception as e:
            errors += 1
            print(f"⚠️ Erreur conversion option {i+1}: {e}")
    
    # Rapport de conversion
    print(f"✅ {len(options)} options converties avec succès")
    if errors > 0:
        print(f"⚠️ {errors} erreurs de conversion")
    
    total_profit = sum(opt.profit_surface or 0 for opt in options)
    total_loss = sum(opt.loss_surface or 0 for opt in options)
    print(f"📊 Surfaces totales: Profit={total_profit:,.2f}, Loss={total_loss:,.2f}")
    
    return options
       