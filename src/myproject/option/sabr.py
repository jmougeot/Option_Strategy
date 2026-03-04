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
        """Volatilité normale (Bachelier) selon SABR."""
        if T <= 0:
            return alpha
        if alpha <= 0:
            return 1e-8

        eps = 1e-7

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

        sigma_B = SABRCalibration.lognormal_vol(F, K, T, alpha, beta, rho, nu)
        FK_mid = np.sqrt(F * K)
        log2 = np.log(F / K) ** 2 if abs(F - K) > eps else 0.0
        A_exp = 1.0 + (1.0 - beta) ** 2 / 24.0 * log2
        sigma_N = sigma_B * FK_mid ** beta * A_exp
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
    # Visualisation
    # ------------------------------------------------------------------

    def plot(
        self,
        n_interp: int = 200,
        title: Optional[str] = None,
        ax=None,
        anomaly_threshold: float = 1.5,
        show: bool = True,
    ):
        """Trace le smile Bloomberg vs la courbe SABR. Surligne les anomalies en rouge."""
        import matplotlib.pyplot as plt

        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result

        new_fig = ax is None
        if new_fig:
            fig, ax = plt.subplots(figsize=(10, 6))
        else:
            fig = ax.get_figure()

        k_range = np.linspace(r.strikes.min() * 0.999, r.strikes.max() * 1.001, n_interp)
        ax.plot(k_range, self.predict(k_range) * 1e4, "b-", linewidth=2, label="SABR calibré", zorder=3)

        anom_strikes = {a["strike"] for a in self.anomalies(anomaly_threshold)}
        normal_mask = np.array([K not in anom_strikes for K in r.strikes])
        anom_mask = ~normal_mask

        if normal_mask.any():
            ax.scatter(r.strikes[normal_mask], r.sigmas_mkt[normal_mask] * 1e4,
                       color="steelblue", s=60, zorder=5, label="Vol Bloomberg")
        if anom_mask.any():
            ax.scatter(r.strikes[anom_mask], r.sigmas_mkt[anom_mask] * 1e4,
                       color="red", s=100, marker="D", zorder=6, label="Anomalie Bloomberg")
            for K, s_mkt in zip(r.strikes[anom_mask], r.sigmas_mkt[anom_mask]):
                ax.annotate(f"K={K:.3f}\n{s_mkt*1e4:.1f}bp",
                            xy=(K, s_mkt * 1e4), xytext=(6, 6),
                            textcoords="offset points", fontsize=8, color="red")

        ax.axvline(self.F, color="gray", linestyle="--", linewidth=1,
                   alpha=0.6, label=f"ATM F={self.F:.3f}")
        ax.set_xlabel("Strike", fontsize=11)
        ax.set_ylabel(
            "Volatilité normale (bp)" if self.vol_type == "normal" else "Volatilité lognormale (%)",
            fontsize=11,
        )
        ax.set_title(title or (
            f"Smile SABR  |  F={self.F:.4f}  T={self.T:.3f}a  "
            f"β={r.beta:.1f}  ρ={r.rho:.3f}  ν={r.nu:.4f}  RMSE={r.rmse_bps:.2f}bp"
        ), fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        if new_fig and show:
            plt.tight_layout()
            plt.show()

        return (fig, ax) if new_fig else ax

    def plot_residuals(self, ax=None, show: bool = True):
        """Barplot des résidus (vol_mkt − vol_SABR) en basis points."""
        import matplotlib.pyplot as plt

        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result

        new_fig = ax is None
        if new_fig:
            fig, ax = plt.subplots(figsize=(9, 4))
        else:
            fig = ax.get_figure()

        anom_strikes = {a["strike"] for a in self.anomalies()}
        colors = ["red" if K in anom_strikes else "steelblue" for K in r.strikes]
        res_bps = r.residuals * 1e4

        ax.bar(range(len(r.strikes)), res_bps, color=colors, edgecolor="white", linewidth=0.5)
        ax.axhline(0, color="black", linewidth=1)
        ax.axhline( r.rmse_bps, color="orange", linestyle="--", alpha=0.8, label=f"+RMSE = {r.rmse_bps:.1f}bp")
        ax.axhline(-r.rmse_bps, color="orange", linestyle="--", alpha=0.8, label=f"−RMSE = {r.rmse_bps:.1f}bp")
        ax.set_xticks(range(len(r.strikes)))
        ax.set_xticklabels([f"{K:.3f}" for K in r.strikes], rotation=45, fontsize=8)
        ax.set_ylabel("Résidu (bp) = mkt − SABR", fontsize=10)
        ax.set_title("Résidus de calibration SABR", fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(True, axis="y", alpha=0.3)

        if new_fig and show:
            plt.tight_layout()
            plt.show()

        return (fig, ax) if new_fig else ax

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
        from myproject.option.option_class import Option

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

    @classmethod
    def calibrate(
        cls,
        options,
        F: Optional[float] = None,
        T: float = 0.25,
        beta: float = 0.0,
        anomaly_threshold: float = 1.5,
        plot: bool = True,
    ) -> Tuple["SABRCalibration", SABRResult, List[Dict]]:
        """
        Pipeline complet : extrait les données → calibre SABR → détecte anomalies.
        """
        strikes, ivs, F_auto = cls.from_options(options, F=F, T=T, beta=beta)
        F_used = F if F is not None else F_auto

        calib = cls(F=F_used, T=T, beta=beta)
        result = calib.fit(strikes, ivs)
        print(calib.summary())

        anoms = calib.anomalies(threshold=anomaly_threshold)

        if plot:
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(1, 2, figsize=(16, 6))
            calib.plot(ax=axes[0], show=False)
            calib.plot_residuals(ax=axes[1], show=False)
            plt.tight_layout()
            plt.show()

        return calib, result, anoms

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
        from myproject.option.bachelier import Bachelier

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

            calib  = cls(F=float(F), T=time_to_expiry, beta=0.0)
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
                calib  = cls(F=float(F), T=time_to_expiry, beta=0.0)
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
def sabr_from_options(options, F=None, T=0.25, beta=0.0, min_iv=1e-6): return SABRCalibration.from_options(options, F, T, beta, min_iv)
def calibrate_from_options(options, F=None, T=0.25, beta=0.0, anomaly_threshold=1.5, plot=True): return SABRCalibration.calibrate(options, F, T, beta, anomaly_threshold, plot)
def compute_sabr_volatility(options, time_to_expiry=0.25, future_price=None, anomaly_threshold=1.5): return SABRCalibration.compute_volatility(options, time_to_expiry, future_price, anomaly_threshold)