"""
Option Builder for Backtesting
================================
Construit des objets ``Option`` (cf. ``myproject.option.option_class``)
à partir des données historiques récupérées via ``BDHFetcher``.

Pour chaque date d'entrée, le builder :
1. Récupère les prix calls / puts / sous-jacent depuis le BDH
2. Retrouve la vol implicite Bachelier et les Greeks
3. Injecte la mixture (densité implicite ou log-normale fallback)
4. Calcule les surfaces de P&L (``_calcul_all_surface``)
5. Calcule les prix intra-vie (``calculate_all_intra_life``)

Les objets ``Option`` produits sont *directement compatibles* avec
``OptionStrategyGeneratorV2`` et le scoring C++.
"""

import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Literal, Optional, cast

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm as norm_dist

# --- Assurer que myproject est importable ---
_src_dir = str(Path(__file__).resolve().parent.parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from src.backtesting.config import SFRConfig
from src.backtesting.bloomberg.bdh_fetcher import BDHFetcher
from src.backtesting.distrib_proba.implied_distribution import ImpliedDistribution

from myproject.option.option_class import Option, bachelier_price


# ============================================================================
# UTILITAIRES BACHELIER
# ============================================================================

def bachelier_implied_vol(
    market_price: float,
    F: float,
    K: float,
    T: float,
    is_call: bool,
    sigma_low: float = 1e-6,
    sigma_high: float = 10.0,
) -> Optional[float]:
    """
    Retrouve la volatilité implicite Bachelier par la méthode de Brent.

    Args:
        market_price: Prix observé de l'option
        F: Prix du sous-jacent (forward)
        K: Strike
        T: Temps jusqu'à expiration (années)
        is_call: True si call

    Returns:
        sigma_normal (vol en unités de prix) ou None si impossible
    """
    if T <= 0 or market_price <= 0:
        return None

    intrinsic = max(F - K, 0.0) if is_call else max(K - F, 0.0)
    if market_price <= intrinsic + 1e-10:
        return 1e-6

    try:
        def objective(sigma: float) -> float:
            return bachelier_price(F, K, sigma, T, is_call) - market_price

        lo = objective(sigma_low)
        hi = objective(sigma_high)
        if lo * hi > 0:
            # Approximation ATM : price ≈ sigma * sqrt(T) / sqrt(2π)
            return market_price * np.sqrt(2 * np.pi) / np.sqrt(T)

        result = brentq(objective, sigma_low, sigma_high, xtol=1e-8, maxiter=100)
        return float(result)  # type: ignore[arg-type]
    except Exception:
        return market_price * np.sqrt(2 * np.pi) / np.sqrt(T)


def bachelier_greeks(
    F: float, K: float, sigma: float, T: float, is_call: bool,
) -> Dict[str, float]:
    """
    Greeks dans le modèle Bachelier (normal model).

    Returns:
        {"delta", "gamma", "vega", "theta"}
    """
    if T <= 0 or sigma <= 0:
        delta = (1.0 if F > K else 0.0) if is_call else (-1.0 if F < K else 0.0)
        return {"delta": delta, "gamma": 0.0, "vega": 0.0, "theta": 0.0}

    sigma_sqrt_T = sigma * np.sqrt(T)
    d = (F - K) / sigma_sqrt_T

    delta = float(norm_dist.cdf(d)) if is_call else float(norm_dist.cdf(d) - 1.0)
    gamma = float(norm_dist.pdf(d) / sigma_sqrt_T)
    vega = float(np.sqrt(T) * norm_dist.pdf(d) / 100.0)
    theta = float(-(sigma * norm_dist.pdf(d)) / (2 * np.sqrt(T)) / 365)

    return {
        "delta": round(delta, 6),
        "gamma": round(gamma, 8),
        "vega": round(vega, 6),
        "theta": round(theta, 6),
    }


# ============================================================================
# OPTION BUILDER
# ============================================================================

class OptionBuilder:
    """
    Construit des objets ``Option`` prêts pour le scoring C++
    à partir des données historiques BDH pour une date donnée.

    Usage::

        builder = OptionBuilder(config, fetcher, implied_dist)
        options = builder.build_at_date(date(2024, 10, 15))
    """

    def __init__(
        self,
        config: SFRConfig,
        fetcher: BDHFetcher,
        implied_dist: Optional[ImpliedDistribution] = None,
    ):
        self.config = config
        self.fetcher = fetcher
        self.implied_dist = implied_dist

    # -----------------------------------------------------------------
    # Grille de prix et mixture
    # -----------------------------------------------------------------

    def _build_price_grid(self) -> np.ndarray:
        """Construit la grille de prix pour les calculs de P&L."""
        margin = self.config.price_grid_margin
        return np.linspace(
            self.config.strike_min - margin,
            self.config.strike_max + margin,
            self.config.price_grid_points,
        )

    def _get_mixture(
        self, target_date: date, price_grid: np.ndarray,
    ) -> Optional[np.ndarray]:
        """
        Récupère la densité de probabilité pour la date donnée.

        Priorité :
        1. Densité implicite (Breeden-Litzenberger) si disponible
        2. Fallback : log-normale centrée sur le sous-jacent
        """
        # 1. Densité implicite
        if self.implied_dist is not None:
            density = self.implied_dist.get_density(target_date)
            if density is not None:
                return density

        # 2. Fallback log-normale
        F = self.fetcher.get_underlying_at_date(target_date)
        if F is None:
            return None

        sigma = 0.01
        x_safe = np.maximum(price_grid, 1e-10)
        q = (1.0 / (x_safe * sigma * np.sqrt(2 * np.pi))) * np.exp(
            -0.5 * (np.log(x_safe / F) / sigma) ** 2
        )
        dx = float(np.mean(np.diff(price_grid)))
        q = q / (np.sum(q) * dx + 1e-10)
        return q

    # -----------------------------------------------------------------
    # Temps
    # -----------------------------------------------------------------

    def _time_to_expiry(self, from_date: date) -> float:
        """Temps restant jusqu'à l'expiration (en années)."""
        delta = self.config.end_date - from_date
        return max(delta.days / 365.25, 1e-6)

    # -----------------------------------------------------------------
    # Construction des options
    # -----------------------------------------------------------------

    def build_at_date(self, target_date: date) -> List[Option]:
        """
        Construit la liste d'objets ``Option`` pour une date donnée.

        Pour chaque strike avec un prix disponible, crée un ``Option``
        avec Greeks, vol implicite, surface de P&L et prix intra-vie.

        Args:
            target_date: Date à laquelle on construit les positions

        Returns:
            Liste d'``Option`` prêts pour ``OptionStrategyGeneratorV2``
        """
        F = self.fetcher.get_underlying_at_date(target_date)
        if F is None:
            return []

        T = self._time_to_expiry(target_date)
        price_grid = self._build_price_grid()
        mixture = self._get_mixture(target_date, price_grid)
        if mixture is None:
            return []

        dx = float(np.mean(np.diff(price_grid)))
        average_mix = float(np.sum(price_grid * mixture * dx))

        # Récupérer les prix calls et puts
        call_strikes, call_prices = self.fetcher.get_call_prices_at_date(target_date)
        put_strikes, put_prices = self.fetcher.get_put_prices_at_date(target_date)

        options: List[Option] = []

        # --- Calls ---
        for strike, premium in zip(call_strikes, call_prices):
            opt = self._create_option(
                strike=strike, premium=premium, option_type="call",
                F=F, T=T, price_grid=price_grid, mixture=mixture,
                average_mix=average_mix,
            )
            if opt is not None:
                options.append(opt)

        # --- Puts ---
        for strike, premium in zip(put_strikes, put_prices):
            opt = self._create_option(
                strike=strike, premium=premium, option_type="put",
                F=F, T=T, price_grid=price_grid, mixture=mixture,
                average_mix=average_mix,
            )
            if opt is not None:
                options.append(opt)

        # Intra-life pour toutes les options
        if options:
            for opt in options:
                opt.calculate_all_intra_life(
                    all_options=options, time_to_expiry=T,
                )

        return options

    def _create_option(
        self,
        strike: float,
        premium: float,
        option_type: str,
        F: float,
        T: float,
        price_grid: np.ndarray,
        mixture: np.ndarray,
        average_mix: float,
    ) -> Optional[Option]:
        """
        Crée un objet ``Option`` complet à partir du prix historique.

        Calcule la vol implicite Bachelier, les Greeks,
        et toute la surface de P&L sous la mixture.
        """
        is_call = option_type == "call"

        # Vol implicite Bachelier
        iv = bachelier_implied_vol(premium, F, strike, T, is_call)
        if iv is None:
            iv = 0.01
        # IV en % normalisé pour l'objet Option
        iv_pct = iv / F * 100 if F > 0 else 0.0

        # Greeks Bachelier
        greeks = bachelier_greeks(F, strike, iv, T, is_call)

        option = Option(
            option_type=option_type,
            strike=strike,
            premium=premium,
            expiration_month=cast(Literal["F","G","H","K","M","N","Q","U","V","X","Z"], self.config.expiry_month),
            expiration_year=self.config.expiry_year,
            position="long",
            underlying_symbol=self.config.underlying,
            underlying_price=F,
            implied_volatility=iv_pct,
            delta=greeks["delta"],
            gamma=greeks["gamma"],
            vega=greeks["vega"],
            theta=greeks["theta"],
        )

        # Surfaces de P&L
        option.prices = price_grid
        option.mixture = mixture
        option.average_mix = average_mix
        option._calcul_all_surface()

        return option
