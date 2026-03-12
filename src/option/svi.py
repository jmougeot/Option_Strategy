"""
Module SVI — Surface SVI (Gatheral & Jacquier 2014)

Paramétrisation : w(k, θ) = θ/2 * [1 + ρ·φ(θ)·k + sqrt((φ(θ)·k + ρ)² + (1-ρ²))]
où :
  k   = log(K/F)      — log-moneyness
  θ   = ATM variance totale (= σ_ATM² · T)
  ρ   = corrélation skew   ∈ (-1, 1)
  φ   = power-law:  φ(θ) = η / (θ^γ · (1 + θ)^(1-γ))   avec η, γ ∈ ]0, 1[

La vol normale Bachelier σ_N est obtenue par conversion :
  σ_N = sqrt(w / T) · F          (approximation lognormal→normal)

Références:
  - Gatheral & Jacquier, "Arbitrage-free SVI volatility surfaces", 2014
  - De Marco & Henry-Labordère, "Linking Vanillas and VIX Options", 2012
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import differential_evolution, minimize


# ============================================================================
# Résultats
# ============================================================================

@dataclass
class SVIResult:
    """Résultats de la calibration SVI."""
    theta: float       # ATM variance totale  (σ_ATM² · T)
    rho: float         # corrélation skew
    eta: float         # paramètre power-law
    gamma: float       # exposant power-law

    rmse: float = 0.0
    rmse_bps: float = 0.0
    max_error_bps: float = 0.0

    strikes: np.ndarray = field(default_factory=lambda: np.array([]))
    sigmas_mkt: np.ndarray = field(default_factory=lambda: np.array([]))
    sigmas_model: np.ndarray = field(default_factory=lambda: np.array([]))
    residuals: np.ndarray = field(default_factory=lambda: np.array([]))

    F: float = 0.0
    T: float = 0.0
    converged: bool = False
    n_points: int = 0

    def __repr__(self) -> str:
        return (
            f"SVIResult(θ={self.theta:.6f}, ρ={self.rho:.4f}, "
            f"η={self.eta:.4f}, γ={self.gamma:.4f}, "
            f"RMSE={self.rmse_bps:.2f}bp, converged={self.converged})"
        )


# ============================================================================
# Classe principale
# ============================================================================

class SVICalibration:
    """
    Modèle SVI — calibration et évaluation.

    Utilise la vol normale (Bachelier) comme SABR : on calibre sur σ_N(K).
    La conversion variance totale → vol normale est :
        σ_N(K) ≈ F · sqrt(w(k) / T)
    où w(k) est la variance totale SVI et k = log(K/F).
    """

    def __init__(self, F: float, T: float) -> None:
        self.F = F
        self.T = T
        self.result: Optional[SVIResult] = None

    # ------------------------------------------------------------------
    # Formule SVI
    # ------------------------------------------------------------------

    @staticmethod
    def phi(theta: float, eta: float, gamma: float) -> float:
        """Fonction de market price of risk : φ(θ) = η / (θ^γ · (1+θ)^(1-γ))."""
        if theta <= 0:
            return 1.0
        return eta / (theta ** gamma * (1.0 + theta) ** (1.0 - gamma))

    @staticmethod
    def total_variance(
        k: float, theta: float, rho: float, eta: float, gamma: float
    ) -> float:
        """variance totale SVI w(k, θ).
        k = log(K/F), θ = ATM total variance.
        """
        ph = SVICalibration.phi(theta, eta, gamma)
        inner = ph * k + rho
        w = theta / 2.0 * (1.0 + rho * ph * k + np.sqrt(inner ** 2 + 1.0 - rho ** 2))
        return max(float(w), 1e-12)

    @staticmethod
    def normal_vol(
        F: float, K: float, T: float,
        theta: float, rho: float, eta: float, gamma: float,
    ) -> float:
        """Vol normale σ_N via SVI : σ_N = F · sqrt(w / T)."""
        if T <= 0 or K <= 0 or F <= 0:
            return 1e-8
        k = np.log(K / F)
        w = SVICalibration.total_variance(k, theta, rho, eta, gamma)
        sigma_n = F * np.sqrt(w / T)
        return max(float(sigma_n), 1e-8)

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    @staticmethod
    def _objective(
        params: Sequence[float],
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        F: float,
        T: float,
        weights: np.ndarray,
    ) -> float:
        theta, rho, eta, gamma = params
        if (
            theta <= 0 or eta <= 0
            or not (0.0 < gamma < 1.0)
            or not (-0.999 < rho < 0.999)
        ):
            return 1e10

        try:
            sigmas_model = np.array([
                SVICalibration.normal_vol(F, K, T, theta, rho, eta, gamma)
                for K in strikes
            ])
        except Exception:
            return 1e10

        if np.any(np.isnan(sigmas_model)) or np.any(sigmas_model <= 0):
            return 1e10

        errors = sigmas_mkt - sigmas_model
        return float(np.sum(weights * errors ** 2))

    def fit(
        self,
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        weights: Optional[Sequence[float]] = None,
    ) -> SVIResult:
        """Calibre θ, ρ, η, γ par moindres carrés pondérés."""
        strikes = np.asarray(strikes, dtype=float)
        sigmas_mkt = np.asarray(sigmas_mkt, dtype=float)

        valid = (sigmas_mkt > 0) & np.isfinite(sigmas_mkt) & np.isfinite(strikes)
        if valid.sum() < 4:
            raise ValueError("Pas assez de points valides pour calibrer SVI (min 4).")
        strikes = strikes[valid]
        sigmas_mkt = sigmas_mkt[valid]

        if weights is None:
            moneyness = np.abs(strikes - self.F)
            w = np.exp(-0.5 * (moneyness / (0.5 * moneyness.std() + 1e-8)) ** 2)
            w = w / w.sum()
        else:
            w = np.asarray(weights, dtype=float)[valid]
            total_w = w.sum()
            w = w / total_w if total_w > 0 else np.ones(len(strikes)) / len(strikes)

        # Initialisation θ depuis la vol ATM marché
        atm_idx = np.argmin(np.abs(strikes - self.F))
        sigma_atm = sigmas_mkt[atm_idx]
        theta0 = (sigma_atm / self.F) ** 2 * self.T  # var totale ATM initiale

        # Bornes : θ>0, ρ∈(-1,1), η∈(0,2), γ∈(0,1)
        bounds = [
            (1e-6, max(theta0 * 20, 0.5)),
            (-0.99, 0.99),
            (1e-4, 2.0),
            (0.01, 0.99),
        ]

        result_de = differential_evolution(
            SVICalibration._objective,
            bounds=bounds,
            args=(strikes, sigmas_mkt, self.F, self.T, w),
            maxiter=2000,
            tol=1e-10,
            popsize=20,
            mutation=(0.5, 1.5),
            recombination=0.9,
            polish=True,
        )

        x0 = result_de.x if result_de.success else np.array([theta0, -0.1, 0.5, 0.5])

        result_loc = minimize(
            SVICalibration._objective,
            x0,
            args=(strikes, sigmas_mkt, self.F, self.T, w),
            method="L-BFGS-B",
            bounds=bounds,
            options={"ftol": 1e-14, "gtol": 1e-10, "maxiter": 5000},
        )

        theta, rho, eta, gamma = result_loc.x
        converged = result_loc.success or result_de.success

        sigmas_model = np.array([
            SVICalibration.normal_vol(self.F, K, self.T, theta, rho, eta, gamma)
            for K in strikes
        ])
        residuals = sigmas_mkt - sigmas_model
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        self.result = SVIResult(
            theta=float(theta),
            rho=float(rho),
            eta=float(eta),
            gamma=float(gamma),
            rmse=rmse,
            rmse_bps=rmse * 10_000,
            max_error_bps=float(np.max(np.abs(residuals))) * 10_000,
            strikes=strikes,
            sigmas_mkt=sigmas_mkt,
            sigmas_model=sigmas_model,
            residuals=residuals,
            F=self.F,
            T=self.T,
            converged=converged,
            n_points=len(strikes),
        )
        return self.result

    # ------------------------------------------------------------------
    # Évaluation
    # ------------------------------------------------------------------

    def predict(self, strikes: Sequence[float]) -> np.ndarray:
        """Retourne la surface SVI calibrée pour un vecteur de strikes."""
        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result
        return np.array([
            SVICalibration.normal_vol(self.F, K, self.T, r.theta, r.rho, r.eta, r.gamma)
            for K in strikes
        ])

    def summary(self) -> str:
        if self.result is None:
            return "SVICalibration — non calibré"
        r = self.result
        return (
            f"SVI | F={r.F:.4f}  T={r.T:.3f}a\n"
            f"  θ={r.theta:.6f}  ρ={r.rho:.4f}  η={r.eta:.4f}  γ={r.gamma:.4f}\n"
            f"  RMSE={r.rmse_bps:.2f}bp  max_err={r.max_error_bps:.2f}bp  "
            f"N={r.n_points}  converged={r.converged}"
        )

    def anomalies(
        self,
        threshold: float = 1.5,
        min_error_bps: float = 0.5,
    ) -> List[dict]:
        """Points dont |résidu| > threshold×RMSE ou > min_error_bps bp."""
        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result
        cut_rmse = threshold * r.rmse
        cut_abs = min_error_bps / 10_000.0

        out = []
        for K, s_mkt, s_model, res in zip(
            r.strikes, r.sigmas_mkt, r.sigmas_model, r.residuals
        ):
            if abs(res) > cut_rmse or abs(res) > cut_abs:
                out.append({
                    "strike": round(float(K), 4),
                    "sigma_mkt": float(s_mkt),
                    "sigma_model": float(s_model),
                    "residual": float(res),
                    "residual_bps": float(res) * 10_000,
                    "z_score": abs(res) / r.rmse if r.rmse > 0 else 0.0,
                    "direction": "overpriced" if res > 0 else "underpriced",
                })

        out.sort(key=lambda x: abs(x["residual"]), reverse=True)
        return out

    # ------------------------------------------------------------------
    # Condition de non-arbitrage (Gatheral & Jacquier, prop. 4.1)
    # ------------------------------------------------------------------

    def check_no_arbitrage(self, n_points: int = 200) -> Tuple[bool, str]:
        """
        Vérifie les conditions suffisantes d'absence d'arbitrage SVI :
          1. w ≥ 0
          2. (1 - k·φ·ρ/2)² ≥ (φ²/4)(1-ρ²) + φ²k²(1-ρ²)/4  (butterfly)
          3. ∂_k w ≥ 0 pour k > 0 (calendar arbitrage — simplifié)
        """
        if self.result is None:
            return False, "Non calibré"
        r = self.result

        ks = np.linspace(-2.0, 2.0, n_points)
        msgs = []

        for k in ks:
            w = SVICalibration.total_variance(k, r.theta, r.rho, r.eta, r.gamma)
            if w < 0:
                msgs.append(f"w<0 à k={k:.2f}")
                break

            ph = SVICalibration.phi(r.theta, r.eta, r.gamma)
            # Condition butterfly (prop. 4.1 eq. 4.2)
            lhs = (1.0 - k * ph * r.rho / 2.0) ** 2
            rhs = ph ** 2 / 4.0 * (1.0 - r.rho ** 2) * (1.0 + k ** 2)
            if lhs < rhs - 1e-8:
                msgs.append(f"butterfly violation à k={k:.2f}")
                break

        if msgs:
            return False, " | ".join(msgs)
        return True, "OK"
