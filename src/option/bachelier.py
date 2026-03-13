# ===============================================================
# Module qui encadre tout l'utilisation du modèle de bachelier
# ===============================================================


import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from scipy.stats import norm
from scipy.optimize import brentq
from typing import Any, Dict, Optional, List, Tuple
from option.option_class import Option
from option.sabr import SABRCalibration


@dataclass
class CalibrationBundle:
    """Contient les résultats SABR et/ou SVI d'une calibration."""
    sabr: Optional[Any] = None   # SABRCalibration | None
    svi: Optional[Any] = None    # SVICalibration | None
    surface: Optional[Any] = None  # SVISurfaceResult | None (multi-expiry)

    def predict(self, strikes) -> Any:
        """Prédit la vol modèle (moyenne si les deux, sinon celui dispo)."""
        if self.sabr is not None and self.svi is not None:
            return (np.array(self.sabr.predict(strikes)) + np.array(self.svi.predict(strikes))) / 2.0
        if self.sabr is not None:
            return self.sabr.predict(strikes)
        if self.svi is not None:
            return self.svi.predict(strikes)
        raise RuntimeError("CalibrationBundle vide")

    def summary(self) -> str:
        parts = []
        if self.sabr is not None and hasattr(self.sabr, "summary"):
            parts.append(self.sabr.summary())
        if self.svi is not None and hasattr(self.svi, "summary"):
            parts.append(self.svi.summary())
        if self.surface is not None and hasattr(self.surface, "summary"):
            parts.append(self.surface.summary())
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
    ) -> Optional[CalibrationBundle]:
        """
        Calcule la volatilité Bachelier (+ grecques) via calibration SABR ou SVI.

        Gère automatiquement les expirations multiples :
        - Groupe les options par (expiration_month, expiration_year)
        - Calcule T et F par groupe (via opt.time_to_expiry et opt.underlying_price)
        - Calibre SABR par groupe indépendamment
        - Calibre SVI : Level 1 par groupe, Level 2 surface si multi-expiry

        vol_model : "sabr" | "svi" | "both"
        Returns CalibrationBundle ou None si calibration échouée.
        """
        if not future_price:
            return None

        F_default = future_price
        T_default = time_to_expiry

        # ── Collecter les F par expiration AVANT de les écraser ──────────────
        expiry_forwards: Dict[Tuple[str, int], List[float]] = defaultdict(list)
        for opt in options:
            key = (opt.expiration_month, opt.expiration_year)
            if opt.underlying_price and opt.underlying_price > 0:
                expiry_forwards[key].append(opt.underlying_price)

        # ── Grouper par expiration ───────────────────────────────────────────
        by_expiry: Dict[Tuple[str, int], List[Option]] = defaultdict(list)
        for opt in options:
            by_expiry[(opt.expiration_month, opt.expiration_year)].append(opt)

        # ── Par groupe : inverser les IV, collecter les données de calib ─────
        # Chaque entrée : (key, T, F, datas, strikes_obs, ivs_obs, weights_obs)
        expiry_blocks: list = []

        for key, opts in sorted(by_expiry.items()):
            # T par groupe : médiane des time_to_expiry des options, ou fallback
            tts = [o.time_to_expiry for o in opts if o.time_to_expiry and o.time_to_expiry > 0]
            T = float(np.median(tts)) if tts else T_default

            # F par groupe : médiane des underlying_price, ou fallback
            fwds = expiry_forwards.get(key, [])
            F = float(np.median(fwds)) if fwds else F_default

            # Inversion Bachelier individuelle
            grouped: Dict[float, Dict[str, List[Option]]] = defaultdict(
                lambda: {"call": [], "put": []}
            )
            for opt in opts:
                opt.underlying_price = F
                opt.implied_volatility = (
                    Bachelier(F, opt.strike, 0.0, T, opt.is_call(), opt.premium).implied_vol()
                    if opt.premium > 0 else 0.0
                )
                sk = round(opt.strike, 6)
                grouped[sk]["call" if opt.is_call() else "put"].append(opt)

            datas: List[Tuple[float, List[Option], List[Option]]] = []
            for sk in sorted(grouped):
                g = grouped[sk]
                calls, puts = g["call"], g["put"]
                if calls or puts:
                    datas.append((calls[0].strike if calls else puts[0].strike, calls, puts))

            if not datas:
                continue

            strikes_obs, ivs_obs, weights_obs = Bachelier.compute_weight(datas, F)
            if not strikes_obs:
                continue

            expiry_blocks.append((key, T, F, datas, strikes_obs, ivs_obs, weights_obs))

        if not expiry_blocks:
            return None

        # ── Calibration ──────────────────────────────────────────────────────
        run_sabr = vol_model in ("sabr", "both")
        run_svi = vol_model in ("svi", "both")
        multi_expiry = len(expiry_blocks) > 1

        # SABR : par expiration (pas de surface pour SABR)
        sabr_by_key: Dict[Tuple[str, int], SABRCalibration] = {}
        if run_sabr:
            for key, T, F, datas, s_obs, iv_obs, w_obs in expiry_blocks:
                iv_arr = np.array(iv_obs, dtype=float)
                if (iv_arr > 0).sum() >= 3:
                    try:
                        cal = SABRCalibration(F=F, T=T, beta=0.0, vol_type="normal")
                        cal.fit(strikes=np.array(s_obs), sigmas_mkt=iv_arr, weights=w_obs)
                        sabr_by_key[key] = cal
                        print(f"  SABR [{key[0]}{key[1]}] calibré : {cal.result}")
                    except Exception as exc:
                        print(f"  SABR [{key[0]}{key[1]}] échoué : {exc}")

        # SVI : Level 1 per-slice, Level 2 surface si multi-expiry
        svi_by_key: Dict[Tuple[str, int], Any] = {}
        surface_result = None
        if run_svi:
            from option.svi import SVICalibration, SVISurfaceCalibration, SliceData

            if multi_expiry:
                # Surface calibration Level 1 + Level 2
                slice_list: List[SliceData] = []
                slice_keys: List[Tuple[str, int]] = []
                for key, T, F, datas, s_obs, iv_obs, w_obs in expiry_blocks:
                    iv_arr = np.array(iv_obs, dtype=float)
                    if (iv_arr > 0).sum() >= 4:
                        slice_list.append(SliceData(
                            F=F, T=T,
                            strikes=np.array(s_obs, dtype=float),
                            sigmas_mkt=iv_arr,
                            weights=np.array(w_obs, dtype=float),
                        ))
                        slice_keys.append(key)
                if slice_list:
                    try:
                        surface_cal = SVISurfaceCalibration()
                        surface_result = surface_cal.fit(slice_list)
                        # Extraire un SVICalibration par slice depuis les résultats surface
                        for i, key in enumerate(slice_keys):
                            T_i = slice_list[i].T
                            if T_i in surface_result.slices:
                                cal = SVICalibration(F=slice_list[i].F, T=T_i)
                                cal.result = surface_result.slices[T_i]
                                svi_by_key[key] = cal
                        print(f"  SVI Surface calibrée : {surface_result.n_slices} slices, "
                              f"RMSE={surface_result.global_rmse_bps:.2f}bp")
                    except Exception as exc:
                        print(f"  SVI Surface échouée : {exc}")
            else:
                # Single expiry : Level 1 standard
                key, T, F, datas, s_obs, iv_obs, w_obs = expiry_blocks[0]
                iv_arr = np.array(iv_obs, dtype=float)
                if (iv_arr > 0).sum() >= 4:
                    try:
                        cal = SVICalibration(F=F, T=T)
                        cal.fit(strikes=np.array(s_obs), sigmas_mkt=iv_arr, weights=w_obs)
                        svi_by_key[key] = cal
                        print(f"  SVI calibré : {cal.result}")
                    except Exception as exc:
                        print(f"  SVI calibration échouée : {exc}")

        # ── Appliquer les IV calibrées par expiration ────────────────────────
        for key, T, F, datas, strikes_obs, ivs_obs, weights_obs in expiry_blocks:
            sabr_cal = sabr_by_key.get(key)
            svi_cal = svi_by_key.get(key)
            sabr_ok = sabr_cal is not None
            svi_ok = svi_cal is not None

            # IV marché par strike
            mkt_iv_by_strike: Dict[float, List[float]] = defaultdict(list)
            for k, iv in zip(strikes_obs, ivs_obs):
                mkt_iv_by_strike[k].append(iv)
            mkt_iv_map: Dict[float, float] = {
                k: sum(vs) / len(vs) for k, vs in mkt_iv_by_strike.items()
            }

            # IV finales calibrées
            unique_strikes = [d[0] for d in datas]
            if sabr_ok and svi_ok:
                sabr_vols = sabr_cal.predict(unique_strikes)
                svi_vols = svi_cal.predict(unique_strikes)
                final_iv_map: Dict[float, float] = {
                    k: max((float(sv) + float(xv)) / 2.0, 0.0)
                    for k, sv, xv in zip(unique_strikes, sabr_vols, svi_vols)
                }
            elif svi_ok:
                svi_vols = svi_cal.predict(unique_strikes)
                final_iv_map = {k: max(float(v), 0.0) for k, v in zip(unique_strikes, svi_vols)}
            elif sabr_ok:
                sabr_vols = sabr_cal.predict(unique_strikes)
                final_iv_map = {k: max(float(v), 0.0) for k, v in zip(unique_strikes, sabr_vols)}
            else:
                final_iv_map = mkt_iv_map

            calibrated = sabr_ok or svi_ok
            for _, calls, puts in datas:
                for opt in calls + puts:
                    k = opt.strike
                    mkt_iv = mkt_iv_map.get(k, 0.0)
                    iv = final_iv_map.get(k, 0.0)
                    opt.market_implied_volatility = mkt_iv
                    opt.sabr_volatility = iv if calibrated else 0.0
                    if iv > 0:
                        opt.implied_volatility = iv
                        if not (opt.status and opt.premium > 0):
                            opt.sabr_corrected = True
                            opt.premium = Bachelier(F, opt.strike, iv, T, opt.is_call()).price()
                        opt.delta = Bachelier(F, opt.strike, iv, T, opt.is_call()).delta()
                        opt.gamma = Bachelier(F, opt.strike, iv, T, opt.is_call()).gamma()
                        opt.theta = Bachelier(F, opt.strike, iv, T, opt.is_call()).theta()

        # ── CalibrationBundle : primary expiry + surface ─────────────────────
        first_key = expiry_blocks[0][0]
        primary_sabr = sabr_by_key.get(first_key)
        primary_svi = svi_by_key.get(first_key)
        if primary_sabr or primary_svi or surface_result:
            return CalibrationBundle(
                sabr=primary_sabr,
                svi=primary_svi,
                surface=surface_result,
            )
        return None