"""
Comparaison de Stratégies d'Options
====================================
Compare différentes stratégies short volatility centrées autour d'un prix cible
pour une date d'expiration donnée.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
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
    
    def __init__(self, options_data: Dict[str, List[Dict]]):
        """
        Args:
            options_data: Dictionnaire avec 'calls' et 'puts' contenant les données d'options
                         Format: {'calls': [...], 'puts': [...]}
        """
        self.calls_data = options_data.get('calls', [])
        self.puts_data = options_data.get('puts', [])
    
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
    
    def build_centered_iron_condor(self,
                                   target_price: float,
                                   days_to_expiry: int,
                                   wing_width: float = 5.0,
                                   body_width: float = 3.0) -> Optional[IronCondor]:
        """
        Construit un Iron Condor centré autour du prix cible
        
        Args:
            target_price: Prix cible (centre de la stratégie)
            days_to_expiry: Jours jusqu'à expiration
            wing_width: Largeur des ailes (écart entre short et long)
            body_width: Distance du corps au prix cible
        
        Returns:
            IronCondor ou None si données insuffisantes
        """
        # Calculer les strikes
        put_strike_high = target_price - body_width  # Short put
        put_strike_low = put_strike_high - wing_width  # Long put (protection)
        call_strike_low = target_price + body_width  # Short call
        call_strike_high = call_strike_low + wing_width  # Long call (protection)
        
        # Trouver les options
        long_put = self.find_closest_option(put_strike_low, days_to_expiry, 'put')
        short_put = self.find_closest_option(put_strike_high, days_to_expiry, 'put')
        short_call = self.find_closest_option(call_strike_low, days_to_expiry, 'call')
        long_call = self.find_closest_option(call_strike_high, days_to_expiry, 'call')
        
        if not all([long_put, short_put, short_call, long_call]):
            return None
        
        # Obtenir la date d'expiration
        exp_date = datetime.strptime(short_put['expiration_date'], "%Y-%m-%d")
        
        return IronCondor(
            name=f"Iron Condor {put_strike_low:.0f}/{put_strike_high:.0f}/{call_strike_low:.0f}/{call_strike_high:.0f}",
            underlying_price=target_price,
            put_strike_low=long_put['strike'],
            put_strike_high=short_put['strike'],
            call_strike_low=short_call['strike'],
            call_strike_high=long_call['strike'],
            put_premium_low=long_put['premium'],
            put_premium_high=short_put['premium'],
            call_premium_low=short_call['premium'],
            call_premium_high=long_call['premium'],
            expiry=exp_date
        )
    
    def build_centered_iron_butterfly(self,
                                     target_price: float,
                                     days_to_expiry: int,
                                     wing_width: float = 5.0) -> Optional[IronButterfly]:
        """
        Construit un Iron Butterfly centré sur le prix cible
        
        Args:
            target_price: Prix cible (ATM strike)
            days_to_expiry: Jours jusqu'à expiration
            wing_width: Largeur des ailes
        
        Returns:
            IronButterfly ou None
        """
        # Strikes
        atm_strike = round(target_price * 2) / 2  # Arrondir au 0.5 le plus proche
        put_strike_low = atm_strike - wing_width
        call_strike_high = atm_strike + wing_width
        
        # Trouver les options
        long_put = self.find_closest_option(put_strike_low, days_to_expiry, 'put')
        short_put = self.find_closest_option(atm_strike, days_to_expiry, 'put')
        short_call = self.find_closest_option(atm_strike, days_to_expiry, 'call')
        long_call = self.find_closest_option(call_strike_high, days_to_expiry, 'call')
        
        if not all([long_put, short_put, short_call, long_call]):
            return None
        
        exp_date = datetime.strptime(short_put['expiration_date'], "%Y-%m-%d")
        
        return IronButterfly(
            name=f"Iron Butterfly {put_strike_low:.0f}/{atm_strike:.0f}/{call_strike_high:.0f}",
            underlying_price=target_price,
            long_put_strike=long_put['strike'],
            atm_strike=short_put['strike'],
            long_call_strike=long_call['strike'],
            long_put_premium=long_put['premium'],
            short_put_premium=short_put['premium'],
            short_call_premium=short_call['premium'],
            long_call_premium=long_call['premium'],
            expiry=exp_date
        )
    
    def build_centered_short_strangle(self,
                                     target_price: float,
                                     days_to_expiry: int,
                                     wing_width: float = 3.0) -> Optional[ShortStrangle]:
        """
        Construit un Short Strangle centré autour du prix cible
        
        Args:
            target_price: Prix cible
            days_to_expiry: Jours jusqu'à expiration
            wing_width: Distance des strikes au prix cible
        
        Returns:
            ShortStrangle ou None
        """
        put_strike = target_price - wing_width
        call_strike = target_price + wing_width
        
        put_opt = self.find_closest_option(put_strike, days_to_expiry, 'put')
        call_opt = self.find_closest_option(call_strike, days_to_expiry, 'call')
        
        if not all([put_opt, call_opt]):
            return None
        
        exp_date = datetime.strptime(put_opt['expiration_date'], "%Y-%m-%d")
        
        return ShortStrangle(
            name=f"Short Strangle {put_strike:.0f}/{call_strike:.0f}",
            underlying_price=target_price,
            put_strike=put_opt['strike'],
            call_strike=call_opt['strike'],
            put_premium=put_opt['premium'],
            call_premium=call_opt['premium'],
            expiry=exp_date
        )
    
    def build_centered_short_straddle(self,
                                     target_price: float,
                                     days_to_expiry: int) -> Optional[ShortStraddle]:
        """
        Construit un Short Straddle centré sur le prix cible (ATM)
        
        Args:
            target_price: Prix cible (strike ATM)
            days_to_expiry: Jours jusqu'à expiration
        
        Returns:
            ShortStraddle ou None
        """
        atm_strike = round(target_price * 2) / 2  # Arrondir au 0.5
        
        put_opt = self.find_closest_option(atm_strike, days_to_expiry, 'put')
        call_opt = self.find_closest_option(atm_strike, days_to_expiry, 'call')
        
        if not all([put_opt, call_opt]):
            return None
        
        exp_date = datetime.strptime(put_opt['expiration_date'], "%Y-%m-%d")
        
        return ShortStraddle(
            name=f"Short Straddle {atm_strike:.0f}",
            underlying_price=target_price,
            strike=atm_strike,
            call_premium=call_opt['premium'],
            put_premium=put_opt['premium'],
            expiry=exp_date
        )
    
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
        
        # Construire et analyser chaque stratégie
        for strat_name in strategies_to_compare:
            strategy = None
            
            if strat_name == 'iron_condor':
                strategy = self.build_centered_iron_condor(target_price, days_to_expiry)
            elif strat_name == 'iron_butterfly':
                strategy = self.build_centered_iron_butterfly(target_price, days_to_expiry)
            elif strat_name == 'short_strangle':
                strategy = self.build_centered_short_strangle(target_price, days_to_expiry)
            elif strat_name == 'short_straddle':
                strategy = self.build_centered_short_straddle(target_price, days_to_expiry)
            
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
                score += (comp.max_profit / max_profit_val) * weights['max_profit']
            
            # 2. Risk/Reward (plus bas = mieux)
            if 'risk_reward' in weights and comp.risk_reward_ratio != float('inf'):
                normalized_rr = 1 - ((comp.risk_reward_ratio - min_rr) / (max_rr - min_rr))
                score += normalized_rr * weights['risk_reward']
            
            # 3. Zone profitable (plus large = mieux)
            if 'profit_zone' in weights and comp.profit_zone_width != float('inf') and max_zone_width > 0:
                score += (comp.profit_zone_width / max_zone_width) * weights['profit_zone']
            
            # 4. Performance au prix cible (plus proche de 100% = mieux)
            if 'target_performance' in weights and max_target_perf > 0:
                score += (comp.profit_at_target_pct / max_target_perf) * weights['target_performance']
            
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


# =============================================================================
# EXEMPLE D'UTILISATION
# =============================================================================

def example_usage():
    """Exemple complet de comparaison de stratégies"""
    
    # Charger les données d'options
    with open('calls_export.json', 'r') as f:
        data = json.load(f)
    
    # Séparer calls et puts
    options_data = {
        'calls': [opt for opt in data['options'] if opt['option_type'] == 'call'],
        'puts': []  # Ajouter des puts si disponibles
    }
    
    # Initialiser le comparateur
    comparer = StrategyComparer(options_data)
    
    # Paramètres de comparaison
    target_price = 100.0  # Prix cible SPY
    days_to_expiry = 30   # 30 jours jusqu'à expiration
    
    print("\n" + "="*80)
    print(f"COMPARAISON DE STRATÉGIES SHORT VOLATILITY")
    print(f"Prix cible: ${target_price:.2f}")
    print(f"Échéance: {days_to_expiry} jours")
    print("="*80)
    
    # Comparer les stratégies
    strategies_to_test = ['iron_condor', 'iron_butterfly', 'short_strangle', 'short_straddle']
    
    # Poids personnalisés pour le scoring
    custom_weights = {
        'max_profit': 0.30,      # Profit maximum
        'risk_reward': 0.30,     # Ratio risque/rendement
        'profit_zone': 0.20,     # Largeur de la zone profitable
        'target_performance': 0.20  # Performance au prix cible
    }
    
    results = comparer.compare_strategies(
        target_price=target_price,
        days_to_expiry=days_to_expiry,
        strategies_to_compare=strategies_to_test,
        weights=custom_weights
    )
    
    # Afficher les résultats
    if results:
        comparer.display_comparison(results)
        
        # Afficher le gagnant
        winner = results[0]
        print(f"\n🏆 STRATÉGIE GAGNANTE: {winner.strategy_name}")
        print(f"   Score: {winner.score:.3f}")
        print(f"   Crédit net: ${winner.net_credit:.2f}")
        print(f"   Profit maximum: ${winner.max_profit:.2f}")
        print(f"   Zone profitable: ${winner.profit_zone_width:.2f}")
        print(f"   P&L au prix cible: ${winner.profit_at_target:.2f}")
        
        # Tracer les graphiques
        print("\n📊 Génération du graphique de comparaison...")
        comparer.plot_strategy_comparison(results)
    else:
        print("⚠ Aucune stratégie n'a pu être construite avec les données disponibles.")


if __name__ == "__main__":
    example_usage()
