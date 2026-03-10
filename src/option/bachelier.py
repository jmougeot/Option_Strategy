# ===============================================================
# Module qui encadre tout l'utilisation du modèle de bachelier
# ===============================================================


import numpy as np
from collections import defaultdict
from scipy.stats import norm
from scipy.optimize import brentq
from scipy.interpolate import CubicSpline as CS
from typing import Any, Dict, Optional, List, Tuple
from option.option_class import Option
from option.sabr import SABRCalibration

class Bachelier:
    """
    Modèle de Bachelier (normal model) pour la valorisation d'options.
    """

    def __init__(
        self,
        F: float,
        K: float,
        sigma: float,
        T: float,
        is_call: bool,
        market_price: Optional[float] = None,
    ) -> None:
        self.F = F
        self.K = K
        self.sigma = sigma
        self.T = T
        self.is_call = is_call
        self.market_price = market_price

    # ------------------------------------------------------------------
    # Prix
    # ------------------------------------------------------------------

    def price(self) -> float:
        """Calcule le prix via le modèle de Bachelier (normal model)."""
        if self.T <= 0:
            return max(self.F - self.K, 0.0) if self.is_call else max(self.K - self.F, 0.0)

        if self.sigma <= 0:
            return max(self.F - self.K, 0.0) if self.is_call else max(self.K - self.F, 0.0)

        sigma_sqrt_T = self.sigma * np.sqrt(self.T)
        d = (self.F - self.K) / sigma_sqrt_T

        if self.is_call:
            p = (self.F - self.K) * norm.cdf(d) + sigma_sqrt_T * norm.pdf(d)
        else:
            p = (self.K - self.F) * norm.cdf(-d) + sigma_sqrt_T * norm.pdf(d)

        return float(max(p, 0.0))

    # ------------------------------------------------------------------
    # Volatilité implicite
    # ------------------------------------------------------------------

    def implied_vol(self) -> float:
        """
        Calcule la volatilité normale implicite via le modèle de Bachelier.
        Résout: price(sigma) = market_price.
        """
        if self.market_price is None:
            raise ValueError("market_price doit être renseigné pour calculer la vol implicite.")

        if self.T <= 0 or self.market_price <= 0:
            return 0.0

        intrinsic = (
            max(self.F - self.K, 0.0) if self.is_call else max(self.K - self.F, 0.0)
        )
        if self.market_price <= intrinsic + 1e-10:
            return 0.0

        def objective(sigma: float) -> float:
            return Bachelier(self.F, self.K, sigma, self.T, self.is_call).price() - self.market_price  # type: ignore[operator]

        try:
            max_vol = self.market_price * np.sqrt(2 * np.pi / self.T) * 10
            vol = brentq(objective, 1e-8, max(max_vol, 1000.0), xtol=1e-10, maxiter=200)
            return float(vol)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Grecques
    # ------------------------------------------------------------------

    def delta(self) -> float:
        """Calcule le delta via le modèle de Bachelier."""
        if self.T <= 0 or self.sigma <= 0:
            if self.is_call:
                return 1.0 if self.F > self.K else 0.0
            else:
                return -1.0 if self.F < self.K else 0.0

        d = (self.F - self.K) / (self.sigma * np.sqrt(self.T))
        return float(norm.cdf(d)) if self.is_call else float(norm.cdf(d) - 1.0)

    def gamma(self) -> float:
        """Calcule le gamma via le modèle de Bachelier."""
        if self.T <= 0 or self.sigma <= 0:
            return 0.0

        sigma_sqrt_T = self.sigma * np.sqrt(self.T)
        d = (self.F - self.K) / sigma_sqrt_T
        return float(norm.pdf(d) / sigma_sqrt_T)

    def theta(self) -> float:
        """Calcule le theta via le modèle de Bachelier (par jour calendaire)."""
        if self.T <= 0 or self.sigma <= 0:
            return 0.0

        sigma_sqrt_T = self.sigma * np.sqrt(self.T)
        d = (self.F - self.K) / sigma_sqrt_T
        theta_annual = -self.sigma * norm.pdf(d) / (2.0 * np.sqrt(self.T))
        days_to_expiry = self.T * 365.0
        return float(theta_annual / days_to_expiry)


    # ------------------------------------------------------------------
    # Calcul des volatilités pour une liste d'options
    # ------------------------------------------------------------------

    @staticmethod
    def compute_volatility(
        options: List[Option],
        time_to_expiry: float = 0.25,
        future_price: Optional[float] = None,
    ) -> Optional[Any]:
        """
        Calcule la volatilité Bachelier (+ grecques) via calibration SABR.
        Poids de calibration basés sur le spread bid-ask (plus le spread est
        grand, plus le poids est faible ; pas de prix → poids 0).
        Returns the fitted SABRCalibration object, or None if calibration failed.
        """
        if not future_price:
            return None

        F = future_price
        T = time_to_expiry

        # ── 1. Calcul IV individuelle ────────────────────────────────────────
        grouped_by_strike: Dict[float, Dict[str, List[Option]]] = defaultdict(
            lambda: {"call": [], "put": []}
        )
        for opt in options:
            opt.underlying_price = F
            opt.implied_volatility = (
                Bachelier(F, opt.strike, 0.0, T, opt.is_call(), opt.premium).implied_vol()
                if opt.status and opt.premium > 0
                else 0.0
            )

            strike_key = round(opt.strike, 6)
            grouped_by_strike[strike_key]["call" if opt.is_call() else "put"].append(opt)

        datas: List[Tuple[float, List[Option], List[Option]]] = []
        for strike_key in sorted(grouped_by_strike):
            strike_group = grouped_by_strike[strike_key]
            calls = strike_group["call"]
            puts = strike_group["put"]
            if not calls and not puts:
                continue

            strike = calls[0].strike if calls else puts[0].strike
            datas.append((strike, calls, puts))

        n = len(datas)
        if n == 0:
            return

        # ── 2. Fusion call+put → iv_merged + poids bid-ask ────────────────
        iv_merged: List[float] = []
        ba_weights: List[float] = []

        for _, calls, puts in datas:
            call_ivs = [opt.implied_volatility for opt in calls if opt.implied_volatility > 0]
            put_ivs = [opt.implied_volatility for opt in puts if opt.implied_volatility > 0]
            ic = float(sum(call_ivs) / len(call_ivs)) if call_ivs else 0.0
            ip = float(sum(put_ivs) / len(put_ivs)) if put_ivs else 0.0
            if ic > 0 and ip > 0:
                iv_merged.append((ic + ip) / 2.0)
            elif ic > 0:
                iv_merged.append(ic)
            elif ip > 0:
                iv_merged.append(ip)
            else:
                iv_merged.append(0.0)

            # Poids basé sur le spread bid-ask : grand spread → faible poids
            if iv_merged[-1] <= 0:
                ba_weights.append(0.0)
            else:
                spreads = []
                for opt in calls + puts:
                    if (opt.bid is not None and opt.ask is not None
                            and opt.ask >= opt.bid >= 0):
                        spreads.append(opt.ask - opt.bid)
                if spreads:
                    avg_spread = sum(spreads) / len(spreads)
                    ba_weights.append(1.0 / (1.0 + avg_spread))
                else:
                    ba_weights.append(1.0)  # prix dispo mais pas de bid/ask

        # ── 3. Calibration SABR avec poids bid-ask ───────────────────────────

        strikes_arr = np.array([d[0] for d in datas])
        iv_arr = np.array(iv_merged)
        w_arr = np.array(ba_weights)

        sabr = SABRCalibration(F=F, T=T, beta=0.0, vol_type="normal")
        sabr_ok = False

        if (iv_arr > 0).sum() >= 3:
            try:
                sabr.fit(strikes=strikes_arr, sigmas_mkt=iv_arr, weights=w_arr)
                sabr_ok = True
                print(f"  SABR calibré : {sabr.result}")
            except Exception as exc:
                print(f"  SABR calibration échouée : {exc}")

        # ── 4. Appliquer les IV (SABR si calibré, sinon marché) ─────────────
        if sabr_ok:
            all_sabr_vols = sabr.predict(strikes_arr)
            final_ivs = [max(float(v), 0.0) for v in all_sabr_vols]
        else:
            final_ivs = iv_merged

        for i, (_, calls, puts) in enumerate(datas):
            iv = final_ivs[i]
            mkt_iv = iv_merged[i]
            for opt in calls + puts:
                opt.market_implied_volatility = mkt_iv
                opt.sabr_volatility = iv if sabr_ok else 0.0
                if iv > 0:
                    opt.implied_volatility = iv
                    # Reconstruire le premium seulement s'il manque
                    if not (opt.status and opt.premium > 0):
                        opt.sabr_corrected = True
                        opt.premium = Bachelier(F, opt.strike, iv, T, opt.is_call()).price()
                    opt.delta = Bachelier(F, opt.strike, iv, T, opt.is_call()).delta()
                    opt.gamma = Bachelier(F, opt.strike, iv, T, opt.is_call()).gamma()
                    opt.theta = Bachelier(F, opt.strike, iv, T, opt.is_call()).theta()

        return sabr if sabr_ok else None