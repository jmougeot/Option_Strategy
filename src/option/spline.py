"""
Arbitrage-Free Smoothing Spline — smile interpolation non-paramétrique.

Espace de travail :
    k = log(K / F)                  — log-moneyness
    w(k) = σ_N(K)² · T             — total variance (Bachelier)

Méthodologie :
    1. Grille de knots en log-moneyness
    2. Smoothing spline cubique naturelle (S''=0 aux bords)
       min  Σ wᵢ (yᵢ − S(xᵢ))²  +  λ ∫ S''(x)² dx
    3. Poids wᵢ = score de fiabilité par point
    4. Contrainte butterfly  : ∂²C/∂K² ≥ 0  (densité risque-neutre ≥ 0)
    5. Contrainte monotonie  : ∂C/∂K  ≤ 0  (call prices décroissants en K)
    6. Extrapolation ailes   : pente asymptotique linéaire en w(k)
    7. Surface multi-maturité: spline par T + interpolation en T
       avec vérification calendar : ∂w/∂T ≥ 0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize
from scipy.stats import norm


# ============================================================================
#  Données d'entrée par slice (pour la surface)
# ============================================================================

@dataclass
class SplineSliceData:
    """Données marché d'une tranche d'expiration pour le spline."""
    F: float
    T: float
    strikes: np.ndarray
    sigmas_mkt: np.ndarray          # vol normales Bachelier
    weights: Optional[np.ndarray] = None


# ============================================================================
#  Résultats
# ============================================================================

@dataclass
class SplineResult:
    """Résultat de la calibration spline pour une maturité."""
    knots_k: np.ndarray = field(default_factory=lambda: np.array([]))
    knots_w: np.ndarray = field(default_factory=lambda: np.array([]))

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
    n_butterfly_violations: int = 0
    n_monotone_violations: int = 0
    converged: bool = False

    wing_slope_left: float = 0.0
    wing_slope_right: float = 0.0

    def __repr__(self) -> str:
        arb_parts = []
        if self.n_butterfly_violations:
            arb_parts.append(f"{self.n_butterfly_violations} butterfly")
        if self.n_monotone_violations:
            arb_parts.append(f"{self.n_monotone_violations} monotone")
        arb = "arb-free" if self.arb_free else ", ".join(arb_parts)
        return (
            f"SplineResult(RMSE={self.rmse_bps:.2f}bp, "
            f"N={self.n_points}, {arb}, converged={self.converged})"
        )


@dataclass
class SplineSurfaceResult:
    """Résultat de la calibration spline multi-maturité."""
    slices: Dict[float, SplineResult] = field(default_factory=dict)
    global_rmse_bps: float = 0.0
    n_calendar_violations: int = 0
    n_slices: int = 0

    def summary(self) -> str:
        lines = [f"SplineSurface | {self.n_slices} slices, "
                 f"RMSE={self.global_rmse_bps:.2f}bp"]
        if self.n_calendar_violations:
            lines[0] += f", ⚠ {self.n_calendar_violations} calendar viol."
        for T in sorted(self.slices):
            r = self.slices[T]
            lines.append(f"  T={T:.3f}a: RMSE={r.rmse_bps:.2f}bp  "
                         f"N={r.n_points}  arb_free={r.arb_free}")
        return "\n".join(lines)


# ============================================================================
#  Helpers — Bachelier pricing (vectorisé)
# ============================================================================

def _bachelier_call_vec(F: float, K: np.ndarray,
                        sigma_n: np.ndarray, T: float) -> np.ndarray:
    """Prix call Bachelier vectorisé."""
    s = sigma_n * np.sqrt(T)
    safe_s = np.where(s > 0, s, 1.0)
    d = np.where(s > 0, (F - K) / safe_s, 0.0)
    intrinsic = np.maximum(F - K, 0.0)
    return np.where(s > 0, (F - K) * norm.cdf(d) + safe_s * norm.pdf(d), intrinsic)


# ============================================================================
#  Helpers — Conversions  k ↔ K  et  w ↔ σ_N
# ============================================================================

def _strikes_to_logm(K: np.ndarray, F: float) -> np.ndarray:
    """K → k = log(K/F)."""
    return np.log(K / F)


def _logm_to_strikes(k: np.ndarray, F: float) -> np.ndarray:
    """k → K = F · exp(k)."""
    return F * np.exp(k)


def _sigma_to_totalvar(sigma_n: np.ndarray, T: float) -> np.ndarray:
    """σ_N → w = σ_N² · T."""
    return sigma_n ** 2 * T


def _totalvar_to_sigma(w: np.ndarray, T: float) -> np.ndarray:
    """w → σ_N = sqrt(w / T)."""
    return np.sqrt(np.maximum(w, 0.0) / T)


# ============================================================================
#  Arbitrage checks
# ============================================================================

def _check_butterfly(K: np.ndarray, C: np.ndarray) -> Tuple[bool, int]:
    """
    Vérifie ∂²C/∂K² ≥ 0 — densité risque-neutre positive.
    Différences finies centrées sur grille non-uniforme.
    """
    n = len(K)
    if n < 3:
        return True, 0
    dK = np.diff(K)
    n_viol = 0
    for i in range(n - 2):
        h1, h2 = dK[i], dK[i + 1]
        d2C = 2.0 * (C[i + 2] / (h2 * (h1 + h2))
                      - C[i + 1] / (h1 * h2)
                      + C[i] / (h1 * (h1 + h2)))
        if d2C < -1e-10:
            n_viol += 1
    return n_viol == 0, n_viol


def _check_monotone(K: np.ndarray, C: np.ndarray) -> Tuple[bool, int]:
    """
    Vérifie ∂C/∂K ≤ 0 — call prices décroissants en strike.
    """
    if len(K) < 2:
        return True, 0
    dC = np.diff(C)
    dK = np.diff(K)
    slope = dC / dK
    n_viol = int(np.sum(slope > 1e-10))
    return n_viol == 0, n_viol


def _butterfly_penalty_vec(K: np.ndarray, C: np.ndarray) -> float:
    """Pénalité quadratique sur les violations butterfly."""
    n = len(K)
    if n < 3:
        return 0.0
    dK = np.diff(K)
    d2C = np.zeros(n - 2)
    for i in range(n - 2):
        h1, h2 = dK[i], dK[i + 1]
        d2C[i] = 2.0 * (C[i + 2] / (h2 * (h1 + h2))
                         - C[i + 1] / (h1 * h2)
                         + C[i] / (h1 * (h1 + h2)))
    return float(np.sum(np.minimum(d2C, 0.0) ** 2))


def _monotone_penalty_vec(K: np.ndarray, C: np.ndarray) -> float:
    """Pénalité quadratique sur les violations de monotonie call."""
    if len(K) < 2:
        return 0.0
    dC_dK = np.diff(C) / np.diff(K)
    return float(np.sum(np.maximum(dC_dK, 0.0) ** 2))


def _check_calendar(T_sorted: List[float],
                    w_evals: Dict[float, np.ndarray]) -> int:
    """
    Calendar arbitrage : w(k, T₁) ≤ w(k, T₂) pour T₁ < T₂.
    Retourne le nombre de points de grille en violation.
    """
    n_viol = 0
    for i in range(len(T_sorted) - 1):
        w1 = w_evals[T_sorted[i]]
        w2 = w_evals[T_sorted[i + 1]]
        n_viol += int(np.sum(w2 - w1 < -1e-10))
    return n_viol


# ============================================================================
#  SplineCalibration — une maturité
# ============================================================================

class SplineCalibration:
    """
    Smoothing spline arbitrage-free sur une maturité.

    Espace de travail : log-moneyness k = log(K/F), total variance w = σ²·T.

    Minimise :
        L = Σ wᵢ (wᵢ_mkt − S(kᵢ))²
          + λ ∫ S''(k)² dk
          + μ_bf  · penalty_butterfly
          + μ_mon · penalty_monotone

    Extrapolation : pente linéaire dans les ailes (slope left/right).
    """

    _N_DENSE: int = 500

    def __init__(self, F: float, T: float) -> None:
        self.F = F
        self.T = T
        self.result: Optional[SplineResult] = None

        # Spline interne en (k → w)
        self._cs: Optional[CubicSpline] = None
        self._k_min: float = 0.0
        self._k_max: float = 0.0
        self._w_left: float = 0.0
        self._w_right: float = 0.0
        self._slope_left: float = 0.0
        self._slope_right: float = 0.0

    # ------------------------------------------------------------------
    #  Calibration
    # ------------------------------------------------------------------

    def fit(
        self,
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        weights: Optional[Sequence[float] | np.ndarray] = None,
        *,
        lambda_smooth: float = 1e-4,
        mu_butterfly: float = 100.0,
        mu_monotone: float = 50.0,
    ) -> SplineResult:
        """
        Calibre le smoothing spline arbitrage-free.

        Parameters
        ----------
        strikes       : strikes observés (espace réel)
        sigmas_mkt    : vol normales Bachelier correspondantes
        weights       : score de fiabilité par point (plus élevé = plus fiable)
        lambda_smooth : pénalité de lissage  (∫ S''² dk)
        mu_butterfly  : pénalité butterfly   (∂²C/∂K² ≥ 0)
        mu_monotone   : pénalité monotonie   (∂C/∂K  ≤ 0)
        """
        strikes = np.asarray(strikes, dtype=float)
        sigmas_mkt = np.asarray(sigmas_mkt, dtype=float)

        # Filtrer les points invalides
        valid = (sigmas_mkt > 0) & np.isfinite(sigmas_mkt) & np.isfinite(strikes)
        if valid.sum() < 4:
            raise ValueError(
                f"Pas assez de points valides ({valid.sum()}) pour le spline (min 4)."
            )
        strikes = strikes[valid]
        sigmas_mkt = sigmas_mkt[valid]

        # Tri par strike croissant
        order = np.argsort(strikes)
        K = strikes[order]
        sigma = sigmas_mkt[order]

        # Poids de fiabilité
        if weights is not None:
            w = np.asarray(weights, dtype=float)[valid][order]
            w = w / w.sum()
        else:
            w = np.ones(len(K)) / len(K)

        F, T = self.F, self.T
        n = len(K)

        # ── Passage en log-moneyness + total variance ─────────────────
        k_obs = _strikes_to_logm(K, F)              # k = log(K/F)
        w_obs = _sigma_to_totalvar(sigma, T)         # w = σ² · T

        # Grille dense pour pénalités
        k_dense = np.linspace(k_obs[0], k_obs[-1], self._N_DENSE)
        K_dense = _logm_to_strikes(k_dense, F)

        # ── Objectif ──────────────────────────────────────────────────
        def objective(y: np.ndarray) -> float:
            # y = valeurs w(k) aux knots observés
            cs = CubicSpline(k_obs, y, bc_type="natural")

            # 1. Fit loss pondéré par fiabilité
            fit_loss = float(np.sum(w * (y - w_obs) ** 2))

            # 2. Smoothness : ∫ S''(k)² dk
            w2 = cs(k_dense, 2)
            dk = k_dense[1] - k_dense[0]
            smooth_loss = float(np.sum(w2 ** 2) * dk)

            # 3. Convertir w(k) dense → σ_N → C(K)
            w_dense = np.maximum(cs(k_dense), 1e-16)
            sigma_dense = _totalvar_to_sigma(w_dense, T)
            C_dense = _bachelier_call_vec(F, K_dense, sigma_dense, T)

            # 4. Butterfly : ∂²C/∂K² ≥ 0
            bf_pen = _butterfly_penalty_vec(K_dense, C_dense)

            # 5. Monotonie : ∂C/∂K ≤ 0
            mono_pen = _monotone_penalty_vec(K_dense, C_dense)

            return (fit_loss
                    + lambda_smooth * smooth_loss
                    + mu_butterfly * bf_pen
                    + mu_monotone * mono_pen)

        # ── Optimisation L-BFGS-B ────────────────────────────────────
        result_opt = minimize(
            objective,
            w_obs.copy(),
            method="L-BFGS-B",
            bounds=[(1e-16, None)] * n,
            options={"maxiter": 3000, "ftol": 1e-14},
        )

        # ── Construire le spline final ────────────────────────────────
        y_opt = result_opt.x
        self._cs = CubicSpline(k_obs, y_opt, bc_type="natural")
        self._k_min = float(k_obs[0])
        self._k_max = float(k_obs[-1])
        self._w_left = float(y_opt[0])
        self._w_right = float(y_opt[-1])

        # Pentes aux bords (extrapolation linéaire en w)
        self._slope_left = float(self._cs(self._k_min, 1))
        self._slope_right = float(self._cs(self._k_max, 1))

        # ── Métriques ─────────────────────────────────────────────────
        w_model_knots = self._cs(k_obs)
        sigma_model = _totalvar_to_sigma(np.maximum(w_model_knots, 0.0), T)
        residuals = sigma - sigma_model
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        # Arb checks sur grille dense
        k_check = np.linspace(k_obs[0], k_obs[-1], self._N_DENSE)
        K_check = _logm_to_strikes(k_check, F)
        w_check = np.maximum(self._cs(k_check), 1e-16)
        sigma_check = _totalvar_to_sigma(w_check, T)
        C_check = _bachelier_call_vec(F, K_check, sigma_check, T)
        bf_ok, n_bf = _check_butterfly(K_check, C_check)
        mono_ok, n_mono = _check_monotone(K_check, C_check)

        self.result = SplineResult(
            knots_k=k_obs,
            knots_w=y_opt,
            strikes=K,
            sigmas_mkt=sigma,
            sigmas_model=sigma_model,
            residuals=residuals,
            rmse=rmse,
            rmse_bps=rmse * 1e4,
            max_error_bps=float(np.max(np.abs(residuals))) * 1e4,
            F=F,
            T=T,
            n_points=n,
            arb_free=(bf_ok and mono_ok),
            n_butterfly_violations=n_bf,
            n_monotone_violations=n_mono,
            converged=result_opt.success,
            wing_slope_left=self._slope_left,
            wing_slope_right=self._slope_right,
        )
        return self.result

    # ------------------------------------------------------------------
    #  Évaluation
    # ------------------------------------------------------------------

    def _eval_totalvar(self, k: np.ndarray) -> np.ndarray:
        """
        Évalue w(k) avec extrapolation linéaire dans les ailes.

        Aile gauche  (k < k_min) : w = w_left  + slope_left  · (k − k_min)
        Aile droite  (k > k_max) : w = w_right + slope_right · (k − k_max)
        Intérieur                 : cubic spline naturelle
        """
        if self._cs is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")

        w = np.empty_like(k, dtype=float)
        inside = (k >= self._k_min) & (k <= self._k_max)
        left = k < self._k_min
        right = k > self._k_max

        if inside.any():
            w[inside] = self._cs(k[inside])
        if left.any():
            w[left] = self._w_left + self._slope_left * (k[left] - self._k_min)
        if right.any():
            w[right] = self._w_right + self._slope_right * (k[right] - self._k_max)

        return np.maximum(w, 1e-16)

    def predict(self, strikes: Sequence[float] | np.ndarray) -> np.ndarray:
        """
        Prédit σ_N(K) — retourne des vol normales Bachelier.

        Interface identique à SABR / SVI : entrée strikes, sortie σ_N.
        Interne : K → k → w(k) via spline → σ_N = sqrt(w/T).
        """
        K = np.asarray(strikes, dtype=float)
        k = _strikes_to_logm(K, self.F)
        w = self._eval_totalvar(k)
        return _totalvar_to_sigma(w, self.T)

    def predict_totalvar(self, k: np.ndarray) -> np.ndarray:
        """Évalue w(k) directement en log-moneyness."""
        return self._eval_totalvar(k)

    def get_spline(self) -> Optional[CubicSpline]:
        """Retourne l'objet CubicSpline interne (k → w)."""
        return self._cs

    # ------------------------------------------------------------------
    #  Résumé
    # ------------------------------------------------------------------

    def summary(self) -> str:
        if self.result is None:
            return "Spline — non calibré"
        r = self.result
        arb_parts = []
        if r.n_butterfly_violations:
            arb_parts.append(f"⚠ {r.n_butterfly_violations} bf")
        if r.n_monotone_violations:
            arb_parts.append(f"⚠ {r.n_monotone_violations} mono")
        arb = " ".join(arb_parts) or "✓ arb-free"
        return (
            f"Spline | F={r.F:.4f}  T={r.T:.3f}a  N={r.n_points}\n"
            f"  RMSE={r.rmse_bps:.2f}bp  max_err={r.max_error_bps:.2f}bp  "
            f"[{arb}]  converged={r.converged}\n"
            f"  wings: slope_L={r.wing_slope_left:.4f}  "
            f"slope_R={r.wing_slope_right:.4f}"
        )


# ============================================================================
#  SplineSurfaceCalibration — multi-maturité
# ============================================================================

class SplineSurfaceCalibration:
    """
    Surface de vol par spline : une SplineCalibration par maturité,
    puis vérification d'absence de calendar arbitrage et interpolation en T.

    Calendar check : w(k, T₁) ≤ w(k, T₂) pour T₁ < T₂ sur grille dense.
    """

    def __init__(self) -> None:
        self._slices: Dict[float, SplineCalibration] = {}
        self.result: Optional[SplineSurfaceResult] = None

    # ------------------------------------------------------------------
    #  Calibration
    # ------------------------------------------------------------------

    def fit(
        self,
        slices: List[SplineSliceData],
        *,
        lambda_smooth: float = 1e-4,
        mu_butterfly: float = 100.0,
        mu_monotone: float = 50.0,
    ) -> SplineSurfaceResult:
        """
        Calibre un spline indépendant par maturité,
        puis vérifie le calendar arbitrage.
        """
        results: Dict[float, SplineResult] = {}
        all_rmse2: list[float] = []

        for sd in slices:
            cal = SplineCalibration(F=sd.F, T=sd.T)
            try:
                res = cal.fit(
                    strikes=sd.strikes,
                    sigmas_mkt=sd.sigmas_mkt,
                    weights=sd.weights,
                    lambda_smooth=lambda_smooth,
                    mu_butterfly=mu_butterfly,
                    mu_monotone=mu_monotone,
                )
                results[sd.T] = res
                self._slices[sd.T] = cal
                all_rmse2.append(res.rmse ** 2)
            except Exception as exc:
                print(f"  Spline T={sd.T:.3f} échoué : {exc}")

        if not results:
            raise ValueError("Aucune slice spline calibrée.")

        # Calendar arbitrage check
        T_sorted = sorted(results.keys())
        n_cal_viol = 0
        if len(T_sorted) > 1:
            k_lo = min(r.knots_k[0] for r in results.values())
            k_hi = max(r.knots_k[-1] for r in results.values())
            k_grid = np.linspace(k_lo, k_hi, SplineCalibration._N_DENSE)

            w_evals: Dict[float, np.ndarray] = {}
            for T_val in T_sorted:
                w_evals[T_val] = self._slices[T_val]._eval_totalvar(k_grid)
            n_cal_viol = _check_calendar(T_sorted, w_evals)

        global_rmse = float(np.sqrt(np.mean(all_rmse2))) if all_rmse2 else 0.0

        self.result = SplineSurfaceResult(
            slices=results,
            global_rmse_bps=global_rmse * 1e4,
            n_calendar_violations=n_cal_viol,
            n_slices=len(results),
        )
        return self.result

    # ------------------------------------------------------------------
    #  Interpolation en maturité
    # ------------------------------------------------------------------

    def predict_at_T(
        self, T_target: float, strikes: np.ndarray, F: float,
    ) -> np.ndarray:
        """
        Interpole la vol entre deux maturités calibrées.
        Interpolation linéaire en w(k, T) puis conversion σ_N.
        """
        T_sorted = sorted(self._slices.keys())
        if not T_sorted:
            raise RuntimeError("Surface non calibrée.")

        if T_target <= T_sorted[0]:
            return self._slices[T_sorted[0]].predict(strikes)
        if T_target >= T_sorted[-1]:
            return self._slices[T_sorted[-1]].predict(strikes)

        # Encadrer T_target
        T_lo, T_hi = T_sorted[0], T_sorted[-1]
        for i in range(len(T_sorted) - 1):
            if T_sorted[i] <= T_target <= T_sorted[i + 1]:
                T_lo, T_hi = T_sorted[i], T_sorted[i + 1]
                break

        k = _strikes_to_logm(np.asarray(strikes, dtype=float), F)
        w_lo = self._slices[T_lo]._eval_totalvar(k)
        w_hi = self._slices[T_hi]._eval_totalvar(k)

        alpha = (T_target - T_lo) / (T_hi - T_lo) if T_hi > T_lo else 0.0
        w_interp = (1 - alpha) * w_lo + alpha * w_hi

        return _totalvar_to_sigma(np.maximum(w_interp, 1e-16), T_target)

    def summary(self) -> str:
        if self.result is None:
            return "SplineSurface — non calibrée"
        return self.result.summary()
