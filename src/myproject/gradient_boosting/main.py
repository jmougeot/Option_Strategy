from myproject.gradient_boosting.bloomberg_to_strat import process_bloomberg_to_strategies
from myproject.gradient_boosting.data_bulilder import train_regression_model, predict_and_rank_strategies

# Configuration
steps = 0.625
price_min = 98
price_max = 98.5
price= price_min
strikes = []
while price<=price_max: 
    strikes.append(price)
    price+=steps
    
target_price = 98.25  # Prix cible au milieu de la range

# Générer toutes les stratégies possibles
print("🔍 Génération des stratégies...")
all_strategies = process_bloomberg_to_strategies(
    underlying='ER',
    strikes=strikes,
    target_price=target_price,
    years=[6],
    price_min=price_min,
    price_max=price_max,
    scenarios=None,  # Pas de scénarios personnalisés
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

print("\n" + "="*60)
print("✨ TERMINÉ")
print("="*60)