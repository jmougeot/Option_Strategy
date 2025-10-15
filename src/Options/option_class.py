from dataclasses import dataclass, field, make_dataclass
from typing import Literal, Optional, List, Dict, Type
from datetime import datetime

try:
    from .option_avaible import STRATEGY_DEFINITIONS
except ImportError:
    from option_avaible import STRATEGY_DEFINITIONS

"""
Système Générique de Stratégies d'Options
==========================================
Architecture auto-génératrice où les stratégies complexes sont créées
automatiquement à partir d'une simple configuration déclarative.
"""

@dataclass
class Option:
    """Représente une option (call ou put) - Brique de base"""
    option_type: Literal['call', 'put']
    strike: float
    premium: float
    expiry: datetime 
    quantity: int = 1
    position: Literal['long', 'short'] = 'short'
    
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
    """Classe de base pour toutes les stratégies d'options"""
    underlying : str = "" # Champ obligatoire sans valeur par défaut
    name: str = ""  # Champs avec valeurs par défaut après
    underlying_price: float = 0.0
    options: List[Option] = field(default_factory=list)
    
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
        breakeven_formula: Optional[callable] = None
    ) -> Type[OptionStrategy]:
        """
        Crée dynamiquement une classe de stratégie
        
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
        
        # Champs communs
        fields.extend([
            ('expiry', datetime, field(default_factory=datetime.now)),
            ('quantity', int, 1)
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
        
        # 3. Créer la méthode max_loss
        if max_loss_formula == 'unlimited':
            def max_loss(self):
                return "Illimité"
        elif callable(max_loss_formula):
            def max_loss(self):
                return max_loss_formula(self)
        else:
            def max_loss(self):
                # Formule par défaut pour les spreads
                total_width = 0
                for i in range(0, len(self.options), 2):
                    if i + 1 < len(self.options):
                        width = abs(self.options[i].strike - self.options[i+1].strike)
                        total_width = max(total_width, width)
                return (total_width - self.total_premium_received()) * self.quantity
        
        # 4. Créer la méthode breakeven_points
        if breakeven_formula:
            breakeven_points = breakeven_formula
        else:
            # Formule par défaut
            def breakeven_points(self):
                # Pour les stratégies symétriques
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
