import numpy as np
import pandas as pd
from myproject.strategy.comparison_class import StrategyComparison
from typing import List, Tuple
from sklearn.model_selection import train_test_split
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error


def max_loss_penalty(max_loss, threshold=20):
    """ pour les pertes maximales."""
    return min(abs(max_loss), threshold) / threshold


def calculate_strategy_score(strategy: StrategyComparison) -> float:
    """
    Calcule un score continu pour une stratÃ©gie (0-100).
    Plus le score est Ã©levÃ©, meilleure est la stratÃ©gie.
    
    Args:
        strategy: Stratégie à évaluer
        
    Returns:
        Score entre 0 et 100
    """
    score = 0.0

    short_call_count = sum(1 for opt in strategy.all_options if opt.is_short() and opt.is_call())
    if short_call_count > 3:
        score -= 50
            
    # 1. Score de profit attendu (0-25 points)
    avg_pnl = strategy.average_pnl or 0
    score += min(avg_pnl * 500, 25)  # Bonus pour profit positif

    max_loss = abs(strategy.max_loss or 0)
    if max_loss < -0.05:
        score -= 8
    elif max_loss < -0.10:
        score -=15
    elif max_loss < -0.20:
        score -= 30
    else:
        score -= min(max_loss * 50, 10) 

    profit_target = strategy.profit_at_target
    if profit_target > 0:
        score += min(profit_target * 300, 15)
    else:
        score += max(profit_target * 300, -7)
    
    # 5. Score de zone profitable (0-10 points)
    zone_width = strategy.profit_zone_width or 0
    score += min(zone_width * 50, 10)
    
    sigma = strategy.sigma_pnl or 0
    if sigma > 0.05:
        score -= 7

    premium = strategy.premium
    if premium < 0:
        score += min(abs(premium) * 100, 5)
    if premium > 5:
        score -= 25

    delta = strategy.total_delta
    if abs(delta) > 100:
        score -= 25
    
    # Toujours retourner un score normalisé entre 0 et 100
    return max(0, min(score, 100))


def data_frame(strategies: List[StrategyComparison]) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Convertit une liste de stratégies en DataFrame de features et array de labels.
    
    Args:
        strategies: Liste de StrategyComparison
        
    Returns:
        Tuple (X, y) oÃ¹ X est le DataFrame des features et y les labels
    """
    feature_list = []
    labels = []
    
    feature_names = [
        'average_pnl',
        'num_breakevens',
        'max_profit',
        'max_loss',
        'premium',
        'profit_at_target',
        'profit_range_min',
        'profit_range_max',
        'sigma_pnl',
        'surface_loss_ponderated',
        'surface_profit_ponderated',
        'surface_loss',
        'surface_profit',
        'risk_reward_ratio',
        'total_delta',
        'total_theta',
        'total_gamma',
        'total_vega',
        'profit_zone_width',
        'max_loss_penalty'
    ]
    
    for s in strategies:
        feats = []
        feats.append(s.average_pnl if s.average_pnl else 0.0)
        feats.append(len(s.breakeven_points) if s.breakeven_points else 0)
        feats.append(s.max_profit if s.max_profit else 0.0)
        feats.append(s.max_loss if s.max_loss else 0.0)
        feats.append(s.premium if s.premium else 0.0)
        feats.append(s.profit_at_target if s.profit_at_target else 0.0)
        feats.append(s.profit_range[0] if s.profit_range else 0.0)
        feats.append(s.profit_range[1] if s.profit_range else 0.0)
        feats.append(s.sigma_pnl if s.sigma_pnl else 0.0)
        feats.append(s.surface_loss_ponderated if s.surface_loss_ponderated else 0.0)
        feats.append(s.surface_profit_ponderated if s.surface_profit_ponderated else 0.0)
        feats.append(s.surface_loss if s.surface_loss else 0.0)
        feats.append(s.surface_profit if s.surface_profit else 0.0)
        feats.append(s.risk_reward_ratio_ponderated if s.risk_reward_ratio_ponderated else 0.0)
        feats.append(s.total_delta if s.total_delta else 0.0)
        feats.append(s.total_theta if s.total_theta else 0.0)
        feats.append(s.total_gamma if s.total_gamma else 0.0)
        feats.append(s.total_vega if s.total_vega else 0.0)
        feats.append(s.profit_zone_width if s.profit_zone_width else 0.0)
        feats.append(max_loss_penalty(abs(s.max_loss) if s.max_loss else 0.0))
        
        feature_list.append(feats)
        
        # Calculer le score continu (0-100) au lieu de label binaire
        score = calculate_strategy_score(s)
        labels.append(score)
    
    X = pd.DataFrame(feature_list, columns=feature_names)
    y = np.array(labels)  # Scores continus entre 0 et 100
    
    return X, y 



def train_regression_model(
    strategies: List[StrategyComparison],
    test_size: float = 0.2,
    random_state: int = 42
):
    """     
    Returns:
        Tuple (model, feature_importance, metrics)
    """
    
    # GÃ©nÃ©rer features et scores
    X, y = data_frame(strategies)
    
    print(f" Dataset: {len(X)} stratagies")
    print(f"   - Score moyen: {np.mean(y):.2f}")
    print(f"   - Score min: {np.min(y):.2f}")
    print(f"   - Score max: {np.max(y):.2f}")
    
    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    
    print(f"Train set: {len(X_train)} stratagies")
    print(f"Test set: {len(X_test)} stratagies")
    
    # CrÃ©er et entraÃ®ner le modÃ¨le de rÃ©gression
    model = LGBMRegressor(
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        n_jobs=-1,
        random_state=random_state,
        verbose=-1
    )
    
    print("\n Entrainement du modéle de régression...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)]
    )
    
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    train_mse = mean_squared_error(y_train, y_pred_train)
    test_mse = mean_squared_error(y_test, y_pred_test)
    train_mae = mean_absolute_error(y_train, y_pred_train)
    test_mae = mean_absolute_error(y_test, y_pred_test)
    train_r2 = r2_score(y_train, y_pred_train)
    test_r2 = r2_score(y_test, y_pred_test)
    
    print("\nRésultats:")
    print(f"   Train - MSE: {train_mse:.4f}, MAE: {train_mae:.4f}, RÂ²: {train_r2:.4f}")
    print(f"   Test  - MSE: {test_mse:.4f}, MAE: {test_mae:.4f}, RÂ²: {test_r2:.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\ Top 10 features importantes:")
    print(feature_importance.head(10))
    
    metrics = {
        'train_mse': train_mse,
        'test_mse': test_mse,
        'train_mae': train_mae,
        'test_mae': test_mae,
        'train_r2': train_r2,
        'test_r2': test_r2
    }
    
    return model, feature_importance, metrics


def predict_and_rank_strategies(
    model,
    strategies: List[StrategyComparison],
    top_n: int = 10
) -> List[StrategyComparison]:

    # Générer features
    X, _ = data_frame(strategies)
    
    # Prédire les scores
    predicted_scores = model.predict(X)
    
    # Trier par score décroissant
    top_indices = np.argsort(predicted_scores)[::-1][:top_n]
    
    # Retourner les meilleures stratagies
    best_strategies = [strategies[i] for i in top_indices]
    
    print(f"\nâœ¨ Top {top_n} stratatégies sélectionnées:")
    for i, (idx, score) in enumerate(zip(top_indices, predicted_scores[top_indices]), 1):
        strategy = strategies[idx]
        print(f"{i}. {strategy.strategy_name} - Score: {score:.2f}")
    
    return best_strategies
