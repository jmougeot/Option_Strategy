from dataclasses import dataclass, field, make_dataclass
from datetime import datetime
from typing import Dict, List, Literal, Optional, Type, Callable


"""
Ce module définit deux niveaux de responsabilités complémentaires:

- Option: Représente un leg individuel (call/put) avec son strike, sa prime, sa quantité, etc.
- OptionStrategy: Base commune des stratégies. Elle gère la liste des options (legs),
    le calcul des primes nettes, le P&L à l'expiration et expose des hooks génériques
    comme max_loss() et breakeven_points() que les stratégies concrètes peuvent surcharger.
- StrategyFactory: Fabrique des classes de stratégies à partir de définitions déclaratives
    (STRATEGY_DEFINITIONS). Elle compose dynamiquement des sous-classes d'OptionStrategy en
    ajoutant les champs spécifiques, en implémentant max_loss() et breakeven_points() lorsque
    des formules sont fournies, et en préparant un BUILD_CONFIG pour la construction générique.
"""
@dataclass
class Option:
    """Brique de base: un leg d'option (call ou put).
    """
    
    # ============ CHAMPS OBLIGATOIRES ============
    option_type: str  # 'call' ou 'put'
    strike: float  # Prix d'exercice
    premium: float  # Prime de l'option

    # ============ CHAMPS OBLIGATOIRES ============
    expiration_day : Optional[str]= None
    expiration_week : Optional[str]= None 
    expiration_month : Literal['F' , 'G', 'H', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z' ] = 'F'
    expiration_year : int = 6

    
    # ============ STRUCTURE DE POSITION ============
    quantity: Optional[int] = 1  # Nombre de contrats
    position: Literal['long', 'short'] = 'short'  # Type de position
    
    # ============ IDENTIFICATION ============
    ticker: Optional[str] = None  # Symbole Bloomberg
    underlying_symbol: Optional[str] = None  # Symbole du sous-jacent
    exchange: Optional[str] = None  # Bourse
    currency: Optional[str] = None  # Devise
    
    # ============ PRIX ET COTATIONS ============
    bid: Optional[float] = None  # Prix acheteur
    ask: Optional[float] = None  # Prix vendeur
    last: Optional[float] = None  # Dernier prix
    mid: Optional[float] = None  # Prix moyen
    settlement_price: Optional[float] = None  # Prix de règlement
    
    # ============ GREEKS (SENSIBILITÉS) ============
    delta: Optional[float] = None  # Sensibilité prix sous-jacent (-1 à 1)
    gamma: Optional[float] = None  # Sensibilité du delta
    vega: Optional[float] = None  # Sensibilité volatilité
    theta: Optional[float] = None  # Décroissance temporelle (négatif)
    rho: Optional[float] = None  # Sensibilité taux d'intérêt
    
    # ============ VOLATILITÉ ============
    implied_volatility: Optional[float] = None  # IV en %
    historical_volatility: Optional[float] = None  # HV en %
    
    # ============ LIQUIDITÉ ET MARCHÉ ============
    open_interest: Optional[int] = None  # Positions ouvertes
    volume: Optional[int] = None  # Volume du jour
    bid_size: Optional[int] = None  # Taille côté achat
    ask_size: Optional[int] = None  # Taille côté vente
    
    # ============ SOUS-JACENT ============
    underlying_price: Optional[float] = None  # Prix actuel du sous-jacent
    underlying_price_change: Optional[float] = None  # Variation du sous-jacent
    
    
    # ============ CARACTÉRISTIQUES CONTRACTUELLES ============
    contract_size: int = 100  # Taille du contrat (actions/unités)
    settlement_type: Optional[str] = None  # 'physical' ou 'cash'
    exercise_style: Optional[str] = None  # 'american' ou 'european'
    
    # ============ DONNÉES BLOOMBERG SPÉCIFIQUES ============
    bloomberg_ticker: Optional[str] = None  # Ticker Bloomberg complet
    security_des: Optional[str] = None  # Description du titre
    timestamp: Optional[datetime] = None  # Timestamp des données

    @classmethod
    def empyOption(cls) -> "Option":
        """
        Crée une Option 'vide' avec des valeurs neutres pour les champs obligatoires.
        - option_type: 'call' (par défaut)
        - strike: 0.0
        - premium: 0.0
        Le reste utilise les valeurs par défaut de la dataclass.
        """
        return cls(
            option_type="call",
            strike=0.0,
            premium=0.0,
        )
    
