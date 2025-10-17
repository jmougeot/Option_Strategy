"""
Module d'Exploration des Strikes pour Stratégies d'Options
===========================================================

Ce module génère automatiquement toutes les combinaisons possibles de strikes
pour différentes stratégies d'options (Fly, Condor, Spreads, etc.).

Caractéristiques:
- Bornes configurables (strike min/max)
- Pas configurable (0.5, 1, etc.)
- Génération exhaustive de toutes les combinaisons valides
- Filtres de validité (distances minimales/maximales entre strikes)
- Support de toutes les stratégies multi-jambes

Auteur: BGC Trading Desk
Date: 2025-10-17
"""

from typing import List, Dict, Tuple, Iterator
from itertools import combinations


class StrikeExplorer:
    """
    Générateur de combinaisons de strikes pour stratégies d'options.
    """
    
    def __init__(self, strike_min: float, strike_max: float, step: float = 0.5):
        """
        Initialise l'explorateur de strikes.
        
        Args:
            strike_min: Strike minimum (borne basse)
            strike_max: Strike maximum (borne haute)
            step: Pas entre les strikes (ex: 0.5, 1)
        """
        self.strike_min = strike_min
        self.strike_max = strike_max
        self.step = step
        
        # Générer tous les strikes possibles
        self.available_strikes = self._generate_strikes()
    
    def _generate_strikes(self) -> List[float]:
        """
        Génère tous les strikes disponibles dans la plage.
        
        Returns:
            Liste des strikes triés
        """
        strikes = []
        current = self.strike_min
        
        while current <= self.strike_max:
            strikes.append(round(current, 2))  # Arrondir pour éviter les erreurs de float
            current += self.step
        
        return sorted(strikes)
    
    def get_available_strikes(self) -> List[float]:
        """Retourne la liste des strikes disponibles."""
        return self.available_strikes.copy()
    
    # ========================================================================
    # BUTTERFLY (3 strikes: Low / Middle / High)
    # ========================================================================
    
    def generate_butterfly_combinations(
        self,
        min_wing_distance: float = 0.5,
        max_wing_distance: float = None,
        symmetric_only: bool = False
    ) -> Iterator[Dict[str, float]]:
        """
        Génère toutes les combinaisons valides pour un Butterfly.
        
        Structure: Vendre 2 ATM, Acheter 1 Low + 1 High
        Exemple: 97 / 100 / 103 (achète 97, vend 2x100, achète 103)
        
        Args:
            min_wing_distance: Distance minimale entre les ailes et le centre
            max_wing_distance: Distance maximale entre les ailes et le centre
            symmetric_only: Si True, génère seulement les Fly symétriques
        
        Yields:
            Dict avec {'low_strike', 'middle_strike', 'high_strike'}
        """
        if max_wing_distance is None:
            max_wing_distance = (self.strike_max - self.strike_min) / 2
        
        for middle in self.available_strikes:
            for low in self.available_strikes:
                if low >= middle:
                    continue
                
                distance_low = middle - low
                if distance_low < min_wing_distance or distance_low > max_wing_distance:
                    continue
                
                for high in self.available_strikes:
                    if high <= middle:
                        continue
                    
                    distance_high = high - middle
                    if distance_high < min_wing_distance or distance_high > max_wing_distance:
                        continue
                    
                    # Si symétrique uniquement, vérifier l'égalité des distances
                    if symmetric_only and distance_low != distance_high:
                        continue
                    
                    yield {
                        'low_strike': low,
                        'middle_strike': middle,
                        'high_strike': high,
                        'wing_distance_low': distance_low,
                        'wing_distance_high': distance_high,
                        'total_width': high - low,
                        'is_symmetric': (distance_low == distance_high)
                    }
    
    # ========================================================================
    # CONDOR (4 strikes: Low / Middle_Low / Middle_High / High)
    # ========================================================================
    
    def generate_condor_combinations(
        self,
        min_wing_distance: float = 0.5,
        max_wing_distance: float = None,
        min_body_width: float = 0.5,
        max_body_width: float = None,
        symmetric_only: bool = False
    ) -> Iterator[Dict[str, float]]:
        """
        Génère toutes les combinaisons valides pour un Iron Condor.
        
        Structure: Achète Low Put, Vend Middle_Low Put, Vend Middle_High Call, Achète High Call
        Exemple: 95 / 97 / 99 / 101
        
        Args:
            min_wing_distance: Distance minimale entre ailes et corps
            max_wing_distance: Distance maximale entre ailes et corps
            min_body_width: Largeur minimale du corps (distance middle_low - middle_high)
            max_body_width: Largeur maximale du corps
            symmetric_only: Si True, génère seulement les Condors symétriques
        
        Yields:
            Dict avec {'low_strike', 'middle_low_strike', 'middle_high_strike', 'high_strike'}
        """
        if max_wing_distance is None:
            max_wing_distance = (self.strike_max - self.strike_min) / 3
        if max_body_width is None:
            max_body_width = (self.strike_max - self.strike_min) / 2
        
        for middle_low in self.available_strikes:
            for middle_high in self.available_strikes:
                if middle_high <= middle_low:
                    continue
                
                body_width = middle_high - middle_low
                if body_width < min_body_width or body_width > max_body_width:
                    continue
                
                for low in self.available_strikes:
                    if low >= middle_low:
                        continue
                    
                    distance_low = middle_low - low
                    if distance_low < min_wing_distance or distance_low > max_wing_distance:
                        continue
                    
                    for high in self.available_strikes:
                        if high <= middle_high:
                            continue
                        
                        distance_high = high - middle_high
                        if distance_high < min_wing_distance or distance_high > max_wing_distance:
                            continue
                        
                        # Si symétrique uniquement
                        if symmetric_only and distance_low != distance_high:
                            continue
                        
                        yield {
                            'low_strike': low,
                            'middle_low_strike': middle_low,
                            'middle_high_strike': middle_high,
                            'high_strike': high,
                            'wing_distance_low': distance_low,
                            'wing_distance_high': distance_high,
                            'body_width': body_width,
                            'total_width': high - low,
                            'is_symmetric': (distance_low == distance_high)
                        }
    
    # ========================================================================
    # SPREADS (2 strikes: Low / High)
    # ========================================================================
    
    def generate_spread_combinations(
        self,
        min_width: float = 0.5,
        max_width: float = None
    ) -> Iterator[Dict[str, float]]:
        """
        Génère toutes les combinaisons valides pour un Spread (Bull/Bear).
        
        Structure: 2 strikes (achète Low, vend High pour Bull Call)
        Exemple: 97 / 99, 98 / 100, etc.
        
        Args:
            min_width: Largeur minimale du spread
            max_width: Largeur maximale du spread
        
        Yields:
            Dict avec {'low_strike', 'high_strike'}
        """
        if max_width is None:
            max_width = self.strike_max - self.strike_min
        
        for low in self.available_strikes:
            for high in self.available_strikes:
                if high <= low:
                    continue
                
                width = high - low
                if width < min_width or width > max_width:
                    continue
                
                yield {
                    'low_strike': low,
                    'high_strike': high,
                    'width': width
                }
    
    # ========================================================================
    # STRADDLE / STRANGLE (1 ou 2 strikes)
    # ========================================================================
    
    def generate_straddle_strikes(self) -> Iterator[Dict[str, float]]:
        """
        Génère tous les strikes pour Straddle (1 strike).
        
        Yields:
            Dict avec {'strike'}
        """
        for strike in self.available_strikes:
            yield {'strike': strike}
    
    def generate_strangle_combinations(
        self,
        min_width: float = 0.5,
        max_width: float = None
    ) -> Iterator[Dict[str, float]]:
        """
        Génère toutes les combinaisons pour Strangle (2 strikes différents).
        
        Structure: Put strike < Call strike
        Exemple: 97P / 99C, 96P / 100C, etc.
        
        Args:
            min_width: Distance minimale entre put et call
            max_width: Distance maximale entre put et call
        
        Yields:
            Dict avec {'put_strike', 'call_strike'}
        """
        if max_width is None:
            max_width = self.strike_max - self.strike_min
        
        for put_strike in self.available_strikes:
            for call_strike in self.available_strikes:
                if call_strike <= put_strike:
                    continue
                
                width = call_strike - put_strike
                if width < min_width or width > max_width:
                    continue
                
                yield {
                    'put_strike': put_strike,
                    'call_strike': call_strike,
                    'width': width
                }
    
    # ========================================================================
    # RATIO SPREADS (2 strikes avec ratios différents)
    # ========================================================================
    
    def generate_ratio_spread_combinations(
        self,
        min_width: float = 0.5,
        max_width: float = None,
        ratios: List[Tuple[int, int]] = [(1, 2), (1, 3), (2, 3)]
    ) -> Iterator[Dict[str, any]]:
        """
        Génère toutes les combinaisons pour Ratio Spreads.
        
        Structure: Achète X options à un strike, vend Y options à un autre
        Exemple: Achète 1 @ 98, Vend 2 @ 100 (ratio 1:2)
        
        Args:
            min_width: Largeur minimale
            max_width: Largeur maximale
            ratios: Liste des ratios possibles (buy, sell)
        
        Yields:
            Dict avec {'low_strike', 'high_strike', 'ratio_buy', 'ratio_sell'}
        """
        if max_width is None:
            max_width = self.strike_max - self.strike_min
        
        for low in self.available_strikes:
            for high in self.available_strikes:
                if high <= low:
                    continue
                
                width = high - low
                if width < min_width or width > max_width:
                    continue
                
                for ratio_buy, ratio_sell in ratios:
                    yield {
                        'low_strike': low,
                        'high_strike': high,
                        'width': width,
                        'ratio_buy': ratio_buy,
                        'ratio_sell': ratio_sell,
                        'ratio': f"{ratio_buy}:{ratio_sell}"
                    }
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def count_combinations(self, strategy_type: str, **kwargs) -> int:
        """
        Compte le nombre de combinaisons possibles pour une stratégie.
        
        Args:
            strategy_type: Type de stratégie ('butterfly', 'condor', 'spread', etc.)
            **kwargs: Paramètres pour le générateur
        
        Returns:
            Nombre de combinaisons
        """
        generators = {
            'butterfly': self.generate_butterfly_combinations,
            'condor': self.generate_condor_combinations,
            'spread': self.generate_spread_combinations,
            'straddle': self.generate_straddle_strikes,
            'strangle': self.generate_strangle_combinations,
            'ratio_spread': self.generate_ratio_spread_combinations
        }
        
        if strategy_type not in generators:
            raise ValueError(f"Strategy type '{strategy_type}' not supported")
        
        generator = generators[strategy_type]
        return sum(1 for _ in generator(**kwargs))
    
    def get_summary(self) -> Dict[str, any]:
        """
        Retourne un résumé de l'explorateur.
        
        Returns:
            Dict avec statistiques
        """
        return {
            'strike_range': f"{self.strike_min} - {self.strike_max}",
            'step': self.step,
            'num_strikes': len(self.available_strikes),
            'available_strikes': self.available_strikes,
            'total_combinations': {
                'butterfly': self.count_combinations('butterfly'),
                'butterfly_symmetric': self.count_combinations('butterfly', symmetric_only=True),
                'condor': self.count_combinations('condor'),
                'condor_symmetric': self.count_combinations('condor', symmetric_only=True),
                'spread': self.count_combinations('spread'),
                'straddle': self.count_combinations('straddle'),
                'strangle': self.count_combinations('strangle'),
            }
        }


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def print_combinations_sample(
    explorer: StrikeExplorer,
    strategy_type: str,
    max_display: int = 10,
    **kwargs
):
    """
    Affiche un échantillon de combinaisons générées.
    
    Args:
        explorer: Instance de StrikeExplorer
        strategy_type: Type de stratégie
        max_display: Nombre maximum de combinaisons à afficher
        **kwargs: Paramètres pour le générateur
    """
    generators = {
        'butterfly': explorer.generate_butterfly_combinations,
        'condor': explorer.generate_condor_combinations,
        'spread': explorer.generate_spread_combinations,
        'straddle': explorer.generate_straddle_strikes,
        'strangle': explorer.generate_strangle_combinations,
        'ratio_spread': explorer.generate_ratio_spread_combinations
    }
    
    if strategy_type not in generators:
        print(f"❌ Strategy type '{strategy_type}' not supported")
        return
    
    generator = generators[strategy_type]
    
    print(f"\n{'='*70}")
    print(f"{strategy_type.upper()} - Échantillon de combinaisons")
    print(f"{'='*70}")
    
    count = 0
    for combo in generator(**kwargs):
        count += 1
        if count <= max_display:
            print(f"{count}. {combo}")
        else:
            break
    
    total = count + sum(1 for _ in generator(**kwargs))
    
    if total > max_display:
        print(f"\n... et {total - max_display} autres combinaisons")
    
    print(f"\nTotal: {total} combinaisons possibles")
    print(f"{'='*70}\n")


# ============================================================================
# DEMO / TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("STRIKE EXPLORER - DEMO")
    print("="*70 + "\n")
    
    # Créer un explorateur avec les paramètres de l'exemple
    explorer = StrikeExplorer(strike_min=97, strike_max=103, step=0.5)
    
    # Afficher le résumé
    summary = explorer.get_summary()
    print(f"Plage de strikes: {summary['strike_range']}")
    print(f"Pas: {summary['step']}")
    print(f"Nombre de strikes: {summary['num_strikes']}")
    print(f"Strikes disponibles: {summary['available_strikes']}")
    print()
    
    # Afficher les statistiques
    print("Nombre de combinaisons possibles:")
    print("-" * 70)
    for strategy, count in summary['total_combinations'].items():
        print(f"  {strategy:25} : {count:6,} combinaisons")
    print()
    
    # Exemples de Butterfly
    print_combinations_sample(explorer, 'butterfly', max_display=8)
    
    # Exemples de Butterfly symétriques uniquement
    print_combinations_sample(explorer, 'butterfly', max_display=8, symmetric_only=True)
    
    # Exemples de Condor
    print_combinations_sample(explorer, 'condor', max_display=8)
    
    # Exemples de Spread
    print_combinations_sample(explorer, 'spread', max_display=8, max_width=3)
    
    # Exemples de Strangle
    print_combinations_sample(explorer, 'strangle', max_display=8, max_width=5)
    
    print("\n✅ Demo terminée!\n")
