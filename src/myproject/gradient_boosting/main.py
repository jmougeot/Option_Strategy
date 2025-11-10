from myproject.gradient_boosting.bloomberg_to_strat import process_bloomberg_to_strategies
from myproject.gradient_boosting.model import xgboost_pretrain_and_finetune, predict_and_rank_strategies as xgb_predict
from myproject.app.utils import strike_list
from myproject.app.widget import ScenarioData
from myproject.gradient_boosting.build_strategies_complete import normalize_and_export_mapping
from pathlib import Path

def SFR ():
    scenario: ScenarioData = ScenarioData([96.03, 96.35 ,96.1, 96.85, 96.35], [0.03, 0.03, 0.03, 0.03, 10], [15, 60, 15, 10, 3])
    underlying = "SFR"
    step = 0.0625
    price_min = 95.75
    price_max = 97
    strikes = strike_list(price_min, price_max, step)
    target_price = 98.25  # Prix cible au milieu de la range

    # Mois d'expiration Bloomberg (F=Feb, G=Apr, H=Jun, J=Jul, K=Aug, M=Sep, N=Oct, Q=Nov, U=Dec, Z=Jan)
    months = ["H"]  
    years = [6]     # 2026

    # Générer toutes les stratégies possibles
    print("Generation des strategies SFR...")
    print(f"   Underlying: {underlying}")
    print(f"   Mois: {months}")
    print(f"   Annees: {years}")
    print(f"   Strikes: {len(strikes)} strikes de {price_min} a {price_max}")
    print(f"   Target price: {target_price}\n")

    all_strategies = process_bloomberg_to_strategies(
        underlying=underlying,
        months=months,  # IMPORTANT: Spécifier les mois d'expiration Bloomberg
        years=years,
        strikes=strikes,
        target_price=target_price,
        price_min=price_min,
        price_max=price_max,
        scenarios=scenario,
    )
    return all_strategies

def ER ():
    scenario: ScenarioData = ScenarioData([96.03, 96.35 ,96.1, 96.85, 96.35], [0.03, 0.03, 0.03, 0.03, 10], [15, 60, 15, 10, 3])
    underlying = "ER"
    step = 0.0625
    price_min = 95.75
    price_max = 97
    strikes = strike_list(price_min, price_max, step)
    target_price = 98.25  # Prix cible au milieu de la range

    # Mois d'expiration Bloomberg (F=Feb, G=Apr, H=Jun, J=Jul, K=Aug, M=Sep, N=Oct, Q=Nov, U=Dec, Z=Jan)
    months = ["H"]  
    years = [6]     # 2026

    # Générer toutes les stratégies possibles
    print("Generation des strategies ER...")

    all_strategies = process_bloomberg_to_strategies(
        underlying=underlying,
        months=months,  # IMPORTANT: Spécifier les mois d'expiration Bloomberg
        years=years,
        strikes=strikes,
        target_price=target_price,
        price_min=price_min,
        price_max=price_max,
        scenarios=scenario,
    )
    return all_strategies

# ============================================================================
# PHASE 1: GENERATION DES STRATEGIES BLOOMBERG (PRE-TRAINING DATA)
# ============================================================================

print("="*80)
print("PHASE 1: GENERATION DES STRATEGIES BLOOMBERG")
print("="*80)

bloomberg_strategies = []

# Générer les stratégies ER
print("\nGeneration des strategies ER...")
bloomberg_strategies.extend(ER())

# Générer les stratégies SFR
print("\nGeneration des strategies SFR...")
bloomberg_strategies.extend(SFR())

print(f"\nTotal strategies Bloomberg generees: {len(bloomberg_strategies)}")

# ============================================================================
# PHASE 2: CHARGEMENT DES DONNEES REELLES DE TRADE_MONITOR (FINE-TUNING DATA)
# ============================================================================

print("\n" + "="*80)
print("PHASE 2: CHARGEMENT DES DONNEES TRADE MONITOR")
print("="*80)

# Chemin vers Trade_monitor.csv
trade_monitor_path = Path(__file__).parent.parent / "trade_monitor_data" / "Trade_monitor.csv"
mapping_csv_path = Path(__file__).parent.parent / "trade_monitor_data" / "Strategy_mapping.csv"

print(f"\nChemin Trade_monitor.csv: {trade_monitor_path}")
print(f"Fichier existe: {trade_monitor_path.exists()}")

# Vérifier que le fichier Trade_monitor.csv existe
if not trade_monitor_path.exists():
    raise FileNotFoundError(f"Le fichier Trade_monitor.csv n'existe pas: {trade_monitor_path}")

# Générer le fichier de mapping si nécessaire
if not mapping_csv_path.exists():
    print("Generation du fichier Strategy_mapping.csv...")
    mapping_df, scores = normalize_and_export_mapping(str(trade_monitor_path), str(mapping_csv_path))
    print(f"Scores calcules: {len(scores)} strategies avec scores")

# Parser le fichier Trade_monitor.csv pour obtenir les stratégies
print("Parsing du fichier Trade_monitor.csv...")
print("\n" + "="*80)
print(f"DONNEES PRETES:")
print(f"   - Bloomberg: {len(bloomberg_strategies)} strategies")
print("="*80)

# ============================================================================
# PHASE 3: ENTRAINEMENT DU MODELE (PRE-TRAIN + FINE-TUNE)
# ============================================================================

print("\n" + "="*80)
print("PHASE 3: ENTRAINEMENT XGBOOST (PRE-TRAIN + FINE-TUNE)")
print("="*80)

model, pretrain_metrics, finetune_metrics, feature_importance = xgboost_pretrain_and_finetune(
    bloomberg_strategies=bloomberg_strategies,
    trade_monitor_strategies=mapping_csv_path,

    test_size=0.2,
    random_state=4)

print("\n" + "="*80)
print("MODELE ENTRAINE ET FINE-TUNE")
print("="*80)

# ============================================================================
# PHASE 4: PREDICTION SUR LES MEILLEURES STRATEGIES
# ============================================================================
print("\n" + "="*80)
print("PHASE 4: PREDICTION DES MEILLEURES STRATEGIES")
print("="*80)

# Prédire aussi sur les stratégies Bloomberg (synthétiques) pour comparaison
print("\nPrediction sur les strategies Bloomberg (synthetiques):")
best_bloomberg_strategies = xgb_predict(
    model=model,
    strategies=bloomberg_strategies,
    top_n=10)


print("\n" + "="*60)
print("DETAILS DES TOP 10 STRATEGIES TRADE MONITOR")
print("="*60)
for i, (strat, score) in enumerate(best_bloomberg_strategies, 1):
    print(f"\n{i}. {strat.strategy_name} (Score prédit: {score:.2f})")
    print(f"   Profit moyen: {strat.average_pnl:.4f}")
    print(f"   Max profit: {strat.max_profit:.4f}")
    print(f"   Max loss: {strat.max_loss:.4f}")
    print(f"   Risk/Reward: {strat.risk_reward_ratio_ponderated:.2f}")
    print(f"   Premium: {strat.premium:.4f}")
    print(f"   Breakevens: {len(strat.breakeven_points)}")
    print(f"   Delta: {strat.total_delta}")
