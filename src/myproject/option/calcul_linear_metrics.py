"""
Calcul Complet des Métriques de Stratégie d'Options
===================================================
Fournit une fonction générale pour calculer TOUTES les métriques d'une stratégie :
- Métriques linéaires (coût, Greeks, IV) - calculées par simple addition
- Métriques de surface (profit/loss surfaces) - calculées en sommant les surfaces de chaque leg

Optimisé pour calculer toutes les métriques en une seule fonction.
Utilise les méthodes de la classe Option pour assurer la cohérence des calculs.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from myproject.option.option_class import Option
import numpy as np


@dataclass
class LinearMetricsAccumulator:
    """
    Accumulateur pour calculer les métriques linéaires de manière incrémentale.
    
    Au fur et à mesure qu'on ajoute des legs (options), les métriques sont mises à jour.
    """
    
    # ============ COÛT NET ============
    net_cost: float = 0.0  # Coût net total (négatif = crédit reçu)
    total_premium_paid: float = 0.0  # Total des primes payées (positions longues)
    total_premium_received: float = 0.0  # Total des primes reçues (positions courtes)
    
    # ============ GREEKS PAR TYPE ============
    # Calls
    delta_calls: float = 0.0
    gamma_calls: float = 0.0
    vega_calls: float = 0.0
    theta_calls: float = 0.0
    
    # Puts
    delta_puts: float = 0.0
    gamma_puts: float = 0.0
    vega_puts: float = 0.0
    theta_puts: float = 0.0
    
    # Total
    delta_total: float = 0.0
    gamma_total: float = 0.0
    vega_total: float = 0.0
    theta_total: float = 0.0
    
    # ============ VOLATILITÉ IMPLICITE ============
    weighted_iv_sum: float = 0.0  # Somme pondérée des IV
    total_weight: float = 0.0  # Somme des poids (primes)
    
    # ============ COMPTEUR DE LEGS ============
    n_legs: int = 0
    n_calls: int = 0
    n_puts: int = 0
    n_long: int = 0
    n_short: int = 0
    
    # ============ LISTE DES OPTIONS ============
    options: List[Option] = field(default_factory=list)
    
    def add_leg(self, option: Option) -> None:
        """
        Ajoute un leg (option) et met à jour toutes les métriques de manière incrémentale.
        
        Args:
            option: Option à ajouter
        """
        # Ajouter à la liste
        self.options.append(option)
        self.n_legs += 1
        
        # Compteurs de type
        if option.option_type == 'call':
            self.n_calls += 1
        else:
            self.n_puts += 1
        
        if option.position == 'long':
            self.n_long += 1
        else:
            self.n_short += 1
        
        # ============ COÛT NET ============
        # Long = on paye la prime (négatif)
        # Short = on reçoit la prime (positif)
        leg_cost = option.premium * (-1 if option.position == 'long' else 1)
        self.net_cost += leg_cost
        
        if option.position == 'long':
            self.total_premium_paid += option.premium
        else:
            self.total_premium_received += option.premium
        
        # ============ GREEKS ============
        # Signe selon la position
        sign = 1 if option.position == 'long' else -1
        
        delta = (option.delta or 0.0) * sign
        gamma = (option.gamma or 0.0) * sign
        vega = (option.vega or 0.0) * sign
        theta = (option.theta or 0.0) * sign
        
        # Accumuler par type
        if option.option_type == 'call':
            self.delta_calls += delta
            self.gamma_calls += gamma
            self.vega_calls += vega
            self.theta_calls += theta
        else:  # put
            self.delta_puts += delta
            self.gamma_puts += gamma
            self.vega_puts += vega
            self.theta_puts += theta
        
        # Accumuler total
        self.delta_total += delta
        self.gamma_total += gamma
        self.vega_total += vega
        self.theta_total += theta
        
        # ============ VOLATILITÉ IMPLICITE PONDÉRÉE ============
        if option.implied_volatility is not None and option.premium > 0:
            weight = abs(option.premium)
            self.weighted_iv_sum += option.implied_volatility * weight
            self.total_weight += weight
    
    def add_legs(self, options: List[Option]) -> None:
        """
        Ajoute plusieurs legs en une fois.
        
        Args:
            options: Liste d'options à ajouter
        """
        for option in options:
            self.add_leg(option)
    
    def get_avg_implied_volatility(self) -> float:
        """
        Calcule la volatilité implicite moyenne pondérée.
        
        Returns:
            IV moyenne pondérée par les primes
        """
        if self.total_weight > 0:
            return self.weighted_iv_sum / self.total_weight
        
        # Fallback : moyenne simple si pas de poids
        ivs = [opt.implied_volatility for opt in self.options 
               if opt.implied_volatility is not None]
        return sum(ivs) / len(ivs) if ivs else 0.0
    
    def to_dict(self) -> Dict:
        """
        Convertit toutes les métriques en dictionnaire.
        
        Returns:
            Dictionnaire avec toutes les métriques
        """
        return {
            # Coût
            'net_cost': self.net_cost,
            'total_premium_paid': self.total_premium_paid,
            'total_premium_received': self.total_premium_received,
            
            # Greeks - Calls
            'delta_calls': self.delta_calls,
            'gamma_calls': self.gamma_calls,
            'vega_calls': self.vega_calls,
            'theta_calls': self.theta_calls,
            
            # Greeks - Puts
            'delta_puts': self.delta_puts,
            'gamma_puts': self.gamma_puts,
            'vega_puts': self.vega_puts,
            'theta_puts': self.theta_puts,
            
            # Greeks - Total
            'delta_total': self.delta_total,
            'gamma_total': self.gamma_total,
            'vega_total': self.vega_total,
            'theta_total': self.theta_total,
            
            # Volatilité
            'avg_implied_volatility': self.get_avg_implied_volatility(),
            
            # Compteurs
            'n_legs': self.n_legs,
            'n_calls': self.n_calls,
            'n_puts': self.n_puts,
            'n_long': self.n_long,
            'n_short': self.n_short,
            
            # Options
            'options': self.options
        }
    
    def __repr__(self) -> str:
        """Représentation lisible de l'accumulateur."""
        return (
            f"LinearMetricsAccumulator("
            f"n_legs={self.n_legs}, "
            f"net_cost={self.net_cost:.2f}, "
            f"delta={self.delta_total:.3f}, "
            f"gamma={self.gamma_total:.3f}, "
            f"vega={self.vega_total:.3f}, "
            f"theta={self.theta_total:.3f}"
            f")"
        )

# ============================================================================
# FONCTION PRINCIPALE - CALCUL EN UNE FOIS
# ============================================================================

def calculate_linear_metrics(options: List[Option],
                           price_min: Optional[float] = None,
                           price_max: Optional[float] = None,
                           num_points: int = 1000) -> Dict:
    """
    Calcule TOUTES les métriques d'une stratégie d'options en une fois.
    
    Cette fonction est optimisée pour calculer :
    1. Métriques linéaires (coût, Greeks, IV) - en une passe sur les options
    2. Métriques de surface (profit/loss) - par calcul vectorisé si demandé
    
    Args:
        options: Liste d'options constituant la stratégie
        price_min: Prix minimum pour le calcul des surfaces (optionnel)
        price_max: Prix maximum pour le calcul des surfaces (optionnel)
        num_points: Nombre de points pour l'intégration des surfaces
        calculate_surfaces: Si True, calcule aussi les surfaces (plus lent)
        
    Returns:
        Dict avec toutes les métriques (linéaires + surfaces si demandé)
    """
    # Initialiser les accumulateurs
    net_cost = 0.0
    total_premium_paid = 0.0
    total_premium_received = 0.0
    total_loss_surface = 0.0
    total_profit_surface = 0.0
    total_gauss_pnl = 0.0

    
    # Greeks par type
    delta_calls = gamma_calls = vega_calls = theta_calls = 0.0
    delta_puts = gamma_puts = vega_puts = theta_puts = 0.0
    delta_total = gamma_total = vega_total = theta_total = 0.0
    
    # Volatilité implicite
    weighted_iv_sum = 0.0
    total_weight = 0.0
    
    # Compteurs
    n_legs = len(options)
    n_calls = n_puts = n_long = n_short = 0
    
    # Parcourir toutes les options UNE SEULE FOIS
    for option in options:
        # ============ COMPTEURS ============
        if option.option_type == 'call':
            n_calls += 1
        else:
            n_puts += 1
        
        if option.position == 'long':
            n_long += 1
        else:
            n_short += 1
        
        # ============ COÛT NET ============
        leg_cost = option.premium * (-1 if option.position == 'long' else 1)
        net_cost += leg_cost
        
        if option.position == 'long':
            total_premium_paid += option.premium
        else:
            total_premium_received += option.premium
        
        # ============ GREEKS ============
        sign = 1 if option.position == 'long' else -1
        
        delta = (option.delta or 0.0) * sign
        gamma = (option.gamma or 0.0) * sign
        vega = (option.vega or 0.0) * sign
        theta = (option.theta or 0.0) * sign
        loss_surface = (option.loss_surface or 0.0) * sign
        profit_surface = (option.profit_surface or 0.0)* sign

        
        # Accumuler par type
        if option.option_type == 'call':
            delta_calls += delta
            gamma_calls += gamma
            vega_calls += vega
            theta_calls += theta
        else:  # put
            delta_puts += delta
            gamma_puts += gamma
            vega_puts += vega
            theta_puts += theta
        
        # Accumuler total
        delta_total += delta
        gamma_total += gamma
        vega_total += vega
        theta_total += theta
        total_loss_surface += loss_surface
        total_profit_surface += profit_surface 
        
        # ============ VOLATILITÉ IMPLICITE ============
        if option.implied_volatility is not None and option.premium > 0:
            weight = abs(option.premium)
            weighted_iv_sum += option.implied_volatility * weight
            total_weight += weight
    
    # Calculer IV moyenne
    if total_weight > 0:
        avg_iv = weighted_iv_sum / total_weight
    else:
        # Fallback : moyenne simple
        ivs = [opt.implied_volatility for opt in options 
               if opt.implied_volatility is not None]
        avg_iv = sum(ivs) / len(ivs) if ivs else 0.0
    
    # ============ PRÉPARER LE DICTIONNAIRE DE RÉSULTATS ============
    result = {
        # Coût
        'net_cost': net_cost,
        'total_premium_paid': total_premium_paid,
        'total_premium_received': total_premium_received,
        
        # Greeks - Calls
        'delta_calls': delta_calls,
        'gamma_calls': gamma_calls,
        'vega_calls': vega_calls,
        'theta_calls': theta_calls,

        #METRIQUE

        'loss_surface' : total_loss_surface,
        'profit_surface' : total_profit_surface,
        'gauss_x_pnl': total_gauss_pnl,
        
        # Greeks - Puts
        'delta_puts': delta_puts,
        'gamma_puts': gamma_puts,

        'vega_puts': vega_puts,
        'theta_puts': theta_puts,
        
        # Greeks - Total
        'delta_total': delta_total,
        'gamma_total': gamma_total,
        'vega_total': vega_total,
        'theta_total': theta_total,
        
        # Volatilité
        'avg_implied_volatility': avg_iv,
        
        # Compteurs
        'n_legs': n_legs,
        'n_calls': n_calls,
        'n_puts': n_puts,
        'n_long': n_long,
        'n_short': n_short
    }

    return result


# ============================================================================
# FONCTIONS UTILITAIRES SUPPLÉMENTAIRES
# ============================================================================

def calculate_greeks_only(options: List[Option]) -> Dict[str, Dict[str, float]]:
    """
    Calcule uniquement les Greeks (plus rapide si on n'a pas besoin des autres métriques).
    
    Args:
        options: Liste d'options
        
    Returns:
        Dict avec 'calls', 'puts', 'total' contenant chacun delta/gamma/vega/theta
    """
    delta_calls = gamma_calls = vega_calls = theta_calls = 0.0
    delta_puts = gamma_puts = vega_puts = theta_puts = 0.0
    
    for option in options:
        sign = 1 if option.position == 'long' else -1
        
        delta = (option.delta or 0.0) * sign
        gamma = (option.gamma or 0.0) * sign
        vega = (option.vega or 0.0) * sign
        theta = (option.theta or 0.0) * sign
        
        if option.option_type == 'call':
            delta_calls += delta
            gamma_calls += gamma
            vega_calls += vega
            theta_calls += theta
        else:
            delta_puts += delta
            gamma_puts += gamma
            vega_puts += vega
            theta_puts += theta
    
    return {
        'calls': {
            'delta': delta_calls,
            'gamma': gamma_calls,
            'vega': vega_calls,
            'theta': theta_calls
        },
        'puts': {
            'delta': delta_puts,
            'gamma': gamma_puts,
            'vega': vega_puts,
            'theta': theta_puts
        },
        'total': {
            'delta': delta_calls + delta_puts,
            'gamma': gamma_calls + gamma_puts,
            'vega': vega_calls + vega_puts,
            'theta': theta_calls + theta_puts
        }
    }


def calculate_net_cost_only(options: List[Option]) -> float:
    """
    Calcule uniquement le coût net (ultra rapide).
    
    Args:
        options: Liste d'options
        
    Returns:
        Coût net (négatif = crédit)
    """
    return sum(
        opt.premium * (-1 if opt.position == 'long' else 1)
        for opt in options
    )

