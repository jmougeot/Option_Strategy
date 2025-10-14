"""
Comparaison de Stratégies d'Options
====================================
Compare différentes stratégies short volatility centrées autour d'un prix cible
pour une date d'expiration donnée.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from strategies import (
    OptionStrategy, ShortPut, ShortCall, ShortStraddle, ShortStrangle,
    IronCondor, IronButterfly, BullPutSpread, BearCallSpread
)


@dataclass
class StrategyComparison:
    """Résultat de comparaison d'une stratégie"""
    strategy_name: str
    strategy: OptionStrategy
    target_price: float
    expiration_date: datetime
    days_to_expiry: int
    
    # Métriques financières
    net_credit: float
    max_profit: float
    max_loss: float
    breakeven_points: List[float]
    
    # Métriques de risque
    profit_range: Tuple[float, float]  # Range de prix profitable
    profit_zone_width: float  # Largeur de la zone profitable
    risk_reward_ratio: float  # Max loss / Max profit
    
    # Performance au prix cible
    profit_at_target: float
    profit_at_target_pct: float  # % du max profit
    
    # Score et ranking
    score: float = 0.0
    rank: int = 0


class StrategyComparer:
    """Compare différentes stratégies d'options"""
    
    # Mapping des noms de stratégies vers les classes
    STRATEGY_CLASSES = {
        'iron_condor': IronCondor,
        'iron_butterfly': IronButterfly,
        'short_strangle': ShortStrangle,
        'short_straddle': ShortStraddle,
        'bull_put_spread': BullPutSpread,
        'bear_call_spread': BearCallSpread,
        'short_put': ShortPut,
        'short_call': ShortCall
    }
    
    def __init__(self, options_data: Dict[str, List[Dict]]):
        """
        Args:
            options_data: Dictionnaire avec 'calls' et 'puts' contenant les données d'options
                         Format: {'calls': [...], 'puts': [...]}
        """
        self.calls_data = options_data.get('calls', [])
        self.puts_data = options_data.get('puts', [])
    
    def build_strategy(self,
                      strategy_name: str,
                      target_price: float,
                      days_to_expiry: int) -> Optional[OptionStrategy]:
        """
        Méthode générique pour construire n'importe quelle stratégie
        La configuration est lue directement depuis la classe de stratégie.
        
        Args:
            strategy_name: Nom de la stratégie (ex: 'iron_condor', 'bull_put_spread')
            target_price: Prix cible
            days_to_expiry: Jours jusqu'à expiration
        
        Returns:
            Instance de la stratégie ou None si impossible à construire
        """
        # Vérifier que la stratégie existe
        if strategy_name not in self.STRATEGY_CLASSES:
            print(f"❌ Stratégie inconnue: {strategy_name}")
            return None
        
        strategy_class = self.STRATEGY_CLASSES[strategy_name]
        config = strategy_class.BUILD_CONFIG
        
        if not config:
            print(f"❌ Configuration manquante pour {strategy_name}")
            return None
        
        # Collecter les options et construire les paramètres
        strikes = {}
        premiums = {}
        exp_date = None
        
        for leg in config['legs']:
            # Calculer le strike
            strike = round((target_price + leg['offset']) * 2) / 2
            
            # Trouver l'option
            option = self.find_closest_option(strike, days_to_expiry, leg['type'])
            if not option:
                print(f"⚠ Option {leg['type']} à {strike} introuvable pour {strategy_name}")
                return None
            
            # Stocker strike et premium avec les noms corrects des paramètres
            strikes[leg['strike_param']] = option['strike']
            premiums[leg['premium_param']] = option['premium']
            
            # Prendre la date d'expiration de la première option
            if exp_date is None:
                exp_date = datetime.strptime(option['expiration_date'], "%Y-%m-%d")
        
        # Construire les kwargs pour la stratégie
        kwargs = {
            'underlying_price': target_price,
            'expiry': exp_date,
            **strikes,
            **premiums
        }
        
        # Créer le nom de la stratégie
        kwargs['name'] = config['name_format'].format(**strikes)
        
        # Instancier la stratégie
        try:
            strategy = strategy_class(**kwargs)
            return strategy
        except Exception as e:
            print(f"❌ Erreur lors de la création de {strategy_name}: {e}")
            return None
    
    def find_closest_option(self, 
                           strike_target: float,
                           days_target: int,
                           option_type: str,
                           tolerance_days: int = 5) -> Optional[Dict]:
        """
        Trouve l'option la plus proche des critères
        
        Args:
            strike_target: Strike cible
            days_target: Jours jusqu'à expiration cible
            option_type: 'call' ou 'put'
            tolerance_days: Tolérance sur les jours
        
        Returns:
            Données de l'option ou None
        """
        data = self.calls_data if option_type.lower() == 'call' else self.puts_data
        
        today = datetime.now()
        best_option = None
        min_diff = float('inf')
        
        for opt in data:
            # Vérifier le strike
            strike_diff = abs(opt['strike'] - strike_target)
            if strike_diff > 0.5:  # Tolérance de 0.5 sur le strike
                continue
            
            # Vérifier les jours
            exp_date = datetime.strptime(opt['expiration_date'], "%Y-%m-%d")
            dte = (exp_date - today).days
            
            if abs(dte - days_target) > tolerance_days:
                continue
            
            # Calculer la différence totale
            total_diff = strike_diff + abs(dte - days_target) * 0.1
            
            if total_diff < min_diff:
                min_diff = total_diff
                best_option = opt
        
        return best_option
    
    def analyze_strategy(self,
                        strategy: OptionStrategy,
                        target_price: float,
                        expiration_date: datetime,
                        price_range: Tuple[float, float] = None) -> StrategyComparison:
        """
        Analyse complète d'une stratégie
        
        Args:
            strategy: Stratégie à analyser
            target_price: Prix cible
            expiration_date: Date d'expiration
            price_range: Range de prix pour l'analyse (min, max)
        
        Returns:
            StrategyComparison avec toutes les métriques
        """
        # Calculer les jours jusqu'à expiration
        days_to_expiry = (expiration_date - datetime.now()).days
        
        # Métriques de base
        net_credit = strategy.total_premium_received()
        max_profit = strategy.max_profit()
        
        # Calculer la perte maximale
        try:
            max_loss = strategy.max_loss()
            if isinstance(max_loss, str):  # "Illimité"
                max_loss = -999999.0  # Valeur symbolique
        except:
            max_loss = -999999.0
        
        # Points de breakeven
        try:
            breakeven_points = strategy.breakeven_points()
        except:
            breakeven_points = []
        
        # Déterminer la range profitable
        if len(breakeven_points) >= 2:
            profit_range = (min(breakeven_points), max(breakeven_points))
            profit_zone_width = profit_range[1] - profit_range[0]
        else:
            profit_range = (0.0, float('inf'))
            profit_zone_width = float('inf')
        
        # Risk/Reward ratio
        if max_loss != 0 and max_loss != -999999.0:
            risk_reward_ratio = abs(max_loss) / max_profit if max_profit > 0 else 0
        else:
            risk_reward_ratio = float('inf')
        
        # Performance au prix cible
        profit_at_target = strategy.profit_at_expiry(target_price)
        profit_at_target_pct = (profit_at_target / max_profit * 100) if max_profit > 0 else 0
        
        return StrategyComparison(
            strategy_name=strategy.name,
            strategy=strategy,
            target_price=target_price,
            expiration_date=expiration_date,
            days_to_expiry=days_to_expiry,
            net_credit=net_credit,
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven_points=breakeven_points,
            profit_range=profit_range,
            profit_zone_width=profit_zone_width,
            risk_reward_ratio=risk_reward_ratio,
            profit_at_target=profit_at_target,
            profit_at_target_pct=profit_at_target_pct
        )
    
    def compare_strategies(self,
                          target_price: float,
                          days_to_expiry: int,
                          strategies_to_compare: List[str] = None,
                          weights: Dict[str, float] = None) -> List[StrategyComparison]:
        """
        Compare plusieurs stratégies centrées sur le prix cible
        
        Args:
            target_price: Prix cible
            days_to_expiry: Jours jusqu'à expiration
            strategies_to_compare: Liste des stratégies à comparer
                                  ['iron_condor', 'iron_butterfly', 'short_strangle', 'short_straddle']
            weights: Poids pour le scoring
                    {'max_profit': 0.3, 'risk_reward': 0.3, 'profit_zone': 0.2, 'target_performance': 0.2}
        
        Returns:
            Liste triée de StrategyComparison
        """
        if strategies_to_compare is None:
            strategies_to_compare = ['iron_condor', 'iron_butterfly', 'short_strangle', 'short_straddle']
        
        if weights is None:
            weights = {
                'max_profit': 0.25,
                'risk_reward': 0.25,
                'profit_zone': 0.25,
                'target_performance': 0.25
            }
        
        comparisons = []
        
        # Construire et analyser chaque stratégie avec la méthode générique
        for strat_name in strategies_to_compare:
            strategy = self.build_strategy(strat_name, target_price, days_to_expiry)
            
            if strategy is None:
                print(f"⚠ Impossible de construire: {strat_name}")
                continue
            
            # Analyser la stratégie
            exp_date = strategy.expiry if hasattr(strategy, 'expiry') else datetime.now() + timedelta(days=days_to_expiry)
            comparison = self.analyze_strategy(strategy, target_price, exp_date)
            comparisons.append(comparison)
        
        # Calculer les scores
        if comparisons:
            comparisons = self._calculate_scores(comparisons, weights)
            comparisons.sort(key=lambda x: x.score, reverse=True)
            
            # Attribuer les rangs
            for i, comp in enumerate(comparisons, 1):
                comp.rank = i
        
        return comparisons
    
    def _calculate_scores(self,
                         comparisons: List[StrategyComparison],
                         weights: Dict[str, float]) -> List[StrategyComparison]:
        """Calcule les scores composites pour chaque stratégie"""
        
        # Trouver les valeurs max pour normalisation
        max_profit_val = max(c.max_profit for c in comparisons)
        max_zone_width = max(c.profit_zone_width for c in comparisons if c.profit_zone_width != float('inf'))
        max_target_perf = max(c.profit_at_target_pct for c in comparisons)
        
        # Risk/reward: plus bas est mieux (inverse la normalisation)
        risk_rewards = [c.risk_reward_ratio for c in comparisons if c.risk_reward_ratio != float('inf')]
        min_rr = min(risk_rewards) if risk_rewards else 1
        max_rr = max(risk_rewards) if risk_rewards else 10
        
        for comp in comparisons:
            score = 0.0
            
            # 1. Max profit (plus élevé = mieux)
            if 'max_profit' in weights and max_profit_val > 0:
                normalized_profit = comp.max_profit / max_profit_val if max_profit_val > 0 else 0
                score += normalized_profit * weights['max_profit']
            
            # 2. Risk/Reward (plus bas = mieux)
            if 'risk_reward' in weights and comp.risk_reward_ratio != float('inf'):
                if max_rr > min_rr:  # Éviter division par zéro
                    normalized_rr = 1 - ((comp.risk_reward_ratio - min_rr) / (max_rr - min_rr))
                else:
                    normalized_rr = 1.0  # Si tous égaux, score maximum
                score += normalized_rr * weights['risk_reward']
            
            # 3. Zone profitable (plus large = mieux)
            if 'profit_zone' in weights and comp.profit_zone_width != float('inf') and max_zone_width > 0:
                normalized_zone = comp.profit_zone_width / max_zone_width if max_zone_width > 0 else 0
                score += normalized_zone * weights['profit_zone']
            
            # 4. Performance au prix cible (plus proche de 100% = mieux)
            if 'target_performance' in weights and max_target_perf > 0:
                normalized_target = comp.profit_at_target_pct / max_target_perf if max_target_perf > 0 else 0
                score += normalized_target * weights['target_performance']
            
            comp.score = score
        
        return comparisons
    
    def display_comparison(self, comparisons: List[StrategyComparison]):
        """Affiche le tableau de comparaison des stratégies"""
        
        print("\n" + "="*130)
        print(f"COMPARAISON DES STRATÉGIES - Prix cible: ${comparisons[0].target_price:.2f} - DTE: {comparisons[0].days_to_expiry}j")
        print("="*130)
        print(f"{'Rank':<6} {'Stratégie':<25} {'Crédit':<10} {'Max Profit':<12} {'Max Loss':<12} "
              f"{'R/R Ratio':<10} {'Zone ±':<10} {'P&L@Target':<12} {'Score':<8}")
        print("-"*130)
        
        for comp in comparisons:
            max_loss_str = f"${abs(comp.max_loss):.2f}" if comp.max_loss != -999999.0 else "Illimité"
            rr_str = f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else "∞"
            zone_str = f"${comp.profit_zone_width:.2f}" if comp.profit_zone_width != float('inf') else "Illimité"
            
            print(f"{comp.rank:<6} {comp.strategy_name:<25} ${comp.net_credit:<9.2f} "
                  f"${comp.max_profit:<11.2f} {max_loss_str:<12} {rr_str:<10} {zone_str:<10} "
                  f"${comp.profit_at_target:<11.2f} {comp.score:<8.3f}")
        
        print("="*130)
        
        # Détails des breakevens
        print("\nPOINTS DE BREAKEVEN:")
        print("-"*80)
        for comp in comparisons:
            if comp.breakeven_points:
                be_str = ", ".join([f"${be:.2f}" for be in comp.breakeven_points])
                print(f"{comp.strategy_name:<25} : {be_str}")
        print("="*130 + "\n")
    
    def plot_strategy_comparison(self,
                                comparisons: List[StrategyComparison],
                                price_range: Tuple[float, float] = None):
        """
        Trace les diagrammes P&L de toutes les stratégies
        
        Args:
            comparisons: Liste des stratégies à tracer
            price_range: Range de prix (min, max) pour le graphique
        """
        try:
            import matplotlib.pyplot as plt
            import numpy as np
        except ImportError:
            print("⚠ matplotlib et numpy requis pour les graphiques")
            return
        
        if not comparisons:
            return
        
        # Déterminer la plage de prix
        if price_range is None:
            target = comparisons[0].target_price
            price_range = (target * 0.85, target * 1.15)
        
        spots = np.linspace(price_range[0], price_range[1], 200)
        
        plt.figure(figsize=(16, 10))
        
        # Tracer chaque stratégie
        for comp in comparisons:
            profits = [comp.strategy.profit_at_expiry(spot) for spot in spots]
            plt.plot(spots, profits, linewidth=2, label=f"{comp.strategy_name} (Score: {comp.score:.2f})")
        
        # Ligne zéro et prix cible
        plt.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
        plt.axvline(x=comparisons[0].target_price, color='green', linestyle=':', 
                   linewidth=2, alpha=0.7, label=f'Prix cible: ${comparisons[0].target_price:.2f}')
        
        plt.xlabel('Prix du sous-jacent à expiration', fontsize=12)
        plt.ylabel('Profit / Perte ($)', fontsize=12)
        plt.title(f'Comparaison des Stratégies - Prix cible: ${comparisons[0].target_price:.2f} - '
                 f'{comparisons[0].days_to_expiry} jours', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.legend(loc='best', fontsize=10)
        plt.tight_layout()
        plt.show()