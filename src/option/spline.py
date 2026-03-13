"""
Arbitrage-Free Spline — smile interpolation non-paramétrique.

Principe :
    1. Cubic spline sur σ_N(K) aux knots observés
    2. Régularisation (pénalité sur la courbure ∫ σ''² dK)
    3. Contrainte butterfly : la densité risque-neutre q(K) = ∂²C/∂K² ≥ 0
       est imposée via une pénalité forte
    4. Extrapolation flat en dehors du range observé

Avantage vs SABR / SVI :
    Capture les déformations locales du smile que les modèles paramétriques
    ne peuvent pas reproduire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize
from scipy.stats import norm


# ============================================================================
# Résultat
# ============================================================================

@dataclass
class SplineResult:
    """Résultats de la calibration spline."""
    strikes: np.ndarray = field(default_factory=lambda: np.array([]))
    sigmas_mkt: np.ndarray = field(default_factory=lambda: np.array([]))
    sigmas_model: np.ndarray = field(default_factory=lambda: np.array([]))
    residuals: np.ndarray = field(default_factory=lambda: np.array([]))

    rmse: float = 0.0
    rmse_bps: float = 0.0
    max_error_bps: float = 0.0

    F: float = 0.0
    T: float = 0.0
    n_points: int = 0
    arb_free: bool = False
    n_arb_violations: int = 0
    converged: bool = False

    def __repr__(self) -> str:
        arb = "arb-free" if self.arb_free else f"{self.n_arb_violations} butterfly viol."
        return (
            f"SplineResult(RMSE={self.rmse_bps:.2f}bp, "
            f"N={self.n_points}, {arb}, converged={self.converged})"
        )


# ============================================================================
# Classe principale
# ============================================================================

class SplineCalibration:
    """
    Smile interpolator via arbitrage-free cubic spline.

    Optimise les valeurs de σ_N aux knots pour minimiser :
        L = Σ wᵢ (σᵢ − σᵢ_mkt)²
          + λ_smooth · ∫ σ''(K)² dK
          + λ_arb   · Σ max(−q(Kⱼ), 0)²
    """

    def __init__(self, F: float, T: float) -> None:
        self.F = F
        self.T = T
        self.result: Optional[SplineResult] = None
        self._cs: Optional[CubicSpline] = None
        self._k_min: float = 0.0
        self._k_max: float = 0.0
        self._sigma_lo: float = 0.0
        self._sigma_hi: float = 0.0

    # ------------------------------------------------------------------
    # Butterfly density check
    # ------------------------------------------------------------------

    @staticmethod
    def _bachelier_call(F: float, K: float, sigma: float, T: float) -> float:
        """Prix call Bachelier."""
        if sigma <= 0 or T <= 0:
            return max(F - K, 0.0)
        s = sigma * np.sqrt(T)
        d = (F - K) / s
        return (F - K) * norm.cdf(d) + s * norm.pdf(d)

    @staticmethod
    def _butterfly_penalty(
        K_grid: np.ndarray,
        sigma_grid: np.ndarray,
        F: float,
        T: float,
    ) -> float:
        """
        Pénalité butterfly: on calcule C(K) sur la grille,
        puis vérifie ∂²C/∂K² ≥ 0 par différences finies.
        """
        n = len(K_grid)
        if n < 3:
            return 0.0

        C = np.array([
            SplineCalibration._bachelier_call(F, K, s, T)
            for K, s in zip(K_grid, sigma_grid)
        ])

        # ∂²C/∂K² par différences finies centrées
        dK = np.diff(K_grid)
        d2C = np.zeros(n - 2)
        for i in range(n - 2):
            h1, h2 = dK[i], dK[i + 1]
            d2C[i] = 2.0 * (C[i + 2] / (h2 * (h1 + h2))
                            - C[i + 1] / (h1 * h2)
                            + C[i] / (h1 * (h1 + h2)))

        violations = np.minimum(d2C, 0.0)
        return float(np.sum(violations ** 2))

    @staticmethod
    def _check_butterfly(
        K_grid: np.ndarray,
        sigma_grid: np.ndarray,
        F: float,
        T: float,
    ) -> tuple[bool, int]:
        """Vérifie butterfly arb-free; retourne (arb_free, n_violations)."""
        n = len(K_grid)
        if n < 3:
            return True, 0

        C = np.array([
            SplineCalibration._bachelier_call(F, K, s, T)
            for K, s in zip(K_grid, sigma_grid)
        ])

        dK = np.diff(K_grid)
        n_viol = 0
        for i in range(n - 2):
            h1, h2 = dK[i], dK[i + 1]
            d2C = 2.0 * (C[i + 2] / (h2 * (h1 + h2))
                         - C[i + 1] / (h1 * h2)
                         + C[i] / (h1 * (h1 + h2)))
            if d2C < -1e-10:
                n_viol += 1
        return n_viol == 0, n_viol

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def fit(
        self,
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        weights: Optional[Sequence[float]] = None,
        lambda_smooth: float = 1e-4,
        lambda_arb: float = 100.0,
    ) -> SplineResult:
        """
        Calibre le spline arbitrage-free.

        Parameters
        ----------
        strikes     : strikes observés
        sigmas_mkt  : vol normales marché correspondantes
        weights     : poids par point (optionnel)
        lambda_smooth : régularisation courbure
        lambda_arb    : pénalité butterfly
        """
        strikes = np.asarray(strikes, dtype=float)
        sigmas_mkt = np.asarray(sigmas_mkt, dtype=float)

        valid = (sigmas_mkt > 0) & np.isfinite(sigmas_mkt) & np.isfinite(strikes)
        if valid.sum() < 4:
            raise ValueError("Pas assez de points valides pour calibrer le spline.")
        strikes = strikes[valid]
        sigmas_mkt = sigmas_mkt[valid]

        order = np.argsort(strikes)
        K = strikes[order]
        sigma = sigmas_mkt[order]

        if weights is not None:
            w = np.asarray(weights, dtype=float)[valid][order]
            w = w / w.sum()
        else:
            w = np.ones(len(K)) / len(K)

        n = len(K)
        F, T = self.F, self.T

        # Grille dense pour la pénalité butterfly
        k_dense = np.linspace(K[0], K[-1], max(200, n * 10))

        def objective(y: np.ndarray) -> float:
            cs = CubicSpline(K, y, bc_type="natural")

            # 1. Fit loss
            fit_loss = float(np.sum(w * (y - sigma) ** 2))

            # 2. Smoothness (intégrale de y''^2)
            y2 = cs(k_dense, 2)
            dk = k_dense[1] - k_dense[0]
            smooth_loss = float(np.sum(y2 ** 2) * dk)

            # 3. Butterfly penalty
            sigma_dense = np.maximum(cs(k_dense), 1e-10)
            arb_loss = SplineCalibration._butterfly_penalty(k_dense, sigma_dense, F, T)

            return fit_loss + lambda_smooth * smooth_loss + lambda_arb * arb_loss

        # Gradient numérique via L-BFGS-B
        result_opt = minimize(
            objective,
            sigma.copy(),
            method="L-BFGS-B",
            bounds=[(1e-8, None)] * n,
            options={"maxiter": 2000, "ftol": 1e-14},
        )

        y_opt = result_opt.x
        self._cs = CubicSpline(K, y_opt, bc_type="natural")
        self._k_min = float(K[0])
        self._k_max = float(K[-1])
        self._sigma_lo = float(y_opt[0])
        self._sigma_hi = float(y_opt[-1])

        sigmas_model = self._cs(K)
        residuals = sigma - sigmas_model
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        # Check arb-free
        k_check = np.linspace(K[0], K[-1], 500)
        arb_free, n_viol = SplineCalibration._check_butterfly(
            k_check, np.maximum(self._cs(k_check), 1e-10), F, T
        )

        self.result = SplineResult(
            strikes=K,
            sigmas_mkt=sigma,
            sigmas_model=sigmas_model,
            residuals=residuals,
            rmse=rmse,
            rmse_bps=rmse * 1e4,
            max_error_bps=float(np.max(np.abs(residuals))) * 1e4,
            F=F,
            T=T,
            n_points=n,
            arb_free=arb_free,
            n_arb_violations=n_viol,
            converged=result_opt.success,
        )
        return self.result

    # ------------------------------------------------------------------
    # Évaluation
    # ------------------------------------------------------------------

    def predict(self, strikes: Sequence[float]) -> np.ndarray:
        """Évalue le spline. Extrapolation flat hors du range observé."""
        if self._cs is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")

        K = np.asarray(strikes, dtype=float)
        sigma = np.empty_like(K, dtype=float)
        inside = (K >= self._k_min) & (K <= self._k_max)
        if inside.any():
            sigma[inside] = self._cs(K[inside])
        sigma[K < self._k_min] = self._sigma_lo
        sigma[K > self._k_max] = self._sigma_hi
        return np.maximum(sigma, 1e-8)

    def summary(self) -> str:
        if self.result is None:
            return "Spline — non calibré"
        r = self.result
        arb = "✓ arb-free" if r.arb_free else f"⚠ {r.n_arb_violations} butterfly viol."
        return (
            f"Spline | F={r.F:.4f}  T={r.T:.3f}a  N={r.n_points}\n"
            f"  RMSE={r.rmse_bps:.2f}bp  max_err={r.max_error_bps:.2f}bp  "
            f"[{arb}]  converged={r.converged}"
        )
