from dataclasses import dataclass, field
from math import log, sqrt, exp, pi, erf
from typing import Literal, Optional, List, Tuple
from datetime import datetime

"""
Stratégies Short Volatility
============================
Définition des principales stratégies de vente de volatilité:
- Short Put / Call
- Short Straddle
- Short Strangle
- Iron Condor
- Iron Butterfly
- Credit Spreads (Bull Put, Bear Call)
"""


@dataclass
class Option:
    """Représente une option (call ou put)"""
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
    """Classe de base pour les stratégies short volatility"""
    name: str
    underlying_price: float
    options: List[Option] = field(default_factory=list)
    
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
# STRATÉGIES SHORT VOLATILITY
# =============================================================================


@dataclass
class ShortPut(OptionStrategy):
    """
    SHORT PUT (Vente de Put)
    ------------------------
    - Vente d'un put
    - Profit: prime reçue
    - Risque: strike - prime (si spot → 0)
    - Vue: neutre à haussière
    """
    strike: float = 0.0
    premium: float = 0.0
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        """Initialise la stratégie après création du dataclass"""
        if not self.name:
            self.name = "Short Put"
        
        put_option = Option(
            option_type='put',
            strike=self.strike,
            premium=self.premium,
            expiry=self.expiry,
            quantity=self.quantity,
            position='short'
        )
        self.add_option(put_option)
    
    def max_loss(self) -> float:
        """Perte maximum = strike - prime reçue"""
        return (self.strike - self.premium) * self.quantity
    
    def breakeven_points(self) -> List[float]:
        """Point de breakeven = strike - prime"""
        return [self.strike - self.premium]


@dataclass
class ShortCall(OptionStrategy):
    """
    SHORT CALL (Vente de Call)
    ---------------------------
    - Vente d'un call
    - Profit: prime reçue
    - Risque: illimité (si spot → ∞)
    - Vue: neutre à baissière
    """
    strike: float = 0.0
    premium: float = 0.0
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        if not self.name:
            self.name = "Short Call"
        
        call_option = Option(
            option_type='call',
            strike=self.strike,
            premium=self.premium,
            expiry=self.expiry,
            quantity=self.quantity,
            position='short'
        )
        self.add_option(call_option)
    
    def max_loss(self) -> str:
        """Risque illimité"""
        return "Illimité (théoriquement)"
    
    def breakeven_points(self) -> List[float]:
        """Point de breakeven = strike + prime"""
        return [self.strike + self.premium]


@dataclass
class ShortStraddle(OptionStrategy):
    """
    SHORT STRADDLE
    --------------
    - Vente d'un call et d'un put au même strike (ATM)
    - Profit: somme des primes reçues
    - Risque: illimité des deux côtés
    - Vue: faible volatilité, marché range
    """
    strike: float = 0.0
    call_premium: float = 0.0
    put_premium: float = 0.0
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        if not self.name:
            self.name = "Short Straddle"
        
        # Ajouter le call short
        self.add_option(Option(
            option_type='call',
            strike=self.strike,
            premium=self.call_premium,
            expiry=self.expiry,
            quantity=self.quantity,
            position='short'
        ))
        
        # Ajouter le put short
        self.add_option(Option(
            option_type='put',
            strike=self.strike,
            premium=self.put_premium,
            expiry=self.expiry,
            quantity=self.quantity,
            position='short'
        ))
    
    def max_loss(self) -> str:
        return "Illimité des deux côtés"
    
    def breakeven_points(self) -> List[float]:
        """Deux points: strike ± (call_premium + put_premium)"""
        total_premium = self.call_premium + self.put_premium
        return [
            self.strike - total_premium,  # Breakeven bas
            self.strike + total_premium   # Breakeven haut
        ]


@dataclass
class ShortStrangle(OptionStrategy):
    """
    SHORT STRANGLE
    --------------
    - Vente d'un call OTM et d'un put OTM (strikes différents)
    - Profit: somme des primes reçues
    - Risque: illimité des deux côtés
    - Vue: faible volatilité, plus large que straddle
    """
    put_strike: float = 0.0
    call_strike: float = 0.0
    put_premium: float = 0.0
    call_premium: float = 0.0
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        if not self.name:
            self.name = "Short Strangle"
        
        # Put OTM (strike plus bas)
        self.add_option(Option(
            option_type='put',
            strike=self.put_strike,
            premium=self.put_premium,
            expiry=self.expiry,
            quantity=self.quantity,
            position='short'
        ))
        
        # Call OTM (strike plus haut)
        self.add_option(Option(
            option_type='call',
            strike=self.call_strike,
            premium=self.call_premium,
            expiry=self.expiry,
            quantity=self.quantity,
            position='short'
        ))
    
    def max_loss(self) -> str:
        return "Illimité des deux côtés"
    
    def breakeven_points(self) -> List[float]:
        total_premium = self.put_premium + self.call_premium
        return [
            self.put_strike - total_premium,   # Breakeven bas
            self.call_strike + total_premium   # Breakeven haut
        ]


@dataclass
class IronCondor(OptionStrategy):
    """
    IRON CONDOR
    -----------
    - Bull Put Spread + Bear Call Spread
    - 4 strikes: put_low < put_high < call_low < call_high
    - Profit: crédit net reçu
    - Risque: largeur du spread - crédit
    - Vue: faible volatilité, range trading
    """
    put_strike_low: float = 0.0      # Put long (protection)
    put_strike_high: float = 0.0     # Put short (vente)
    call_strike_low: float = 0.0     # Call short (vente)
    call_strike_high: float = 0.0    # Call long (protection)
    
    put_premium_low: float = 0.0     # Prime payée pour put long
    put_premium_high: float = 0.0    # Prime reçue pour put short
    call_premium_low: float = 0.0    # Prime reçue pour call short
    call_premium_high: float = 0.0   # Prime payée pour call long
    
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        if not self.name:
            self.name = "Iron Condor"
        
        # Put Spread (Bull Put Spread)
        self.add_option(Option('put', self.put_strike_low, self.put_premium_low, 
                              self.expiry, self.quantity, 'long'))
        self.add_option(Option('put', self.put_strike_high, self.put_premium_high, 
                              self.expiry, self.quantity, 'short'))
        
        # Call Spread (Bear Call Spread)
        self.add_option(Option('call', self.call_strike_low, self.call_premium_low, 
                              self.expiry, self.quantity, 'short'))
        self.add_option(Option('call', self.call_strike_high, self.call_premium_high, 
                              self.expiry, self.quantity, 'long'))
    
    def max_loss(self) -> float:
        """Perte max = largeur du spread - crédit net"""
        put_spread_width = self.put_strike_high - self.put_strike_low
        call_spread_width = self.call_strike_high - self.call_strike_low
        max_spread = max(put_spread_width, call_spread_width)
        return (max_spread - self.total_premium_received()) * self.quantity
    
    def breakeven_points(self) -> List[float]:
        net_credit = self.total_premium_received()
        return [
            self.put_strike_high - net_credit,   # Breakeven bas
            self.call_strike_low + net_credit    # Breakeven haut
        ]


@dataclass
class IronButterfly(OptionStrategy):
    """
    IRON BUTTERFLY (FLY)
    --------------------
    - Short straddle ATM + Long strangle pour protection
    - 3 strikes: put_low < ATM < call_high
    - Profit: crédit net reçu
    - Risque: largeur du spread - crédit
    - Vue: très faible volatilité, prix reste au strike ATM
    """
    long_put_strike: float = 0.0     # Put long (protection)
    atm_strike: float = 0.0          # Strike ATM (short put + short call)
    long_call_strike: float = 0.0    # Call long (protection)
    
    long_put_premium: float = 0.0    # Prime payée
    short_put_premium: float = 0.0   # Prime reçue
    short_call_premium: float = 0.0  # Prime reçue
    long_call_premium: float = 0.0   # Prime payée
    
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        if not self.name:
            self.name = "Iron Butterfly"
        
        # Long put (protection)
        self.add_option(Option('put', self.long_put_strike, self.long_put_premium,
                              self.expiry, self.quantity, 'long'))
        # Short put ATM
        self.add_option(Option('put', self.atm_strike, self.short_put_premium,
                              self.expiry, self.quantity, 'short'))
        # Short call ATM
        self.add_option(Option('call', self.atm_strike, self.short_call_premium,
                              self.expiry, self.quantity, 'short'))
        # Long call (protection)
        self.add_option(Option('call', self.long_call_strike, self.long_call_premium,
                              self.expiry, self.quantity, 'long'))
    
    def max_loss(self) -> float:
        """Perte max = largeur du spread - crédit net"""
        put_width = self.atm_strike - self.long_put_strike
        call_width = self.long_call_strike - self.atm_strike
        max_width = max(put_width, call_width)
        return (max_width - self.total_premium_received()) * self.quantity
    
    def breakeven_points(self) -> List[float]:
        net_credit = self.total_premium_received()
        return [
            self.atm_strike - net_credit,   # Breakeven bas
            self.atm_strike + net_credit    # Breakeven haut
        ]


@dataclass
class BullPutSpread(OptionStrategy):
    """
    BULL PUT SPREAD (Credit Spread)
    --------------------------------
    - Vente put strike haut + achat put strike bas
    - Profit: crédit net reçu
    - Risque: largeur du spread - crédit
    - Vue: neutre à haussière
    """
    long_put_strike: float = 0.0     # Put long (protection)
    short_put_strike: float = 0.0    # Put short (vente)
    long_put_premium: float = 0.0    # Prime payée
    short_put_premium: float = 0.0   # Prime reçue
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        if not self.name:
            self.name = "Bull Put Spread"
        
        self.add_option(Option('put', self.long_put_strike, self.long_put_premium,
                              self.expiry, self.quantity, 'long'))
        self.add_option(Option('put', self.short_put_strike, self.short_put_premium,
                              self.expiry, self.quantity, 'short'))
    
    def max_loss(self) -> float:
        """Perte max = largeur du spread - crédit net"""
        width = self.short_put_strike - self.long_put_strike
        return (width - self.total_premium_received()) * self.quantity
    
    def breakeven_points(self) -> List[float]:
        return [self.short_put_strike - self.total_premium_received()]


@dataclass
class BearCallSpread(OptionStrategy):
    """
    BEAR CALL SPREAD (Credit Spread)
    ---------------------------------
    - Vente call strike bas + achat call strike haut
    - Profit: crédit net reçu
    - Risque: largeur du spread - crédit
    - Vue: neutre à baissière
    """
    short_call_strike: float = 0.0    # Call short (vente)
    long_call_strike: float = 0.0     # Call long (protection)
    short_call_premium: float = 0.0   # Prime reçue
    long_call_premium: float = 0.0    # Prime payée
    expiry: datetime = field(default_factory=datetime.now)
    quantity: int = 1
    
    def __post_init__(self):
        if not self.name:
            self.name = "Bear Call Spread"
        
        self.add_option(Option('call', self.short_call_strike, self.short_call_premium,
                              self.expiry, self.quantity, 'short'))
        self.add_option(Option('call', self.long_call_strike, self.long_call_premium,
                              self.expiry, self.quantity, 'long'))
    
    def max_loss(self) -> float:
        """Perte max = largeur du spread - crédit net"""
        width = self.long_call_strike - self.short_call_strike
        return (width - self.total_premium_received()) * self.quantity
    
    def breakeven_points(self) -> List[float]:
        return [self.short_call_strike + self.total_premium_received()]
