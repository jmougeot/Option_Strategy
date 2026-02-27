"""
Module SABR — Calibration et détection d'anomalies
====================================================
Implémente le modèle SABR (Hagan et al. 2002) en volatilité normale (Bachelier)
adapté aux taux d'intérêt (SOFR, SFR futures), où les prix tournent autour de 95-97.

Référence :
    Hagan, P.S., Kumar, D., Lesniewski, A.S., Woodward, D.E. (2002).
    "Managing Smile Risk". Wilmott Magazine, Sept. 2002.

Notations
---------
    F     : prix forward du sous-jacent
    K     : strike
    T     : temps à l'expiration (années)
    alpha : volatilité forward (σ₀ dans la littérature)
    beta  : exposant CEV (0 = pure normal, 1 = log-normal)
    rho   : corrélation entre F et vol (−1 < ρ < 1)
    nu    : vol-of-vol (ν > 0)

Usage typique
-------------
    from myproject.option.sabr import SABRCalibration

    calib = SABRCalibration(F=96.0, T=0.25, beta=0.0)
    result = calib.fit(strikes, implied_normal_vols)

    print(calib.summary())
    anomalies = calib.anomalies(threshold=2.0)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import differential_evolution, minimize


# ============================================================================
# FORMULES SABR
# ============================================================================

def sabr_lognormal_vol(
    F: float, K: float, T: float,
    alpha: float, beta: float, rho: float, nu: float,
) -> float:
    """
    Volatilité lognormale (Black) selon Hagan et al. 2002, éq. (2.17b).
    """
    # Garde fou
    if T <= 0:
        return alpha
    if K <= 0 or F <= 0:
        return 1e-8

    eps = 1e-7

    # Approximation ATM 
    if abs(F - K) < eps:
        FK_beta = F ** (1.0 - beta)
        atm_correction = (
            (1 - beta) ** 2 / 24.0 * alpha ** 2 / FK_beta ** 2
            + rho * beta * nu * alpha / (4.0 * F ** (1.0 - beta))
            + (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
        )
        return alpha / FK_beta * (1.0 + atm_correction * T)

    # Terme de base pour la formule
    log_FK = np.log(F / K)
    FK_mid = np.sqrt(F * K)
    FK_beta = FK_mid ** (1.0 - beta)

    # Série en log(F/K)
    log2 = log_FK ** 2
    log4 = log_FK ** 4
    A_exp = 1.0 + (1.0 - beta) ** 2 / 24.0 * log2 + (1.0 - beta) ** 4 / 1920.0 * log4

    # Facteur z / χ(z)
    z = nu / alpha * FK_beta * log_FK
    sqrt_disc = np.sqrt(1.0 - 2.0 * rho * z + z ** 2)
    chi = np.log((sqrt_disc + z - rho) / (1.0 - rho))
    z_chi = z / chi if abs(chi) > eps else 1.0

    # Correction temporelle
    time_corr = (
        (1.0 - beta) ** 2 / 24.0 * alpha ** 2 / FK_beta ** 2
        + rho * beta * nu * alpha / (4.0 * FK_beta)
        + (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
    )

    sigma_B = alpha / (FK_beta * A_exp) * z_chi * (1.0 + time_corr * T)
    return max(sigma_B, 1e-8)


def sabr_normal_vol(
    F: float, K: float, T: float,
    alpha: float, beta: float, rho: float, nu: float,
) -> float:
    """
    Volatilité normale (Bachelier) selon SABR.
    """
    if T <= 0:
        return alpha
    if alpha <= 0:
        return 1e-8

    eps = 1e-7

    # ── Cas pur normal (beta = 0) : formule exacte ───────────────────────────
    if abs(beta) < eps:
        diff = F - K
        if abs(diff) < eps:
            # ATM
            atm_corr = (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
            return alpha * (1.0 + atm_corr * T)
        else:
            z = nu / alpha * diff
            sqrt_disc = np.sqrt(1.0 - 2.0 * rho * z + z ** 2)
            chi = np.log((sqrt_disc + z - rho) / (1.0 - rho))
            z_chi = z / chi if abs(chi) > eps else 1.0
            atm_corr = (2.0 - 3.0 * rho ** 2) / 24.0 * nu ** 2
            return alpha * z_chi * (1.0 + atm_corr * T)

    # ── Cas général (beta ≠ 0) : conversion lognormal → normal ──────────────
    sigma_B = sabr_lognormal_vol(F, K, T, alpha, beta, rho, nu)
    FK_mid = np.sqrt(F * K)
    log2 = np.log(F / K) ** 2 if abs(F - K) > eps else 0.0
    A_exp = 1.0 + (1.0 - beta) ** 2 / 24.0 * log2
    sigma_N = sigma_B * FK_mid ** beta * A_exp
    return max(sigma_N, 1e-8)


def sabr_vol(
    F: float, K: float, T: float,
    alpha: float, beta: float, rho: float, nu: float,
    vol_type: str = "normal",
) -> float:
    """
    Interface unifiée : renvoie la vol SABR lognormale ou normale.
    """
    if vol_type == "lognormal":
        return sabr_lognormal_vol(F, K, T, alpha, beta, rho, nu)
    return sabr_normal_vol(F, K, T, alpha, beta, rho, nu)


# ============================================================================
# RÉSIDU ET OBJECTIF D'OPTIMISATION
# ============================================================================

def _sabr_objective(
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
            [sabr_vol(F, K, T, alpha, beta, rho, nu, vol_type) for K in strikes]
        )
    except Exception:
        return 1e10

    if np.any(np.isnan(sigmas_model)) or np.any(sigmas_model <= 0):
        return 1e10

    errors = sigmas_mkt - sigmas_model
    return float(np.sum(weights * errors ** 2))


# ============================================================================
# CLASSE PRINCIPALE : SABRCalibration
# ============================================================================

@dataclass
class SABRResult:
    """Résultats de la calibration SABR."""
    alpha: float
    beta: float
    rho: float
    nu: float

    # Métriques de fit
    rmse: float = 0.0
    rmse_bps: float = 0.0          # RMSE en basis points (×10000)
    max_error_bps: float = 0.0

    # Données d'entrée
    strikes: np.ndarray = field(default_factory=lambda: np.array([]))
    sigmas_mkt: np.ndarray = field(default_factory=lambda: np.array([]))
    sigmas_model: np.ndarray = field(default_factory=lambda: np.array([]))
    residuals: np.ndarray = field(default_factory=lambda: np.array([]))

    # Info
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


class SABRCalibration:
    """
    Calibration SABR sur une surface de volatilités Bloomberg.
    """

    def __init__(
        self,
        F: float,
        T: float,
        beta: float = 0.0,
        vol_type: str = "normal",
    ):
        self.F = F
        self.T = T
        self.beta = beta
        self.vol_type = vol_type
        self.result: Optional[SABRResult] = None

    # ── Calibration ──────────────────────────────────────────────────────────

    def fit(
        self,
        strikes: np.ndarray,
        sigmas_mkt: np.ndarray,
        weights: Optional[Sequence[float]] = None,
        seed: int = 42,
    ) -> SABRResult:
        """
        Calibre les paramètres SABR (alpha, rho, nu) par moindres carrés pondérés.
        """
        strikes = np.asarray(strikes, dtype=float)
        sigmas_mkt = np.asarray(sigmas_mkt, dtype=float)

        # Filtrer les points valides
        valid = (sigmas_mkt > 0) & np.isfinite(sigmas_mkt) & np.isfinite(strikes)
        if valid.sum() < 3:
            raise ValueError(f"Pas assez de points valides pour calibrer SABR ")
        strikes = strikes[valid]
        sigmas_mkt = sigmas_mkt[valid]

        # Pondérations : plus fort autour de l'ATM (proxy de vega gaussien)
        if weights is None:
            moneyness = np.abs(strikes - self.F)
            w = np.exp(-0.5 * (moneyness / (0.5 * moneyness.std() + 1e-8)) ** 2)
            w = w / w.sum()
        else:
            w = np.asarray(weights, dtype=float)[valid]
            w = w / w.sum()

        # ── 1. Initialisation heuristique ────────────────────────────────
        atm_idx = np.argmin(np.abs(strikes - self.F))
        sigma_atm = sigmas_mkt[atm_idx]
        alpha0 = sigma_atm   # pour beta=0, alpha ≈ sigma_ATM

        # ── 2. Optimisation globale (robustesse) ─────────────────────────
        bounds = [
            (1e-6, sigma_atm * 5),   #
            (-0.99, 0.99),            
            (1e-4, 5.0),             
        ]

        result_de = differential_evolution(
            _sabr_objective,
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

        best_params = result_de.x if result_de.success else np.array([alpha0, -0.1, 0.5])

        # ── 3. Raffinement local ─────────────────────────────────────────
        result_loc = minimize(
            _sabr_objective,
            best_params,
            args=(strikes, sigmas_mkt, self.F, self.T, self.beta, w, self.vol_type),
            method="L-BFGS-B",
            bounds=bounds,
            options={"ftol": 1e-14, "gtol": 1e-10, "maxiter": 5000},
        )

        alpha, rho, nu = result_loc.x
        converged = result_loc.success or result_de.success

        # ── 4. Calcul des résidus ────────────────────────────────────────
        sigmas_model = np.array([
            sabr_vol(self.F, K, self.T, alpha, self.beta, rho, nu, self.vol_type)
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

    # ── Évaluation ───────────────────────────────────────────────────────────

    def predict(self, strikes: Sequence[float]) -> np.ndarray:
        """
        Retourne la surface SABR calibrée pour un vecteur de strikes.
        """
        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result
        return np.array([
            sabr_vol(self.F, K, self.T, r.alpha, r.beta, r.rho, r.nu, self.vol_type)
            for K in strikes
        ])

    # ── Détection d'anomalies ─────────────────────────────────────────────────

    def anomalies(
        self,
        threshold: float = 1.5,
        min_error_bps: float = 0.5,
    ) -> List[Dict]:
        """
        Retourne les points dont |résidu| > threshold×RMSE  OU  |résidu| > min_error_bps bp.
        Triés par résidu décroissant.
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

    # ── Résumé ───────────────────────────────────────────────────────────────

    def summary(self) -> str:
        """Affiche un résumé formaté de la calibration."""
        if self.result is None:
            return "SABRCalibration : non calibree"
        r = self.result
        lines = [
            "=" * 52,
            "         SABR Calibration Summary",
            "=" * 52,
            f"  Forward      F  = {r.F:.4f}",
            f"  Maturite     T  = {r.T:.4f} ans",
            f"  Vol-type        = {self.vol_type}",
            "-" * 52,
            f"  alpha (s0)   = {r.alpha:.6f}",
            f"  beta         = {r.beta:.2f}  (fixe)",
            f"  rho    (rho) = {r.rho:.4f}",
            f"  nu     (nu)  = {r.nu:.6f}",
            "-" * 52,
            f"  RMSE         = {r.rmse_bps:.2f} bp",
            f"  Max |erreur| = {r.max_error_bps:.2f} bp",
            f"  Points       = {r.n_points}",
            f"  Converge     = {r.converged}",
            "-" * 52,
        ]

        anom = self.anomalies()
        if anom:
            lines.append(f"  /!\\ {len(anom)} anomalie(s) detectee(s) :")
            for a in anom:
                lines.append(
                    f"     K={a['strike']:.4f}  mkt={a['sigma_mkt']*1e4:.1f}bp  "
                    f"model={a['sigma_model']*1e4:.1f}bp  "
                    f"D={a['residual_bps']:+.1f}bp  ({a['direction']})"
                )
        else:
            lines.append("  OK  Aucune anomalie detectee")

        return "\n".join(lines)

    # ── Visualisation ────────────────────────────────────────────────────────

    def plot(
        self,
        n_interp: int = 200,
        title: Optional[str] = None,
        ax=None,
        anomaly_threshold: float = 1.5,
        show: bool = True,
    ):
        """
        Trace le smile Bloomberg vs la courbe SABR calibrée.
        Surligne en rouge les points aberrants.

        Parameters
        ----------
        n_interp          : nombre de points pour la courbe SABR continue
        title             : titre personnalisé
        ax                : axes matplotlib existants (None = nouveau)
        anomaly_threshold : z-score pour colorier les outliers
        show              : appeler plt.show() (False si intégré dans une UI)

        Returns
        -------
        (fig, ax) ou ax si ax passé en argument
        """
        import matplotlib.pyplot as plt

        if self.result is None:
            raise RuntimeError("Calibrer d'abord avec .fit()")
        r = self.result

        new_fig = ax is None
        if new_fig:
            fig, ax = plt.subplots(figsize=(10, 6))
        else:
            fig = ax.get_figure()

        # Courbe SABR continue
        k_range = np.linspace(r.strikes.min() * 0.999, r.strikes.max() * 1.001, n_interp)
        sabr_curve = self.predict(k_range)
        ax.plot(k_range, sabr_curve * 1e4, "b-", linewidth=2, label="SABR calibré", zorder=3)

        # Points marché — normal vs anomalie
        anom_strikes = {a["strike"] for a in self.anomalies(anomaly_threshold)}

        normal_mask = np.array([K not in anom_strikes for K in r.strikes])
        anom_mask = ~normal_mask

        if normal_mask.any():
            ax.scatter(
                r.strikes[normal_mask],
                r.sigmas_mkt[normal_mask] * 1e4,
                color="steelblue", s=60, zorder=5, label="Vol Bloomberg",
            )

        if anom_mask.any():
            ax.scatter(
                r.strikes[anom_mask],
                r.sigmas_mkt[anom_mask] * 1e4,
                color="red", s=100, marker="D", zorder=6, label="Anomalie Bloomberg",
            )
            for K, s_mkt in zip(r.strikes[anom_mask], r.sigmas_mkt[anom_mask]):
                ax.annotate(
                    f"K={K:.3f}\n{s_mkt*1e4:.1f}bp",
                    xy=(K, s_mkt * 1e4),
                    xytext=(6, 6),
                    textcoords="offset points",
                    fontsize=8,
                    color="red",
                )

        # Ligne du forward ATM
        ax.axvline(self.F, color="gray", linestyle="--", linewidth=1,
                   alpha=0.6, label=f"ATM F={self.F:.3f}")

        # Mise en forme
        ax.set_xlabel("Strike", fontsize=11)
        y_label = "Volatilité normale (bp)" if self.vol_type == "normal" else "Volatilité lognormale (%)"
        ax.set_ylabel(y_label, fontsize=11)
        plot_title = title or (
            f"Smile SABR  |  F={self.F:.4f}  T={self.T:.3f}a  "
            f"β={r.beta:.1f}  ρ={r.rho:.3f}  ν={r.nu:.4f}  "
            f"RMSE={r.rmse_bps:.2f}bp"
        )
        ax.set_title(plot_title, fontsize=12)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

        if new_fig and show:
            plt.tight_layout()
            plt.show()

        return (fig, ax) if new_fig else ax

    def plot_residuals(self, ax=None, show: bool = True):
        """
        Barplot des résidus (vol_mkt − vol_SABR) en basis points.
        """
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

        ax.bar(range(len(r.strikes)), res_bps, color=colors,
               edgecolor="white", linewidth=0.5)
        ax.axhline(0, color="black", linewidth=1)
        ax.axhline(r.rmse_bps, color="orange", linestyle="--",
                   alpha=0.8, label=f"+RMSE = {r.rmse_bps:.1f}bp")
        ax.axhline(-r.rmse_bps, color="orange", linestyle="--",
                   alpha=0.8, label=f"−RMSE = {r.rmse_bps:.1f}bp")

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


# ============================================================================
# HELPERS : extraction depuis les objets Option Bloomberg
# ============================================================================

def sabr_from_options(
    options,
    F: Optional[float] = None,
    T: float = 0.25,
    beta: float = 0.0,
    min_iv: float = 1e-6,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Extrait (strikes, implied_vols, F) depuis une liste d'objets Option Bloomberg.

    Parameters
    ----------
    options : List[Option] — options (calls ou puts, même expiry)
    F       : forward override (si None, déduit de underlying_price)
    T       : temps à expiration en années (informatif)
    beta    : inutilisé ici, transmis en retour
    min_iv  : filtre les vols implicites sous ce seuil

    Returns
    -------
    (strikes, implied_vols, F) prêts pour SABRCalibration.fit()
    """
    from myproject.option.option_class import Option

    valid_options = [
        o for o in options
        if isinstance(o, Option)
        and o.implied_volatility > min_iv
        and o.strike > 0
    ]

    if not valid_options:
        raise ValueError("Aucune option valide dans la liste fournie.")

    strikes = np.array([o.strike for o in valid_options])
    ivs = np.array([o.implied_volatility for o in valid_options])

    order = np.argsort(strikes)
    strikes = strikes[order]
    ivs = ivs[order]

    if F is None:
        prices = [
            o.underlying_price for o in valid_options
            if o.underlying_price and o.underlying_price > 0
        ]
        F = float(np.median(prices)) if prices else float(np.median(strikes))

    return strikes, ivs, F


def calibrate_from_options(
    options,
    F: Optional[float] = None,
    T: float = 0.25,
    beta: float = 0.0,
    anomaly_threshold: float = 1.5,
    plot: bool = True,
) -> Tuple["SABRCalibration", SABRResult, List[Dict]]:
    """
    Pipeline complet : extrait les données Bloomberg → calibre SABR → détecte anomalies.

    Parameters
    ----------
    options            : List[Option] — options importées depuis Bloomberg
    F                  : forward override (None = auto-détecté depuis underlying_price)
    T                  : temps à expiration en années
    beta               : exposant CEV (0 = pure normal, adapté aux taux)
    anomaly_threshold  : multiplicateur de RMSE pour signaler une anomalie
    plot               : afficher le smile SABR + résidus

    Returns
    -------
    (calib, result, anomalies)
        calib     : SABRCalibration — instance calibrée
        result    : SABRResult — paramètres + métriques
        anomalies : List[Dict] — points aberrants détectés

    Exemple
    -------
    >>> from myproject.option.sabr import calibrate_from_options
    >>> calib, result, anoms = calibrate_from_options(options, F=96.25, T=0.25)
    >>> for a in anoms:
    ...     print(a)
    """
    strikes, ivs, F_auto = sabr_from_options(options, F=F, T=T, beta=beta)
    F_used = F if F is not None else F_auto

    calib = SABRCalibration(F=F_used, T=T, beta=beta)
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
