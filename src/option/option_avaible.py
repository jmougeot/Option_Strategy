
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
