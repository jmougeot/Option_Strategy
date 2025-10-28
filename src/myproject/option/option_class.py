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
    delta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    rho: Optional[float] = None

    # ============ METRIQUES (stockage éventuel) ============
    loss_surface: float = 0
    profit_surface: float = 0
    pnl_array : Optional[np.ndarray]= None
    mixture : Optional[np.ndarray]= None
    pnl_ponderation: Optional[np.ndarray] = None 

    # ============ VOLATILITÉ ============
    implied_volatility: Optional[float] = None
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
    
    def _pnl_at_expiry_array(self, prices: np.ndarray) -> np.ndarray:
        """
        Calcule le P&L à l'expiration pour un array de prix du sous-jacent.
        
        Convention:
          - long  -> P&L = intrinsic - premium
          - short -> P&L = premium - intrinsic
        
        Args:
            prices: Array numpy des prix du sous-jacent
            
        Returns:
            Array numpy du P&L pour chaque prix
        """
        if self.option_type.lower() == "call":
            intrinsic = np.maximum(prices - self.strike, 0.0)
        else:  # put
            intrinsic = np.maximum(self.strike - prices, 0.0)

        sign = -1.0 if self.position == "long" else 1.0
        qty = float(self.quantity or 1)
        
        # P&L = sign * (premium - intrinsic) * quantity * contract_size
        pnl = sign * (self.premium - intrinsic) * qty * float(self.contract_size or 1)
        return pnl
    
    def _calculate_pnl_array(self, price_min: float, price_max: float, num_points: int = 500) -> np.ndarray:
        """
        Calcule le P&L array sur une grille de prix entre price_min et price_max.
        Stocke le résultat dans self.pnl_array.
        
        Args:
            price_min: Prix minimum de la grille
            price_max: Prix maximum de la grille
            num_points: Nombre de points dans la grille (défaut: 500)
            
        Returns:
            Array numpy du P&L pour chaque prix de la grille
            
        Example:
            >>> option = Option(option_type='call', strike=100, premium=5, position='long')
            >>> pnl = option.calculate_pnl_array(80, 120, num_points=200)
            >>> # pnl contient le P&L pour 200 points entre 80 et 120
        """
        if not np.isfinite(price_min) or not np.isfinite(price_max) or price_min >= price_max:
            raise ValueError("price_min doit être inférieur à price_max et tous deux finis")
        
        num_points = max(2, int(num_points))
        
        # Créer la grille de prix
        prices = np.linspace(price_min, price_max, num_points, dtype=float)
        
        # Calculer le P&L pour chaque prix
        pnl_array = self._pnl_at_expiry_array(prices)
        
        # Stocker dans l'attribut de l'instance
        self.x = prices
        self.pnl_array = pnl_array
        
        return pnl_array
    
    def _pnl_ponderation_array(self, x: np.ndarray):
        if self.mixture is None or self.pnl_array is None:
            return None

        # pas moyen (dx) sur la grille
        dx = float(np.diff(x).mean())
        self.x = x
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
            if hasattr(self, "x") and self.x is not None and len(self.x) > 1:
                dx = float(np.mean(np.diff(self.x)))
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
            if hasattr(self, "x") and self.x is not None and len(self.x) > 1:
                dx = float(np.mean(np.diff(self.x)))
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
