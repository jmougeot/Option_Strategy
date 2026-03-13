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
from typing import Dict, List, Optional, Sequence, Tuple

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
    arb_free: bool = False
    arb_violations_initial: int = 0

    def __repr__(self) -> str:
        arb = "arb-free" if self.arb_free else f"{self.arb_violations_initial} butterfly viol."
        return (
            f"SVIResult(θ={self.theta:.6f}, ρ={self.rho:.4f}, "
            f"η={self.eta:.4f}, γ={self.gamma:.4f}, "
            f"RMSE={self.rmse_bps:.2f}bp, converged={self.converged}, {arb})"
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
    # Densité risque-neutre — condition nécessaire et suffisante
    # d'absence d'arbitrage butterfly (Gatheral 2006, eq. 1.7)
    # ------------------------------------------------------------------

    @staticmethod
    def _g_func_static(
        k_arr: np.ndarray,
        theta: float, rho: float, eta: float, gamma: float,
    ) -> np.ndarray:
        """
        Calcule g(k) = (1 − k·w'/(2w))² − (w')²/4·(1/w + 1/4) + w''/2

        g(k) ≥ 0  ⟺  pas d'arbitrage butterfly au point k.
        C'est la condition *nécessaire et suffisante* (densité risque-neutre
        non-négative) — plus précise que la condition suffisante prop. 4.1.

        w', w'' sont calculés analytiquement depuis la paramétrisation SVI :
          z   = φ·k + ρ            D  = √(z² + 1 − ρ²)
          w'  = θφ/2·(ρ + z/D)     w'' = θφ²/2·(1−ρ²)/D³
        """
        ph = SVICalibration.phi(theta, eta, gamma)
        z  = ph * k_arr + rho
        D2 = np.maximum(z**2 + 1.0 - rho**2, 1e-14)
        D  = np.sqrt(D2)
        w   = np.maximum(theta / 2.0 * (1.0 + rho * ph * k_arr + D), 1e-12)
        wp  = theta * ph / 2.0 * (rho + z / D)
        wpp = theta * ph**2 / 2.0 * (1.0 - rho**2) / np.maximum(D**3, 1e-14)
        return (
            (1.0 - k_arr * wp / (2.0 * w))**2
            - wp**2 / 4.0 * (1.0 / w + 0.25)
            + wpp / 2.0
        )

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

    @staticmethod
    def _objective_arb(
        params: Sequence[float],
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        F: float,
        T: float,
        weights: np.ndarray,
        k_arb: np.ndarray,
        lam: float,
    ) -> float:
        """
        Objectif augmenté — Phase 2 (correction arbitrage).

        L(θ,ρ,η,γ) = Σᵢ wᵢ·(σ_SVI(Kᵢ) − σ_mkt(Kᵢ))²
                   + λ · Σⱼ max(−g(kⱼ), 0)²

        λ est adaptatif : calculé dans fit() pour que la pénalité soit
        comparable au fit_loss de la Phase 1 au niveau de violation observé.
        """
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
        fit_loss = float(np.sum(weights * errors**2))

        # Pénalité butterfly : Σⱼ max(−g(kⱼ), 0)²
        g = SVICalibration._g_func_static(k_arb, theta, rho, eta, gamma)
        arb_penalty = float(np.sum(np.minimum(g, 0.0)**2))
        return fit_loss + lam * arb_penalty

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

        # ── Phase 2 : correction locale arbitrage-safe ────────────────────────
        # Vérifie g(k) ≥ 0 sur une grille fine (condition nécessaire et
        # suffisante pour l'absence d'arbitrage butterfly). Si des violations
        # existent, re-optimise avec une pénalité adaptative λ pour les
        # corriger localement tout en préservant le fit marché de Phase 1.
        k_arb = np.linspace(-3.0, 3.0, 300)
        g_before = SVICalibration._g_func_static(k_arb, theta, rho, eta, gamma)
        n_viol_initial = int((g_before < 0).sum())
        arb_free = n_viol_initial == 0

        if n_viol_initial > 0:
            fit_loss_1 = float(np.sum(w * (sigmas_mkt - sigmas_model) ** 2))
            viol_scale = max(float(np.abs(g_before[g_before < 0]).max()), 1e-8)
            # λ adaptatif : pénalité ≈ fit_loss_1 quand g_violation ≈ viol_scale
            lam = float(np.clip(fit_loss_1 / viol_scale**2, 1.0, 1e6))

            result_arb = minimize(
                SVICalibration._objective_arb,
                [theta, rho, eta, gamma],
                args=(strikes, sigmas_mkt, self.F, self.T, w, k_arb, lam),
                method="L-BFGS-B",
                bounds=bounds,
                options={"ftol": 1e-14, "gtol": 1e-10, "maxiter": 5000},
            )

            if result_arb.success:
                theta_c, rho_c, eta_c, gamma_c = result_arb.x
                g_after = SVICalibration._g_func_static(k_arb, theta_c, rho_c, eta_c, gamma_c)
                # N'accepter que si la correction réduit (ou maintient) les violations
                if (g_after < 0).sum() <= n_viol_initial:
                    theta, rho, eta, gamma = theta_c, rho_c, eta_c, gamma_c
                    converged = True
                    sigmas_model = np.array([
                        SVICalibration.normal_vol(self.F, K, self.T, theta, rho, eta, gamma)
                        for K in strikes
                    ])
                    residuals = sigmas_mkt - sigmas_model
                    rmse = float(np.sqrt(np.mean(residuals ** 2)))
                    g_final = SVICalibration._g_func_static(k_arb, theta, rho, eta, gamma)
                    arb_free = bool(np.all(g_final >= -1e-6))

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
            arb_free=arb_free,
            arb_violations_initial=n_viol_initial,
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

    def check_butterfly_arbitrage(
        self, n_points: int = 300, tol: float = 1e-6,
    ) -> Tuple[bool, int, float]:
        """
        Vérifie l'absence d'arbitrage butterfly via la condition exacte g(k) ≥ 0.

        Returns (arb_free, n_violations, min_g) :
          - arb_free    : True si aucune violation détectée
          - n_violations: nombre de points k avec g(k) < −tol
          - min_g       : valeur minimale de g(k) sur la grille
        """
        if self.result is None:
            return False, -1, float("nan")
        r = self.result
        k_grid = np.linspace(-3.0, 3.0, n_points)
        g = SVICalibration._g_func_static(k_grid, r.theta, r.rho, r.eta, r.gamma)
        n_viol = int((g < -tol).sum())
        return n_viol == 0, n_viol, float(g.min())

    def summary(self) -> str:
        if self.result is None:
            return "SVICalibration — non calibré"
        r = self.result
        arb_tag = "✓ arb-free" if r.arb_free else f"⚠ {r.arb_violations_initial} butterfly viol."
        return (
            f"SVI | F={r.F:.4f}  T={r.T:.3f}a  [{arb_tag}]\n"
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
        Vérifie l'absence d'arbitrage butterfly via la condition exacte g(k) ≥ 0
        (densité risque-neutre non-négative — condition nécessaire et suffisante).
        """
        if self.result is None:
            return False, "Non calibré"
        r = self.result
        arb_free, n_viol, min_g = self.check_butterfly_arbitrage(n_points=n_points)
        if not arb_free:
            return False, f"{n_viol} butterfly violation(s), min g(k)={min_g:.4f}"
        return True, "OK — arb-free (g(k) ≥ 0 sur [-3, 3])"


# ============================================================================
# Calibration surface multi-expiration (Level 1 + Level 2)
# ============================================================================

@dataclass
class SliceData:
    """Données d'un slice (une expiration) pour la calibration surface."""
    F: float
    T: float
    strikes: np.ndarray
    sigmas_mkt: np.ndarray
    weights: Optional[np.ndarray] = None


@dataclass
class SVISurfaceResult:
    """Résultats de la calibration surface SVI multi-expiration."""
    slices: Dict[float, SVIResult]
    global_rmse_bps: float
    regularization_loss: float
    lambdas: Dict[str, float]
    n_slices: int = 0
    converged: bool = False

    def summary(self) -> str:
        lines = [
            f"SVI Surface | {self.n_slices} slices  "
            f"RMSE={self.global_rmse_bps:.2f}bp  "
            f"reg_loss={self.regularization_loss:.6f}"
        ]
        for T, r in sorted(self.slices.items()):
            arb = "✓" if r.arb_free else "⚠"
            lines.append(
                f"  T={T:.3f}a  θ={r.theta:.6f}  ρ={r.rho:.4f}  "
                f"η={r.eta:.4f}  γ={r.gamma:.4f}  "
                f"RMSE={r.rmse_bps:.2f}bp [{arb}]"
            )
        return "\n".join(lines)


class SVISurfaceCalibration:
    """
    Calibration SVI à deux niveaux (Gatheral & Jacquier 2014).

    Niveau 1 — calibration indépendante par expiration via SVICalibration.fit()
    Niveau 2 — re-optimisation jointe avec régularisation inter-maturité :

      L(x) = Σⱼ Σᵢ wᵢⱼ (σ_SVI(Kᵢⱼ; pⱼ) − σᵢⱼ_mkt)²
           + λ_θ Σⱼ (θ̃ⱼ₊₁ − θ̃ⱼ)² + λ_ρ Σⱼ (ρⱼ₊₁ − ρⱼ)²
           + λ_η Σⱼ (ηⱼ₊₁ − ηⱼ)² + λ_γ Σⱼ (γⱼ₊₁ − γⱼ)²

    où θ̃ⱼ = θⱼ / Tⱼ (variance par unité de temps — croissance naturelle
    de θ avec T neutralisée).
    """

    DEFAULT_LAMBDAS: Dict[str, float] = {
        "theta": 1.0,
        "rho": 5.0,
        "eta": 10.0,
        "gamma": 10.0,
    }

    def __init__(self) -> None:
        self.result: Optional[SVISurfaceResult] = None

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------

    def fit(
        self,
        slices: List[SliceData],
        lambdas: Optional[Dict[str, float]] = None,
    ) -> SVISurfaceResult:
        """Calibre la surface SVI multi-expiration."""
        slices = sorted(slices, key=lambda s: s.T)
        lam = {**self.DEFAULT_LAMBDAS, **(lambdas or {})}
        N = len(slices)

        if N < 2:
            return self._fit_single(slices[0], lam)

        # ── Level 1 : calibration indépendante par slice ──────────────
        level1: List[SVICalibration] = []
        for s in slices:
            cal = SVICalibration(F=s.F, T=s.T)
            w = list(s.weights) if s.weights is not None else None
            cal.fit(s.strikes, s.sigmas_mkt, weights=w)
            level1.append(cal)

        # Vérifier que toutes les calibrations ont convergé
        if any(c.result is None for c in level1):
            return self._fit_single(slices[0], lam)

        # Fit loss de Level 1 (pour scaling adaptatif des λ)
        fit_loss_1 = sum(
            float(np.sum((c.result.sigmas_mkt - c.result.sigmas_model) ** 2))  # type: ignore[union-attr]
            for c in level1
        )

        # ── Level 2 : re-optimisation jointe ──────────────────────────
        # Vecteur x = [θ₁, ρ₁, η₁, γ₁, θ₂, ρ₂, η₂, γ₂, ...]
        results1 = [c.result for c in level1]  # type: ignore[union-attr]
        x0 = np.array([
            [r.theta, r.rho, r.eta, r.gamma]  # type: ignore[union-attr]
            for r in results1
        ]).ravel()

        # Bornes par slice
        bounds_all: List[Tuple[float, float]] = []
        for r in results1:
            bounds_all.extend([
                (1e-6, max(r.theta * 20, 0.5)),  # type: ignore[union-attr]
                (-0.99, 0.99),
                (1e-4, 2.0),
                (0.01, 0.99),
            ])

        # Lambda scaling adaptatif : on veut reg ≈ fraction du fit_loss
        params_l1 = x0.reshape(N, 4)
        Ts = np.array([s.T for s in slices])
        theta_over_T = params_l1[:, 0] / Ts
        param_stds = [
            max(float(np.std(theta_over_T)), 1e-8),
            max(float(np.std(params_l1[:, 1])), 1e-8),
            max(float(np.std(params_l1[:, 2])), 1e-8),
            max(float(np.std(params_l1[:, 3])), 1e-8),
        ]
        scale_ref = max(fit_loss_1, 1e-12) / max(N - 1, 1)
        scaled_lam = {
            k: lam[k] * scale_ref / param_stds[i] ** 2
            for i, k in enumerate(["theta", "rho", "eta", "gamma"])
        }

        # Données pré-packées pour l'objectif (F, T, strikes, sigmas, weights)
        slice_pack = []
        for r in results1:
            slice_pack.append((r.F, r.T, r.strikes, r.sigmas_mkt,  # type: ignore[union-attr]
                               np.ones(r.n_points) / r.n_points))  # type: ignore[union-attr]

        result_opt = minimize(
            SVISurfaceCalibration._surface_objective,
            x0,
            args=(slice_pack, scaled_lam),
            method="L-BFGS-B",
            bounds=bounds_all,
            options={"ftol": 1e-12, "gtol": 1e-8, "maxiter": 5000},
        )

        # ── Construction des résultats ────────────────────────────────
        params_opt = result_opt.x.reshape(N, 4)
        slice_results: Dict[float, SVIResult] = {}
        all_residuals: List[float] = []

        for j, r in enumerate(results1):
            theta_j, rho_j, eta_j, gamma_j = params_opt[j]
            sigmas_model = np.array([
                SVICalibration.normal_vol(r.F, K, r.T, theta_j, rho_j, eta_j, gamma_j)  # type: ignore[union-attr]
                for K in r.strikes  # type: ignore[union-attr]
            ])
            residuals = r.sigmas_mkt - sigmas_model  # type: ignore[union-attr]
            rmse_j = float(np.sqrt(np.mean(residuals ** 2)))
            all_residuals.extend(residuals.tolist())

            # Vérification arbitrage par slice
            k_arb = np.linspace(-3.0, 3.0, 300)
            g = SVICalibration._g_func_static(k_arb, theta_j, rho_j, eta_j, gamma_j)
            arb_free_j = bool(np.all(g >= -1e-6))
            n_viol_j = int((g < 0).sum())

            slice_results[r.T] = SVIResult(  # type: ignore[union-attr]
                theta=float(theta_j), rho=float(rho_j),
                eta=float(eta_j), gamma=float(gamma_j),
                rmse=rmse_j, rmse_bps=rmse_j * 10_000,
                max_error_bps=float(np.max(np.abs(residuals))) * 10_000,
                strikes=r.strikes, sigmas_mkt=r.sigmas_mkt,  # type: ignore[union-attr]
                sigmas_model=sigmas_model, residuals=residuals,
                F=r.F, T=r.T, converged=result_opt.success,  # type: ignore[union-attr]
                n_points=r.n_points,  # type: ignore[union-attr]
                arb_free=arb_free_j, arb_violations_initial=n_viol_j,
            )

        global_rmse = float(np.sqrt(np.mean(np.array(all_residuals) ** 2)))
        reg_loss = SVISurfaceCalibration._regularization(
            params_opt, [s.T for s in slices], scaled_lam,
        )

        self.result = SVISurfaceResult(
            slices=slice_results,
            global_rmse_bps=global_rmse * 10_000,
            regularization_loss=reg_loss,
            lambdas=lam,
            n_slices=N,
            converged=result_opt.success,
        )
        return self.result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fit_single(self, s: SliceData, lam: Dict[str, float]) -> SVISurfaceResult:
        """Fallback : un seul slice → Level 1 uniquement."""
        cal = SVICalibration(F=s.F, T=s.T)
        w = list(s.weights) if s.weights is not None else None
        r = cal.fit(s.strikes, s.sigmas_mkt, weights=w)
        self.result = SVISurfaceResult(
            slices={s.T: r},
            global_rmse_bps=r.rmse_bps,
            regularization_loss=0.0,
            lambdas=lam,
            n_slices=1,
            converged=r.converged,
        )
        return self.result

    @staticmethod
    def _surface_objective(
        x: np.ndarray,
        slice_pack: List[Tuple[float, float, np.ndarray, np.ndarray, np.ndarray]],
        lam: Dict[str, float],
    ) -> float:
        """Objectif Level 2 : fit loss + régularisation inter-maturité."""
        N = len(slice_pack)
        params = x.reshape(N, 4)
        fit_loss = 0.0

        for j, (F_j, T_j, strikes_j, sigmas_j, w_j) in enumerate(slice_pack):
            theta_j, rho_j, eta_j, gamma_j = params[j]
            if (theta_j <= 0 or eta_j <= 0
                    or not (0.0 < gamma_j < 1.0)
                    or not (-0.999 < rho_j < 0.999)):
                return 1e10
            try:
                sigmas_model = np.array([
                    SVICalibration.normal_vol(F_j, K, T_j, theta_j, rho_j, eta_j, gamma_j)
                    for K in strikes_j
                ])
            except Exception:
                return 1e10
            if np.any(np.isnan(sigmas_model)) or np.any(sigmas_model <= 0):
                return 1e10
            fit_loss += float(np.sum(w_j * (sigmas_j - sigmas_model) ** 2))

        reg = SVISurfaceCalibration._regularization(
            params, [sp[1] for sp in slice_pack], lam,
        )
        return fit_loss + reg

    @staticmethod
    def _regularization(
        params: np.ndarray,
        Ts: List[float],
        lam: Dict[str, float],
    ) -> float:
        """
        R = λ_θ Σⱼ(θ̃ⱼ₊₁ − θ̃ⱼ)² + λ_ρ Σⱼ(ρⱼ₊₁ − ρⱼ)² + …
        avec θ̃ⱼ = θⱼ / Tⱼ.
        """
        N = len(Ts)
        if N < 2:
            return 0.0
        reg = 0.0
        for j in range(N - 1):
            d_theta = params[j + 1, 0] / Ts[j + 1] - params[j, 0] / Ts[j]
            d_rho = params[j + 1, 1] - params[j, 1]
            d_eta = params[j + 1, 2] - params[j, 2]
            d_gamma = params[j + 1, 3] - params[j, 3]
            reg += (lam["theta"] * d_theta ** 2
                    + lam["rho"] * d_rho ** 2
                    + lam["eta"] * d_eta ** 2
                    + lam["gamma"] * d_gamma ** 2)
        return reg

    def summary(self) -> str:
        if self.result is None:
            return "SVISurfaceCalibration — non calibré"
        return self.result.summary()
