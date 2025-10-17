"""
Générateur Automatique de Butterflies
======================================
Génère toutes les combinaisons possibles de Butterfly à partir des données Bloomberg
et retourne une liste d'options standardisée.

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

from typing import List, Dict, Optional, Union
from dataclasses import dataclass


@dataclass
class FlyConfiguration:
    """Configuration d'un Butterfly"""
    name: str
    lower_strike: float
    middle_strike: float
    upper_strike: float
    option_type: str  # 'call' ou 'put'
    expiration_date: str
    
    # Données des options (si disponibles)
    lower_option: Optional[Dict] = None
    middle_option: Optional[Dict] = None
    upper_option: Optional[Dict] = None
    
    # Métriques
    wing_width_lower: float = 0.0  # middle - lower
    wing_width_upper: float = 0.0  # upper - middle
    is_symmetric: bool = False
    
    def __post_init__(self):
        """Calcule les métriques après initialisation"""
        self.wing_width_lower = round(self.middle_strike - self.lower_strike, 2)
        self.wing_width_upper = round(self.upper_strike - self.middle_strike, 2)
        self.is_symmetric = abs(self.wing_width_lower - self.wing_width_upper) < 0.01
    
    @property
    def strikes_str(self) -> str:
        """Format lisible des strikes"""
        return f"{self.lower_strike}/{self.middle_strike}/{self.upper_strike}"
    
    @property
    def estimated_cost(self) -> float:
        """Coût estimé (premium net)"""
        if not all([self.lower_option, self.middle_option, self.upper_option]):
            return 0.0
        
        # Fly = Long 1 lower + Short 2 middle + Long 1 upper
        cost = (
            -self.lower_option['premium']  # Long = payer
            + 2 * self.middle_option['premium']  # Short = recevoir
            - self.upper_option['premium']  # Long = payer
        )
        return round(cost, 4)
    
    @property
    def center_strike(self) -> float:
        """Strike central (middle strike)"""
        return self.middle_strike
    
    @property
    def lower_wing_width(self) -> float:
        """Alias pour compatibilité avec comparateur"""
        return self.wing_width_lower
    
    @property
    def upper_wing_width(self) -> float:
        """Alias pour compatibilité avec comparateur"""
        return self.wing_width_upper
    
    def to_standard_options_list(self) -> List[Dict]:
        """
        Convertit la configuration en liste d'options standardisée
        Compatible avec StrategyComparer et autres modules
        
        Returns:
            Liste de dictionnaires d'options au format standard Bloomberg
        """
        options_list = []
        
        if self.lower_option:
            options_list.append(self.lower_option.copy())
        
        if self.middle_option:
            # Pour un Fly, on a besoin de 2x le middle (short 2 contracts)
            options_list.append(self.middle_option.copy())
            options_list.append(self.middle_option.copy())
        
        if self.upper_option:
            options_list.append(self.upper_option.copy())
        
        return options_list
    
    def to_strategy_dict(self) -> Dict:
        """
        Convertit la configuration en dictionnaire de stratégie standard
        
        Returns:
            Dictionnaire avec tous les champs nécessaires pour créer une stratégie
        """
        return {
            'name': self.name,
            'type': 'butterfly',
            'option_type': self.option_type,
            'strikes': [self.lower_strike, self.middle_strike, self.upper_strike],
            'expiration_date': self.expiration_date,
            'structure': {
                'lower_strike': self.lower_strike,
                'middle_strike': self.middle_strike,
                'upper_strike': self.upper_strike,
                'wing_width_lower': self.wing_width_lower,
                'wing_width_upper': self.wing_width_upper,
                'is_symmetric': self.is_symmetric
            },
            'metrics': {
                'estimated_cost': self.estimated_cost,
                'center_strike': self.center_strike,
                'avg_wing_width': (self.wing_width_lower + self.wing_width_upper) / 2
            },
            'options': self.to_standard_options_list()
        }


class FlyGenerator:
    """
    Générateur de toutes les combinaisons possibles de Butterfly
    """
    
    def __init__(self, options_data: Dict[str, List[Dict]]):
        """
        Initialise le générateur avec les données d'options Bloomberg
        
        Args:
            options_data: Dictionnaire avec 'calls' et 'puts'
        """
        self.calls_data = options_data.get('calls', [])
        self.puts_data = options_data.get('puts', [])
        
        # Créer des index pour accès rapide
        self._index_options()
    
    def _index_options(self):
        """Crée des index pour accès rapide par strike et expiration"""
        self.calls_by_strike_exp = {}
        self.puts_by_strike_exp = {}
        
        for call in self.calls_data:
            key = (call['strike'], call['expiration_date'])
            self.calls_by_strike_exp[key] = call
        
        for put in self.puts_data:
            key = (put['strike'], put['expiration_date'])
            self.puts_by_strike_exp[key] = put
    
    def get_available_strikes(self, 
                             option_type: str = 'call',
                             expiration_date: Optional[str] = None) -> List[float]:
        """
        Récupère la liste des strikes disponibles
        
        Args:
            option_type: 'call' ou 'put'
            expiration_date: Filtrer par date d'expiration (optionnel)
        
        Returns:
            Liste triée des strikes disponibles
        """
        data = self.calls_data if option_type.lower() == 'call' else self.puts_data
        
        if expiration_date:
            strikes = [opt['strike'] for opt in data if opt['expiration_date'] == expiration_date]
        else:
            strikes = [opt['strike'] for opt in data]
        
        return sorted(set(strikes))
    
    def get_available_expirations(self, option_type: str = 'call') -> List[str]:
        """
        Récupère la liste des dates d'expiration disponibles
        
        Args:
            option_type: 'call' ou 'put'
        
        Returns:
            Liste triée des dates d'expiration
        """
        data = self.calls_data if option_type.lower() == 'call' else self.puts_data
        expirations = [opt['expiration_date'] for opt in data]
        return sorted(set(expirations))
    
    def generate_all_flies(self,
                          price_min: float,
                          price_max: float,
                          strike_min: float,
                          strike_max: float,
                          option_type: str = 'call',
                          expiration_date: Optional[str] = None,
                          require_symmetric: bool = False,
                          min_wing_width: float = 0.25,
                          max_wing_width: float = 5.0) -> List[FlyConfiguration]:
        """
        Génère toutes les combinaisons possibles de Butterfly
        
        Args:
            price_min: Prix minimum pour la tête du Fly (middle strike)
            price_max: Prix maximum pour la tête du Fly (middle strike)
            strike_min: Strike minimum pour les jambes (lower et upper)
            strike_max: Strike maximum pour les jambes (lower et upper)
            option_type: 'call' ou 'put'
            expiration_date: Date d'expiration (optionnel, sinon toutes)
            require_symmetric: Si True, ne génère que des Flies symétriques
            min_wing_width: Largeur minimale des ailes
            max_wing_width: Largeur maximale des ailes
        
        Returns:
            Liste de configurations de Butterfly
        """
        flies = []
        
        # Déterminer les expirations à traiter
        if expiration_date:
            expirations = [expiration_date]
        else:
            expirations = self.get_available_expirations(option_type)
        
        # Pour chaque expiration
        for exp_date in expirations:
            # Récupérer les strikes disponibles
            available_strikes = self.get_available_strikes(option_type, exp_date)
            
            # Filtrer les strikes dans les bornes
            valid_strikes = [s for s in available_strikes if strike_min <= s <= strike_max]
            
            if len(valid_strikes) < 3:
                continue  # Pas assez de strikes pour un Fly
            
            # Générer toutes les combinaisons de 3 strikes
            for i, lower in enumerate(valid_strikes):
                for j, middle in enumerate(valid_strikes[i+1:], start=i+1):
                    # Vérifier que middle est dans l'intervalle de prix
                    if not (price_min <= middle <= price_max):
                        continue
                    
                    for k, upper in enumerate(valid_strikes[j+1:], start=j+1):
                        # Calculer les largeurs d'ailes
                        wing_lower = middle - lower
                        wing_upper = upper - middle
                        
                        # Vérifier les contraintes de largeur
                        if wing_lower < min_wing_width or wing_lower > max_wing_width:
                            continue
                        if wing_upper < min_wing_width or wing_upper > max_wing_width:
                            continue
                        
                        # Vérifier la symétrie si requis
                        if require_symmetric and abs(wing_lower - wing_upper) > 0.01:
                            continue
                        
                        # Récupérer les options
                        index = self.calls_by_strike_exp if option_type.lower() == 'call' else self.puts_by_strike_exp
                        
                        lower_opt = index.get((lower, exp_date))
                        middle_opt = index.get((middle, exp_date))
                        upper_opt = index.get((upper, exp_date))
                        
                        # Vérifier que toutes les options existent
                        if not all([lower_opt, middle_opt, upper_opt]):
                            continue
                        
                        # Créer la configuration
                        fly_type = "Long" if option_type.lower() == 'call' else "Long"
                        fly_name = f"{fly_type}CallFly" if option_type.lower() == 'call' else f"{fly_type}PutFly"
                        
                        fly = FlyConfiguration(
                            name=f"{fly_name} {lower}/{middle}/{upper}",
                            lower_strike=lower,
                            middle_strike=middle,
                            upper_strike=upper,
                            option_type=option_type,
                            expiration_date=exp_date,
                            lower_option=lower_opt,
                            middle_option=middle_opt,
                            upper_option=upper_opt
                        )
                        
                        flies.append(fly)
        
        return flies
    
    def get_options_list(self,
                        price_min: float,
                        price_max: float,
                        strike_min: float,
                        strike_max: float,
                        option_type: str = 'call',
                        expiration_date: Optional[str] = None,
                        require_symmetric: bool = False,
                        min_wing_width: float = 0.25,
                        max_wing_width: float = 5.0,
                        deduplicate: bool = True) -> List[Dict]:
        """
        Génère tous les Flies et retourne directement une liste d'options standardisée
        """
        # Générer tous les Flies selon les critères
        flies = self.generate_all_flies(
            price_min=price_min,
            price_max=price_max,
            strike_min=strike_min,
            strike_max=strike_max,
            option_type=option_type,
            expiration_date=expiration_date,
            require_symmetric=require_symmetric,
            min_wing_width=min_wing_width,
            max_wing_width=max_wing_width
        )
        
        if not flies:
            return []
        
        if deduplicate:
            # Retourner une liste dédupliquée
            all_options = {}
            for fly in flies:
                for opt in fly.to_standard_options_list():
                    key = (opt['strike'], opt['expiration_date'], opt['option_type'])
                    all_options[key] = opt
            return list(all_options.values())
        else:
            # Retourner toutes les options (avec duplicatas possibles)
            all_options = []
            for fly in flies:
                all_options.extend(fly.to_standard_options_list())
            return all_options

