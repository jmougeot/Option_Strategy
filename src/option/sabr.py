"""
Module SABR — Calibration et détection d'anomalie

Tout est encapsulé dans la classe SABRCalibration.
SABRResult est un dataclass léger qui stocke les résultats.
Des alias module-level assurent la compatibilité avec l'existant.
"""

from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple
import numpy as np
from scipy.optimize import differential_evolution, minimize


# ============================================================================
# RÉSULTATS DE CALIBRATION
# ============================================================================

@dataclass
class SABRResult:
    """Résultats de la calibration SABR."""
    alpha: float
    beta: float
    rho: float
    nu: float

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
            f"SABRResult(alpha={self.alpha:.6f}, beta={self.beta:.2f}, "
            f"rho={self.rho:.4f}, nu={self.nu:.6f}, "
            f"RMSE={self.rmse_bps:.2f}bp, converged={self.converged})"
        )


# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class SABRCalibration:
    """
    Modèle SABR — formules de vol, calibration, détection d'anomalies,
    visualisation et calcul des volatilités sur une liste d'options.
    """

    def __init__(
        self,
        F: float,
        T: float,
        beta: float = 0.0,
        vol_type: str = "normal",
    ) -> None:
        self.F = F
        self.T = T
        self.beta = beta
        self.vol_type = vol_type
        self.result: Optional[SABRResult] = None

    # ------------------------------------------------------------------
    # Formules de volatilité SABR
    # ------------------------------------------------------------------

    @staticmethod
    def lognormal_vol(
        F: float, K: float, T: float,
        alpha: float, beta: float, rho: float, nu: float,
    ) -> float:
        """Volatilité lognormale (Black) — Hagan et al. 2002, éq. (2.17b)."""
        if T <= 0:
            return alpha
        if K <= 0 or F <= 0:
            return 1e-8

        eps = 1e-7

        if abs(F - K) < eps:
            FK_beta = F ** (1.0 - beta)
            atm_corr = (
                (1 - beta) ** 2 / 24.0 * alpha ** 2 / FK_beta ** 2
                + rho * beta * nu * alpha / (4.0 * F ** (1.0 - beta))
                + (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
            )
            return alpha / FK_beta * (1.0 + atm_corr * T)

        log_FK = np.log(F / K)
        FK_mid = np.sqrt(F * K)
        FK_beta = FK_mid ** (1.0 - beta)

        log2 = log_FK ** 2
        log4 = log_FK ** 4
        A_exp = 1.0 + (1.0 - beta) ** 2 / 24.0 * log2 + (1.0 - beta) ** 4 / 1920.0 * log4

        z = nu / alpha * FK_beta * log_FK
        sqrt_disc = np.sqrt(1.0 - 2.0 * rho * z + z ** 2)
        chi = np.log((sqrt_disc + z - rho) / (1.0 - rho))
        z_chi = z / chi if abs(chi) > eps else 1.0

        time_corr = (
            (1.0 - beta) ** 2 / 24.0 * alpha ** 2 / FK_beta ** 2
            + rho * beta * nu * alpha / (4.0 * FK_beta)
            + (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
        )

        sigma_B = alpha / (FK_beta * A_exp) * z_chi * (1.0 + time_corr * T)
        return max(sigma_B, 1e-8)

    @staticmethod
    def normal_vol(
        F: float, K: float, T: float,
        alpha: float, beta: float, rho: float, nu: float,
    ) -> float:
        """Volatilité normale (Bachelier) — Hagan et al. 2002, éq. B.67a."""
        if T <= 0:
            return alpha
        if alpha <= 0:
            return 1e-8

        eps = 1e-7

        # ── β ≈ 0 : formule directe normal SABR ──
        if abs(beta) < eps:
            diff = F - K
            if abs(diff) < eps:
                atm_corr = (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
                return alpha * (1.0 + atm_corr * T)
            else:
                z = nu / alpha * diff
                sqrt_disc = np.sqrt(1.0 - 2.0 * rho * z + z ** 2)
                chi = np.log((sqrt_disc + z - rho) / (1.0 - rho))
                z_chi = z / chi if abs(chi) > eps else 1.0
                atm_corr = (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
                return alpha * z_chi * (1.0 + atm_corr * T)

        # ── β > 0 : formule Hagan (A.69b) pour la vol normale ──
        if K <= 0 or F <= 0:
            return 1e-8

        one_m_beta = 1.0 - beta

        if abs(F - K) < eps:
            # ATM : σ_N = α·F^β·[1 + C_N·T]
            F1b = F ** one_m_beta
            time_corr = (
                -beta * (2.0 - beta) / 24.0 * alpha ** 2 / (F1b * F1b)
                + rho * beta * nu * alpha / (4.0 * F1b)
                + (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
            )
            return alpha * F ** beta * (1.0 + time_corr * T)

        # Non-ATM
        F1b = F ** one_m_beta
        K1b = K ** one_m_beta

        # Préfacteur : α·(1-β)·(F - K) / (F^{1-β} - K^{1-β})
        prefactor = alpha * one_m_beta * (F - K) / (F1b - K1b)

        # ζ = (ν/α)·(F^{1-β} - K^{1-β}) / (1-β)
        zeta = nu / alpha * (F1b - K1b) / one_m_beta

        sqrt_disc = np.sqrt(1.0 - 2.0 * rho * zeta + zeta ** 2)
        chi = np.log((sqrt_disc + zeta - rho) / (1.0 - rho))
        zeta_chi = zeta / chi if abs(chi) > eps else 1.0

        # Correction temporelle C_N
        FK_1b = (F * K) ** one_m_beta              # (FK)^{1-β}
        FK_half_1b = (F * K) ** (one_m_beta / 2.0)  # (FK)^{(1-β)/2}
        time_corr = (
            -beta * (2.0 - beta) / 24.0 * alpha ** 2 / FK_1b
            + rho * beta * nu * alpha / (4.0 * FK_half_1b)
            + (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
        )

        sigma_N = prefactor * zeta_chi * (1.0 + time_corr * T)
        return max(sigma_N, 1e-8)

    @staticmethod
    def vol(
        F: float, K: float, T: float,
        alpha: float, beta: float, rho: float, nu: float,
        vol_type: str = "normal",
    ) -> float:
        """Interface unifiée : vol SABR lognormale ou normale."""
        if vol_type == "lognormal":
            return SABRCalibration.lognormal_vol(F, K, T, alpha, beta, rho, nu)
        return SABRCalibration.normal_vol(F, K, T, alpha, beta, rho, nu)

    # ------------------------------------------------------------------
    # Objectif d'optimisation (privé)
    # ------------------------------------------------------------------

    @staticmethod
    def _objective(
        params: Sequence[float],
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        F: float,
        T: float,
        beta: float,
        weights: np.ndarray,
        vol_type: str = "normal",
    ) -> float:
        """Erreur quadratique pondérée entre vol SABR et vol marché."""
        alpha, rho, nu = params
        if alpha <= 0 or nu <= 0 or rho <= -0.999 or rho >= 0.999:
            return 1e10

        try:
            sigmas_model = np.array(
                [SABRCalibration.vol(F, K, T, alpha, beta, rho, nu, vol_type) for K in strikes]
            )
        except Exception:
            return 1e10

        if np.any(np.isnan(sigmas_model)) or np.any(sigmas_model <= 0):
            return 1e10

        errors = sigmas_mkt - sigmas_model
        return float(np.sum(weights * errors ** 2))

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def fit(
        self,
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        weights: Optional[Sequence[float]] = None,
        seed: int = 42,
    ) -> SABRResult:
        """Calibre les paramètres SABR (alpha, rho, nu) par moindres carrés pondérés."""
        strikes = np.asarray(strikes, dtype=float)
        sigmas_mkt = np.asarray(sigmas_mkt, dtype=float)

        valid = (sigmas_mkt > 0) & np.isfinite(sigmas_mkt) & np.isfinite(strikes)
        if valid.sum() < 3:
            raise ValueError("Pas assez de points valides pour calibrer SABR.")
        strikes = strikes[valid]
        sigmas_mkt = sigmas_mkt[valid]

        if weights is None:
            moneyness = np.abs(strikes - self.F)
            w = np.exp(-0.5 * (moneyness / (0.5 * moneyness.std() + 1e-8)) ** 2)
            w = w / w.sum()
        else:
            w = np.asarray(weights, dtype=float)[valid]
            w = w / w.sum()

        atm_idx = np.argmin(np.abs(strikes - self.F))
        sigma_atm = sigmas_mkt[atm_idx]

        bounds = [(1e-6, sigma_atm * 5), (-0.99, 0.99), (1e-4, 5.0)]

        result_de = differential_evolution(
            SABRCalibration._objective,
            bounds=bounds,
            args=(strikes, sigmas_mkt, self.F, self.T, self.beta, w, self.vol_type),
            seed=seed,
            maxiter=2000,
            tol=1e-10,
            popsize=20,
            mutation=(0.5, 1.5),
            recombination=0.9,
            polish=True,
        )

        best_params = result_de.x if result_de.success else np.array([sigma_atm, -0.1, 0.5])

        result_loc = minimize(
            SABRCalibration._objective,
            best_params,
            args=(strikes, sigmas_mkt, self.F, self.T, self.beta, w, self.vol_type),
            method="L-BFGS-B",
            bounds=bounds,
            options={"ftol": 1e-14, "gtol": 1e-10, "maxiter": 5000},
        )

        alpha, rho, nu = result_loc.x
        converged = result_loc.success or result_de.success

        sigmas_model = np.array([
            SABRCalibration.vol(self.F, K, self.T, alpha, self.beta, rho, nu, self.vol_type)
            for K in strikes
        ])
        residuals = sigmas_mkt - sigmas_model
        rmse = float(np.sqrt(np.mean(residuals ** 2)))

        self.result = SABRResult(
            alpha=float(alpha),
            beta=float(self.beta),
            rho=float(rho),
            nu=float(nu),
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
        """Retourne la surface SABR calibrée pour un vecteur de strikes."""
        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result
        return np.array([
            SABRCalibration.vol(self.F, K, self.T, r.alpha, r.beta, r.rho, r.nu, self.vol_type)
            for K in strikes
        ])

    def summary(self) -> str:
        """Retourne un résumé texte de la calibration."""
        if self.result is None:
            return "SABRCalibration — non calibré"
        r = self.result
        return (
            f"SABR | F={r.F:.4f}  T={r.T:.3f}a  β={r.beta:.1f}\n"
            f"  α={r.alpha:.6f}  ρ={r.rho:.4f}  ν={r.nu:.6f}\n"
            f"  RMSE={r.rmse_bps:.2f}bp  max_err={r.max_error_bps:.2f}bp  "
            f"N={r.n_points}  converged={r.converged}"
        )

    # ------------------------------------------------------------------
    # Détection d'anomalies
    # ------------------------------------------------------------------

    def anomalies(
        self,
        threshold: float = 1.5,
        min_error_bps: float = 0.5,
    ) -> List[Dict]:
        """
        Retourne les points dont |résidu| > threshold×RMSE ou |résidu| > min_error_bps bp.
        Triés par résidu absolu décroissant.
        """
        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result
        cut_rmse = threshold * r.rmse
        cut_abs  = min_error_bps / 10_000.0

        out = []
        for K, s_mkt, s_model, res in zip(r.strikes, r.sigmas_mkt, r.sigmas_model, r.residuals):
            if abs(res) > cut_rmse or abs(res) > cut_abs:
                out.append({
                    "strike":       round(float(K), 4),
                    "sigma_mkt":    float(s_mkt),
                    "sigma_model":  float(s_model),
                    "residual":     float(res),
                    "residual_bps": float(res) * 10_000,
                    "z_score":      abs(res) / r.rmse if r.rmse > 0 else 0.0,
                    "direction":    "overpriced" if res > 0 else "underpriced",
                })

        out.sort(key=lambda x: abs(x["residual"]), reverse=True)
        return out

    # ------------------------------------------------------------------
    # Helpers : extraction et pipeline depuis des objets Option
    # ------------------------------------------------------------------

    @staticmethod
    def from_options(
        options,
        F: Optional[float] = None,
        T: float = 0.25,
        beta: float = 0.0,
        min_iv: float = 1e-6,
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Extrait (strikes, implied_vols, F) depuis une liste d'objets Option Bloomberg.
        """
        from option.option_class import Option

        valid_options = [
            o for o in options
            if isinstance(o, Option) and o.implied_volatility > min_iv and o.strike > 0
        ]

        if not valid_options:
            raise ValueError("Aucune option valide dans la liste fournie.")

        strikes = np.array([o.strike for o in valid_options])
        ivs = np.array([o.implied_volatility for o in valid_options])
        order = np.argsort(strikes)
        strikes, ivs = strikes[order], ivs[order]

        if F is None:
            prices = [o.underlying_price for o in valid_options
                      if o.underlying_price and o.underlying_price > 0]
            F = float(np.median(prices)) if prices else float(np.median(strikes))

        return strikes, ivs, F

    # ------------------------------------------------------------------
    # Calcul des volatilités pour toute une liste d'options
    # ------------------------------------------------------------------

    @classmethod
    def compute_volatility(
        cls,
        options,
        time_to_expiry: float = 0.25,
        future_price: Optional[float] = None,
        anomaly_threshold: float = 1.5,
    ) -> Optional["SABRCalibration"]:
        """
        Calibre SABR et enrichit chaque option avec sabr_volatility,
        """
        from option.bachelier import Bachelier

        F = future_price
        if not F:
            return None

        by_strike: dict = defaultdict(list)
        for o in options:
            if o.implied_volatility > 0 and o.strike > 0:
                by_strike[round(o.strike, 6)].append(o.implied_volatility)

        if len(by_strike) < 3:
            return None

        strikes = np.array(sorted(by_strike.keys()))
        sigmas  = np.array([float(np.mean(by_strike[K])) for K in strikes])

        try:
            sigmas_work = sigmas.copy()
            corrected_set: dict[float, float] = {}

            calib  = cls(F=float(F), T=time_to_expiry, beta=0.5)
            result = calib.fit(strikes, sigmas_work)

            for _ in range(len(strikes)):
                anoms = calib.anomalies(threshold=anomaly_threshold)
                if not anoms:
                    break

                worst = anoms[0]
                K_bad = worst["strike"]
                idx   = np.argmin(np.abs(strikes - K_bad))

                corrected_set[round(K_bad, 4)] = sigmas_work[idx]
                sigmas_work[idx] = worst["sigma_model"]

                if len(strikes) < 3:
                    break
                calib  = cls(F=float(F), T=time_to_expiry, beta=0.5)
                result = calib.fit(strikes, sigmas_work)

            for opt in options:
                if opt.strike <= 0:
                    continue
                opt.sabr_volatility = SABRCalibration.vol(
                    float(F), opt.strike, time_to_expiry,
                    result.alpha, result.beta, result.rho, result.nu,
                )
                if opt.implied_volatility > 0:
                    K_rounded = round(opt.strike, 4)
                    if K_rounded in corrected_set:
                        opt.sabr_is_anomaly    = True
                        opt.sabr_corrected     = True
                        opt.implied_volatility = opt.sabr_volatility
                        opt.sabr_residual      = 0.0
                        opt.sabr_z_score       = 0.0
                        opt.premium = Bachelier(
                            float(F), opt.strike, opt.sabr_volatility,
                            time_to_expiry, opt.is_call(),
                        ).price()
                    else:
                        opt.sabr_is_anomaly = False
                        opt.sabr_corrected  = False
                        opt.sabr_residual   = opt.implied_volatility - opt.sabr_volatility
                        opt.sabr_z_score    = (
                            abs(opt.sabr_residual) / result.rmse if result.rmse > 0 else 0.0
                        )
                else:
                    opt.sabr_residual   = 0.0
                    opt.sabr_z_score    = 0.0
                    opt.sabr_is_anomaly = False
                    opt.sabr_corrected  = False

            return calib

        except Exception as e:
            print(f"[SABR] Erreur de calibration : {e}")
            import traceback
            traceback.print_exc()
            return None


# ============================================================================
# Aliases module-level (compatibilité avec __init__.py et code existant)
# ============================================================================

def sabr_lognormal_vol(F, K, T, alpha, beta, rho, nu):          return SABRCalibration.lognormal_vol(F, K, T, alpha, beta, rho, nu)
def sabr_normal_vol(F, K, T, alpha, beta, rho, nu):             return SABRCalibration.normal_vol(F, K, T, alpha, beta, rho, nu)
def sabr_vol(F, K, T, alpha, beta, rho, nu, vol_type="normal"): return SABRCalibration.vol(F, K, T, alpha, beta, rho, nu, vol_type)
def compute_sabr_volatility(options, time_to_expiry=0.25, future_price=None, anomaly_threshold=1.5): return SABRCalibration.compute_volatility(options, time_to_expiry, future_price, anomaly_threshold)
