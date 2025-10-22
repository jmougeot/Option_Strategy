from dataclasses import dataclass
from datetime import datetime
from typing import  Literal, Optional, Tuple
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
    loss_surface: Optional[float] = None
    profit_surface: Optional[float] = None
    pnl_surface: Optional[float] = None
    pnl_array:Optional[np.ndarray]= None
    
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

    # ---------- Helpers internes ----------
    def _pnl_at_expiry_array(self, prices: np.ndarray) -> np.ndarray:
        """
        P&L à l'expiration pour un vecteur de prix du sous-jacent.
        Convention:
          long  -> P&L = intrinsic - premium
          short -> P&L = premium   - intrinsic
        """
        if self.option_type.lower() == "call":
            intrinsic = np.maximum(prices - self.strike, 0.0)
        else:  # put
            intrinsic = np.maximum(self.strike - prices, 0.0)

        sign = -1.0 if self.position == "long" else 1.0
        qty  = float(self.quantity or 1)
        # notionnel (par défaut on intègre en valeur notionnelle)
        pnl = sign * (self.premium - intrinsic) * qty * float(self.contract_size or 1)
        return pnl

    # ---------- Surfaces (aires) ----------
    def calcul_profit_surface(self, min_price: float, max_price: float, num_points: int = 200) -> float:
        """
        Aire de la partie positive de P&L (gain) entre min_price et max_price.
        Intégration trapézoïdale.
        """
        if not np.isfinite(min_price) or not np.isfinite(max_price) or min_price >= max_price:
            raise ValueError("min_price < max_price et tous deux finis sont requis.")
        num_points = max(2, int(num_points))

        prices = np.linspace(min_price, max_price, num_points, dtype=float)
        pnl = self._pnl_at_expiry_array(prices)
        gains = np.maximum(pnl, 0.0)
        area = float(np.trapz(gains, prices))  # intégrale
        return area

    def calcul_loss_surface(self, min_price: float, max_price: float, num_points: int = 200) -> float:
        """
        Aire de la partie négative de P&L (perte) entre min_price et max_price.
        On retourne une valeur positive (= intégrale de max(-P&L, 0)).
        """
        if not np.isfinite(min_price) or not np.isfinite(max_price) or min_price >= max_price:
            raise ValueError("min_price < max_price et tous deux finis sont requis.")
        num_points = max(2, int(num_points))

        prices = np.linspace(min_price, max_price, num_points, dtype=float)
        pnl = self._pnl_at_expiry_array(prices)
        losses = np.maximum(-pnl, 0.0)
        area = float(np.trapz(losses, prices))
        return area

# ... ta dataclass Option inchangée au-dessus ...

    def weighted_pnl_with_gaussian(self,
                                   prices: np.ndarray,
                                   pnl_array: np.ndarray,
                                   center_price: float,
                                   std_dev: float) -> Tuple[np.ndarray, float]:
        """
        Produit élément-par-élément entre une gaussienne (normalisée) et un P&L déjà calculé
        sur la grille 'prices', puis intégrale trapézoïdale du résultat.

        Args:
            prices: np.ndarray des prix (shape [N])
            pnl_array: np.ndarray du P&L sur la même grille (shape [N])
            center_price: moyenne (mu) de la gaussienne
            std_dev: écart-type (sigma) de la gaussienne (> 0)

        Returns:
            (weighted_array, weighted_area)
              - weighted_array: pnl_array * gaussian (shape [N])
              - weighted_area : float, intégrale de weighted_array sur 'prices'
        """
        if prices.shape != pnl_array.shape:
            raise ValueError("prices et pnl_array doivent avoir la même shape.")
        if std_dev <= 0:
            raise ValueError("std_dev doit être strictement positif.")
        if prices.ndim != 1:
            raise ValueError("prices doit être un vecteur 1D.")

        # Gaussienne centrée sur center_price
        gauss = (1.0 / (std_dev * np.sqrt(2 * np.pi))) * np.exp(
            -0.5 * ((prices - center_price) / std_dev) ** 2
        )
        # Normalisation: aire = 1 sur 'prices'
        norm = np.trapz(gauss, prices)
        if norm == 0.0:
            # Sécurité numérique si l'intervalle est trop étroit vs sigma
            gauss = np.zeros_like(prices, dtype=float)
        else:
            gauss /= norm

        weighted_array = pnl_array * gauss
        weighted_area = float(np.trapz(weighted_array, prices))
        return weighted_array, weighted_area

    def weighted_pnl_with_gaussian_on_range(self,
                                            min_price: float,
                                            max_price: float,
                                            center_price: float,
                                            std_dev: float,
                                            num_points: int = 500,
                                            mode: Literal["pnl", "profit", "loss"] = "pnl"
                                            ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Variante pratique: construit la grille de prix, calcule le P&L de CETTE option
        (ou seulement sa partie profit/perte selon 'mode'), puis applique la gaussienne.

        Args:
            min_price, max_price: bornes de la grille (min < max)
            center_price: moyenne de la gaussienne
            std_dev: écart-type (> 0)
            num_points: taille de la grille
            mode: "pnl" (brut), "profit" (=max(pnl,0)), "loss" (=max(-pnl,0))

        Returns:
            (prices, weighted_array, weighted_area)
        """
        if not np.isfinite(min_price) or not np.isfinite(max_price) or min_price >= max_price:
            raise ValueError("min_price < max_price et tous deux finis requis.")
        num_points = max(2, int(num_points))

        prices = np.linspace(min_price, max_price, num_points, dtype=float)
        pnl = self._pnl_at_expiry_array(prices)

        if mode == "profit":
            pnl_used = np.maximum(pnl, 0.0)
        elif mode == "loss":
            pnl_used = np.maximum(-pnl, 0.0)
        else:
            pnl_used = pnl  # "pnl"

        weighted_array, weighted_area = self.weighted_pnl_with_gaussian(
            prices=prices,
            pnl_array=pnl_used,
            center_price=center_price,
            std_dev=std_dev,
        )
        return prices, weighted_array, weighted_area