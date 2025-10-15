from dataclasses import dataclass, field, make_dataclass
from typing import Literal, Optional, List, Dict, Type
from datetime import datetime

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
    name: str = ""
    underlying : str
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


# =============================================================================
# CONFIGURATIONS DÉCLARATIVES DES STRATÉGIES
# =============================================================================

STRATEGY_DEFINITIONS = {
    'ShortPut': {
        'description': """
        SHORT PUT (Vente de Put)
        - Vente d'un put
        - Profit: prime reçue
        - Risque: strike - prime (si spot → 0)
        - Vue: neutre à haussière
        """,
        'legs': [
            {'type': 'put', 'position': 'short', 'param_prefix': 'short_put', 'offset': -2}
        ],
        'max_loss_formula': lambda self: (self.short_put_strike - self.short_put_premium) * self.quantity,
        'breakeven_formula': lambda self: [self.short_put_strike - self.short_put_premium]
    },
    
    'ShortCall': {
        'description': """
        SHORT CALL (Vente de Call)
        - Vente d'un call
        - Profit: prime reçue
        - Risque: illimité (si spot → ∞)
        - Vue: neutre à baissière
        """,
        'legs': [
            {'type': 'call', 'position': 'short', 'param_prefix': 'short_call', 'offset': 2}
        ],
        'max_loss_formula': 'unlimited',
        'breakeven_formula': lambda self: [self.short_call_strike + self.short_call_premium]
    },
    
    'ShortStraddle': {
        'description': """
        SHORT STRADDLE
        - Vente d'un call et d'un put au même strike (ATM)
        - Profit: somme des primes reçues
        - Risque: illimité des deux côtés
        - Vue: faible volatilité, marché range
        """,
        'legs': [
            {'type': 'put', 'position': 'short', 'param_prefix': 'put', 'offset': 0},
            {'type': 'call', 'position': 'short', 'param_prefix': 'call', 'offset': 0}
        ],
        'max_loss_formula': 'unlimited',
        'breakeven_formula': lambda self: [
            self.put_strike - (self.put_premium + self.call_premium),
            self.call_strike + (self.put_premium + self.call_premium)
        ]
    },
    
    'ShortStrangle': {
        'description': """
        SHORT STRANGLE
        - Vente d'un call OTM et d'un put OTM (strikes différents)
        - Profit: somme des primes reçues
        - Risque: illimité des deux côtés
        - Vue: faible volatilité, plus large que straddle
        """,
        'legs': [
            {'type': 'put', 'position': 'short', 'param_prefix': 'put', 'offset': -2},
            {'type': 'call', 'position': 'short', 'param_prefix': 'call', 'offset': 2}
        ],
        'max_loss_formula': 'unlimited',
        'breakeven_formula': lambda self: [
            self.put_strike - (self.put_premium + self.call_premium),
            self.call_strike + (self.put_premium + self.call_premium)
        ]
    },
    
    'IronCondor': {
        'description': """
        IRON CONDOR
        - Bull Put Spread + Bear Call Spread
        - 4 strikes: put_low < put_high < call_low < call_high
        - Profit: crédit net reçu
        - Risque: largeur du spread - crédit
        - Vue: faible volatilité, range trading
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'long_put', 'offset': -6},
            {'type': 'put', 'position': 'short', 'param_prefix': 'short_put', 'offset': -3},
            {'type': 'call', 'position': 'short', 'param_prefix': 'short_call', 'offset': 3},
            {'type': 'call', 'position': 'long', 'param_prefix': 'long_call', 'offset': 6}
        ],
        'max_loss_formula': lambda self: max(
            self.short_put_strike - self.long_put_strike,
            self.long_call_strike - self.short_call_strike
        ) - self.total_premium_received(),
        'breakeven_formula': lambda self: [
            self.short_put_strike - self.total_premium_received(),
            self.short_call_strike + self.total_premium_received()
        ]
    },
    
    'IronButterfly': {
        'description': """
        IRON BUTTERFLY
        - Short straddle ATM + Long strangle pour protection
        - 3 strikes: put_low < ATM < call_high
        - Profit: crédit net reçu
        - Risque: largeur du spread - crédit
        - Vue: très faible volatilité, prix reste au strike ATM
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'long_put', 'offset': -3},
            {'type': 'put', 'position': 'short', 'param_prefix': 'atm_put', 'offset': 0},
            {'type': 'call', 'position': 'short', 'param_prefix': 'atm_call', 'offset': 0},
            {'type': 'call', 'position': 'long', 'param_prefix': 'long_call', 'offset': 3}
        ],
        'max_loss_formula': lambda self: max(
            self.atm_put_strike - self.long_put_strike,
            self.long_call_strike - self.atm_call_strike
        ) - self.total_premium_received(),
        'breakeven_formula': lambda self: [
            self.atm_put_strike - self.total_premium_received(),
            self.atm_call_strike + self.total_premium_received()
        ]
    },
    
    'BullPutSpread': {
        'description': """
        BULL PUT SPREAD (Credit Spread)
        - Vente put strike haut + achat put strike bas
        - Profit: crédit net reçu
        - Risque: largeur du spread - crédit
        - Vue: neutre à haussière
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'long_put', 'offset': -6},
            {'type': 'put', 'position': 'short', 'param_prefix': 'short_put', 'offset': -3}
        ],
        'max_loss_formula': lambda self: (
            self.short_put_strike - self.long_put_strike - self.total_premium_received()
        ) * self.quantity,
        'breakeven_formula': lambda self: [self.short_put_strike - self.total_premium_received()]
    },
    
    'BearCallSpread': {
        'description': """
        BEAR CALL SPREAD (Credit Spread)
        - Vente call strike bas + achat call strike haut
        - Profit: crédit net reçu
        - Risque: largeur du spread - crédit
        - Vue: neutre à baissière
        """,
        'legs': [
            {'type': 'call', 'position': 'short', 'param_prefix': 'short_call', 'offset': 3},
            {'type': 'call', 'position': 'long', 'param_prefix': 'long_call', 'offset': 6}
        ],
        'max_loss_formula': lambda self: (
            self.long_call_strike - self.short_call_strike - self.total_premium_received()
        ) * self.quantity,
        'breakeven_formula': lambda self: [self.short_call_strike + self.total_premium_received()]
    },
    
    # =========================================================================
    # STRATÉGIES LONG (ACHAT) - Position haussière/volatilité
    # =========================================================================
    
    'LongCall': {
        'description': """
        LONG CALL (Achat de Call)
        - Achat d'un call
        - Profit: illimité (si spot → ∞)
        - Risque: prime payée
        - Vue: haussière
        """,
        'legs': [
            {'type': 'call', 'position': 'long', 'param_prefix': 'long_call', 'offset': 2}
        ],
        'max_loss_formula': lambda self: -self.long_call_premium * self.quantity,
        'breakeven_formula': lambda self: [self.long_call_strike + self.long_call_premium]
    },
    
    'LongPut': {
        'description': """
        LONG PUT (Achat de Put)
        - Achat d'un put
        - Profit: strike - prime (si spot → 0)
        - Risque: prime payée
        - Vue: baissière
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'long_put', 'offset': -2}
        ],
        'max_loss_formula': lambda self: -self.long_put_premium * self.quantity,
        'breakeven_formula': lambda self: [self.long_put_strike - self.long_put_premium]
    },
    
    'LongStraddle': {
        'description': """
        LONG STRADDLE
        - Achat d'un call et d'un put au même strike (ATM)
        - Profit: illimité des deux côtés
        - Risque: somme des primes payées
        - Vue: forte volatilité attendue, direction incertaine
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'put', 'offset': 0},
            {'type': 'call', 'position': 'long', 'param_prefix': 'call', 'offset': 0}
        ],
        'max_loss_formula': lambda self: -(self.put_premium + self.call_premium) * self.quantity,
        'breakeven_formula': lambda self: [
            self.put_strike - (self.put_premium + self.call_premium),
            self.call_strike + (self.put_premium + self.call_premium)
        ]
    },
    
    'LongStrangle': {
        'description': """
        LONG STRANGLE
        - Achat d'un call OTM et d'un put OTM (strikes différents)
        - Profit: illimité des deux côtés
        - Risque: somme des primes payées
        - Vue: forte volatilité, moins cher qu'un straddle
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'put', 'offset': -2},
            {'type': 'call', 'position': 'long', 'param_prefix': 'call', 'offset': 2}
        ],
        'max_loss_formula': lambda self: -(self.put_premium + self.call_premium) * self.quantity,
        'breakeven_formula': lambda self: [
            self.put_strike - (self.put_premium + self.call_premium),
            self.call_strike + (self.put_premium + self.call_premium)
        ]
    },
    
    # =========================================================================
    # SPREADS DÉBIT (DEBIT SPREADS) - Directionnels avec risque limité
    # =========================================================================
    
    'BullCallSpread': {
        'description': """
        BULL CALL SPREAD (Debit Spread)
        - Achat call strike bas + vente call strike haut
        - Profit: largeur du spread - débit payé
        - Risque: débit payé
        - Vue: modérément haussière
        """,
        'legs': [
            {'type': 'call', 'position': 'long', 'param_prefix': 'long_call', 'offset': -3},
            {'type': 'call', 'position': 'short', 'param_prefix': 'short_call', 'offset': 3}
        ],
        'max_loss_formula': lambda self: -(
            self.long_call_premium - self.short_call_premium
        ) * self.quantity,
        'breakeven_formula': lambda self: [
            self.long_call_strike + (self.long_call_premium - self.short_call_premium)
        ]
    },
    
    'BearPutSpread': {
        'description': """
        BEAR PUT SPREAD (Debit Spread)
        - Achat put strike haut + vente put strike bas
        - Profit: largeur du spread - débit payé
        - Risque: débit payé
        - Vue: modérément baissière
        """,
        'legs': [
            {'type': 'put', 'position': 'short', 'param_prefix': 'short_put', 'offset': -6},
            {'type': 'put', 'position': 'long', 'param_prefix': 'long_put', 'offset': -3}
        ],
        'max_loss_formula': lambda self: -(
            self.long_put_premium - self.short_put_premium
        ) * self.quantity,
        'breakeven_formula': lambda self: [
            self.long_put_strike - (self.long_put_premium - self.short_put_premium)
        ]
    },
    
    # =========================================================================
    # BUTTERFLY & CONDOR SPREADS - Neutral, profit au centre
    # =========================================================================
    
    'LongCallButterfly': {
        'description': """
        LONG CALL BUTTERFLY
        - Achat 1 call bas + vente 2 calls ATM + achat 1 call haut
        - Profit: max si prix = strike central à l'expiration
        - Risque: débit payé
        - Vue: très faible volatilité, prix stable au centre
        """,
        'legs': [
            {'type': 'call', 'position': 'long', 'param_prefix': 'lower_call', 'offset': -3},
            {'type': 'call', 'position': 'short', 'param_prefix': 'middle_call', 'offset': 0},
            {'type': 'call', 'position': 'short', 'param_prefix': 'middle_call2', 'offset': 0},
            {'type': 'call', 'position': 'long', 'param_prefix': 'upper_call', 'offset': 3}
        ],
        'max_loss_formula': lambda self: -(
            self.lower_call_premium + self.upper_call_premium - 
            self.middle_call_premium - self.middle_call2_premium
        ) * self.quantity,
        'breakeven_formula': lambda self: [
            self.lower_call_strike + (self.lower_call_premium + self.upper_call_premium - 
                                      self.middle_call_premium - self.middle_call2_premium),
            self.upper_call_strike - (self.lower_call_premium + self.upper_call_premium - 
                                      self.middle_call_premium - self.middle_call2_premium)
        ]
    },
    
    'LongPutButterfly': {
        'description': """
        LONG PUT BUTTERFLY
        - Achat 1 put haut + vente 2 puts ATM + achat 1 put bas
        - Profit: max si prix = strike central à l'expiration
        - Risque: débit payé
        - Vue: très faible volatilité, prix stable au centre
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'upper_put', 'offset': 3},
            {'type': 'put', 'position': 'short', 'param_prefix': 'middle_put', 'offset': 0},
            {'type': 'put', 'position': 'short', 'param_prefix': 'middle_put2', 'offset': 0},
            {'type': 'put', 'position': 'long', 'param_prefix': 'lower_put', 'offset': -3}
        ],
        'max_loss_formula': lambda self: -(
            self.upper_put_premium + self.lower_put_premium - 
            self.middle_put_premium - self.middle_put2_premium
        ) * self.quantity,
        'breakeven_formula': lambda self: [
            self.lower_put_strike + (self.upper_put_premium + self.lower_put_premium - 
                                     self.middle_put_premium - self.middle_put2_premium),
            self.upper_put_strike - (self.upper_put_premium + self.lower_put_premium - 
                                     self.middle_put_premium - self.middle_put2_premium)
        ]
    },
    
    # =========================================================================
    # RATIO SPREADS - Positions asymétriques
    # =========================================================================
    
    'CallRatioSpread': {
        'description': """
        CALL RATIO SPREAD
        - Achat 1 call ATM + vente 2 calls OTM
        - Profit: max si prix = strike call vendu à l'expiration
        - Risque: illimité à la hausse
        - Vue: légèrement haussière, volatilité faible
        """,
        'legs': [
            {'type': 'call', 'position': 'long', 'param_prefix': 'long_call', 'offset': 0},
            {'type': 'call', 'position': 'short', 'param_prefix': 'short_call1', 'offset': 3},
            {'type': 'call', 'position': 'short', 'param_prefix': 'short_call2', 'offset': 3}
        ],
        'max_loss_formula': 'unlimited',
        'breakeven_formula': lambda self: [
            self.long_call_strike + (self.long_call_premium - 
                                     self.short_call1_premium - self.short_call2_premium),
            self.short_call1_strike + ((self.short_call1_strike - self.long_call_strike) - 
                                       (self.long_call_premium - self.short_call1_premium - 
                                        self.short_call2_premium))
        ]
    },
    
    'PutRatioSpread': {
        'description': """
        PUT RATIO SPREAD
        - Achat 1 put ATM + vente 2 puts OTM
        - Profit: max si prix = strike put vendu à l'expiration
        - Risque: important à la baisse
        - Vue: légèrement baissière, volatilité faible
        """,
        'legs': [
            {'type': 'put', 'position': 'long', 'param_prefix': 'long_put', 'offset': 0},
            {'type': 'put', 'position': 'short', 'param_prefix': 'short_put1', 'offset': -3},
            {'type': 'put', 'position': 'short', 'param_prefix': 'short_put2', 'offset': -3}
        ],
        'max_loss_formula': lambda self: (
            2 * self.short_put1_strike - self.long_put_strike + 
            (self.long_put_premium - self.short_put1_premium - self.short_put2_premium)
        ) * self.quantity,
        'breakeven_formula': lambda self: [
            self.short_put1_strike - ((self.long_put_strike - self.short_put1_strike) - 
                                      (self.long_put_premium - self.short_put1_premium - 
                                       self.short_put2_premium)),
            self.long_put_strike - (self.long_put_premium - 
                                    self.short_put1_premium - self.short_put2_premium)
        ]
    }
}


# =============================================================================
# GÉNÉRATION AUTOMATIQUE DE TOUTES LES STRATÉGIES
# =============================================================================

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


# Générer toutes les stratégies automatiquement
GENERATED_STRATEGIES = generate_all_strategies()

# =============================================================================
# EXPORTS - Toutes les stratégies générées dynamiquement
# =============================================================================

# Stratégies SHORT (Vente) - Position neutre/range
ShortPut = GENERATED_STRATEGIES['ShortPut']
ShortCall = GENERATED_STRATEGIES['ShortCall']
ShortStraddle = GENERATED_STRATEGIES['ShortStraddle']
ShortStrangle = GENERATED_STRATEGIES['ShortStrangle']

# Stratégies IRON (Définies) - Risque/reward défini
IronCondor = GENERATED_STRATEGIES['IronCondor']
IronButterfly = GENERATED_STRATEGIES['IronButterfly']

# Credit Spreads - Vente nette
BullPutSpread = GENERATED_STRATEGIES['BullPutSpread']
BearCallSpread = GENERATED_STRATEGIES['BearCallSpread']

# Stratégies LONG (Achat) - Position directionnelle/volatilité
LongCall = GENERATED_STRATEGIES['LongCall']
LongPut = GENERATED_STRATEGIES['LongPut']
LongStraddle = GENERATED_STRATEGIES['LongStraddle']
LongStrangle = GENERATED_STRATEGIES['LongStrangle']

# Debit Spreads - Achat net directionnel
BullCallSpread = GENERATED_STRATEGIES['BullCallSpread']
BearPutSpread = GENERATED_STRATEGIES['BearPutSpread']

# Butterfly Spreads - Profit au centre
LongCallButterfly = GENERATED_STRATEGIES['LongCallButterfly']
LongPutButterfly = GENERATED_STRATEGIES['LongPutButterfly']

# Ratio Spreads - Positions asymétriques
CallRatioSpread = GENERATED_STRATEGIES['CallRatioSpread']
PutRatioSpread = GENERATED_STRATEGIES['PutRatioSpread']
BearCallSpread = GENERATED_STRATEGIES['BearCallSpread']