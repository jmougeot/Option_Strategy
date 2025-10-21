"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
from typing import Dict, List
from myproject.option.multi_structure_comparer import MultiStructureComparer
from myproject.option.comparison_class import StrategyComparison

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
        border-left: 5px solid #1f77b4;
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

@st.cache_data
def load_options_from_bloomberg(params: Dict) -> Dict:
    """
    Charge les données d'options depuis Bloomberg
    
    Args:
        params: Dictionnaire avec underlying, months, years, strikes
        
    Returns:
        Dictionnaire au format {options: [...]}
    """
    try:
        from src.myproject.bloomberg_data_importer import import_euribor_options
        
        data = import_euribor_options(
            underlying=params['underlying'],
            months=params['months'],
            years=params['years'],
            strikes=params['strikes'],
            include_calls=True,
            include_puts=True
        )
        
        return data
    except ImportError as e:
        st.error(f"❌ Erreur d'import du module Bloomberg: {e}")
        # stop the Streamlit run but also return an empty dict to satisfy the type checker
        st.stop()
        return {}
    except Exception as e:
        st.error(f"❌ Erreur lors de l'import Bloomberg: {e}")
        # stop the Streamlit run but also return an empty dict to satisfy the type checker
        st.stop()
        return {}

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
    
    # Filtrer les stratégies valides (avec strategy != None)
    valid_comparisons = [comp for comp in comparisons if comp.strategy is not None]
    
    # Tracer chaque stratégie
    for idx, comp in enumerate(valid_comparisons):
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
    """Crée un DataFrame pour l'affichage des comparaisons avec tous les critères."""
    
    data = []
    for idx, comp in enumerate(comparisons, 1):
        data.append({
            'Rang': idx,
            'Stratégie': comp.strategy_name,
            'Score': f"{comp.score:.3f}",
            # Critères financiers
            'Max Profit': format_currency(comp.max_profit),
            'Max Loss': format_currency(comp.max_loss) if comp.max_loss != float('inf') else 'Illimité',
            'R/R Ratio': f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else '∞',
            'Zone ±': format_currency(comp.profit_zone_width),
            'P&L@Target': format_currency(comp.profit_at_target),
            # Nouveaux critères de surfaces
            'Surf. Profit': f"{comp.surface_profit:.2f}",
            'Surf. Loss': f"{comp.surface_loss:.2f}",
            'Surf. Gauss': f"{comp.surface_gauss:.2f}",
            'P/L Ratio': f"{(comp.surface_profit/comp.surface_loss):.2f}" if comp.surface_loss > 0 else '∞',
            # Greeks
            'Delta': f"{comp.total_delta:.3f}",
            'Gamma': f"{comp.total_gamma:.3f}",
            'Vega': f"{comp.total_vega:.3f}",
            'Theta': f"{comp.total_theta:.3f}"
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
        
        # Paramètres d'import Bloomberg
        underlying = st.text_input(
            "Sous-jacent:",
            value="ER",
            help="Code Bloomberg (ex: ER pour EURIBOR)"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            months_input = st.text_input(
                "Mois d'expiration:",
                value="F,G,H,K,M,N",
                help="Codes séparés par virgule (F=Jan, G=Feb, H=Mar, K=Apr, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec)"
            )
            years_input = st.text_input(
                "Années:",
                value="6",
                help="Années sur 1 chiffre séparées par virgule (6=2026, 7=2027)"
            )
        
        with col2:
            strike = st.number_input(
                "Strike :",
                value=97.0,
                step=0.625,
                help="Target Price"
            )
        
        strike_step = st.number_input(
            "Pas des strikes:",
            value=0.625,
            step=0.001,
            help="Incrément entre chaque strike"
        )
        
        # Nombre de strikes à générer
        nb_strikes = st.number_input(
            "Nombre de strikes:",
            value=13,
            step=1,
            help="Nombre de strikes à générer à partir du strike minimum"
        )
        
        # Construire les paramètres
        # Générer la liste de strikes basée sur le strike minimum
        strikes_list = [round(strike + i * strike_step, 2) for i in range(nb_strikes)]
        
        bloomberg_params = {
            'underlying': underlying,
            'months': [m.strip() for m in months_input.split(',')],
            'years': [int(y.strip()) for y in years_input.split(',')],
            'strikes': strikes_list
        }
                
        st.markdown("---")
        
        # Section 2: Paramètres de marché
        st.subheader("💹 Paramètres de Marché")
        
        # Intervalle de prix au lieu d'un prix unique
        col1, col2 = st.columns(2)
        with col1:
            price_min = st.number_input(
                "Prix Min ($)",
                value=96.0,
                step=0.001,
                help="Borne inférieure de l'intervalle de prix"
            )
        
        with col2:
            price_max = st.number_input(
                "Prix Max ($)",
                value=98,
                step=0.001,
                help="Borne supérieure de l'intervalle de prix"
            )
        
        price_step = st.number_input(
            "Pas de Prix ($)",
            value=0.625,
            step=0.001,
            help="Incrément entre chaque prix cible à tester"
        )
        
        # Validation
        if price_min >= price_max:
            st.error("⚠️ Le prix minimum doit être inférieur au prix maximum")
        else:
            target_prices = [round(price_min + i * price_step, 2) 
                           for i in range(int((price_max - price_min) / price_step) + 1)]
                
        # Section 3: Options d'auto-génération
        st.subheader("Options de Génération")
                
        with st.expander("Paramètres de génération", expanded=True):
            include_flies = st.checkbox("Inclure les Butterflies", value=True)
            include_condors = st.checkbox("Inclure les Condors", value=True)
            require_symmetric = st.checkbox("Uniquement structures symétriques", value=False)
            top_n_structures = st.number_input(
                "Nombre de meilleures structures à afficher:",
                min_value=5,
                max_value=50,
                value=10,
                step=5
            )
                
        # Section 4: Pondération du scoring
        st.subheader("⚖️ Pondération du Score")
        
        with st.expander("Personnaliser les poids", expanded=False):
            st.markdown("**Critères Classiques**")
            weight_max_profit = st.slider("Max Profit", 0, 100, 15, 5) / 100
            weight_rr = st.slider("Risque/Rendement", 0, 100, 15, 5) / 100
            weight_zone = st.slider("Zone Profitable", 0, 100, 10, 5) / 100
            weight_target = st.slider("Performance Cible", 0, 100, 10, 5) / 100
            
            st.markdown("**Nouveaux Critères (Surfaces)**")
            weight_surface_gauss = st.slider("Surface Gaussienne", 0, 100, 35, 5) / 100
            weight_profit_loss_ratio = st.slider("Ratio Profit/Loss", 0, 100, 15, 5) / 100
            
            total_weight = (weight_max_profit + weight_rr + weight_zone + 
                          weight_target + weight_surface_gauss + weight_profit_loss_ratio)
            if abs(total_weight - 1.0) > 0.01:
                st.warning(f"⚠️ Total: {total_weight*100:.0f}% (devrait être 100%)")
            else:
                st.success(f"✅ Total: {total_weight*100:.0f}%")
        
        scoring_weights = {
            'max_profit': weight_max_profit,
            'risk_reward': weight_rr,
            'profit_zone': weight_zone,
            'target_performance': weight_target,
            'surface_gauss': weight_surface_gauss,
            'profit_loss_ratio': weight_profit_loss_ratio
        }
        
        st.markdown("---")
        
        # Bouton de comparaison
        compare_button = st.button("🚀 COMPARER", type="primary", width='stretch')
    
    # ========================================================================
    # ZONE PRINCIPALE
    # ========================================================================
    
    if compare_button:
        # Chargement des données depuis Bloomberg
        with st.spinner("� Import depuis Bloomberg en cours..."):
            data = load_options_from_bloomberg(bloomberg_params)
            
            # Optionnellement sauvegarder
            save_data = st.checkbox("Sauvegarder les données importées en JSON", value=True)
            if save_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_filename = f"bloomberg_import_{timestamp}.json"
                with open(save_filename, 'w') as f:
                    json.dump(data, f, indent=2)
                st.success(f"💾 Données sauvegardées dans {save_filename}")
            
            options_data = prepare_options_data(data)
            
            nb_calls = len(options_data['calls'])
            nb_puts = len(options_data['puts'])
            
            st.success(f"✅ {nb_calls + nb_puts} options chargées depuis Bloomberg ({nb_calls} calls, {nb_puts} puts)")
        
        # Vérification des puts
        if nb_puts == 0:
            st.error("❌ Aucun put trouvé dans les données. Régénérez la base avec generate_full_database.py")
            return
        
        # Validation de l'intervalle de prix
        if price_min >= price_max:
            st.error("❌ Le prix minimum doit être inférieur au prix maximum")
            return
        
        # Calculer les prix cibles
        target_prices = [round(price_min + i * price_step, 2) 
                        for i in range(int((price_max - price_min) / price_step) + 1)]
        
        # Comparaison avec auto-génération pour TOUS les prix cibles
        with st.spinner(f"🔄 Auto-génération et comparaison pour {len(target_prices)} prix cibles..."):
            multi_comparer = MultiStructureComparer(options_data)
            
            all_comparisons = []
            
            # Tester chaque prix cible
            for target_price in target_prices:
                comparisons = multi_comparer.compare_all_structures(
                    target_price=target_price,
                    strike=strike, 
                    include_flies=include_flies,
                    include_condors=include_condors,
                    require_symmetric=require_symmetric,
                    top_n=top_n_structures,
                    weights=scoring_weights 
                )
                
                if comparisons:
                    all_comparisons.extend(comparisons)
        
        if not all_comparisons:
            st.error("❌ Aucune stratégie n'a pu être construite avec les paramètres donnés")
            return
        
        # Trouver la meilleure combinaison globale
        all_comparisons.sort(key=lambda x: x.score, reverse=True)
        
        # Pour l'affichage, on utilise la meilleure stratégie
        best_comparison = all_comparisons[0]
        best_target_price = best_comparison.target_price
        
        # Filtrer les comparaisons pour ce prix optimal
        comparisons = [c for c in all_comparisons if c.target_price == best_target_price]
        st.info(f"🎯 **Meilleur prix cible identifié : ${best_target_price:.2f}**")
        
        # ====================================================================
        # AFFICHAGE DES POIDS UTILISÉS
        # ====================================================================
        
        with st.expander("📊 Poids de scoring utilisés", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Critères Classiques**")
                st.write(f"• Max Profit: **{scoring_weights['max_profit']*100:.0f}%**")
                st.write(f"• Risque/Rendement: **{scoring_weights['risk_reward']*100:.0f}%**")
                st.write(f"• Zone Profitable: **{scoring_weights['profit_zone']*100:.0f}%**")
                st.write(f"• Performance Cible: **{scoring_weights['target_performance']*100:.0f}%**")
            with col2:
                st.markdown("**Critères de Surfaces**")
                st.write(f"• Poximité avec le strike: **{scoring_weights['surface_gauss']*100:.0f}%**")
                st.write(f"• Ratio Profit/Loss: **{scoring_weights['profit_loss_ratio']*100:.0f}%**")
                st.markdown("---")
                total = sum(scoring_weights.values())
                st.write(f"**Total: {total*100:.0f}%**")
        
        # ====================================================================
        # TABS POUR L'AFFICHAGE
        # ====================================================================
        
        tab1, tab2 = st.tabs([
            "🏆 Vue d'Ensemble", 
            "📈 Diagramme P&L", 
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
                    "� Max Profit",
                    format_currency(winner.max_profit),
                    ""
                )
            with col3:
                max_loss_str = format_currency(winner.max_loss) if winner.max_loss != float('inf') else "Illimité"
                st.metric(
                    "⚠️ Max Loss",
                    max_loss_str,
                    ""
                )
            with col4:
                st.metric(
                    "🎯 P&L au Prix Cible",
                    format_currency(winner.profit_at_target),
                    f"{winner.profit_at_target_pct:.1f}% du max"
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
                width='stretch',
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
            st.plotly_chart(fig, width='stretch')
        
        # ----------------------------------------------------------------
        # TAB 2: DIAGRAMME P&L
        # ----------------------------------------------------------------
        with tab2:
            st.header("Diagramme de Profit/Perte à l'Expiration")
            
            fig_payoff = create_payoff_diagram(comparisons, best_target_price)
            st.plotly_chart(fig_payoff, width='stretch')
            
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
            
            st.dataframe(pd.DataFrame(be_data), width='stretch', hide_index=True)
        

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    main()
