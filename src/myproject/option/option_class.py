from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Tuple
import numpy as np

@dataclass
class Option:
    # ============ CHAMPS OBLIGATOIRES ============
    option_type: str  # 'call' ou 'put'
    strike: float
    premium: float

    # ============ CHAMPS OBLIGATOIRES ============
    expiration_day : Optional[str]= None
    expiration_week : Optional[str]= None 
    expiration_month : Literal['F','G','H','K','M','N','Q','U','V','X','Z'] = 'F'
    expiration_year : int = 6

    # ============ STRUCTURE DE POSITION ============
    quantity: Optional[int] = 1
    position: Literal['long', 'short'] = 'short'
    
    # ============ IDENTIFICATION ============
    ticker: Optional[str] = None
    underlying_symbol: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    
    # ============ PRIX ET COTATIONS ============
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mid: Optional[float] = None
    settlement_price: Optional[float] = None
    
    # ============ GREEKS ============
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    rho: float = 0.0

    # ============ METRIQUES (stockage éventuel) ============
    prices: Optional[np.ndarray] = None
    loss_surface: float = 0
    profit_surface: float = 0
    pnl_array: Optional[np.ndarray] = None
    mixture: Optional[np.ndarray] = None
    pnl_ponderation: Optional[np.ndarray] = None
    
    # Métriques calculées avec la mixture
    average_pnl: float = 0.0
    sigma_pnl: float = 0.0 

    # ============ VOLATILITÉ ============
    implied_volatility: float = 0.0
    historical_volatility: Optional[float] = None
    
    # ============ LIQUIDITÉ ============
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    
    # ============ SOUS-JACENT ============
    underlying_price: Optional[float] = None
    underlying_price_change: Optional[float] = None
    
    # ============ CONTRAT ============
    contract_size: int = 100
    settlement_type: Optional[str] = None
    exercise_style: Optional[str] = None
    
    # ============ BLOOMBERG ============
    bloomberg_ticker: Optional[str] = None
    security_des: Optional[str] = None
    timestamp: Optional[datetime] = None



    @classmethod
    def empyOption(cls) -> "Option":
        return cls(option_type="call", strike=0.0, premium=0.0)
        
    def _pnl_at_expiry_array(self) -> np.ndarray:
        """
        Calcule le P&L à l'expiration pour un array de prix du sous-jacent.
        
        Convention:
          - long  -> P&L = intrinsic - premium
          - short -> P&L = premium - intrinsic
        
        Returns:
            Array numpy du P&L pour chaque prix
        """
        if self.prices is None:
            raise ValueError("prices doit être défini avant d'appeler _pnl_at_expiry_array")
        
        if self.option_type.lower() == "call":
            pnl = np.maximum(self.prices - self.strike, 0.0) - self.premium
        else:  # put
            pnl = np.maximum(self.strike - self.prices, 0.0) - self.premium
        return pnl
    
    def _calculate_pnl_array(self) -> np.ndarray:
        """
        Calcule le P&L array sur une grille de prix entre price_min et price_max.
        Stocke le résultat dans self.pnl_array.
        
        Returns:
            Array numpy du P&L pour chaque prix de la grille
            
        Example:
            >>> option = Option(option_type='call', strike=100, premium=5, position='long')
            >>> option.prices = np.linspace(80, 120, 200)
            >>> pnl = option._calculate_pnl_array()
            >>> # pnl contient le P&L pour 200 points entre 80 et 120
        """
        if self.prices is None:
            raise ValueError("prices doit être défini avant d'appeler _calculate_pnl_array")

        # Calculer le P&L pour chaque prix
        pnl_array = self._pnl_at_expiry_array()
        
        # Stocker dans l'attribut de l'instance
        self.pnl_array = pnl_array
        
        return pnl_array
    
    def _pnl_ponderation_array(self):
        """
        Calcule la pondération du P&L par la mixture.
        Retourne: p(x) × PnL(x) × dx
        """
        if self.mixture is None or self.pnl_array is None or self.prices is None:
            return None

        # pas moyen (dx) sur la grille
        dx = float(np.diff(self.prices).mean())
        self._dx = dx

        # intégrande discrétisé : p(x) * PnL(x) * dx
        self.pnl_ponderation = self.mixture * self.pnl_array * dx
        return self.pnl_ponderation

    def _average_pnl(self):
        """
        Espérance du PnL: E[PnL] = ∫ p(x) * pnl(x) dx ≈ sum(mixture * pnl * dx).
        Normalise si la densité n'intègre pas exactement à 1.
        """
        if self.mixture is None or self.pnl_array is None:
            return None

        dx = getattr(self, "_dx", None)
        if dx is None:
            # Valeur de repli si _pnl_ponderation_array n'a pas été appelée
            if self.prices is not None and len(self.prices) > 1:
                dx = float(np.mean(np.diff(self.prices)))
            else:
                return None

        mass = float(np.sum(self.mixture) * dx)  # ∫ p(x) dx
        if mass <= 0:
            return None

        mu = float(np.sum(self.mixture * self.pnl_array * dx) / mass)
        self.average_pnl = mu
        return mu

    def _sigma_pnl(self):
        """
        Ecart-type du PnL sous la mixture:
        σ = sqrt( E[(PnL - μ)^2] )  avec E[·] pris sous la densité p(x).
        Discrétisation par somme pondérée (méthode rectangle) et normalisation.
        """
        if self.mixture is None or self.pnl_array is None:
            return None

        # Assure qu'on a l'espérance et le pas dx
        mu = getattr(self, "average_pnl", None)
        if mu is None:
            mu = self._average_pnl()
            if mu is None:
                return None

        dx = getattr(self, "_dx", None)
        if dx is None:
            if self.prices is not None and len(self.prices) > 1:
                dx = float(np.mean(np.diff(self.prices)))
            else:
                return None

        # Normalisation de la densité (robuste aux petites erreurs numériques)
        mass = float(np.sum(self.mixture) * dx)  # ≈ 1 si p est bien normalisée
        if mass <= 0:
            return None

        var = float(np.sum(self.mixture * (self.pnl_array - mu) ** 2 * dx) / mass)
        sigma = float(np.sqrt(max(var, 0.0)))
        self.sigma_pnl = sigma
        return sigma

    def _calcul_surface(self) -> Tuple[float, float]:
        """
        Aire de la partie négative de P&L (perte) entre min_price et max_price.
        On retourne une valeur positive (= intégrale de max(-P&L, 0)).
        """
        loss = 0.0
        win = 0.0
        if self.pnl_ponderation is None:
            return 0.0, 0.0
        
        for xi in self.pnl_ponderation:
            if xi < 0:
                loss += xi
            else:
                win += xi
        self.loss_surface = -loss
        self.profit_surface = win
        # loss is negative (sum of negative contributions), return positive loss
        return -loss, win
    
    def _calcul_all_surface(self):
        """
        Calcule toutes les surfaces et métriques associées à la mixture.
        
        Ordre d'exécution:
        1. Calcul du P&L array
        2. Calcul de la pondération (mixture × P&L × dx)
        3. Calcul de l'espérance du P&L
        4. Calcul de l'écart-type du P&L
        5. Calcul des surfaces de profit et perte
        
        Returns:
            Tuple[float, float]: (loss_surface, profit_surface)
        """
        # 1. Calculer le P&L array (utilise self.prices)
        self._calculate_pnl_array()
        
        # 2. Calculer la pondération (mixture × P&L × dx)
        self._pnl_ponderation_array()
        
        # 3. Calculer l'espérance du P&L
        self._average_pnl()
        
        # 4. Calculer l'écart-type du P&L
        self._sigma_pnl()
        
        # 5. Calculer les surfaces de profit et perte
        return self._calcul_surface()
    
    # ============================================================================
    # POSITION HELPERS - Méthodes utilitaires pour faciliter les checks de position
    # ============================================================================
    
    def is_long_call(self) -> bool:
        """Retourne True si c'est un long call."""
        return self.position == 'long' and self.option_type.lower() == 'call'
    
    def is_short_call(self) -> bool:
        """Retourne True si c'est un short call."""
        return self.position == 'short' and self.option_type.lower() == 'call'
    
    def is_long_put(self) -> bool:
        """Retourne True si c'est un long put."""
        return self.position == 'long' and self.option_type.lower() == 'put'
    
    def is_short_put(self) -> bool:
        """Retourne True si c'est un short put."""
        return self.position == 'short' and self.option_type.lower() == 'put'
    
    def is_long(self) -> bool:
        """Retourne True si la position est long (call ou put)."""
        return self.position == 'long'
    
    def is_short(self) -> bool:
        """Retourne True si la position est short (call ou put)."""
        return self.position == 'short'
    
    def is_call(self) -> bool:
        """Retourne True si c'est un call (long ou short)."""
        return self.option_type.lower() == 'call'
    
    def is_put(self) -> bool:
        """Retourne True si c'est un put (long ou short)."""
        return self.option_type.lower() == 'put'
    
    def position_name(self) -> str:
        """
        Retourne une chaîne décrivant la position.
        
        Returns:
            str: Format "Long Call", "Short Put", etc.
        """
        pos = "Long" if self.position == 'long' else "Short"
        typ = "Call" if self.option_type.lower() == 'call' else "Put"
        return f"{pos} {typ}"
    
    def position_sign(self) -> int:
        """
        Retourne le signe de la position pour les calculs.
        
        Returns:
            int: +1 pour long, -1 pour short
        """
        return 1 if self.position == 'long' else -1

