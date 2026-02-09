"""
Implied Probability Distribution (Breeden-Litzenberger)
========================================================
Extrait la distribution de probabilité risque-neutre implicite
à partir des prix d'options observés sur le marché.

Méthode:
    q_T(K) = e^{rT} × ∂²C/∂K²

Où:
    - q_T(K) est la densité risque-neutre au strike K
    - C(K) est le prix du call en fonction du strike
    - r est le taux sans risque
    - T est le temps jusqu'à expiration

Références:
    Breeden, D.T. & Litzenberger, R.H. (1978)
    "Prices of State-Contingent Claims Implicit in Option Prices"
"""

from datetime import date
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d

from backtesting.config import SFRConfig
from backtesting.bloomberg.bdh_fetcher import BDHFetcher


class ImpliedDistribution:
    """
    Calcule la distribution de probabilité implicite du marché
    via Breeden-Litzenberger à partir des prix de calls/puts.

    Usage:
        dist = ImpliedDistribution(config, fetcher)
        density = dist.compute_at_date(target_date)
        all_densities = dist.compute_all_dates()
    """

    def __init__(self, config: SFRConfig, fetcher: BDHFetcher):
        self.config = config
        self.fetcher = fetcher

        # Grille de prix pour la densité
        self.price_grid: np.ndarray = np.linspace(
            config.strike_min - config.price_grid_margin,
            config.strike_max + config.price_grid_margin,
            config.price_grid_points,
        )

        # Cache des résultats : {date -> density_array}
        self._densities: Dict[date, np.ndarray] = {}
        self._call_splines: Dict[date, CubicSpline] = {}

    # -----------------------------------------------------------------
    # Méthode principale : Breeden-Litzenberger
    # -----------------------------------------------------------------

    def compute_at_date(
        self,
        target_date: date,
        smooth_sigma: float = 0.5,
        use_put_call_parity: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Calcule la densité implicite pour une date donnée.

        Étapes:
        1. Récupérer les prix de calls (et puts via parity si activé)
        2. Interpoler C(K) avec un spline cubique
        3. Calculer q_T(K) = e^{rT} × ∂²C/∂K²
        4. Normaliser la densité

        Args:
            target_date: Date pour laquelle calculer la densité
            smooth_sigma: Écart-type du lissage gaussien (0 = pas de lissage)
            use_put_call_parity: Utiliser la parité put-call pour compléter

        Returns:
            Densité q_T(x) sur self.price_grid, ou None si données insuffisantes
        """
        # Récupérer les prix
        strikes_c, call_prices = self.fetcher.get_call_prices_at_date(target_date)

        if len(strikes_c) < 4:
            return None

        # Optionnel: compléter avec la parité put-call
        if use_put_call_parity:
            strikes_c, call_prices = self._apply_put_call_parity(
                target_date, strikes_c, call_prices
            )

        # Filtrer les prix valides
        valid = call_prices > 0
        if np.sum(valid) < 4:
            return None

        K = strikes_c[valid]
        C = call_prices[valid]

        # Interpolation cubique des prix de calls C(K)
        try:
            cs = CubicSpline(K, C, bc_type="natural")
            self._call_splines[target_date] = cs
        except Exception as e:
            print(f"[ImpliedDist] Erreur spline à {target_date}: {e}")
            return None

        # Dérivée seconde : ∂²C/∂K²
        d2C_dK2 = cs(self.price_grid, 2)

        # Temps restant jusqu'à expiration
        days_to_expiry = (self.config.end_date - target_date).days
        T = max(days_to_expiry / 365.25, 1e-6)

        # Breeden-Litzenberger : q_T(K) = e^{rT} × ∂²C/∂K²
        discount = np.exp(self.config.risk_free_rate * T)
        q_T = discount * d2C_dK2

        # La densité doit être positive
        q_T = np.maximum(q_T, 0.0)

        # Lissage gaussien optionnel
        if smooth_sigma > 0:
            # Convertir sigma en nombre de points
            dx = float(np.mean(np.diff(self.price_grid)))
            sigma_pts = smooth_sigma / dx
            q_T = gaussian_filter1d(q_T, sigma=sigma_pts)
            q_T = np.maximum(q_T, 0.0)

        # Normaliser : ∫ q_T(x) dx = 1
        dx = float(np.mean(np.diff(self.price_grid)))
        total_mass = np.sum(q_T) * dx
        if total_mass > 1e-10:
            q_T = q_T / total_mass
        else:
            return None

        self._densities[target_date] = q_T
        return q_T

    def _apply_put_call_parity(
        self,
        target_date: date,
        strikes_c: np.ndarray,
        call_prices: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Complète les prix de calls manquants via la parité put-call:
            C(K) = P(K) + F - K × e^{-rT}

        Pour les options sur futures (SOFR), la parité se simplifie:
            C(K) - P(K) = F - K   (pas d'actualisation car futures)

        Args:
            target_date: Date cible
            strikes_c: Strikes des calls
            call_prices: Prix des calls

        Returns:
            (strikes, call_prices) potentiellement enrichis
        """
        strikes_p, put_prices = self.fetcher.get_put_prices_at_date(target_date)
        F = self.fetcher.get_underlying_at_date(target_date)

        if F is None or len(strikes_p) == 0:
            return strikes_c, call_prices

        # Créer un dictionnaire des calls existants
        call_dict = dict(zip(strikes_c, call_prices))

        # Pour chaque put sans call correspondant, calculer le call synthétique
        for k, p_price in zip(strikes_p, put_prices):
            if k not in call_dict and p_price > 0:
                # Parité sur futures: C = P + F - K
                synthetic_call = p_price + F - k
                if synthetic_call > 0:
                    call_dict[k] = synthetic_call

        # Reconstruire les arrays triés
        all_strikes = sorted(call_dict.keys())
        strikes_out = np.array(all_strikes)
        prices_out = np.array([call_dict[k] for k in all_strikes])

        return strikes_out, prices_out

    # -----------------------------------------------------------------
    # Calcul sur toutes les dates
    # -----------------------------------------------------------------

    def compute_all_dates(
        self,
        smooth_sigma: float = 0.5,
        min_strikes: int = 4,
    ) -> Dict[date, np.ndarray]:
        """
        Calcule la densité implicite pour chaque date de l'historique.

        Args:
            smooth_sigma: Lissage gaussien
            min_strikes: Nombre minimum de strikes requis

        Returns:
            {date: density_array}
        """
        all_dates = self.fetcher.get_all_dates()
        print(f"[ImpliedDist] Calcul de la densité pour {len(all_dates)} dates...")

        n_success = 0
        for d in all_dates:
            q_T = self.compute_at_date(d, smooth_sigma=smooth_sigma)
            if q_T is not None:
                n_success += 1

        print(f"[ImpliedDist] Densité calculée pour {n_success}/{len(all_dates)} dates")
        return self._densities

    # -----------------------------------------------------------------
    # Moments et statistiques
    # -----------------------------------------------------------------

    def get_moments(self, target_date: date) -> Optional[Dict[str, float]]:
        """
        Calcule les moments de la distribution implicite pour une date.

        Returns:
            Dict avec mean, std, skewness, kurtosis, ou None si pas de données
        """
        q_T = self._densities.get(target_date)
        if q_T is None:
            q_T = self.compute_at_date(target_date)
        if q_T is None:
            return None

        x = self.price_grid
        dx = float(np.mean(np.diff(x)))

        # Moyenne
        mean = float(np.sum(x * q_T) * dx)

        # Variance et écart-type
        var = float(np.sum((x - mean) ** 2 * q_T) * dx)
        std = float(np.sqrt(max(var, 0.0)))

        # Skewness (asymétrie)
        skew = 0.0
        if std > 1e-10:
            skew = float(np.sum(((x - mean) / std) ** 3 * q_T) * dx)

        # Kurtosis (excess)
        kurt = 0.0
        if std > 1e-10:
            kurt = float(np.sum(((x - mean) / std) ** 4 * q_T) * dx) - 3.0

        return {
            "mean": mean,
            "std": std,
            "skewness": skew,
            "kurtosis": kurt,
        }

    def get_quantiles(
        self,
        target_date: date,
        quantiles: List[float] = [0.05, 0.25, 0.50, 0.75, 0.95],
    ) -> Optional[Dict[float, float]]:
        """
        Calcule les quantiles de la distribution implicite.

        Args:
            target_date: Date cible
            quantiles: Liste de quantiles (0-1) à calculer

        Returns:
            {quantile: value}, ou None si pas de données
        """
        q_T = self._densities.get(target_date)
        if q_T is None:
            q_T = self.compute_at_date(target_date)
        if q_T is None:
            return None

        x = self.price_grid
        dx = float(np.mean(np.diff(x)))

        # CDF cumulative
        cdf = np.cumsum(q_T) * dx

        result = {}
        for q in quantiles:
            idx = np.searchsorted(cdf, q)
            if idx >= len(x):
                idx = len(x) - 1
            result[q] = float(x[idx])

        return result

    # -----------------------------------------------------------------
    # Accesseurs
    # -----------------------------------------------------------------

    def get_density(self, target_date: date) -> Optional[np.ndarray]:
        """Retourne la densité précalculée pour une date."""
        return self._densities.get(target_date)

    def get_available_dates(self) -> List[date]:
        """Retourne les dates pour lesquelles la densité a été calculée."""
        return sorted(self._densities.keys())

    def get_cdf(self, target_date: date) -> Optional[np.ndarray]:
        """Retourne la CDF (fonction de répartition) pour une date."""
        q_T = self._densities.get(target_date)
        if q_T is None:
            return None
        dx = float(np.mean(np.diff(self.price_grid)))
        return np.cumsum(q_T) * dx
