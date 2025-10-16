"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import re
import sys
from pathlib import Path
from typing import Dict, List
from strategy.comparer import StrategyComparer, StrategyComparison



# ============================================================================
# CONFIGURATION DE LA PAGE
# ============================================================================

st.set_page_config(
    page_title="Options Strategy Comparator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# STYLES CSS PERSONNALISÉS
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .winner-card {
        background-color: #d4edda;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 6px solid #28a745;
        margin: 1rem 0;
    }
    .warning-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 24px;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def categorize_strategy(strategy: str) -> str:
    """
    Catégorise une stratégie dans une seule catégorie
    
    Args:
        strategy: Nom de la stratégie en CamelCase
        
    Returns:
        Nom de la catégorie avec emoji
    """
    if strategy.startswith('Short'):
        return '📉 Short Strategies'
    elif strategy.startswith('Iron'):
        return '🔷 Iron Strategies'
    elif strategy.startswith('Long') and 'Butterfly' in strategy:
        return '🦋 Butterfly Strategies'
    elif strategy.startswith('Long'):
        return '📈 Long Strategies'
    elif 'Butterfly' in strategy:
        return '🦋 Butterfly Strategies'
    elif 'Ratio' in strategy:
        return '⚖️ Ratio Strategies'
    elif 'Spread' in strategy:
        return '📊 Spread Strategies'
    else:
        return '📦 Other'

def camel_case_to_display_name(name: str) -> str:
    """
    Convertit un nom en CamelCase en format d'affichage
    Ex: 'IronCondor' -> 'Iron Condor'
    
    Args:
        name: Nom en CamelCase
        
    Returns:
        Nom formaté pour l'affichage
    """
    return re.sub('([A-Z])', r' \1', name).strip()

@st.cache_data
def load_options_data(filepath: str = 'calls_export.json') -> Dict:
    """Loads options data from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"❌ File {filepath} not found. Run generate_full_database.py first")
        st.stop()
    except json.JSONDecodeError:
        st.error(f"❌ Error reading file {filepath}")
        st.stop()

def prepare_options_data(data: Dict) -> Dict[str, List]:
    """Separates calls and puts."""
    calls = [opt for opt in data['options'] if opt['option_type'] == 'call']
    puts = [opt for opt in data['options'] if opt['option_type'] == 'put']
    
    return {'calls': calls, 'puts': puts}

def format_currency(value: float) -> str:
    """Formats a value as currency."""
    if value == float('inf'):
        return "Unlimited"
    return f"${value:.2f}"

def format_percentage(value: float) -> str:
    """Formats a percentage."""
    return f"{value:.1f}%"

def create_payoff_diagram(comparisons: List[StrategyComparison], target_price: float):
    """
    Crée un diagramme P&L interactif pour toutes les stratégies
    
    Args:
        comparisons: Liste des stratégies à afficher
        target_price: Prix cible pour la référence verticale
        
    Returns:
        Figure Plotly avec les courbes P&L
    """
    # Générer la plage de prix (±20% autour du prix cible)
    price_range = [target_price * (1 + i/100) for i in range(-20, 21, 1)]
    
    fig = go.Figure()
    
    # Lignes de référence
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=target_price, line_dash="dot", line_color="red", 
                  annotation_text="Target", opacity=0.7)
    
    # Palette de couleurs
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', 
              '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Tracer chaque stratégie
    for idx, comp in enumerate(comparisons):
        color = colors[idx % len(colors)]
        
        # Calculer P&L (optimisé avec list comprehension)
        pnl_values = [comp.strategy.profit_at_expiry(price) for price in price_range]
        
        # Courbe P&L
        fig.add_trace(go.Scatter(
            x=price_range,
            y=pnl_values,
            mode='lines',
            name=comp.strategy_name,
            line=dict(color=color, width=2.5),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Prix: $%{x:.2f}<br>' +
                         'P&L: $%{y:.2f}<extra></extra>'
        ))
        
        # Markers de breakeven
        if comp.breakeven_points:
            fig.add_trace(go.Scatter(
                x=comp.breakeven_points,
                y=[0] * len(comp.breakeven_points),
                mode='markers',
                marker=dict(size=10, color=color, symbol='circle-open', line=dict(width=2)),
                showlegend=False,
                hovertemplate='<b>Breakeven</b><br>Prix: $%{x:.2f}<extra></extra>'
            ))
    
    # Configuration du layout
    fig.update_layout(
        title="Diagramme de P&L à l'Expiration",
        xaxis_title="Prix du Sous-Jacent ($)",
        yaxis_title="Profit / Perte ($)",
        height=500,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor='white',
        xaxis=dict(gridcolor='lightgray'),
        yaxis=dict(gridcolor='lightgray', zeroline=True, zerolinecolor='gray')
    )
    
    return fig

def create_comparison_table(comparisons: List[StrategyComparison]) -> pd.DataFrame:
    """Crée un DataFrame pour l'affichage des comparaisons."""
    
    data = []
    for idx, comp in enumerate(comparisons, 1):
        data.append({
            'Rang': idx,
            'Stratégie': comp.strategy_name,
            'Crédit': format_currency(comp.net_credit),
            'Max Profit': format_currency(comp.max_profit),
            'Max Loss': format_currency(comp.max_loss) if comp.max_loss != float('inf') else 'Illimité',
            'R/R Ratio': f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else '∞',
            'Zone ±': format_currency(comp.profit_zone_width),
            'P&L@Target': format_currency(comp.profit_at_target),
            'Score': f"{comp.score:.3f}"
        })
    
    return pd.DataFrame(data)

def create_score_breakdown_chart(comparison: StrategyComparison):
    """Crée un graphique de décomposition du score."""
    
    # Affichage simple du score global
    fig = go.Figure(data=[
        go.Bar(
            x=[comparison.score],
            y=['Score Global'],
            orientation='h',
            marker_color='#1f77b4',
            text=[f"{comparison.score:.3f}"],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title=f"Score Global - {comparison.strategy_name}",
        xaxis_title="Score (0-1)",
        yaxis_title="",
        height=200,
        showlegend=False,
        xaxis=dict(range=[0, 1])
    )
    
    return fig

# ============================================================================
# INTERFACE PRINCIPALE
# ============================================================================

def main():
    # En-tête
    st.markdown('<div class="main-header">📊 Comparateur de Stratégies Options</div>', 
                unsafe_allow_html=True)
    st.markdown("---")
    
    # ========================================================================
    # SIDEBAR - PARAMÈTRES
    # ========================================================================
    
    with st.sidebar:
        st.header("⚙️ Paramètres")
        
        # Section 1: Données source
        st.subheader("📂 Source de Données")
        data_source = st.radio(
            "Source:",
            ["JSON Local", "Bloomberg API (À venir)"],
            help="Choisissez la source des données d'options"
        )
        
        # Ensure json_file is always defined to avoid "possibly unbound" errors.
        json_file = "calls_export.json"
        
        if data_source == "JSON Local":
            json_file = st.text_input(
                "Fichier JSON:",
                value="calls_export.json",
                help="Nom du fichier JSON contenant les données"
            )
        
        st.markdown("---")
        
        # Section 2: Paramètres de marché
        st.subheader("💹 Paramètres de Marché")
        
        target_price = st.number_input(
            "Prix Cible ($)",
            min_value=50.0,
            max_value=200.0,
            value=100.0,
            step=0.5,
            help="Prix autour duquel centrer les stratégies"
        )
        
        days_to_expiry = st.slider(
            "Jours jusqu'à l'Expiration",
            min_value=7,
            max_value=90,
            value=30,
            step=1,
            help="Horizon temporel pour les stratégies"
        )
        
        st.markdown("---")
        
        # Section 3: Sélection des stratégies
        st.subheader("🎯 Stratégies à Comparer")
        
        # 🔄 AUTO-DÉTECTION : Toutes les stratégies sont chargées automatiquement
        available_strategies = sorted(StrategyComparer.AVAILABLE_STRATEGIES)
        
        # Stratégies par défaut (short volatility populaires)
        default_strategies = {'IronCondor', 'IronButterfly', 'ShortStrangle', 'ShortStraddle'}
        
        # Grouper par catégories (chaque stratégie dans UNE SEULE catégorie)
        categories = {}
        for strategy in available_strategies:
            category = categorize_strategy(strategy)
            if category not in categories:
                categories[category] = []
            categories[category].append(strategy)
        
        selected_strategies = []
        
        # Ordre d'affichage des catégories
        category_order = [
            '📉 Short Strategies', 
            '🔷 Iron Strategies', 
            '📊 Spread Strategies', 
            '📈 Long Strategies', 
            '🦋 Butterfly Strategies', 
            '⚖️ Ratio Strategies', 
            '📦 Other'
        ]
        
        # Afficher par catégories avec expanders
        for category in category_order:
            if category in categories and categories[category]:
                # Ouvrir par défaut les catégories Short et Iron
                is_expanded = category in ['📉 Short Strategies', '🔷 Iron Strategies']
                
                with st.expander(f"{category} ({len(categories[category])})", expanded=is_expanded):
                    for strategy in categories[category]:
                        display_name = camel_case_to_display_name(strategy)
                        
                        if st.checkbox(
                            display_name, 
                            value=(strategy in default_strategies),
                            key=f"strat_{strategy}"
                        ):
                            selected_strategies.append(strategy)
        
        # Info sur la sélection
        st.info(f"📊 {len(selected_strategies)}/{len(available_strategies)} stratégies sélectionnées")
        
        st.markdown("---")
        
        # Section 4: Pondération du scoring
        st.subheader("⚖️ Pondération du Score")
        
        with st.expander("Personnaliser les poids", expanded=False):
            weight_max_profit = st.slider("Max Profit", 0, 100, 30, 5) / 100
            weight_rr = st.slider("Risque/Rendement", 0, 100, 30, 5) / 100
            weight_zone = st.slider("Zone Profitable", 0, 100, 20, 5) / 100
            weight_target = st.slider("Performance Cible", 0, 100, 20, 5) / 100
            
            total_weight = weight_max_profit + weight_rr + weight_zone + weight_target
            if abs(total_weight - 1.0) > 0.01:
                st.warning(f"⚠️ Total: {total_weight*100:.0f}% (devrait être 100%)")
        
        scoring_weights = {
            'max_profit': weight_max_profit,
            'risk_reward': weight_rr,
            'profit_zone': weight_zone,
            'target_performance': weight_target
        }
        
        st.markdown("---")
        
        # Bouton de comparaison
        compare_button = st.button("🚀 COMPARER", type="primary", use_container_width=True)
    
    # ========================================================================
    # ZONE PRINCIPALE
    # ========================================================================
    
    if compare_button:
        if not selected_strategies:
            st.error("❌ Veuillez sélectionner au moins une stratégie à comparer")
            return
        
        # Chargement des données
        with st.spinner("📂 Chargement des données..."):
            data = load_options_data(json_file)
            options_data = prepare_options_data(data)
            
            nb_calls = len(options_data['calls'])
            nb_puts = len(options_data['puts'])
            
            st.success(f"✅ {nb_calls + nb_puts} options chargées ({nb_calls} calls, {nb_puts} puts)")
        
        # Vérification des puts
        if nb_puts == 0:
            st.error("❌ Aucun put trouvé dans les données. Régénérez la base avec generate_full_database.py")
            return
        
        # Comparaison des stratégies
        with st.spinner("🔄 Comparaison des stratégies en cours..."):
            comparer = StrategyComparer(options_data)
            
            comparisons = comparer.compare_strategies(
                target_price=target_price,
                days_to_expiry=days_to_expiry,
                strategies_to_compare=selected_strategies,
                weights=scoring_weights
            )
        
        if not comparisons:
            st.error(" Aucune stratégie n'a pu être construite avec les paramètres donnés")
            return
        
        st.success(f"✅ {len(comparisons)} stratégies comparées avec succès!")
        
        # ====================================================================
        # TABS POUR L'AFFICHAGE
        # ====================================================================
        
        tab1, tab2, tab3, tab4 = st.tabs([
            " Vue d'Ensemble", 
            " Diagramme P&L", 
            " Analyse Détaillée",
            " Données Brutes"
        ])
        
        # ----------------------------------------------------------------
        # TAB 1: VUE D'ENSEMBLE
        # ----------------------------------------------------------------
        with tab1:
            st.header("Vue d'Ensemble des Stratégies")
            
            # Carte de la stratégie gagnante
            winner = comparisons[0]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "🥇 Meilleure Stratégie",
                    winner.strategy_name,
                    f"Score: {winner.score:.3f}"
                )
            with col2:
                st.metric(
                    "💰 Crédit Net",
                    format_currency(winner.net_credit),
                    ""
                )
            with col3:
                st.metric(
                    "📊 Max Profit",
                    format_currency(winner.max_profit),
                    ""
                )
            with col4:
                max_loss_str = format_currency(winner.max_loss) if winner.max_loss != float('inf') else "Illimité"
                st.metric(
                    "⚠️ Max Loss",
                    max_loss_str,
                    ""
                )
            
            st.markdown("---")
            
            # Tableau de comparaison
            st.subheader("Tableau Comparatif")
            df = create_comparison_table(comparisons)
            
            # Colorer la première ligne (gagnante)
            def highlight_winner(row):
                if row['Rang'] == 1:
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                df.style.apply(highlight_winner, axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            # Graphique de comparaison des scores
            st.subheader("Comparaison des Scores")
            
            score_data = pd.DataFrame({
                'Stratégie': [c.strategy_name for c in comparisons],
                'Score Total': [c.score for c in comparisons]
            })
            
            fig = px.bar(
                score_data,
                x='Score Total',
                y='Stratégie',
                orientation='h',
                color='Score Total',
                color_continuous_scale='blues',
                text='Score Total'
            )
            fig.update_traces(texttemplate='%{text:.3f}', textposition='outside')
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        # ----------------------------------------------------------------
        # TAB 2: DIAGRAMME P&L
        # ----------------------------------------------------------------
        with tab2:
            st.header("Diagramme de Profit/Perte à l'Expiration")
            
            fig_payoff = create_payoff_diagram(comparisons, target_price)
            st.plotly_chart(fig_payoff, use_container_width=True)
            
            # Tableau des breakevens
            st.subheader("Points de Breakeven")
            
            be_data = []
            for comp in comparisons:
                breakevens = ', '.join([f"${be:.2f}" for be in comp.breakeven_points])
                be_data.append({
                    'Stratégie': comp.strategy_name,
                    'Breakevens': breakevens,
                    'Zone': format_currency(comp.profit_zone_width)
                })
            
            st.dataframe(pd.DataFrame(be_data), use_container_width=True, hide_index=True)
        
        # ----------------------------------------------------------------
        # TAB 3: ANALYSE DÉTAILLÉE
        # ----------------------------------------------------------------
        with tab3:
            st.header("🏆 Analyse Détaillée de la Stratégie Gagnante")
            
            winner = comparisons[0]
            
            # Informations générales
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="winner-card">
                    <h3>🎯 {winner.strategy_name}</h3>
                    <h4>Score Global: {winner.score:.4f}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                st.subheader("📈 Métriques Financières")
                st.write(f"**Crédit net reçu:** {format_currency(winner.net_credit)}")
                st.write(f"**Profit maximum:** {format_currency(winner.max_profit)}")
                max_loss_display = format_currency(winner.max_loss) if winner.max_loss != float('inf') else "Illimité ⚠️"
                st.write(f"**Perte maximale:** {max_loss_display}")
                rr_display = f"{winner.risk_reward_ratio:.2f}:1" if winner.risk_reward_ratio != float('inf') else "∞"
                st.write(f"**Ratio Risque/Rendement:** {rr_display}")
                
                st.subheader("🎯 Zone Profitable")
                st.write(f"**Largeur:** {format_currency(winner.profit_zone_width)}")
                if len(winner.breakeven_points) >= 2:
                    st.write(f"**Range:** {format_currency(winner.breakeven_points[0])} - {format_currency(winner.breakeven_points[1])}")
                
                st.subheader("💰 Performance au Prix Cible")
                st.write(f"**Prix cible:** {format_currency(target_price)}")
                st.write(f"**P&L:** {format_currency(winner.profit_at_target)}")
                if winner.max_profit != float('inf') and winner.max_profit > 0:
                    pct = (winner.profit_at_target / winner.max_profit) * 100
                    st.write(f"**% du max profit:** {format_percentage(pct)}")
            
            with col2:
                # Décomposition du score
                fig_breakdown = create_score_breakdown_chart(winner)
                st.plotly_chart(fig_breakdown, use_container_width=True)
                
                # Recommandations
                st.subheader("💡 Recommandations")
                
                if winner.max_loss != float('inf'):
                    st.success("✅ Stratégie à risque défini - Recommandée pour un risque contrôlé")
                else:
                    st.warning("⚠️ Stratégie à risque illimité - Utiliser avec prudence et stops")
                
                st.info(f"""
                **Actions suggérées:**
                1. Vérifier la liquidité des options
                2. Calculer la marge requise
                3. Définir un plan d'ajustement
                4. Monitorer la volatilité implicite
                """)
            
            st.markdown("---")
            
            # Simulation P&L
            st.subheader("📉 Simulation P&L à Différents Prix")
            
            price_scenarios = [
                target_price * 0.90,
                target_price * 0.95,
                target_price,
                target_price * 1.05,
                target_price * 1.10
            ]
            
            sim_data = []
            for comp in comparisons[:3]:  # Top 3
                row = {'Stratégie': comp.strategy_name}
                for price in price_scenarios:
                    pnl = comp.strategy.profit_at_expiry(price)
                    pct_change = ((price - target_price) / target_price) * 100
                    row[f"${price:.2f}\n({pct_change:+.0f}%)"] = format_currency(pnl)
                sim_data.append(row)
            
            st.dataframe(pd.DataFrame(sim_data), use_container_width=True, hide_index=True)
        
        # ----------------------------------------------------------------
        # TAB 4: DONNÉES BRUTES
        # ----------------------------------------------------------------
        with tab4:
            st.header("📋 Données Brutes")
            
            for idx, comp in enumerate(comparisons, 1):
                with st.expander(f"{idx}. {comp.strategy_name} (Score: {comp.score:.3f})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Métriques Financières:**")
                        st.json({
                            "net_credit": comp.net_credit,
                            "max_profit": comp.max_profit if comp.max_profit != float('inf') else "Illimité",
                            "max_loss": comp.max_loss if comp.max_loss != float('inf') else "Illimité",
                            "risk_reward_ratio": comp.risk_reward_ratio if comp.risk_reward_ratio != float('inf') else "∞"
                        })
                    
                    with col2:
                        st.write("**Scores:**")
                        st.json({
                            "score": round(comp.score, 4)
                        })
                    
                    with col3:
                        st.write("**Autres:**")
                        st.json({
                            "breakeven_points": comp.breakeven_points,
                            "profit_zone_width": comp.profit_zone_width,
                            "profit_at_target": comp.profit_at_target
                        })

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    main()
