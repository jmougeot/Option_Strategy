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
        strategy: StratÃ©gie Ã  Ã©valuer
        
    Returns:
        Score entre 0 et 100
    """
    score = 0.0
    
    # 1. Score de profit attendu (0-25 points)
    avg_pnl = strategy.average_pnl or 0
    if avg_pnl > 0:
        score += min(avg_pnl * 500, 25)  # Bonus pour profit positif
    else:
        score += max(avg_pnl * 500, -10)  # PÃ©nalitÃ© pour profit nÃ©gatif
    
    # 2. Score de risk/reward (0-20 points)
    rr_ratio = strategy.risk_reward_ratio_ponderated or 0
    if rr_ratio > 0:
        score += min(rr_ratio * 5, 20)
    
    # 3. Score de max_loss (0-15 points) - moins c'est risquÃ©, mieux c'est
    max_loss = abs(strategy.max_loss or 0)
    if max_loss < 0.02:
        score += 15
    elif max_loss < 0.05:
        score += 10
    elif max_loss < 0.10:
        score += 5
    else:
        score -= min(max_loss * 50, 10)  # PÃ©nalitÃ© pour pertes importantes
    
    # 4. Score de profit au target (0-15 points)
    profit_target = strategy.profit_at_target or 0
    if profit_target > 0:
        score += min(profit_target * 300, 15)
    else:
        score += max(profit_target * 300, -10)
    
    # 5. Score de zone profitable (0-10 points)
    zone_width = strategy.profit_zone_width or 0
    score += min(zone_width * 50, 10)
    
    # 6. Score de surfaces pondÃ©rÃ©es (0-10 points)
    surface_profit = strategy.surface_profit_ponderated or 0
    surface_loss = abs(strategy.surface_loss_ponderated or 0)
    if surface_loss > 0:
        surface_ratio = surface_profit / surface_loss
        score += min(surface_ratio * 2, 10)
    elif surface_profit > 0:
        score += 10
    
    # 7. PÃ©nalitÃ© pour volatilitÃ© (0 Ã  -5 points)
    sigma = strategy.sigma_pnl or 0
    if sigma > 0.05:
        score -= min((sigma - 0.05) * 50, 5)
    
    # 8. Bonus pour premium reÃ§u (0-5 points)
    premium = strategy.premium or 0
    if premium < 0:  # CrÃ©dit reÃ§u
        score += min(abs(premium) * 100, 5)
    
    # Normaliser le score entre 0 et 100
    return max(0, min(score, 100))


def data_frame(strategies: List[StrategyComparison]) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Convertit une liste de stratÃ©gies en DataFrame de features et array de labels.
    
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
    
    print(f"\nðŸ”„ Train set: {len(X_train)} stratagies")
    print(f"ðŸ§ª Test set: {len(X_test)} stratagies")
    
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
    
    print("\nðŸš€ EntraÃ®nement du modÃ¨le de rÃ©gression...")
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
    
    print("\nðŸ“ˆ RÃ©sultats:")
    print(f"   Train - MSE: {train_mse:.4f}, MAE: {train_mae:.4f}, RÂ²: {train_r2:.4f}")
    print(f"   Test  - MSE: {test_mse:.4f}, MAE: {test_mae:.4f}, RÂ²: {test_r2:.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\nðŸ”‘ Top 10 features importantes:")
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
    """
    PrÃ©dit les scores et retourne les meilleures stratÃ©gies.
    
    Args:
        model: ModÃ¨le entraÃ®nÃ©
        strategies: Liste de stratÃ©gies Ã  Ã©valuer
        top_n: Nombre de meilleures stratÃ©gies
        
    Returns:
        Liste des top_n meilleures stratÃ©gies
    """
    if model is None:
        print("âš ï¸ Aucun modÃ¨le fourni")
        return strategies[:top_n]
    
    # Générer features
    X, _ = data_frame(strategies)
    
    # Prédire les scores
    predicted_scores = model.predict(X)
    
    # Trier par score décroissant
    top_indices = np.argsort(predicted_scores)[::-1][:top_n]
    
    # Retourner les meilleures stratagies
    best_strategies = [strategies[i] for i in top_indices]
    
    print(f"\nâœ¨ Top {top_n} stratÃ©gies sÃ©lectionnÃ©es:")
    for i, (idx, score) in enumerate(zip(top_indices, predicted_scores[top_indices]), 1):
        strategy = strategies[idx]
        print(f"{i}. {strategy.strategy_name} - Score prÃ©dit: {score:.2f}")
    
    return best_strategies
