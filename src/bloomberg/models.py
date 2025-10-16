"""
Bloomberg Data Models
====================
Dataclasses pour représenter les données d'options et de taux (EURIBOR).

Auteur: BGC Trading Desk
Date: 2025-10-16
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class OptionData:
    """
    Données complètes pour une option (actions, indices, taux).
    
    Attributs principaux:
        ticker: Ticker Bloomberg complet (ex: "SPY 12/20/24 C450 Index")
        underlying: Symbole du sous-jacent (ex: "SPY", "AAPL", "ER")
        option_type: "CALL" ou "PUT"
        strike: Prix d'exercice
        expiry: Date d'expiration
    
    Prix de marché:
        bid, ask, last, mid: Prix bid/ask/dernier/mid
        volume: Volume du jour
        open_interest: Intérêt ouvert (nombre de contrats ouverts)
    
    Greeks (sensibilités):
        delta: Variation du prix de l'option pour 1$ de variation du sous-jacent
        gamma: Variation du delta pour 1$ de variation du sous-jacent
        vega: Variation du prix pour 1% de variation de la volatilité
        theta: Déclin temporel (perte de valeur par jour)
        rho: Sensibilité aux taux d'intérêt
    
    Volatilité:
        implied_volatility: Volatilité implicite en %
    """
    # Identification
    ticker: str
    underlying: str
    option_type: str  # 'CALL' ou 'PUT'
    strike: float
    expiry: date
    
    # Prix de marché
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mid: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    
    # Greeks (sensibilités aux facteurs de marché)
    delta: Optional[float] = None  # Sensibilité au prix du sous-jacent
    gamma: Optional[float] = None  # Sensibilité du delta
    vega: Optional[float] = None   # Sensibilité à la volatilité
    theta: Optional[float] = None  # Déclin temporel
    rho: Optional[float] = None    # Sensibilité aux taux
    
    # Volatilité implicite
    implied_volatility: Optional[float] = None  # En %
    
    def __repr__(self) -> str:
        """Affichage condensé pour debug."""
        return (
            f"OptionData({self.ticker} | "
            f"Strike={self.strike} | Last={self.last} | "
            f"Delta={self.delta} | IV={self.implied_volatility}%)"
        )
    
    @property
    def spread(self) -> Optional[float]:
        """Calcule le spread bid-ask si disponible."""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None
    
    @property
    def is_liquid(self) -> bool:
        """
        Vérifie si l'option est liquide (critères simples).
        
        Critères:
        - Volume > 0 ou Open Interest > 10
        - Spread < 10% du mid (si disponible)
        """
        has_volume = (self.volume or 0) > 0 or (self.open_interest or 0) > 10
        
        if self.mid and self.spread:
            tight_spread = self.spread < (self.mid * 0.10)
            return has_volume and tight_spread
        
        return has_volume


@dataclass
class EuriborOptionData(OptionData):
    """
    Extension pour les options EURIBOR (taux d'intérêt).
    
    EURIBOR = Euro Interbank Offered Rate
    Options sur futures de taux EURIBOR 3 mois sur Eurex.
    
    Particularités:
    - Ticker format: "ER{Expiry} C/P {Strike} Comdty"
    - Strike en points de taux (ex: 97.50 = taux implicite 2.50%)
    - Expiry trimestriel (Mars/Juin/Sept/Déc)
    
    Exemple:
        ER H5 C97.50 Comdty = Option CALL sur future EURIBOR Mars 2025, strike 97.50
    """
    contract_size: float = 2500.0  # Taille du contrat EURIBOR (2500€ par point de base)
    
    @property
    def implied_rate(self) -> float:
        """
        Convertit le strike en taux d'intérêt implicite.
        
        Formule: Taux = 100 - Strike
        Exemple: Strike 97.50 → Taux = 2.50%
        """
        return 100.0 - self.strike
    
    @property
    def tick_value(self) -> float:
        """
        Valeur monétaire d'un tick (0.01 point = 1 point de base).
        
        Pour EURIBOR 3M: 1 tick = 2500€ × 0.01 = 25€
        """
        return self.contract_size * 0.01
    
    def payoff_at_rate(self, final_rate: float) -> float:
        """
        Calcule le payoff de l'option à expiration pour un taux final donné.
        
        Args:
            final_rate: Taux EURIBOR final (ex: 2.75 pour 2.75%)
        
        Returns:
            Payoff en euros (positif = gain, négatif = perte)
        
        Exemple:
            CALL strike 97.50 (taux implicite 2.50%), taux final 2.75%
            → future_price = 97.25
            → intrinsic = max(0, 97.25 - 97.50) = 0
            → CALL out-of-the-money, perte de la prime payée
        """
        # Convertir le taux final en prix du future
        future_price = 100.0 - final_rate
        
        # Valeur intrinsèque
        if self.option_type == 'CALL':
            intrinsic = max(0, future_price - self.strike)
        else:  # PUT
            intrinsic = max(0, self.strike - future_price)
        
        # Valeur en euros (points × contract_size)
        return intrinsic * self.contract_size


# Alias pour compatibilité
RateOptionData = EuriborOptionData
