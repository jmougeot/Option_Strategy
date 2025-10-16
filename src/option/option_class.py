from dataclasses import dataclass, field, make_dataclass
from datetime import datetime
from typing import Dict, List, Literal, Optional, Type, Callable

from .option_avaible import STRATEGY_DEFINITIONS

"""
Ce module définit deux niveaux de responsabilités complémentaires:

- Option: Représente un leg individuel (call/put) avec son strike, sa prime, sa quantité, etc.
- OptionStrategy: Base commune des stratégies. Elle gère la liste des options (legs),
    le calcul des primes nettes, le P&L à l'expiration et expose des hooks génériques
    comme max_loss() et breakeven_points() que les stratégies concrètes peuvent surcharger.
- StrategyFactory: Fabrique des classes de stratégies à partir de définitions déclaratives
    (STRATEGY_DEFINITIONS). Elle compose dynamiquement des sous-classes d'OptionStrategy en
    ajoutant les champs spécifiques, en implémentant max_loss() et breakeven_points() lorsque
    des formules sont fournies, et en préparant un BUILD_CONFIG pour la construction générique.
"""

@dataclass
class Option:
    """Brique de base: un leg d'option (call ou put).

    Responsabilités:
    - Calculer la valeur intrinsèque à l'expiration
    - Calculer la valeur (payoff) à l'expiration selon la position (long/short)
    """
    option_type: Literal['call', 'put']
    strike: float
    premium: float
    expiry: datetime 
    quantity: int = 1
    position: Literal['long', 'short'] = 'short'

    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    mid: Optional[float] = None

    # Greeks
    delta: Optional[float] = None
    gamma: Optional[float] = None
    vega: Optional[float] = None
    theta: Optional[float] = None
    rho: Optional[float] = None

    # Autres données
    implied_volatility: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    
    def intrinsic_value(self, spot_price: float) -> float:
        """Calcule la valeur intrinsèque de l'option"""
        if self.option_type == 'call':
            return max(0, spot_price - self.strike)
        else:  # put
            return max(0, self.strike - spot_price)
    
    def value_at_expiry(self, spot_price: float) -> float:
        """Valeur de l'option à l'expiration"""
        intrinsic = self.intrinsic_value(spot_price)
        
        if self.position == 'long':
            return (intrinsic - self.premium) * self.quantity
        else:  # short
            return (self.premium - intrinsic) * self.quantity


@dataclass
class OptionStrategy:
    """Base commune de toutes les stratégies d'options.

    Responsabilités:
    - Conserver la liste des legs (options)
    - Calculer la prime nette reçue/versée (total_premium_received)
    - Fournir un calcul par défaut de max_profit et max_loss
    - Calculer le P&L à l'expiration pour un prix spot donné
    - Déclarer un hook breakeven_points() (par défaut non implémenté)
    """
    underlying : str = "" # Champ obligatoire sans valeur par défaut
    name: str = ""  # Champs avec valeurs par défaut après
    underlying_price: float = 0.0
    options: List[Option] = field(default_factory=list)
    expiry: datetime = field(default_factory=datetime.now)
    
    # Configuration de construction (définie par les sous-classes ou générée)
    BUILD_CONFIG: Dict = field(default_factory=dict, init=False, repr=False)
    
    def add_option(self, option: Option):
        """Ajoute une option à la stratégie"""
        self.options.append(option)
    
    def total_premium_received(self) -> float:
        """Calcule le total des primes reçues (moins les primes payées)"""
        total = 0.0
        for opt in self.options:
            if opt.position == 'short':
                total += opt.premium * opt.quantity
            else:  # long
                total -= opt.premium * opt.quantity
        return total
    
    def max_profit(self) -> float:
        """Profit maximum de la stratégie"""
        return self.total_premium_received()
    
    def max_loss(self):
        """Perte maximale par défaut.

        Par défaut, on approxime la perte maximale comme:
            (largeur maximale de spread entre les strikes) - crédit net reçu
        multiplié par la quantité. Le résultat est une perte → valeur négative.

        Les stratégies avec perte illimitée (ex: short call découvert) doivent
        surcharger cette méthode pour retourner "Illimité".
        """
        if not self.options:
            return 0.0

        # Largeur maximale observée entre strikes (approximation générique)
        strikes = [o.strike for o in self.options if hasattr(o, "strike")]
        if len(strikes) < 2:
            return 0.0

        total_width = max(strikes) - min(strikes)

        # Crédit net reçu (positif) – on ne permet pas que le crédit rende la perte positive
        credit = max(0.0, float(self.total_premium_received()))

        # Quantité globale (si présente)
        qty = abs(getattr(self, "quantity", 1))

        loss = (total_width - credit) * qty
        return -abs(loss)

    def profit_at_expiry(self, spot_price: float) -> float:
        """Calcule le profit/perte à l'expiration pour un prix spot donné"""
        total_value = sum(opt.value_at_expiry(spot_price) for opt in self.options)
        return total_value
        
    def breakeven_points(self) -> List[float]:
        """Points de breakeven (à implémenter dans les sous-classes)"""
        raise NotImplementedError("Les sous-classes doivent implémenter cette méthode")



# =============================================================================
# GÉNÉRATEUR AUTOMATIQUE DE STRATÉGIES
# =============================================================================

class StrategyFactory:
    """
    Factory qui génère automatiquement des classes de stratégies
    à partir d'une configuration déclarative
    """
    
    @staticmethod
    def create_strategy_class(
        name: str,
        description: str,
        legs: List[Dict],
        max_loss_formula: str = 'defined',
        breakeven_formula: Optional[Callable[["OptionStrategy"], List[float]]] = None,
    ) -> Type[OptionStrategy]:
        """
        Crée dynamiquement une sous-classe d'OptionStrategy.
        
        Args:
            name: Nom de la stratégie (ex: "IronCondor")
            description: Description de la stratégie
            legs: Liste des legs avec leurs configurations
                  Ex: [{'type': 'put', 'position': 'long', 'param_prefix': 'long_put'}]
            max_loss_formula: 'defined', 'unlimited', ou une formule
            breakeven_formula: Fonction pour calculer les breakevens
        
        Returns:
            Une classe de stratégie générée dynamiquement
        """
        
        # 1. Construire les champs (fields) du dataclass
        fields = []
        
        # Ajouter les champs pour chaque leg
        for leg in legs:
            prefix = leg['param_prefix']
            fields.append((f"{prefix}_strike", float, 0.0))
            fields.append((f"{prefix}_premium", float, 0.0))
        
        # Champs communs (expiry est déjà dans OptionStrategy)
        fields.extend([
            ('quantity', int, 1),
        ])
        
        # 2. Créer la méthode __post_init__
        def post_init(self):
            if not self.name:
                self.name = name
            
            # Ajouter chaque option
            for leg in legs:
                prefix = leg['param_prefix']
                strike = getattr(self, f"{prefix}_strike")
                premium = getattr(self, f"{prefix}_premium")
                
                self.add_option(Option(
                    option_type=leg['type'],
                    strike=strike,
                    premium=premium,
                    expiry=self.expiry,
                    quantity=self.quantity,
                    position=leg['position']
                ))
        
        # 3. Créer la méthode max_loss (spécifique à la stratégie si formule fournie)
        def max_loss(self):
            """Perte maximale spécifique à la stratégie générée.

            Cases:
            - 'unlimited'/'illimité' → retourne la chaîne "Illimité"
            - callable → utilise la formule fournie et renvoie une valeur négative
            - sinon → fallback vers une approximation de spread (comme OptionStrategy)
            """
            try:
                # 1) cas "illimité"
                if isinstance(max_loss_formula, str) and max_loss_formula.lower() in ("unlimited", "illimité"):
                    return "Illimité"

                # 2) cas formule fournie (callable)
                if callable(max_loss_formula):
                    res = max_loss_formula(self)
                    if isinstance(res, str) and res.lower() in ("unlimited", "illimité"):
                        return "Illimité"
                    return -abs(float(res))  # perte => négative

                # 3) fallback: se rabattre sur le calcul par défaut d'OptionStrategy
                return OptionStrategy.max_loss(self)
            except Exception:
                # garde-fou (cohérent avec l'analyseur côté UI)
                return -999999.0
            
        # 4. Créer la méthode breakeven_points
        def breakeven_points(self):
            if breakeven_formula:
            # Utiliser la formule fournie par la définition de stratégie
                return breakeven_formula(self)
            else:
            # Formule par défaut (simple approximation pour stratégies symétriques)
                net_credit = self.total_premium_received()
                if len(self.options) == 2:
                    return [self.options[0].strike - net_credit,
                            self.options[1].strike + net_credit]
                return []
        
        # 5. Créer le BUILD_CONFIG
        build_config = {
            'legs': [],
            'name_format': name + ' ' + '/'.join([f"{{{leg['param_prefix']}_strike:.0f}}" for leg in legs])
        }
        
        for leg in legs:
            build_config['legs'].append({
                'type': leg['type'],
                'action': 'sell' if leg['position'] == 'short' else 'buy',
                'offset': leg.get('offset', 0),
                'strike_param': f"{leg['param_prefix']}_strike",
                'premium_param': f"{leg['param_prefix']}_premium"
            })
        
        # 6. Créer la classe dynamiquement
        cls = make_dataclass(
            name,
            fields,
            bases=(OptionStrategy,),
            namespace={
                '__doc__': description,
                '__post_init__': post_init,
                'max_loss': max_loss,
                'breakeven_points': breakeven_points,
                'BUILD_CONFIG': build_config
            }
        )
        
        return cls


def generate_all_strategies() -> Dict[str, Type[OptionStrategy]]:
    """
    Génère automatiquement toutes les classes de stratégies
    à partir des définitions déclaratives
    
    Returns:
        Dict avec nom_stratégie -> classe générée
    """
    strategies = {}
    
    for strategy_name, config in STRATEGY_DEFINITIONS.items():
        strategy_class = StrategyFactory.create_strategy_class(
            name=strategy_name,
            description=config['description'],
            legs=config['legs'],
            max_loss_formula=config['max_loss_formula'],
            breakeven_formula=config.get('breakeven_formula')
        )
        strategies[strategy_name] = strategy_class
    
    return strategies


GENERATED_STRATEGIES = generate_all_strategies()
