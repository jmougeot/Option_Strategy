from myproject.gradient_boosting.bloomberg_to_strat import process_bloomberg_to_strategies
from myproject.gradient_boosting.data_bulilder import train_regression_model, predict_and_rank_strategies
from myproject.app.utils import strike_list
from myproject.app.widget import ScenarioData

scenario: ScenarioData = ScenarioData([96.03, 96.35 ,96.1, 96,85, 96.35], [0.03, 0.03, 0.03, 0.03, 10], [15, 60, 15, 10, 50])

# Configuration
underlying = "SFR"
step = 0.0625
price_min = 95.75
price_max = 97
price = price_min
strikes = strike_list(price_min, price_max, step)
target_price = 98.25  # Prix cible au milieu de la range

# Mois d'expiration Bloomberg (F=Feb, G=Apr, H=Jun, J=Jul, K=Aug, M=Sep, N=Oct, Q=Nov, U=Dec, Z=Jan)
months = ["H"]  
years = [6]     # 2026

# Générer toutes les stratégies possibles
print("🔍 Génération des stratégies...")
print(f"   Underlying: {underlying}")
print(f"   Mois: {months}")
print(f"   Années: {years}")
print(f"   Strikes: {len(strikes)} strikes de {price_min} à {price_max}")
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

print(f"✅ {len(all_strategies)} stratégies générées\n")

# Entraîner le modèle de régression
print("🤖 Entraînement du modèle de machine learning...")
model, feature_importance, metrics = train_regression_model(
    all_strategies,
    test_size=0.2,
    random_state=42
)

# Prédire et classer les meilleures stratégies
print("\n" + "="*60)
print("📊 PRÉDICTION ET CLASSEMENT DES MEILLEURES STRATÉGIES")
print("="*60)
best_strategies = predict_and_rank_strategies(
    model=model,
    strategies=all_strategies,
    top_n=10
)

# Afficher les détails des meilleures stratégies
print("\n" + "="*60)
print("📈 DÉTAILS DES TOP 10 STRATÉGIES")
print("="*60)
for i, strat in enumerate(best_strategies, 1):
    print(f"\n{i}. {strat.strategy_name}")
    print(f"   Profit moyen: {strat.average_pnl:.4f}")
    print(f"   Max profit: {strat.max_profit:.4f}")
    print(f"   Max loss: {strat.max_loss:.4f}")
    print(f"   Risk/Reward: {strat.risk_reward_ratio_ponderated:.2f}")
    print(f"   Premium: {strat.premium:.4f}")
    print(f"   Breakevens: {len(strat.breakeven_points)}")
    print(f"   Delat {strat.total_delta}")

print("\n" + "="*60)
print("✨ TERMINÉ")
print("="*60)