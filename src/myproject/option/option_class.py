from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple
import numpy as np


# Nombre de dates intermédiaires pour le pricing intra-vie
N_INTRA_DATES = 5


def breeden_litzenberger_density(
    strikes: np.ndarray,
    call_prices: np.ndarray,
    price_grid: np.ndarray,
    risk_free_rate: float = 0.0,
    time_to_expiry: float = 1.0
) -> Optional[np.ndarray]:
    """
    Extrait la densité risque-neutre q_T(K) via la formule de Breeden-Litzenberger.
    
    La formule est : q_T(K) = e^{rT} * ∂²C/∂K²(K)
    
    Args:
        strikes: Array des strikes triés (croissants)
        call_prices: Array des prix des calls correspondants
        price_grid: Grille de prix sur laquelle interpoler la densité
        risk_free_rate: Taux sans risque annuel
        time_to_expiry: Temps jusqu'à expiration (en années)
        
    Returns:
        Densité risque-neutre q_T(x) sur la grille price_grid, ou None si échec
    """
    if len(strikes) < 4:
        # Pas assez de strikes pour calculer une dérivée seconde fiable
        return None
    
    # Trier par strike
    sort_idx = np.argsort(strikes)
    K = strikes[sort_idx]
    C = call_prices[sort_idx]
    
    # Filtrer les prix valides (> 0)
    valid_mask = C > 0
    if np.sum(valid_mask) < 4:
        return None
    
    K = K[valid_mask]
    C = C[valid_mask]
    
    # Interpolation cubique des prix de calls
    try:
        from scipy.interpolate import CubicSpline as CS
        cs = CS(K, C)
        
        # Dérivée seconde = d²C/dK²
        # CubicSpline permet de calculer les dérivées directement
        d2C_dK2 = cs(price_grid, 2)  # dérivée seconde
        
        # Formule de Breeden-Litzenberger: q_T(K) = e^{rT} * d²C/dK²
        discount_factor = np.exp(risk_free_rate * time_to_expiry)
        q_T = discount_factor * d2C_dK2
        
        # La densité doit être positive
        q_T = np.maximum(q_T, 0.0)
        
        # Normaliser pour que l'intégrale = 1
        dx = float(np.mean(np.diff(price_grid))) if len(price_grid) > 1 else 1.0
        total_mass = np.sum(q_T) * dx
        if total_mass > 1e-10:
            q_T = q_T / total_mass
        else:
            return None
            
        return q_T
        
    except Exception as e:
        print(f"⚠️ Erreur Breeden-Litzenberger: {e}")
        return None


@dataclass
class Option:
    # ============ CHAMPS OBLIGATOIRES ============
    option_type: str  # 'call' ou 'put'
    strike: float
    premium: float
    timestamp: Optional[float] = None

    # ============ CHAMPS OBLIGATOIRES ============
    expiration_month: Literal["F", "G", "H", "K", "M", "N", "Q", "U", "V", "X", "Z"] = ("F")
    expiration_year: int = 6

    # ============ STRUCTURE DE POSITION ============
    quantity: Optional[int] = 1
    position: Literal["long", "short"] = "short"

    # ============ IDENTIFICATION ============
    ticker: Optional[str] = None
    bloomberg_ticker: Optional[str] = None  # Ticker Bloomberg complet
    underlying_symbol: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None

    # ============ PRIX ET COTATIONS ============
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mid: Optional[float] = None
    roll: Optional[float] = None  # Roll moyen (normalisé par nombre de trimestres)
    roll_quarterly: Optional[float] = None  # Roll Q-1 (trimestre précédent)
    roll_sum: Optional[float] = None  # Roll brut (prix_roll - prix_courant, non normalisé)
    rolls_detail: Dict[str, float] = field(default_factory=dict)  # Rolls par expiry (ex: {"H6": 0.5, "M6": 0.3})

    # ============ GREEKS ============
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    rho: float = 0.0

    # ============ METRIQUES ============
    prices: Optional[np.ndarray] = None
    pnl_array: Optional[np.ndarray] = None
    mixture: Optional[np.ndarray] = None
    pnl_ponderation: Optional[np.ndarray] = None
    average_pnl: float = 0.0
    sigma_pnl: float = 0.0
    tail_penalty: float = 0.0  # ∫ max(-pnl, 0)² dx (zone négative au carré, pour achat)
    tail_penalty_short: float = 0.0  # ∫ max(pnl, 0)² dx (zone positive au carré, pour vente)
    dx: Optional[float] = None
    average_mix: float = 0.0

    # ============ INTRA-VIE (Pricing intermédiaire) ============
    # Prix de l'option à N_INTRA_DATES dates intermédiaires (t1, t2, ..., t5)
    # Calculés via le tilt terminal (ratio d'espérances) selon intra_life.md
    intra_life_prices: Optional[List[float]] = None  # [V_t1, V_t2, V_t3, V_t4, V_t5]
    intra_life_pnl: Optional[List[float]] = None     # P&L moyen à chaque date [pnl_t1, ..., pnl_t5]
    intra_life_dates: Optional[List[float]] = None   # Fractions de temps [0.2, 0.4, 0.6, 0.8, 1.0]
    market_density: Optional[np.ndarray] = None      # q_T(x) - densité risque-neutre du marché
    view_density: Optional[np.ndarray] = None        # p_T(x) - densité de la vue macro
    tilt_weights: Optional[np.ndarray] = None        # L_T = p_T / q_T (Radon-Nikodym)

    # ============ VOLATILITÉ ============
    implied_volatility: float = 0.0
    historical_volatility: Optional[float] = None

    # ============ LIQUIDITÉ ============
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None

    # ============ SOUS-JACENT ============
    underlying_price: Optional[float] = None

    @classmethod
    def empyOption(cls) -> "Option":
        return cls(option_type="call", strike=0.0, premium=0.0)

    # ============================================================================
    # Calcul des surfaces en foncion des scénarios
    # ============================================================================

    def _pnl_at_expiry_array(self) -> Optional[np.ndarray]:
        """
        Calcule le P&L à l'expiration pour un array de prix du sous-jacent.

        Convention:
          - long  -> P&L = intrinsic - premium
          - short -> P&L = premium - intrinsic

        Returns:
            Array numpy du P&L pour chaque prix, ou None si prices non défini
        """
        if self.prices is None:
            return None

        try:
            if self.option_type.lower() == "call":
                pnl = np.maximum(self.prices - self.strike, 0.0) - self.premium
            else:  # put
                pnl = np.maximum(self.strike - self.prices, 0.0) - self.premium
            return pnl
        except Exception:
            return None

    def _calculate_pnl_array(self) -> Optional[np.ndarray]:
        """
        Calcule le P&L array sur une grille de prix entre price_min et price_max.
        Stocke le résultat dans self.pnl_array.

        Returns:
            Array numpy du P&L pour chaque prix de la grille, ou None si erreur

        Example:
            >>> option = Option(option_type='call', strike=100, premium=5, position='long')
            >>> option.prices = np.linspace(80, 120, 200)
            >>> pnl = option._calculate_pnl_array()
            >>> # pnl contient le P&L pour 200 points entre 80 et 120
        """
        if self.prices is None:
            return None

        try:
            # Calculer le P&L pour chaque prix
            pnl_array = self._pnl_at_expiry_array()
            if pnl_array is None:
                return None

            # Stocker dans l'attribut de l'instance
            self.pnl_array = pnl_array
            return pnl_array
        except Exception:
            return None

    def _pnl_ponderation_array(self):
        """
        Calcule la pondération du P&L par la mixture.
        Retourne: p(x) × PnL(x) × dx
        """
        if self.mixture is None or self.pnl_array is None or self.prices is None:
            return None

        # pas moyen (dx) sur la grille
        dx = float(np.diff(self.prices).mean())
        self._dx = dx

        # intégrande discrétisé : p(x) * PnL(x) * dx
        self.pnl_ponderation = self.mixture * self.pnl_array * dx
        return self.pnl_ponderation

    def _average_pnl(self):
        """
        Espérance du PnL: E[PnL] = ∫ p(x) * pnl(x) dx ≈ sum(mixture * pnl * dx).
        """
        if self.mixture is None or self.pnl_array is None:
            return None

        if self.dx is None:
            # Valeur de repli si _pnl_ponderation_array n'a pas été appelée
            if self.prices is not None and len(self.prices) > 1:
                self.dx = float(np.mean(np.diff(self.prices)))
            else:
                return None

        mass = float(np.sum(self.mixture) * self.dx)  # ∫ p(x) dx
        if mass <= 0:
            return None

        mu = float(np.sum(self.mixture * self.pnl_array * self.dx) / mass)
        self.average_pnl = mu
        return mu

    def _sigma_pnl(self):
        """
        Ecart-type du PnL sous la mixture:
        σ = sqrt( E[(PnL - μ)^2] )  avec E[·] pris sous la densité p(x).
        Discrétisation par somme pondérée (méthode rectangle) et normalisation.
        """
        if self.mixture is None or self.pnl_array is None:
            return None

        # Assure qu'on a l'espérance et le pas dx
        mu = getattr(self, "average_pnl", None)
        if mu is None:
            mu = self._average_pnl()
            if mu is None:
                return None

        dx = getattr(self, "_dx", None)
        if dx is None:
            if self.prices is not None and len(self.prices) > 1:
                dx = float(np.mean(np.diff(self.prices)))
            else:
                return None

        # Normalisation de la densité (robuste aux petites erreurs numériques)
        mass = float(np.sum(self.mixture) * dx)  # ≈ 1 si p est bien normalisée
        if mass <= 0:
            return None

        var = float(np.sum(self.mixture * (self.pnl_array - mu) ** 2 * dx) / mass)
        sigma = float(np.sqrt(max(var, 0.0)))
        self.sigma_pnl = sigma
        return sigma


    def _calculate_tail_penalty(self) -> None:
        if self.pnl_array is None or self.prices is None:
            self.tail_penalty = 0.0
            self.tail_penalty_short = 0.0
            return
        try:
            # Calculer dx si pas déjà fait
            if self.dx is None and len(self.prices) > 1:
                self.dx = float(np.mean(np.diff(self.prices)))

            dx = self.dx if self.dx is not None else 1.0

            # Créer une gaussienne de pondération
            center = self.average_mix if self.average_mix else float(np.mean(self.prices))

            # σ = 3× taille intervalle → gaussienne plus plate, plus de poids aux extrémités
            sigma = float(self.prices[-1] - self.prices[0]) * 3.0
            if sigma <= 0:
                sigma = 1.0
            
            gauss_weights = np.exp(-0.5 * ((self.prices - center) / sigma) ** 2)
            gauss_weights = gauss_weights / (np.sum(gauss_weights) * dx + 1e-10)
            
            # tail_penalty (long) = ∫ max(-pnl, 0)² × gauss × dx
            losses_long = np.maximum(-self.pnl_array, 0.0) ** 2
            self.tail_penalty = float(np.sum(losses_long * gauss_weights) * dx)

            # tail_penalty_short = ∫ max(pnl, 0)² × gauss × dx
            losses_short = np.maximum(self.pnl_array, 0.0) ** 2
            self.tail_penalty_short = float(np.sum(losses_short * gauss_weights) * dx)
        except Exception:
            self.tail_penalty = 0.0
            self.tail_penalty_short = 0.0

    
    def _calcul_all_surface(self) -> None:
        # 1. Calculer le P&L array (utilise self.prices)
        self._calculate_pnl_array()

        # 2. Calculer la pondération (mixture × P&L × dx)
        self._pnl_ponderation_array()

        # 3. Calculer l'espérance du P&L
        self._average_pnl()

        # 4. Calculer l'écart-type du P&L
        self._sigma_pnl()

        # 5. Calculer le tail penalty: ∫ max(-pnl, 0)² dx (zone négative au carré)
        self._calculate_tail_penalty()

    # ============================================================================
    # INTRA-VIE - Pricing intermédiaire avec tilt terminal
    # ============================================================================
    
    def _build_market_density(self, 
                              sigma_market: Optional[float] = None,
                              all_options: Optional[List["Option"]] = None,
                              risk_free_rate: float = 0.0,
                              time_to_expiry: float = 1.0) -> Optional[np.ndarray]:
        """
        Construit la densité risque-neutre du marché q_T(x).
        
        Deux méthodes disponibles:
        1. Breeden-Litzenberger (si all_options fourni): extrait q_T des prix de marché
           q_T(K) = e^{rT} * ∂²C/∂K²(K)
        2. Approximation log-normale (fallback): basée sur la volatilité implicite
        
        Args:
            sigma_market: Volatilité implicite à utiliser (pour log-normale)
            all_options: Liste d'options pour Breeden-Litzenberger (même expiration)
            risk_free_rate: Taux sans risque annuel
            time_to_expiry: Temps jusqu'à expiration (en années)
            
        Returns:
            Densité q_T(x) sur la grille de prix
        """
        if self.prices is None or self.underlying_price is None:
            return None
        
        # ===== MÉTHODE 1: BREEDEN-LITZENBERGER =====
        # Si on a accès à plusieurs options, extraire la densité implicite
        if all_options is not None and len(all_options) >= 4:
            # Extraire les calls avec leurs strikes et prix
            calls_data = [
                (opt.strike, opt.premium)
                for opt in all_options
                if opt.option_type.lower() == "call" 
                and opt.premium > 0 
                and opt.strike > 0
                and opt.expiration_month == self.expiration_month
                and opt.expiration_year == self.expiration_year
            ]
            
            if len(calls_data) >= 4:
                strikes = np.array([c[0] for c in calls_data])
                call_prices = np.array([c[1] for c in calls_data])
                
                q_T = breeden_litzenberger_density(
                    strikes=strikes,
                    call_prices=call_prices,
                    price_grid=self.prices,
                    risk_free_rate=risk_free_rate,
                    time_to_expiry=time_to_expiry
                )
                
                if q_T is not None:
                    self.market_density = q_T
                    return q_T
        
        # ===== MÉTHODE 2: APPROXIMATION LOG-NORMALE (Fallback) =====
        sigma = sigma_market if sigma_market is not None else self.implied_volatility
        if sigma <= 0:
            sigma = 0.01  # Valeur de repli
            
        # Densité log-normale centrée sur le forward (= underlying_price pour simplifier)
        F0 = self.underlying_price
        x = self.prices
        
        # Log-normale: q(x) = (1 / (x * sigma * sqrt(2π))) * exp(-0.5 * ((ln(x/F0)) / sigma)^2)
        # Pour éviter les divisions par zéro
        x_safe = np.maximum(x, 1e-10)
        log_ratio = np.log(x_safe / F0)
        
        q_T = (1.0 / (x_safe * sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * (log_ratio / sigma) ** 2)
        
        # Normaliser
        dx = float(np.mean(np.diff(self.prices))) if len(self.prices) > 1 else 1.0
        q_T = q_T / (np.sum(q_T) * dx + 1e-10)
        
        self.market_density = q_T
        return q_T
    
    def _calculate_tilt_weights(self) -> Optional[np.ndarray]:
        """
        Calcule les poids du tilt terminal L_T = p_T(x) / q_T(x).
        
        p_T = vue macro (self.mixture)
        q_T = densité risque-neutre du marché
        
        Returns:
            Array des poids L_T sur la grille de prix
        """
        if self.mixture is None:
            return None
            
        # Construire la densité marché si pas déjà fait
        if self.market_density is None:
            self._build_market_density()
            
        if self.market_density is None:
            return None
            
        # L_T = p_T / q_T avec protection contre division par zéro
        self.view_density = self.mixture.copy()
        L_T = self.view_density / (self.market_density + 1e-10)
        
        self.tilt_weights = L_T
        return L_T
    
    def _calculate_intra_life_prices(self, 
                                     n_dates: int = N_INTRA_DATES,
                                     risk_free_rate: float = 0.0) -> Optional[List[float]]:
        """
        Calcule les prix de l'option à n_dates intermédiaires avant expiration.
        
        Utilise le tilt terminal selon la formule:
        V_t^view = E^Q[D(t,T) * g(F_T) * L_T | F_t] / E^Q[L_T | F_t]
        
        Où:
        - Q = mesure risque-neutre du marché
        - g(F_T) = payoff de l'option
        - L_T = p_T(F_T) / q_T(F_T) = tilt terminal
        - D(t,T) = discount factor
        
        Args:
            n_dates: Nombre de dates intermédiaires (défaut: 5)
            risk_free_rate: Taux sans risque annuel
            
        Returns:
            Liste des prix [V_t1, V_t2, ..., V_tn]
        """
        if self.prices is None or self.pnl_array is None:
            return None
            
        # Calculer les poids du tilt si pas déjà fait
        if self.tilt_weights is None:
            self._calculate_tilt_weights()
            
        if self.tilt_weights is None:
            return None
            
        dx = float(np.mean(np.diff(self.prices))) if len(self.prices) > 1 else 1.0
        
        # Payoff de l'option (intrinsic value at expiry)
        if self.option_type.lower() == "call":
            payoff = np.maximum(self.prices - self.strike, 0.0)
        else:
            payoff = np.maximum(self.strike - self.prices, 0.0)
        
        # Dates intermédiaires: t/T = 0.2, 0.4, 0.6, 0.8, 1.0 (pour n_dates=5)
        self.intra_life_dates = [(i + 1) / n_dates for i in range(n_dates)]
        self.intra_life_prices = []
        self.intra_life_pnl = []
        
        # Coût initial de l'option (ce qu'on a payé/reçu)
        initial_cost = self.premium
        
        for t_frac in self.intra_life_dates:
            # Time to expiry restant (en fraction de la période totale)
            tau = 1.0 - t_frac  # temps restant jusqu'à expiration
            
            # Discount factor simplifié (on suppose T=1 an comme normalisation)
            discount = np.exp(-risk_free_rate * tau)
            
            # Calcul du prix avec tilt:
            # V_t^view = E^Q[D * g(F_T) * L_T] / E^Q[L_T]
            # ≈ sum(q_T * D * payoff * L_T * dx) / sum(q_T * L_T * dx)
            # = sum(p_T * D * payoff * dx) / sum(p_T * dx)  (car p_T = q_T * L_T)
            
            if self.view_density is not None:
                numerator = np.sum(self.view_density * discount * payoff * dx)
                denominator = np.sum(self.view_density * dx) + 1e-10
                V_t = float(numerator / denominator)
            elif self.mixture is not None:
                # Fallback: utiliser la mixture directement
                numerator = np.sum(self.mixture * discount * payoff * dx)
                denominator = np.sum(self.mixture * dx) + 1e-10
                V_t = float(numerator / denominator)
            else:
                # Dernier fallback: utiliser le premium actuel
                V_t = self.premium
            
            self.intra_life_prices.append(V_t)
            
            # Calcul du P&L moyen à cette date
            # P&L = valeur actuelle - coût initial
            # Pour long: on a payé initial_cost, on peut revendre à V_t
            # P&L = V_t - initial_cost
            pnl_t = V_t - initial_cost
            self.intra_life_pnl.append(pnl_t)
        
        return self.intra_life_prices
    
    def calculate_all_intra_life(self, 
                                 sigma_market: Optional[float] = None,
                                 n_dates: int = N_INTRA_DATES,
                                 risk_free_rate: float = 0.0,
                                 all_options: Optional[List["Option"]] = None,
                                 time_to_expiry: float = 1.0) -> Optional[List[float]]:
        """
        Calcule tous les éléments nécessaires pour le pricing intra-vie.
        
        1. Construit la densité marché q_T (Breeden-Litzenberger si all_options fourni)
        2. Calcule les poids du tilt L_T = p_T / q_T  
        3. Calcule les prix à n_dates intermédiaires
        
        Args:
            sigma_market: Volatilité implicite pour la densité marché (log-normale)
            n_dates: Nombre de dates intermédiaires
            risk_free_rate: Taux sans risque annuel
            all_options: Liste d'options pour Breeden-Litzenberger (même expiration)
            time_to_expiry: Temps jusqu'à expiration (en années)
            
        Returns:
            Liste des prix intra-vie [V_t1, ..., V_tn]
        """
        self._build_market_density(sigma_market, all_options, risk_free_rate, time_to_expiry)
        self._calculate_tilt_weights()
        return self._calculate_intra_life_prices(n_dates, risk_free_rate)

    # ============================================================================
    # POSITION HELPERS - Méthodes utilitaires pour faciliter les checks de position
    # ============================================================================
    def is_call(self) -> bool:
        """Retourne True si c'est un call (long ou short)."""
        return self.option_type.lower() == "call"

    def is_put(self) -> bool:
        """Retourne True si c'est un put (long ou short)."""
        return self.option_type.lower() == "put"
