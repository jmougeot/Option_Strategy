"""
Strategy Persistence Module
Handles saving and loading of option strategies to/from JSON files
"""

import json
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path
from myproject.strategy.comparison_class import StrategyComparison
from myproject.option.option_class import Option


def strategy_to_dict(strategy: StrategyComparison) -> Dict[str, Any]:
    """
    Convertit une StrategyComparison en dictionnaire sérialisable
    """
    return {
        'strategy_name': strategy.strategy_name,
        'target_price': strategy.target_price,
        'premium': strategy.premium,
        
        # Expiration
        'expiration_day': strategy.expiration_day,
        'expiration_week': strategy.expiration_week,
        'expiration_month': strategy.expiration_month,
        'expiration_year': strategy.expiration_year,
        
        # Métriques financières
        'max_profit': strategy.max_profit if strategy.max_profit != float('inf') else None,
        'max_loss': strategy.max_loss if strategy.max_loss != float('-inf') else None,
        'breakeven_points': strategy.breakeven_points,
        
        # Métriques de risque
        'profit_range': list(strategy.profit_range),
        'profit_zone_width': strategy.profit_zone_width,
        'surface_profit': strategy.surface_profit,
        'surface_loss': strategy.surface_loss,
        'risk_reward_ratio': strategy.risk_reward_ratio,
        
        # Greeks - Calls
        'total_delta_calls': strategy.total_delta_calls,
        'total_gamma_calls': strategy.total_gamma_calls,
        'total_vega_calls': strategy.total_vega_calls,
        'total_theta_calls': strategy.total_theta_calls,
        
        # Greeks - Puts
        'total_delta_puts': strategy.total_delta_puts,
        'total_gamma_puts': strategy.total_gamma_puts,
        'total_vega_puts': strategy.total_vega_puts,
        'total_theta_puts': strategy.total_theta_puts,
        
        # Greeks - Total
        'total_delta': strategy.total_delta,
        'total_gamma': strategy.total_gamma,
        'total_vega': strategy.total_vega,
        'total_theta': strategy.total_theta,
        
        # Volatilité
        'avg_implied_volatility': strategy.avg_implied_volatility,
        
        # Performance
        'profit_at_target': strategy.profit_at_target,
        'profit_at_target_pct': strategy.profit_at_target_pct,
        
        # Score
        'score': strategy.score,
        'rank': strategy.rank,
        
        # Options
        'all_options': [option_to_dict(opt) for opt in strategy.all_options]
    }


def option_to_dict(option: Option) -> Dict[str, Any]:
    """
    Convertit une Option en dictionnaire sérialisable
    """
    return {
        'option_type': option.option_type,
        'strike': option.strike,
        'premium': option.premium,
        'position': option.position,
        'quantity': option.quantity,
        'expiration_day': option.expiration_day,
        'expiration_week': option.expiration_week,
        'expiration_month': option.expiration_month,
        'expiration_year': option.expiration_year,
        'delta': option.delta,
        'gamma': option.gamma,
        'vega': option.vega,
        'theta': option.theta,
        'implied_volatility': option.implied_volatility,
        'profit_surface': option.profit_surface,
        'loss_surface': option.loss_surface
    }


def dict_to_option(data: Dict[str, Any]) -> Option:
    """
    Reconstruit une Option depuis un dictionnaire
    """
    return Option(
        option_type=data['option_type'],
        strike=data['strike'],
        premium=data['premium'],
        position=data['position'],
        quantity=data.get('quantity', 1),
        expiration_day=data.get('expiration_day'),
        expiration_week=data.get('expiration_week'),
        expiration_month=data['expiration_month'],
        expiration_year=data['expiration_year'],
        delta=data.get('delta'),
        gamma=data.get('gamma'),
        vega=data.get('vega'),
        theta=data.get('theta'),
        implied_volatility=data.get('implied_volatility'),
        profit_surface=data.get('profit_surface', 0.0),
        loss_surface=data.get('loss_surface', 0.0)
    )


def dict_to_strategy(data: Dict[str, Any]) -> StrategyComparison:
    """
    Reconstruit une StrategyComparison depuis un dictionnaire
    """
    return StrategyComparison(
        strategy_name=data['strategy_name'],
        strategy=None,  # Le strategy object n'est pas sérialisé
        target_price=data['target_price'],
        premium=data['premium'],
        
        # Expiration
        expiration_day=data.get('expiration_day'),
        expiration_week=data.get('expiration_week'),
        expiration_month=data['expiration_month'],
        expiration_year=data['expiration_year'],
        
        # Métriques financières
        max_profit=data['max_profit'] if data['max_profit'] is not None else float('inf'),
        max_loss=data['max_loss'] if data['max_loss'] is not None else float('-inf'),
        breakeven_points=data['breakeven_points'],
        
        # Métriques de risque
        profit_range=tuple(data['profit_range']),
        profit_zone_width=data['profit_zone_width'],
        surface_profit=data['surface_profit'],
        surface_loss=data['surface_loss'],
        risk_reward_ratio=data['risk_reward_ratio'],
        
        # Greeks - Calls
        total_delta_calls=data.get('total_delta_calls', 0.0),
        total_gamma_calls=data.get('total_gamma_calls', 0.0),
        total_vega_calls=data.get('total_vega_calls', 0.0),
        total_theta_calls=data.get('total_theta_calls', 0.0),
        
        # Greeks - Puts
        total_delta_puts=data.get('total_delta_puts', 0.0),
        total_gamma_puts=data.get('total_gamma_puts', 0.0),
        total_vega_puts=data.get('total_vega_puts', 0.0),
        total_theta_puts=data.get('total_theta_puts', 0.0),
        
        # Greeks - Total
        total_delta=data.get('total_delta', 0.0),
        total_gamma=data.get('total_gamma', 0.0),
        total_vega=data.get('total_vega', 0.0),
        total_theta=data.get('total_theta', 0.0),
        
        # Volatilité
        avg_implied_volatility=data.get('avg_implied_volatility', 0.0),
        
        # Performance
        profit_at_target=data.get('profit_at_target', 0.0),
        profit_at_target_pct=data.get('profit_at_target_pct', 0.0),
        
        # Score
        score=data.get('score', 0.0),
        rank=data.get('rank', 0),
        
        # Options
        all_options=[dict_to_option(opt_data) for opt_data in data.get('all_options', [])]
    )


def save_strategies_to_json(
    strategies: List[StrategyComparison],
    filepath: str,
    metadata: Dict[str, Any] | None = None
) -> None:
    """
    Sauvegarde une liste de stratégies dans un fichier JSON
    
    Args:
        strategies: Liste des stratégies à sauvegarder
        filepath: Chemin du fichier JSON
        metadata: Métadonnées additionnelles (paramètres de génération, etc.)
    """
    data = {
        'metadata': {
            'saved_at': datetime.now().isoformat(),
            'nb_strategies': len(strategies),
            **(metadata or {})
        },
        'strategies': [strategy_to_dict(s) for s in strategies]
    }
    
    # Créer le dossier si nécessaire
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_strategies_from_json(filepath: str) -> tuple[List[StrategyComparison], Dict[str, Any]]:
    """
    Charge une liste de stratégies depuis un fichier JSON
    
    Args:
        filepath: Chemin du fichier JSON
        
    Returns:
        Tuple (strategies, metadata)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    strategies = [dict_to_strategy(s) for s in data['strategies']]
    metadata = data.get('metadata', {})
    
    return strategies, metadata


def list_saved_strategies(directory: str = "saved_strategies") -> List[Dict[str, Any]]:
    """
    Liste tous les fichiers de stratégies sauvegardés
    
    Args:
        directory: Dossier où chercher les fichiers
        
    Returns:
        Liste de dictionnaires avec info sur chaque fichier
    """
    path = Path(directory)
    if not path.exists():
        return []
    
    files = []
    for json_file in path.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                metadata = data.get('metadata', {})
                files.append({
                    'filename': json_file.name,
                    'filepath': str(json_file),
                    'saved_at': metadata.get('saved_at', 'Unknown'),
                    'nb_strategies': metadata.get('nb_strategies', 0),
                    'underlying': metadata.get('underlying', 'Unknown'),
                    'target_price': metadata.get('target_price', 'Unknown')
                })
        except Exception:
            continue
    
    # Trier par date (plus récent d'abord)
    files.sort(key=lambda x: x['saved_at'], reverse=True)
    return files
