"""
Générateur Automatique de Condors (Iron Condor, Call/Put Condor)
=================================================================
Génère toutes les combinaisons possibles de Condor à partir des données Bloomberg.

"""

from typing import List, Dict, Tuple, Optional, Union, Literal
from dataclasses import dataclass, field
from datetime import datetime
from .option_class import Option
from .option_utils import dict_to_option, calculate_greeks_from_options


@dataclass
class CondorConfiguration:
    """Configuration d'un Condor avec liste d'options unifiée"""
    name: str
    condor_type: Literal['iron', 'call', 'put']
    
    # 4 strikes pour un Condor
    strike1: float  # Lower
    strike2: float  # Lower-middle
    strike3: float  # Upper-middle
    strike4: float  # Upper
    
    expiration_date: str
    
    # Liste unifiée d'options (simplifie tout!)
    all_options: List[Option] = field(default_factory=list)
    
    # Données des options Bloomberg (temporaire, pour compatibilité)
    option1: Optional[Dict] = None
    option2: Optional[Dict] = None
    option3: Optional[Dict] = None
    option4: Optional[Dict] = None
    
    # Métriques
    lower_spread_width: float = 0.0  # strike2 - strike1
    upper_spread_width: float = 0.0  # strike4 - strike3
    body_width: float = 0.0  # strike3 - strike2
    is_symmetric: bool = False
    center_strike: float = 0.0
    
    def __post_init__(self):
        """Calcule les métriques et construit all_options"""
        self.lower_spread_width = round(self.strike2 - self.strike1, 2)
        self.upper_spread_width = round(self.strike4 - self.strike3, 2)
        self.body_width = round(self.strike3 - self.strike2, 2)
        self.center_strike = round((self.strike2 + self.strike3) / 2, 2)
        
        # Symétrique si les spreads ont la même largeur
        self.is_symmetric = abs(self.lower_spread_width - self.upper_spread_width) < 0.01
        
        # Construire all_options à partir des dicts Bloomberg
        if all([self.option1, self.option2, self.option3, self.option4]):
            self._build_options_list()
    
    def _build_options_list(self):
        """Construit la liste unifiée d'Option objects selon le type de Condor"""
        self.all_options = []
        
        if self.condor_type == 'iron':
            # Iron Condor = Short Put Spread + Short Call Spread
            # Option1: Long lower put, Option2: Short higher put
            # Option3: Short lower call, Option4: Long higher call
            
            if self.option1:
                opt1 = dict_to_option(self.option1, position='long', quantity=1)
                if opt1:
                    self.all_options.append(opt1)
            
            if self.option2:
                opt2 = dict_to_option(self.option2, position='short', quantity=1)
                if opt2:
                    self.all_options.append(opt2)
            
            if self.option3:
                opt3 = dict_to_option(self.option3, position='short', quantity=1)
                if opt3:
                    self.all_options.append(opt3)
            
            if self.option4:
                opt4 = dict_to_option(self.option4, position='long', quantity=1)
                if opt4:
                    self.all_options.append(opt4)
        
        else:
            # Call/Put Condor: Long 1 + Short 1 + Short 1 + Long 1
            if self.option1:
                opt1 = dict_to_option(self.option1, position='long', quantity=1)
                if opt1:
                    self.all_options.append(opt1)
            
            if self.option2:
                opt2 = dict_to_option(self.option2, position='short', quantity=1)
                if opt2:
                    self.all_options.append(opt2)
            
            if self.option3:
                opt3 = dict_to_option(self.option3, position='short', quantity=1)
                if opt3:
                    self.all_options.append(opt3)
            
            if self.option4:
                opt4 = dict_to_option(self.option4, position='long', quantity=1)
                if opt4:
                    self.all_options.append(opt4)
    
    @property
    def strikes_str(self) -> str:
        """Format lisible des strikes"""
        return f"{self.strike1}/{self.strike2}/{self.strike3}/{self.strike4}"
    
    @property
    def estimated_credit(self) -> float:
        """Crédit estimé calculé depuis all_options"""
        if not self.all_options:
            return 0.0
        
        total_credit = 0.0
        for opt in self.all_options:
            # Long = payer (négatif), Short = recevoir (positif)
            multiplier = opt.quantity * (-1 if opt.position == 'long' else 1)
            total_credit += opt.premium * multiplier
        
        return round(total_credit, 4)
    
    @property
    def total_delta(self) -> float:
        """Delta total calculé depuis all_options"""
        greeks = calculate_greeks_from_options(self.all_options)
        return greeks['delta']
    
    @property
    def total_gamma(self) -> float:
        """Gamma total calculé depuis all_options"""
        greeks = calculate_greeks_from_options(self.all_options)
        return greeks['gamma']
    
    @property
    def total_vega(self) -> float:
        """Vega total calculé depuis all_options"""
        greeks = calculate_greeks_from_options(self.all_options)
        return greeks['vega']
    
    @property
    def total_theta(self) -> float:
        """Theta total calculé depuis all_options"""
        greeks = calculate_greeks_from_options(self.all_options)
        return greeks['theta']
    
    def to_standard_options_list(self) -> List[Dict]:
        """
        Convertit la configuration en liste d'options standardisée
        Compatible avec StrategyComparer et autres modules
        
        Returns:
            Liste de dictionnaires d'options au format standard Bloomberg
        """
        options_list = []
        
        if self.option1:
            options_list.append(self.option1.copy())
        
        if self.option2:
            options_list.append(self.option2.copy())
        
        if self.option3:
            options_list.append(self.option3.copy())
        
        if self.option4:
            options_list.append(self.option4.copy())
        
        return options_list
    
    def to_strategy_dict(self) -> Dict:
        """
        Convertit la configuration en dictionnaire de stratégie standard
        
        Returns:
            Dictionnaire avec tous les champs nécessaires pour créer une stratégie
        """
        return {
            'name': self.name,
            'type': f'{self.condor_type}_condor',
            'condor_type': self.condor_type,
            'strikes': [self.strike1, self.strike2, self.strike3, self.strike4],
            'expiration_date': self.expiration_date,
            'structure': {
                'strike1': self.strike1,
                'strike2': self.strike2,
                'strike3': self.strike3,
                'strike4': self.strike4,
                'lower_spread_width': self.lower_spread_width,
                'upper_spread_width': self.upper_spread_width,
                'body_width': self.body_width,
                'is_symmetric': self.is_symmetric
            },
            'metrics': {
                'estimated_credit': self.estimated_credit,
                'center_strike': self.center_strike,
                'avg_spread_width': (self.lower_spread_width + self.upper_spread_width) / 2
            },
            'options': self.to_standard_options_list()
        }


class CondorGenerator:
    """
    Générateur de toutes les combinaisons possibles de Condor
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
        """
        data = self.calls_data if option_type.lower() == 'call' else self.puts_data
        expirations = [opt['expiration_date'] for opt in data]
        return sorted(set(expirations))
    
    def generate_iron_condors(self,
                              price_min: float,
                              price_max: float,
                              strike_min: float,
                              strike_max: float,
                              expiration_date: Optional[str] = None,
                              require_symmetric: bool = False,
                              min_spread_width: float = 0.25,
                              max_spread_width: float = 5.0,
                              min_body_width: float = 0.5,
                              max_body_width: float = 10.0) -> List[CondorConfiguration]:
        """
        Génère toutes les combinaisons possibles d'Iron Condor
        
        Iron Condor = Short Put Spread + Short Call Spread
        Structure: Long Put (strike1) + Short Put (strike2) + Short Call (strike3) + Long Call (strike4)
        """
        condors = []
        
        # Déterminer les expirations à traiter
        if expiration_date:
            expirations = [expiration_date]
        else:
            # Pour Iron Condor, on a besoin des deux types
            call_exps = set(self.get_available_expirations('call'))
            put_exps = set(self.get_available_expirations('put'))
            expirations = sorted(call_exps & put_exps)  # Intersection
        
        # Pour chaque expiration
        for exp_date in expirations:
            # Récupérer les strikes disponibles pour calls et puts
            call_strikes = self.get_available_strikes('call', exp_date)
            put_strikes = self.get_available_strikes('put', exp_date)
            
            # On a besoin des mêmes strikes pour calls et puts
            common_strikes = sorted(set(call_strikes) & set(put_strikes))
            
            # Filtrer dans les bornes
            valid_strikes = [s for s in common_strikes if strike_min <= s <= strike_max]
            
            if len(valid_strikes) < 4:
                continue  # Pas assez de strikes pour un Condor
            
            # Générer toutes les combinaisons de 4 strikes
            for i, s1 in enumerate(valid_strikes):
                for j, s2 in enumerate(valid_strikes[i+1:], start=i+1):
                    for k, s3 in enumerate(valid_strikes[j+1:], start=j+1):
                        for l, s4 in enumerate(valid_strikes[k+1:], start=k+1):
                            # Calculer les métriques
                            lower_spread = s2 - s1
                            upper_spread = s4 - s3
                            body = s3 - s2
                            center = (s2 + s3) / 2
                            
                            # Vérifier que le centre est dans l'intervalle de prix
                            if not (price_min <= center <= price_max):
                                continue
                            
                            # Vérifier les contraintes de largeur
                            if lower_spread < min_spread_width or lower_spread > max_spread_width:
                                continue
                            if upper_spread < min_spread_width or upper_spread > max_spread_width:
                                continue
                            if body < min_body_width or body > max_body_width:
                                continue
                            
                            # Vérifier la symétrie si requis
                            if require_symmetric and abs(lower_spread - upper_spread) > 0.01:
                                continue
                            
                            # Récupérer les options
                            put1 = self.puts_by_strike_exp.get((s1, exp_date))
                            put2 = self.puts_by_strike_exp.get((s2, exp_date))
                            call3 = self.calls_by_strike_exp.get((s3, exp_date))
                            call4 = self.calls_by_strike_exp.get((s4, exp_date))
                            
                            # Vérifier que toutes les options existent
                            if not all([put1, put2, call3, call4]):
                                continue
                            
                            # Créer la configuration
                            condor = CondorConfiguration(
                                name=f"IronCondor {s1}/{s2}/{s3}/{s4}",
                                condor_type='iron',
                                strike1=s1,
                                strike2=s2,
                                strike3=s3,
                                strike4=s4,
                                expiration_date=exp_date,
                                option1=put1,
                                option2=put2,
                                option3=call3,
                                option4=call4
                            )
                            
                            condors.append(condor)
        
        return condors
    
    def generate_call_condors(self,
                             price_min: float,
                             price_max: float,
                             strike_min: float,
                             strike_max: float,
                             expiration_date: Optional[str] = None,
                             require_symmetric: bool = False,
                             min_wing_width: float = 0.25,
                             max_wing_width: float = 5.0,
                             min_body_width: float = 0.5,
                             max_body_width: float = 10.0) -> List[CondorConfiguration]:
        """
        Génère toutes les combinaisons possibles de Call Condor
        
        Call Condor = Long lower call + Short 2 middle calls + Long upper call
        """
        return self._generate_single_type_condors(
            option_type='call',
            price_min=price_min,
            price_max=price_max,
            strike_min=strike_min,
            strike_max=strike_max,
            expiration_date=expiration_date,
            require_symmetric=require_symmetric,
            min_wing_width=min_wing_width,
            max_wing_width=max_wing_width,
            min_body_width=min_body_width,
            max_body_width=max_body_width
        )
    
    def generate_put_condors(self,
                            price_min: float,
                            price_max: float,
                            strike_min: float,
                            strike_max: float,
                            expiration_date: Optional[str] = None,
                            require_symmetric: bool = False,
                            min_wing_width: float = 0.25,
                            max_wing_width: float = 5.0,
                            min_body_width: float = 0.5,
                            max_body_width: float = 10.0) -> List[CondorConfiguration]:
        """
        Génère toutes les combinaisons possibles de Put Condor
        
        Put Condor = Long lower put + Short 2 middle puts + Long upper put
        
        """
        return self._generate_single_type_condors(
            option_type='put',
            price_min=price_min,
            price_max=price_max,
            strike_min=strike_min,
            strike_max=strike_max,
            expiration_date=expiration_date,
            require_symmetric=require_symmetric,
            min_wing_width=min_wing_width,
            max_wing_width=max_wing_width,
            min_body_width=min_body_width,
            max_body_width=max_body_width
        )
    
    def _generate_single_type_condors(self,
                                     option_type: str,
                                     price_min: float,
                                     price_max: float,
                                     strike_min: float,
                                     strike_max: float,
                                     expiration_date: Optional[str] = None,
                                     require_symmetric: bool = False,
                                     min_wing_width: float = 0.25,
                                     max_wing_width: float = 5.0,
                                     min_body_width: float = 0.5,
                                     max_body_width: float = 10.0) -> List[CondorConfiguration]:
        """Génère des Condors d'un seul type (call ou put)"""
        condors = []
        
        # Déterminer les expirations
        if expiration_date:
            expirations = [expiration_date]
        else:
            expirations = self.get_available_expirations(option_type)
        
        # Pour chaque expiration
        for exp_date in expirations:
            # Récupérer les strikes disponibles
            available_strikes = self.get_available_strikes(option_type, exp_date)
            
            # Filtrer dans les bornes
            valid_strikes = [s for s in available_strikes if strike_min <= s <= strike_max]
            
            if len(valid_strikes) < 4:
                continue
            
            # Générer toutes les combinaisons de 4 strikes
            for i, s1 in enumerate(valid_strikes):
                for j, s2 in enumerate(valid_strikes[i+1:], start=i+1):
                    for k, s3 in enumerate(valid_strikes[j+1:], start=j+1):
                        for l, s4 in enumerate(valid_strikes[k+1:], start=k+1):
                            # Calculer les métriques
                            lower_wing = s2 - s1
                            upper_wing = s4 - s3
                            body = s3 - s2
                            center = (s2 + s3) / 2
                            
                            # Vérifier contraintes
                            if not (price_min <= center <= price_max):
                                continue
                            
                            if lower_wing < min_wing_width or lower_wing > max_wing_width:
                                continue
                            if upper_wing < min_wing_width or upper_wing > max_wing_width:
                                continue
                            if body < min_body_width or body > max_body_width:
                                continue
                            
                            if require_symmetric and abs(lower_wing - upper_wing) > 0.01:
                                continue
                            
                            # Récupérer les options
                            index = self.calls_by_strike_exp if option_type.lower() == 'call' else self.puts_by_strike_exp
                            
                            opt1 = index.get((s1, exp_date))
                            opt2 = index.get((s2, exp_date))
                            opt3 = index.get((s3, exp_date))
                            opt4 = index.get((s4, exp_date))
                            
                            if not all([opt1, opt2, opt3, opt4]):
                                continue
                            
                            # Créer la configuration
                            condor_type = 'call' if option_type.lower() == 'call' else 'put'
                            name = f"Long{'Call' if condor_type == 'call' else 'Put'}Condor {s1}/{s2}/{s3}/{s4}"
                            
                            condor = CondorConfiguration(
                                name=name,
                                condor_type=condor_type,
                                strike1=s1,
                                strike2=s2,
                                strike3=s3,
                                strike4=s4,
                                expiration_date=exp_date,
                                option1=opt1,
                                option2=opt2,
                                option3=opt3,
                                option4=opt4
                            )
                            
                            condors.append(condor)
        
        return condors
    
    def get_options_list(self,
                        price_min: float,
                        price_max: float,
                        strike_min: float,
                        strike_max: float,
                        condor_type: str = 'iron',
                        expiration_date: Optional[str] = None,
                        require_symmetric: bool = False,
                        min_spread_width: float = 0.25,
                        max_spread_width: float = 5.0,
                        min_body_width: float = 0.5,
                        max_body_width: float = 10.0,
                        deduplicate: bool = True) -> List[Dict]:
        """
        Génère tous les Condors et retourne directement une liste d'options standardisée
        
        MÉTHODE PRINCIPALE pour obtenir une liste d'options prête à l'emploi.

        """
        # Générer les Condors selon le type
        if condor_type.lower() == 'iron':
            condors = self.generate_iron_condors(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                expiration_date=expiration_date,
                require_symmetric=require_symmetric,
                min_spread_width=min_spread_width,
                max_spread_width=max_spread_width,
                min_body_width=min_body_width,
                max_body_width=max_body_width
            )
        elif condor_type.lower() == 'call':
            condors = self.generate_call_condors(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                expiration_date=expiration_date,
                require_symmetric=require_symmetric,
                min_wing_width=min_spread_width,
                max_wing_width=max_spread_width,
                min_body_width=min_body_width,
                max_body_width=max_body_width
            )
        elif condor_type.lower() == 'put':
            condors = self.generate_put_condors(
                price_min=price_min,
                price_max=price_max,
                strike_min=strike_min,
                strike_max=strike_max,
                expiration_date=expiration_date,
                require_symmetric=require_symmetric,
                min_wing_width=min_spread_width,
                max_wing_width=max_spread_width,
                min_body_width=min_body_width,
                max_body_width=max_body_width
            )
        else:
            raise ValueError(f"Type de Condor '{condor_type}' non reconnu. "
                           f"Utilisez 'iron', 'call' ou 'put'")
        
        if not condors:
            return []
        
        if deduplicate:
            # Retourner une liste dédupliquée
            all_options = {}
            for condor in condors:
                for opt in condor.to_standard_options_list():
                    key = (opt['strike'], opt['expiration_date'], opt['option_type'])
                    all_options[key] = opt
            return list(all_options.values())
        else:
            # Retourner toutes les options (avec duplicatas possibles)
            all_options = []
            for condor in condors:
                all_options.extend(condor.to_standard_options_list())
            return all_options