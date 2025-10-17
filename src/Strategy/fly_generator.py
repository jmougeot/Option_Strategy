"""
Générateur Automatique de Butterflies
======================================
Génère toutes les combinaisons possibles de Butterfly (Fly) à partir des données Bloomberg.

Le module explore toutes les combinaisons où:
- La tête du Fly (middle strike) est comprise entre price_min et price_max
- Les jambes (lower et upper strikes) sont comprises entre strike_min et strike_max
- Les intervalles entre strikes respectent les contraintes définies

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


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
    
    def filter_flies(self,
                    flies: List[FlyConfiguration],
                    symmetric_only: bool = False,
                    max_cost: Optional[float] = None,
                    min_cost: Optional[float] = None,
                    wing_width: Optional[float] = None) -> List[FlyConfiguration]:
        """
        Filtre les configurations de Butterfly selon des critères
        
        Args:
            flies: Liste de configurations à filtrer
            symmetric_only: Garder uniquement les Flies symétriques
            max_cost: Coût maximum acceptable
            min_cost: Coût minimum acceptable
            wing_width: Largeur d'aile spécifique (pour Flies symétriques)
        
        Returns:
            Liste filtrée de configurations
        """
        filtered = flies.copy()
        
        if symmetric_only:
            filtered = [f for f in filtered if f.is_symmetric]
        
        if wing_width is not None:
            filtered = [f for f in filtered 
                       if abs(f.wing_width_lower - wing_width) < 0.01 
                       and abs(f.wing_width_upper - wing_width) < 0.01]
        
        if max_cost is not None:
            filtered = [f for f in filtered if f.estimated_cost <= max_cost]
        
        if min_cost is not None:
            filtered = [f for f in filtered if f.estimated_cost >= min_cost]
        
        return filtered
    
    def get_best_flies(self,
                      flies: List[FlyConfiguration],
                      criterion: str = 'cost',
                      top_n: int = 10) -> List[FlyConfiguration]:
        """
        Sélectionne les meilleurs Butterflies selon un critère
        
        Args:
            flies: Liste de configurations
            criterion: Critère de sélection ('cost', 'wing_width', 'symmetric')
            top_n: Nombre de résultats à retourner
        
        Returns:
            Liste des meilleurs Butterflies
        """
        if criterion == 'cost':
            # Trier par coût (débit le plus faible = meilleur)
            sorted_flies = sorted(flies, key=lambda f: abs(f.estimated_cost))
        elif criterion == 'wing_width':
            # Trier par largeur d'aile (plus étroit = meilleur)
            sorted_flies = sorted(flies, key=lambda f: (f.wing_width_lower + f.wing_width_upper) / 2)
        elif criterion == 'symmetric':
            # Trier par symétrie (plus symétrique = meilleur)
            sorted_flies = sorted(flies, key=lambda f: abs(f.wing_width_lower - f.wing_width_upper))
        else:
            sorted_flies = flies
        
        return sorted_flies[:top_n]
    
    def generate_statistics(self, flies: List[FlyConfiguration]) -> Dict:
        """
        Génère des statistiques sur les Butterflies générés
        
        Args:
            flies: Liste de configurations
        
        Returns:
            Dictionnaire avec les statistiques
        """
        if not flies:
            return {
                'total': 0,
                'symmetric': 0,
                'call_flies': 0,
                'put_flies': 0,
                'avg_cost': 0.0,
                'avg_wing_width': 0.0,
                'unique_middle_strikes': 0,
                'unique_expirations': 0
            }
        
        symmetric_count = sum(1 for f in flies if f.is_symmetric)
        call_count = sum(1 for f in flies if f.option_type.lower() == 'call')
        put_count = sum(1 for f in flies if f.option_type.lower() == 'put')
        
        avg_cost = sum(f.estimated_cost for f in flies) / len(flies)
        avg_wing = sum((f.wing_width_lower + f.wing_width_upper) / 2 for f in flies) / len(flies)
        
        unique_middles = len(set(f.middle_strike for f in flies))
        unique_exps = len(set(f.expiration_date for f in flies))
        
        return {
            'total': len(flies),
            'symmetric': symmetric_count,
            'call_flies': call_count,
            'put_flies': put_count,
            'avg_cost': round(avg_cost, 4),
            'avg_wing_width': round(avg_wing, 2),
            'unique_middle_strikes': unique_middles,
            'unique_expirations': unique_exps,
            'min_cost': round(min(f.estimated_cost for f in flies), 4),
            'max_cost': round(max(f.estimated_cost for f in flies), 4),
            'min_wing_width': round(min(f.wing_width_lower for f in flies), 2),
            'max_wing_width': round(max(f.wing_width_upper for f in flies), 2)
        }


def main():
    """Exemple d'utilisation"""
    print("=" * 70)
    print("GÉNÉRATEUR DE BUTTERFLIES")
    print("=" * 70)
    print()
    print("Ce module sera utilisé dans app.py pour générer")
    print("automatiquement toutes les combinaisons de Fly possibles.")
    print()
    print("Exemple d'utilisation:")
    print()
    print("  generator = FlyGenerator(options_data)")
    print("  flies = generator.generate_all_flies(")
    print("      price_min=97.0,")
    print("      price_max=103.0,")
    print("      strike_min=96.0,")
    print("      strike_max=104.0,")
    print("      option_type='call'")
    print("  )")
    print()
    print(f"Fonctionnalités:")
    print("  ✓ Génération automatique de toutes les combinaisons")
    print("  ✓ Filtrage par symétrie, coût, largeur d'aile")
    print("  ✓ Sélection des meilleurs Flies selon critères")
    print("  ✓ Statistiques détaillées")
    print()


if __name__ == "__main__":
    main()
