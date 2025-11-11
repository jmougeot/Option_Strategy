"""
Filtres pour éliminer les stratégies avec des valeurs extrêmes ou invalides.
"""

from myproject.strategy.comparison_class import StrategyComparison


def filter_extreme_strategies(strategy: StrategyComparison) -> bool:
    """
    Filtre les stratégies avec des valeurs extrêmes ou invalides.

    Args:
        strategy: Stratégie à filtrer

    Returns:
        True si la stratégie est valide, False si elle doit être éliminée
    """

    # 1. Premium invalide ou None
    if strategy.premium is None:
        return False

    # 2. Premium extrême (trop grand positif ou négatif)
    if abs(strategy.premium) > 0.1:  # Ajusté pour options réalistes
        return False

    # 3. Delta total extrême (normallement entre -100 et +100 pour stratégies réalistes)
    if strategy.total_delta is not None:
        if abs(strategy.total_delta) > 100:  # Marge de sécurité
            return False

    # 4. Gamma total extrême (valeurs anormalement élevées)
    if strategy.total_gamma is not None:
        if abs(strategy.total_gamma) > 50:
            return False

    # 5. Vega total extrême
    if strategy.total_vega is not None:
        if abs(strategy.total_vega) > 100:
            return False

    # 6. Theta total extrême
    if strategy.total_theta is not None:
        if abs(strategy.total_theta) > 50:
            return False

    # 7. Max profit négatif (stratégie qui ne peut que perdre)
    if strategy.max_profit is not None and strategy.max_profit < -10.0:
        return False

    # 8. Max loss positif (incohérence mathématique)
    if strategy.max_loss is not None and strategy.max_loss > 10.0:
        return False

    # 9. Risk/Reward ratio invalide (inf, nan, ou extrême)
    if strategy.risk_reward_ratio is not None:
        if not (-1000 < strategy.risk_reward_ratio < 1000):
            return False

    # 10. Surface profit/loss extrêmes ou invalides
    if strategy.surface_profit is not None:
        if abs(strategy.surface_profit) > 1000:
            return False

    if strategy.surface_loss is not None:
        if abs(strategy.surface_loss) > 1000:
            return False

    # 11. Implied volatility moyenne anormale
    if strategy.avg_implied_volatility is not None:
        if (
            strategy.avg_implied_volatility < 0.01
            or strategy.avg_implied_volatility > 5.0
        ):  # IV entre 1% et 500%
            return False

    # 12. Profit at target extrême
    if strategy.profit_at_target is not None:
        if abs(strategy.profit_at_target) > 100:
            return False

    # 13. Vérifier que le pnl_array existe et n'est pas vide
    if strategy.pnl_array is None or len(strategy.pnl_array) == 0:
        return False

    # 14. Vérifier que le prices array existe et n'est pas vide
    if strategy.prices is None or len(strategy.prices) == 0:
        return False

    # 15. Vérifier cohérence entre pnl_array et prices
    if len(strategy.pnl_array) != len(strategy.prices):
        return False

    # 16. Vérifier qu'il y a au moins une option dans la stratégie
    if not strategy.all_options or len(strategy.all_options) == 0:
        return False

    # 17. Sigma PnL anormal (trop élevé = stratégie trop volatile)
    if strategy.sigma_pnl is not None:
        if strategy.sigma_pnl > 50:  # Écart-type > 50 = stratégie extrêmement risquée
            return False

    # 18. Limiter le nombre de short calls (risque illimité)
    short_call_count = sum(
        1 for opt in strategy.all_options if opt.is_short and opt.is_call
    )
    if short_call_count > 3:
        return False

    # Stratégie valide
    return True
