# ===============================================================
# Module qui encadre tout l'utilisation du modèle de bachelier
# ===============================================================


import numpy as np
from collections import defaultdict
from dataclasses import dataclass
from scipy.stats import norm
from scipy.optimize import brentq
from typing import Any, Dict, Optional, List, Tuple
from option.option_class import Option
from option.sabr import SABRCalibration


@dataclass
class CalibrationBundle:
    """Contient les résultats SABR et/ou SSVI d'une calibration."""
    sabr: Optional[Any] = None   # SABRCalibration | None
    ssvi: Optional[Any] = None   # SSVICalibration | None

    def predict(self, strikes) -> Any:
        """Prédit la vol modèle (moyenne si les deux, sinon celui dispo)."""
        import numpy as np
        if self.sabr is not None and self.ssvi is not None:
            return (np.array(self.sabr.predict(strikes)) + np.array(self.ssvi.predict(strikes))) / 2.0
        if self.sabr is not None:
            return self.sabr.predict(strikes)
        if self.ssvi is not None:
            return self.ssvi.predict(strikes)
        raise RuntimeError("CalibrationBundle vide")

    def summary(self) -> str:
        parts = []
        if self.sabr is not None and hasattr(self.sabr, "summary"):
            parts.append(self.sabr.summary())
        if self.ssvi is not None and hasattr(self.ssvi, "summary"):
            parts.append(self.ssvi.summary())
        return "\n".join(parts)

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
            vol: float = brentq(objective, 1e-8, max(max_vol, 1000.0), xtol=1e-10, maxiter=200)  # type: ignore[assignment]
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
    def find_anomaly(
    
    ):
        return

    @staticmethod
    def compute_weight(
        datas: List[Tuple[float, List[Option], List[Option]]],
        F: float,
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Le poids est calculé de cette manière :
          1. w_spread   : 1 / (1 + bid-ask spread)  — liquidité
          2. w_cp       : exp(-|iv_call - iv_put| / iv_mid)  — cohérence
                          call/put au même strike (grand écart → faible poids)
          3. w_moneyness: exp(-k * |strike - F| / F)  — proximité ATM
                          (loin de F → moins fiable)
        """
        strikes_obs: List[float] = []
        ivs_obs: List[float] = []
        weights_obs: List[float] = []

        # Coefficient de décroissance moneyness : exp(-3 * |K-F|/F)
        # → à 10% hors-la-monnaie le poids tombe à ~74%, à 30% il tombe à ~40%
        MONEYNESS_DECAY = 3.0

        for strike, calls, puts in datas:
            # ─ 1. IV moyen call vs put au même strike (pour facteur de cohérence) ─
            call_ivs = [iv for opt in calls if (iv := opt.implied_volatility) is not None and iv > 0]
            put_ivs  = [iv for opt in puts  if (iv := opt.implied_volatility) is not None and iv > 0]
            ic = sum(call_ivs) / len(call_ivs) if call_ivs else None
            ip = sum(put_ivs)  / len(put_ivs)  if put_ivs  else None

            if ic is not None and ip is not None:
                iv_mid = (ic + ip) / 2.0
                # Facteur de cohérence : ecart relatif call/put
                w_cp = float(np.exp(-abs(ic - ip) / iv_mid)) if iv_mid > 0 else 0.0
            else:
                w_cp = 1.0  # un seul côté disponible : pas de pénalité

            # ─ 2. Facteur de moneyness : diminue avec la distance au forward ─
            moneyness_dist = abs(strike - F) / F if F > 0 else 0.0
            w_moneyness = float(np.exp(-MONEYNESS_DECAY * moneyness_dist))

            # ─ 3. Poids par option ──────────────────────────────────────
            for opt in calls + puts:
                iv = opt.implied_volatility
                if iv is None or iv <= 0:
                    continue

                # Poids bid-ask
                if (opt.bid is not None and opt.ask is not None
                        and opt.ask >= opt.bid >= 0):
                    spread = opt.ask - opt.bid
                    w_spread = 1.0 / (1.0 + spread)
                else:
                    w_spread = 1.0

                w = w_spread * w_cp * w_moneyness

                strikes_obs.append(strike)
                ivs_obs.append(float(iv))
                weights_obs.append(w)

        return strikes_obs, ivs_obs, weights_obs

    @staticmethod
    def compute_volatility(
        options: List[Option],
        time_to_expiry: float = 0.25,
        future_price: Optional[float] = None,
        vol_model: str = "sabr",
    ) -> Optional[Any]:
        """
        Calcule la volatilité Bachelier (+ grecques) via calibration SABR ou SSVI.
        vol_model : "sabr" | "ssvi" | "both"
        Poids de calibration basés sur le spread bid-ask.
        Returns the fitted calibration object, or None if calibration failed.
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
                if opt.premium > 0
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


        # ── 2. Collecte des observations individuelles (call et put séparés) ──
        strikes_obs, ivs_obs, weights_obs = Bachelier.compute_weight(datas, F)

        if len(strikes_obs) == 0:
            return None

        # IV marché par strike (moyenne call+put) pour market_implied_volatility
        mkt_iv_by_strike: Dict[float, List[float]] = defaultdict(list)
        for k, iv in zip(strikes_obs, ivs_obs):
            mkt_iv_by_strike[k].append(iv)
        mkt_iv_map: Dict[float, float] = {
            k: sum(vs) / len(vs) for k, vs in mkt_iv_by_strike.items()
        }

        # ── 3. Calibration — SABR / SSVI / Both ──────────────────────────────
        strikes_np = np.array(strikes_obs, dtype=float)
        iv_np_arr = np.array(ivs_obs, dtype=float)
        run_sabr = vol_model in ("sabr", "both")
        run_ssvi = vol_model in ("ssvi", "both")

        sabr = SABRCalibration(F=F, T=T, beta=0.0, vol_type="normal")
        sabr_ok = False
        ssvi_ok = False
        ssvi = None

        if run_sabr and (iv_np_arr > 0).sum() >= 3:
            try:
                sabr.fit(strikes=strikes_np, sigmas_mkt=iv_np_arr, weights=weights_obs)
                sabr_ok = True
                print(f"  SABR calibré : {sabr.result}")
            except Exception as exc:
                print(f"  SABR calibration échouée : {exc}")

        if run_ssvi and (iv_np_arr > 0).sum() >= 4:
            try:
                from option.ssvi import SSVICalibration
                ssvi = SSVICalibration(F=F, T=T)
                ssvi.fit(strikes=strikes_np, sigmas_mkt=iv_np_arr, weights=weights_obs)
                ssvi_ok = True
                print(f"  SSVI calibré : {ssvi.result}")
            except Exception as exc:
                print(f"  SSVI calibration échouée : {exc}")

        # ── 4. Choisir les IV finales ─────────────────────────────────────────
        unique_strikes = [d[0] for d in datas]
        if sabr_ok and ssvi_ok and ssvi is not None:
            # "both" : moyenne des deux surfaces
            sabr_vols = sabr.predict(unique_strikes)
            ssvi_vols = ssvi.predict(unique_strikes)
            final_iv_map: Dict[float, float] = {
                k: max((float(sv) + float(xv)) / 2.0, 0.0)
                for k, sv, xv in zip(unique_strikes, sabr_vols, ssvi_vols)
            }
        elif ssvi_ok and ssvi is not None:
            ssvi_vols = ssvi.predict(unique_strikes)
            final_iv_map = {k: max(float(v), 0.0) for k, v in zip(unique_strikes, ssvi_vols)}
        elif sabr_ok:
            sabr_vols = sabr.predict(unique_strikes)
            final_iv_map = {k: max(float(v), 0.0) for k, v in zip(unique_strikes, sabr_vols)}
        else:
            final_iv_map = mkt_iv_map

        calibrated = sabr_ok or ssvi_ok

        for _, calls, puts in datas:
            for opt in calls + puts:
                k = opt.strike
                mkt_iv = mkt_iv_map.get(k, 0.0)
                iv = final_iv_map.get(k, 0.0)
                opt.market_implied_volatility = mkt_iv
                opt.sabr_volatility = iv if calibrated else 0.0
                if iv > 0:
                    opt.implied_volatility = iv
                    # Reconstruire le premium seulement s'il manque
                    if not (opt.status and opt.premium > 0):
                        opt.sabr_corrected = True
                        opt.premium = Bachelier(F, opt.strike, iv, T, opt.is_call()).price()
                    opt.delta = Bachelier(F, opt.strike, iv, T, opt.is_call()).delta()
                    opt.gamma = Bachelier(F, opt.strike, iv, T, opt.is_call()).gamma()
                    opt.theta = Bachelier(F, opt.strike, iv, T, opt.is_call()).theta()

        # Retourner un CalibrationBundle
        if sabr_ok or ssvi_ok:
            return CalibrationBundle(
                sabr=sabr if sabr_ok else None,
                ssvi=ssvi if ssvi_ok else None,
            )
        return None