import streamlit as st
from dataclasses import dataclass
from myproject.app.utils import strike_list
from typing import Optional 

@dataclass
class UIParams:
    underlying: str
    months: list[str]
    years: list[int]
    strike: float
    price_min: float
    price_max: float
    price_step: float
    max_legs: int
    strikes: list[float]

def sidebar_params() -> UIParams:
    st.header("⚙️ Paramètres")

    c1, c2 = st.columns(2)
    with c1:
        underlying = st.text_input("Sous-jacent:", value="ER", help="Code Bloomberg (ER = EURIBOR)")
    with c2:
        years_input = st.text_input("Années:", value="6", help="6=2026, 7=2027 (séparées par virgule)")

    c1, c2 = st.columns(2)
    with c1:
        months_input = st.text_input("Mois d'expiration:", value="F,G,H,K,M,N",
                                     help="F=Jan, G=Feb, H=Mar, K=Apr, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec")
    with c2:
        strike = st.number_input("Strike :", value=98.0, format="%.4f", help="Target Price")

    c1, c2 = st.columns(2)
    with c1:
        price_min = st.number_input("Prix Min ($)", value=97.750, step=0.0001, format="%.4f")
    with c2:
        price_max = st.number_input("Prix Max ($)", value=98.250, step=0.0001, format="%.4f")

    price_step = st.number_input("Pas de Prix ($)", value=0.0625, step=0.0001, format="%.4f")
    strikes = strike_list(price_min, price_max, price_step)


    max_legs = st.slider("Nombre maximum de legs par stratégie:", 1, 4, 4)
    top_n = st.number_input("Nombre de meilleures structures à afficher:", value=10, min_value=1, max_value=100)

    years = [int(y.strip()) for y in years_input.split(",") if y.strip()]
    months = [m.strip() for m in months_input.split(",") if m.strip()]

    return UIParams(underlying, months, years, strike, price_min, price_max, price_step, max_legs, strikes)

def scoring_weights_block() -> dict:
    st.subheader("⚖️ Pondération du Score - COMPLET")
    
    # STRATÉGIES PRÉDÉFINIES
    preset_strategies = {
        "Balanced (Équilibré)": {
            'max_profit': 0.10, 'risk_reward': 0.10, 'profit_zone': 0.08, 'target_performance': 0.08,
            'surface_profit': 0.12, 'surface_loss': 0.08, 'profit_loss_ratio': 0.12,
            'delta_neutral': 0.06, 'gamma_exposure': 0.04, 'vega_exposure': 0.04, 'theta_positive': 0.04,
            'implied_vol': 0.04, 'breakeven_count': 0.03, 'breakeven_spread': 0.03
        },
        "Short Vol (Vente de Volatilité)": {
            'max_profit': 0.05, 'risk_reward': 0.10, 'profit_zone': 0.15, 'target_performance': 0.10,
            'surface_profit': 0.10, 'surface_loss': 0.15, 'profit_loss_ratio': 0.10,
            'delta_neutral': 0.10, 'gamma_exposure': 0.05, 'vega_exposure': 0.05, 'theta_positive': 0.15,
            'implied_vol': 0.00, 'breakeven_count': 0.00, 'breakeven_spread': 0.00
        },
        "Directional (Directionnel)": {
            'max_profit': 0.20, 'risk_reward': 0.15, 'profit_zone': 0.05, 'target_performance': 0.15,
            'surface_profit': 0.15, 'surface_loss': 0.05, 'profit_loss_ratio': 0.10,
            'delta_neutral': 0.02, 'gamma_exposure': 0.03, 'vega_exposure': 0.02, 'theta_positive': 0.02,
            'implied_vol': 0.02, 'breakeven_count': 0.02, 'breakeven_spread': 0.02
        },
        "Income (Génération de Revenus)": {
            'max_profit': 0.12, 'risk_reward': 0.08, 'profit_zone': 0.12, 'target_performance': 0.12,
            'surface_profit': 0.08, 'surface_loss': 0.10, 'profit_loss_ratio': 0.08,
            'delta_neutral': 0.08, 'gamma_exposure': 0.04, 'vega_exposure': 0.04, 'theta_positive': 0.18,
            'implied_vol': 0.03, 'breakeven_count': 0.03, 'breakeven_spread': 0.05
        },
        "Delta Neutral (Market Neutral)": {
            'max_profit': 0.08, 'risk_reward': 0.12, 'profit_zone': 0.10, 'target_performance': 0.08,
            'surface_profit': 0.10, 'surface_loss': 0.10, 'profit_loss_ratio': 0.10,
            'delta_neutral': 0.20, 'gamma_exposure': 0.06, 'vega_exposure': 0.08, 'theta_positive': 0.06,
            'implied_vol': 0.04, 'breakeven_count': 0.04, 'breakeven_spread': 0.04
        },
        "Manuel (Personnalisé)": None  # Sera configuré manuellement
    }
    


    strategy_choice = st.selectbox(
        "Choisir une stratégie:",
        list(preset_strategies.keys()),
        index=0,
        help="Sélectionnez une stratégie prédéfinie ou 'Manuel' pour personnaliser"
    )
    
    # Initialiser les poids avec la stratégie sélectionnée
    if strategy_choice != "Manuel (Personnalisé)":
        weights = preset_strategies[strategy_choice].copy()
        
        # Afficher les poids de la stratégie sélectionnée
        if 'force_manual' not in st.session_state or not st.session_state['force_manual']:
            with st.expander("📊 Voir les poids de cette stratégie", expanded=False):
                cols = st.columns(4)
                with cols[0]:
                    st.markdown("**💰 Financier**")
                    st.write(f"Max Profit: {weights['max_profit']*100:.0f}%")
                    st.write(f"R/R: {weights['risk_reward']*100:.0f}%")
                    st.write(f"Zone: {weights['profit_zone']*100:.0f}%")
                    st.write(f"Target: {weights['target_performance']*100:.0f}%")
                with cols[1]:
                    st.markdown("**📐 Surfaces**")
                    st.write(f"Profit: {weights['surface_profit']*100:.0f}%")
                    st.write(f"Loss: {weights['surface_loss']*100:.0f}%")
                    st.write(f"P/L: {weights['profit_loss_ratio']*100:.0f}%")
                with cols[2]:
                    st.markdown("**🔢 Greeks**")
                    st.write(f"Delta: {weights['delta_neutral']*100:.0f}%")
                    st.write(f"Gamma: {weights['gamma_exposure']*100:.0f}%")
                    st.write(f"Vega: {weights['vega_exposure']*100:.0f}%")
                    st.write(f"Theta: {weights['theta_positive']*100:.0f}%")
                with cols[3]:
                    st.markdown("**📊 Autres**")
                    st.write(f"IV: {weights['implied_vol']*100:.0f}%")
                    st.write(f"BE Count: {weights['breakeven_count']*100:.0f}%")
                    st.write(f"BE Spread: {weights['breakeven_spread']*100:.0f}%")
            
            return weights
    
    # Mode MANUEL - Afficher tous les sliders
    if 'force_manual' in st.session_state:
        del st.session_state['force_manual']
    
    with st.expander("📊 Personnaliser TOUS les poids de scoring", expanded=True):
        st.markdown("**Tous les attributs participent au scoring. Total doit être ~100%**")
        
        # MÉTRIQUES FINANCIÈRES
        st.markdown("### 💰 Métriques Financières (40%)")
        col1, col2 = st.columns(2)
        with col1:
            w_max_profit = st.slider("Max Profit", 0, 100, 10, 1) / 100
            w_rr = st.slider("Risque/Rendement", 0, 100, 10, 1) / 100
        with col2:
            w_zone = st.slider("Zone Profitable", 0, 100, 8, 1) / 100
            w_target = st.slider("Performance Cible", 0, 100, 8, 1) / 100
        
        # SURFACES
        st.markdown("### 📐 Surfaces (32%)")
        col1, col2, col3 = st.columns(3)
        with col1:
            w_surf_profit = st.slider("Surface Profit", 0, 100, 12, 1) / 100
        with col2:
            w_surf_loss = st.slider("Surface Loss (inversé)", 0, 100, 8, 1) / 100
        with col3:
            w_pl_ratio = st.slider("Ratio Profit/Loss", 0, 100, 12, 1) / 100
        
        # GREEKS
        st.markdown("### 🔢 Greeks (18%)")
        col1, col2 = st.columns(2)
        with col1:
            w_delta = st.slider("Delta Neutralité", 0, 100, 6, 1) / 100
            w_gamma = st.slider("Gamma Exposure", 0, 100, 4, 1) / 100
        with col2:
            w_vega = st.slider("Vega Exposure", 0, 100, 4, 1) / 100
            w_theta = st.slider("Theta Positif", 0, 100, 4, 1) / 100
        
        # VOLATILITÉ
        st.markdown("### 📊 Volatilité (4%)")
        w_vol = st.slider("Volatilité Implicite", 0, 100, 4, 1) / 100
        
        # BREAKEVENS
        st.markdown("### 🎯 Breakevens (6%)")
        col1, col2 = st.columns(2)
        with col1:
            w_be_count = st.slider("Nombre de Breakevens", 0, 100, 3, 1) / 100
        with col2:
            w_be_spread = st.slider("Écart des Breakevens", 0, 100, 3, 1) / 100
        
        # Calculer et afficher le total
        total = (w_max_profit + w_rr + w_zone + w_target + 
                w_surf_profit + w_surf_loss + w_pl_ratio +
                w_delta + w_gamma + w_vega + w_theta + 
                w_vol + w_be_count + w_be_spread)
        
        if total < 0.95 or total > 1.05:
            st.warning(f"⚠️ Total des poids: {total*100:.1f}% (devrait être proche de 100%)")
        else:
            st.success(f"✅ Total des poids: {total*100:.1f}%")
    
    return {
        # Métriques financières
        "max_profit": w_max_profit,
        "risk_reward": w_rr,
        "profit_zone": w_zone,
        "target_performance": w_target,
        # Surfaces
        "surface_profit": w_surf_profit,
        "surface_loss": w_surf_loss,
        "profit_loss_ratio": w_pl_ratio,
        # Greeks
        "delta_neutral": w_delta,
        "gamma_exposure": w_gamma,
        "vega_exposure": w_vega,
        "theta_positive": w_theta,
        # Volatilité
        "implied_vol": w_vol,
        # Breakevens
        "breakeven_count": w_be_count,
        "breakeven_spread": w_be_spread,
    }

@dataclass
class ScenarioData:
    centers: list[float]
    std_devs: list[float]
    weights: list[float]

def scenario_params() -> Optional[ScenarioData]:
    """
    Interface pour définir les scénarios de marché (mixture gaussienne).
    L'utilisateur peut ajouter autant de scénarios qu'il souhaite.
    Chaque scénario = (prix cible, incertitude/volatilité, probabilité)
    """    
    a = st.checkbox("Ajouter des scénarios ")
    if a == True : 
        if 'scenarios' not in st.session_state:
            st.session_state.scenarios = [
                {'price': 98.0, 'std': 0.10, 'weight': 50.0},  # Scénario neutre par défaut
            ]
        
        scenarios_to_delete = []
    
        for i, scenario in enumerate(st.session_state.scenarios):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**Scénario {i+1}**")
                
                with col2:
                    price = st.number_input(
                        "Prix Cible",
                        value=float(scenario['price']),
                        step=0.01,
                        format="%.4f",
                        key=f"price_{i}",
                        help="Prix attendu pour ce scénario"
                    )
                    st.session_state.scenarios[i]['price'] = price
                
                with col3:
                    std = st.number_input(
                        "Incertitude",
                        value=float(scenario['std']),
                        min_value=0.001,
                        step=0.01,
                        format="%.4f",
                        key=f"std_{i}",
                        help="Écart-type : plus c'est grand, plus le scénario est incertain"
                    )
                    st.session_state.scenarios[i]['std'] = std
                
                with col4:
                    weight = st.number_input(
                        "Probabilité",
                        value=float(scenario['weight']),
                        min_value=0.1,
                        max_value=100.0,
                        step=1.0,
                        format="%.1f",
                        key=f"weight_{i}",
                        help="Poids du scénario (sera normalisé)"
                    )
                    st.session_state.scenarios[i]['weight'] = weight
                
                with col5:
                    if len(st.session_state.scenarios) > 1:
                        if st.button("🗑️", key=f"delete_{i}", help="Supprimer ce scénario"):
                            scenarios_to_delete.append(i)
                
                st.divider()
        
        # Supprimer les scénarios marqués
        for idx in sorted(scenarios_to_delete, reverse=True):
            st.session_state.scenarios.pop(idx)
            st.rerun()
        
        if st.button("➕ Ajouter un scénario", use_container_width=True):
            # Ajouter un nouveau scénario avec des valeurs par défaut
            last_price = st.session_state.scenarios[-1]['price'] if st.session_state.scenarios else 98.0
            st.session_state.scenarios.append({
                'price': last_price + 0.10,
                'std': 0.10,
                'weight': 25.0
            })
            st.rerun()
        
        total_weight = sum(s['weight'] for s in st.session_state.scenarios)
        normalized_weights = [s['weight'] / total_weight for s in st.session_state.scenarios]
        

        # Préparer les données pour le retour
        centers = [s['price'] for s in st.session_state.scenarios]
        std_devs = [s['std'] for s in st.session_state.scenarios]
        weights = normalized_weights
        
        return ScenarioData(centers=centers, std_devs=std_devs, weights=weights)
    else : 
        
        return None 