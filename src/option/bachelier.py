# ===============================================================
# Module qui encadre tout l'utilisation du modèle de bachelier
# ===============================================================


import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from scipy.interpolate import CubicSpline as CS
from typing import Optional, List, Tuple
from option.option_class import Option


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
    # Prix vectorisé
    # ------------------------------------------------------------------

    def price_vec(self, F_vec: np.ndarray) -> np.ndarray:
        """
        Version vectorisée : calcule les prix pour un array de prix forward F_vec,
        en conservant K, sigma, T et is_call de l'instance.
        """
        if self.T <= 0 or self.sigma <= 0:
            return np.maximum(F_vec - self.K, 0.0) if self.is_call else np.maximum(self.K - F_vec, 0.0)

        sigma_sqrt_T = self.sigma * np.sqrt(self.T)
        d = (F_vec - self.K) / sigma_sqrt_T

        if self.is_call:
            prices = (F_vec - self.K) * norm.cdf(d) + sigma_sqrt_T * norm.pdf(d)
        else:
            prices = (self.K - F_vec) * norm.cdf(-d) + sigma_sqrt_T * norm.pdf(d)

        return np.maximum(prices, 0.0)

    # ------------------------------------------------------------------
    # Densité risque-neutre (Breeden-Litzenberger)
    # ------------------------------------------------------------------

    @staticmethod
    def breeden_litzenberger_density(
        strikes: np.ndarray,
        call_prices: np.ndarray,
        price_grid: np.ndarray,
        risk_free_rate: float = 0.0,
        time_to_expiry: float = 1.0,
    ) -> Optional[np.ndarray]:
        """
        Extrait la densité risque-neutre q_T(K) via la formule de Breeden-Litzenberger.

        q_T(K) = e^{rT} * d²C/dK²
        """
        if len(strikes) < 4:
            return None

        sort_idx = np.argsort(strikes)
        K = strikes[sort_idx]
        C = call_prices[sort_idx]

        valid_mask = C > 0
        if np.sum(valid_mask) < 4:
            return None

        K = K[valid_mask]
        C = C[valid_mask]

        try:
            cs = CS(K, C)
            d2C_dK2 = cs(price_grid, 2)

            discount_factor = np.exp(risk_free_rate * time_to_expiry)
            q_T = discount_factor * d2C_dK2
            q_T = np.maximum(q_T, 0.0)

            dx = float(np.mean(np.diff(price_grid))) if len(price_grid) > 1 else 1.0
            total_mass = np.sum(q_T) * dx
            if total_mass > 1e-10:
                q_T = q_T / total_mass
            else:
                return None

            return q_T

        except Exception as e:
            print(f"Erreur Breeden-Litzenberger: {e}")
            return None

    # ------------------------------------------------------------------
    # Calcul des volatilités pour une liste d'options
    # ------------------------------------------------------------------

    @staticmethod
    def compute_volatility(
        options: List[Option],
        time_to_expiry: float = 0.25,
        future_price: Optional[float] = None,
    ) -> None:
        """
        Calcule la volatilité Bachelier (+ grecques) via calibration SABR.
        Poids de calibration basés sur le spread bid-ask (plus le spread est
        grand, plus le poids est faible ; pas de prix → poids 0).
        """
        if not future_price:
            return

        F = future_price
        T = time_to_expiry

        options.sort(key=lambda x: (x.strike, x.option_type))

        # ── 1. Calcul IV individuelle ────────────────────────────────────────
        datas: List[Tuple[float, Option, Option]] = []
        for j in range(len(options) // 2):
            call = options[2 * j]
            put  = options[2 * j + 1]
            call.underlying_price = F
            put.underlying_price  = F

            call.implied_volatility = (
                Bachelier(F, call.strike, 0.0, T, True, call.premium).implied_vol()
                if call.status and call.premium > 0
                else 0.0
            )
            put.implied_volatility = (
                Bachelier(F, put.strike, 0.0, T, False, put.premium).implied_vol()
                if put.status and put.premium > 0
                else 0.0
            )

            datas.append((call.strike, call, put))

        n = len(datas)
        if n == 0:
            return

        # ── 2. Fusion call+put → iv_merged + poids bid-ask ────────────────
        IV_DIVERGENCE_THRESHOLD = 0.30

        def _neighbor_avg(iv_list: List[float], idx: int) -> Optional[float]:
            neighbors = [iv_list[j] for j in (idx - 1, idx + 1) if 0 <= j < n and iv_list[j] > 0]
            return sum(neighbors) / len(neighbors) if neighbors else None

        iv_c = [d[1].implied_volatility for d in datas]
        iv_p = [d[2].implied_volatility for d in datas]
        iv_merged: List[float] = []
        ba_weights: List[float] = []

        for i, (_, call, put) in enumerate(datas):
            ic, ip = iv_c[i], iv_p[i]
            if ic > 0 and ip > 0:
                if abs(ic - ip) <= IV_DIVERGENCE_THRESHOLD:
                    iv_merged.append((ic + ip) / 2.0)
                else:
                    err_c = abs(ic - _neighbor_avg(iv_c, i)) if _neighbor_avg(iv_c, i) is not None else float("inf")
                    err_p = abs(ip - _neighbor_avg(iv_p, i)) if _neighbor_avg(iv_p, i) is not None else float("inf")
                    if err_c <= err_p:
                        put.status = False
                        put.implied_volatility = 0.0
                        iv_merged.append(ic)
                    else:
                        call.status = False
                        call.implied_volatility = 0.0
                        iv_merged.append(ip)
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
                for opt in (call, put):
                    if (opt.bid is not None and opt.ask is not None
                            and opt.ask >= opt.bid >= 0):
                        spreads.append(opt.ask - opt.bid)
                if spreads:
                    avg_spread = sum(spreads) / len(spreads)
                    ba_weights.append(1.0 / (1.0 + avg_spread))
                else:
                    ba_weights.append(1.0)  # prix dispo mais pas de bid/ask

        # ── 3. Calibration SABR avec poids bid-ask ───────────────────────────
        from option.sabr import SABRCalibration

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

        # ── 4. Application SABR → IV, premium, grecques ──────────────────────
        if sabr_ok:
            all_sabr_vols = sabr.predict(strikes_arr)
            for i, (_, call, put) in enumerate(datas):
                iv = max(float(all_sabr_vols[i]), 0.0)
                mkt_iv = iv_merged[i]
                for opt in (call, put):
                    opt.market_implied_volatility = mkt_iv
                    opt.sabr_volatility = iv
                    opt.sabr_residual = (mkt_iv - iv) if mkt_iv > 0 else 0.0
                    opt.sabr_z_score = (
                        abs(opt.sabr_residual) / max(sabr.result.rmse, 1e-10)
                        if mkt_iv > 0 else 0.0
                    )
                    if iv > 0:
                        opt.implied_volatility = iv
                        opt.sabr_corrected = True
                        if not (opt.status and opt.premium > 0):
                            opt.premium = Bachelier(F, opt.strike, iv, T, opt.is_call()).price()
                            sym = "C" if opt.is_call() else "P"
                            print(f"  SABR → {sym} K={opt.strike}: IV={iv:.4f}  Premium={opt.premium:.6f}")
                        opt.delta = Bachelier(F, opt.strike, iv, T, opt.is_call()).delta()
                        opt.gamma = Bachelier(F, opt.strike, iv, T, opt.is_call()).gamma()
                        opt.theta = Bachelier(F, opt.strike, iv, T, opt.is_call()).theta()
        else:
            # Fallback : pas assez de points pour SABR, on garde les IV individuelles
            for i, (_, call, put) in enumerate(datas):
                iv = max(iv_merged[i], 0.0)
                for opt in (call, put):
                    opt.market_implied_volatility = iv
                    if iv > 0:
                        opt.implied_volatility = iv
                        if not (opt.status and opt.premium > 0):
                            opt.premium = Bachelier(F, opt.strike, iv, T, opt.is_call()).price()
                        opt.delta = Bachelier(F, opt.strike, iv, T, opt.is_call()).delta()
                        opt.gamma = Bachelier(F, opt.strike, iv, T, opt.is_call()).gamma()
                        opt.theta = Bachelier(F, opt.strike, iv, T, opt.is_call()).theta()