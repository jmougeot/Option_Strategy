import xgboost as xgb
from sklearn.metrics import root_mean_squared_error, r2_score, mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from myproject.gradient_boosting.data_bulilder import data_frame_bloomberg, prepare_dataframe_for_xgboost
from myproject.strategy.comparison_class import StrategyComparison
from typing import List, Tuple
from pathlib import Path
import numpy as np
import pandas as pd


def xgboost_pretrain_and_finetune(
    bloomberg_strategies: List[StrategyComparison],
    trade_monitor_strategies,
    test_size: float = 0.2,
    random_state: int = 42
):
    """
    Pre-train XGBoost sur les données Bloomberg puis fine-tune sur Trade Monitor
    
    Args:
        bloomberg_strategies: Stratégies générées depuis Bloomberg
        trade_monitor_strategies: Stratégies réelles du Trade Monitor
        test_size: Proportion du test set pour Trade Monitor
        random_state: Seed pour reproductibilité
        
    Returns:
        Tuple (model, metrics_pretrain, metrics_finetune, feature_importance)
    """
    
    print("="*80)
    print("PHASE 1: PRE-TRAINING SUR DONNEES BLOOMBERG")
    print("="*80)
    
    # Convertir les stratégies Bloomberg en features
    X_bloomberg, y_bloomberg = data_frame_bloomberg(bloomberg_strategies)
    
    print(f"\nDataset Bloomberg: {len(X_bloomberg)} strategies")
    print(f"   - Score moyen: {np.mean(y_bloomberg):.2f}")
    print(f"   - Score min: {np.min(y_bloomberg):.2f}")
    print(f"   - Score max: {np.max(y_bloomberg):.2f}")
    
    # Charger les stratégies Trade Monitor depuis le CSV
    if isinstance(trade_monitor_strategies, (str, Path)):
        # C'est un chemin vers un CSV, le charger
        tm_df = pd.read_csv(str(trade_monitor_strategies))
        y_tm = np.array(tm_df['score'].values)
        X_tm = tm_df.drop(columns=['score'], errors='ignore')
        X_tm = prepare_dataframe_for_xgboost(X_tm)
    else:
        # C'est une liste de stratégies, la convertir
        X_tm, y_tm = data_frame_bloomberg(trade_monitor_strategies)
    
    print(f"\nDataset Trade Monitor: {len(X_tm)} strategies")
    print(f"   - Score moyen: {np.mean(y_tm):.2f}")
    print(f"   - Score min: {np.min(y_tm):.2f}")
    print(f"   - Score max: {np.max(y_tm):.2f}")
    
    # Aligner les colonnes entre Bloomberg et Trade Monitor
    # Utiliser les colonnes de Bloomberg comme référence
    print(f"\nAlignement des colonnes...")
    print(f"   - Colonnes Bloomberg: {len(X_bloomberg.columns)}")
    print(f"   - Colonnes Trade Monitor: {len(X_tm.columns)}")
    
    # Ajouter les colonnes manquantes dans Trade Monitor avec des 0
    for col in X_bloomberg.columns:
        if col not in X_tm.columns:
            X_tm[col] = 0
    
    # Supprimer les colonnes en trop dans Trade Monitor
    X_tm = X_tm[X_bloomberg.columns]
    
    print(f"   - Colonnes alignées: {len(X_tm.columns)}")
    
    # Split Trade Monitor en train/test pour validation
    X_tm_train, X_tm_test, y_tm_train, y_tm_test = train_test_split(
        X_tm, y_tm, test_size=test_size, random_state=random_state
    )
    
    print(f"\nSplit Trade Monitor:")
    print(f"   - Train: {len(X_tm_train)} strategies")
    print(f"   - Test: {len(X_tm_test)} strategies")
    
    # Initialiser le modèle XGBoost
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=random_state,
        tree_method='hist',
        early_stopping_rounds=50
    )
    
    print("\n" + "="*80)
    print("ENTRAINEMENT PHASE 1: Pre-train sur Bloomberg")
    print("="*80)
    
    # Pre-train sur Bloomberg avec validation sur Trade Monitor test
    model.fit(
        X_bloomberg, 
        y_bloomberg, 
        eval_set=[(X_tm_test, y_tm_test)],
        verbose=50
    )
    
    # Évaluer le modèle pré-entraîné
    y_pred_bloomberg = model.predict(X_bloomberg)
    y_pred_tm_test = model.predict(X_tm_test)
    
    pretrain_metrics = {
        'train_mse': mean_squared_error(y_bloomberg, y_pred_bloomberg),
        'train_rmse': root_mean_squared_error(y_bloomberg, y_pred_bloomberg),
        'train_mae': mean_absolute_error(y_bloomberg, y_pred_bloomberg),
        'train_r2': r2_score(y_bloomberg, y_pred_bloomberg),
        'test_mse': mean_squared_error(y_tm_test, y_pred_tm_test),
        'test_rmse': root_mean_squared_error(y_tm_test, y_pred_tm_test),
        'test_mae': mean_absolute_error(y_tm_test, y_pred_tm_test),
        'test_r2': r2_score(y_tm_test, y_pred_tm_test)
    }
    
    print("\nResultats Pre-training:")
    print(f"   Bloomberg Train - RMSE: {pretrain_metrics['train_rmse']:.4f}, MAE: {pretrain_metrics['train_mae']:.4f}, R²: {pretrain_metrics['train_r2']:.4f}")
    print(f"   Trade Monitor Test - RMSE: {pretrain_metrics['test_rmse']:.4f}, MAE: {pretrain_metrics['test_mae']:.4f}, R²: {pretrain_metrics['test_r2']:.4f}")
    
    print("\n" + "="*80)
    print("PHASE 2: FINE-TUNING SUR DONNEES TRADE MONITOR")
    print("="*80)
    
    # Fine-tune sur Trade Monitor train (continuer l'entraînement)
    # Réduire le learning rate pour un fine-tuning plus doux
    model.set_params(learning_rate=0.01, n_estimators=500)
    
    print("\nFine-tuning avec learning rate reduit (0.01)...")
    
    # Continuer l'entraînement depuis le modèle pré-entraîné
    model.fit(
        X_tm_train, 
        y_tm_train,
        xgb_model=model.get_booster(),  # Continuer depuis le modèle pré-entraîné
        eval_set=[(X_tm_test, y_tm_test)],
        verbose=50
    )
    
    # Évaluer le modèle fine-tuné
    y_pred_tm_train = model.predict(X_tm_train)
    y_pred_tm_test_final = model.predict(X_tm_test)
    
    finetune_metrics = {
        'train_mse': mean_squared_error(y_tm_train, y_pred_tm_train),
        'train_rmse': root_mean_squared_error(y_tm_train, y_pred_tm_train),
        'train_mae': mean_absolute_error(y_tm_train, y_pred_tm_train),
        'train_r2': r2_score(y_tm_train, y_pred_tm_train),
        'test_mse': mean_squared_error(y_tm_test, y_pred_tm_test_final),
        'test_rmse': root_mean_squared_error(y_tm_test, y_pred_tm_test_final),
        'test_mae': mean_absolute_error(y_tm_test, y_pred_tm_test_final),
        'test_r2': r2_score(y_tm_test, y_pred_tm_test_final)
    }
    
    print("\nResultats Fine-tuning:")
    print(f"   Trade Monitor Train - RMSE: {finetune_metrics['train_rmse']:.4f}, MAE: {finetune_metrics['train_mae']:.4f}, R²: {finetune_metrics['train_r2']:.4f}")
    print(f"   Trade Monitor Test - RMSE: {finetune_metrics['test_rmse']:.4f}, MAE: {finetune_metrics['test_mae']:.4f}, R²: {finetune_metrics['test_r2']:.4f}")
    
    # Amélioration après fine-tuning
    improvement_rmse = pretrain_metrics['test_rmse'] - finetune_metrics['test_rmse']
    improvement_r2 = finetune_metrics['test_r2'] - pretrain_metrics['test_r2']
    
    print("\nAmelioration apres fine-tuning:")
    print(f"   RMSE: {improvement_rmse:+.4f} ({improvement_rmse/pretrain_metrics['test_rmse']*100:+.2f}%)")
    print(f"   R²: {improvement_r2:+.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_bloomberg.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\nTop 10 features importantes:")
    print(feature_importance.head(10))
    
    # Sauvegarder le modèle
    model.save_model("xgb_finetuned.json")
    print("\nModele sauvegarde: xgb_finetuned.json")
    
    return model, pretrain_metrics, finetune_metrics, feature_importance


def predict_and_rank_strategies(
    model,
    strategies: List[StrategyComparison],
    top_n: int = 10
) -> List[Tuple[StrategyComparison, float]]:
    """
    Prédit et classe les meilleures stratégies
    
    Args:
        model: Modèle XGBoost entraîné
        strategies: Liste de stratégies à prédire
        is_trade_monitor: Si True, utilise data_frame_trade_monitor, sinon data_frame_bloomberg
        top_n: Nombre de meilleures stratégies à retourner
        
    Returns:
        Liste de tuples (stratégie, score prédit) triés par score décroissant
    """
    
    # Générer features selon le type de données
  
    X, _ = data_frame_bloomberg(strategies)
    
    # Prédire les scores
    predicted_scores = model.predict(X)
    
    # Trier par score décroissant
    top_indices = np.argsort(predicted_scores)[::-1][:top_n]
    
    # Retourner les meilleures stratégies avec leurs scores
    best_strategies = [(strategies[i], predicted_scores[i]) for i in top_indices]
    
    print(f"\nTop {top_n} strategies selectionnees:")
    for i, (strategy, score) in enumerate(best_strategies, 1):
        print(f"{i}. {strategy.strategy_name} - Score: {score:.2f}")
    
    return best_strategies


