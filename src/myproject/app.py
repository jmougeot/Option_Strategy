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
        st.stop()
    except Exception as e:
        st.error(f"❌ Erreur lors de l'import Bloomberg: {e}")
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
            'Max Profit': format_currency(comp.max_profit),
            'Max Loss': format_currency(comp.max_loss) if comp.max_loss != float('inf') else 'Illimité',
            'R/R Ratio': f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else '∞',
            'Zone ±': format_currency(comp.profit_zone_width),
            'P&L@Target': format_currency(comp.profit_at_target),
            'Delta': f"{comp.total_delta:.3f}",
            'Gamma': f"{comp.total_gamma:.3f}",
            'Vega': f"{comp.total_vega:.3f}",
            'Theta': f"{comp.total_theta:.3f}",
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
            strike_min = st.number_input(
                "Strike minimum:",
                value=96.0,
                step=0.25,
                help="Prix d'exercice minimum"
            )
            strike_max = st.number_input(
                "Strike maximum:",
                value=99.0,
                step=0.25,
                help="Prix d'exercice maximum"
            )
        
        strike_step = st.number_input(
            "Pas des strikes:",
            value=0.25,
            step=0.01,
            help="Incrément entre chaque strike"
        )
        
        # Construire les paramètres
        bloomberg_params = {
            'underlying': underlying,
            'months': [m.strip() for m in months_input.split(',')],
            'years': [int(y.strip()) for y in years_input.split(',')],
            'strikes': [round(strike_min + i * strike_step, 2) 
                       for i in range(int((strike_max - strike_min) / strike_step) + 1)]
        }
                
        st.markdown("---")
        
        # Section 2: Paramètres de marché
        st.subheader("💹 Paramètres de Marché")
        
        # Intervalle de prix au lieu d'un prix unique
        col1, col2 = st.columns(2)
        with col1:
            price_min = st.number_input(
                "Prix Min ($)",
                min_value=50.0,
                max_value=200.0,
                value=97.0,
                step=0.5,
                help="Borne inférieure de l'intervalle de prix"
            )
        
        with col2:
            price_max = st.number_input(
                "Prix Max ($)",
                min_value=50.0,
                max_value=200.0,
                value=103.0,
                step=0.5,
                help="Borne supérieure de l'intervalle de prix"
            )
        
        price_step = st.number_input(
            "Pas de Prix ($)",
            min_value=0.01,
            max_value=5.0,
            value=0.1,
            step=0.01,
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
                    strike_min=strike_min,
                    strike_max=strike_max,
                    days_to_expiry=days_to_expiry,
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
        
        # Message de succès
        structures_info = []
        if include_flies:
            structures_info.append("Butterflies")
        if include_condors:
            structures_info.append("Condors")
        structures_text = ' + '.join(structures_info) if structures_info else "Aucune structure"
        
        st.success(f"✅ {len(all_comparisons)} combinaisons analysées - Structures: {structures_text}")
        st.info(f"🎯 **Meilleur prix cible identifié : ${best_target_price:.2f}**")
        
        # ====================================================================
        # TABS POUR L'AFFICHAGE
        # ====================================================================
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏆 Vue d'Ensemble", 
            "📈 Diagramme P&L", 
            "🔍 Analyse Détaillée",
            "🎯 Toutes les Combinaisons",
            "📋 Données Brutes"
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
            
            fig_payoff = create_payoff_diagram(comparisons, best_target_price)
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
                st.write(f"**Prix cible optimal:** {format_currency(best_target_price)}")
                st.write(f"**P&L:** {format_currency(winner.profit_at_target)}")
                if winner.max_profit != float('inf') and winner.max_profit > 0:
                    pct = (winner.profit_at_target / winner.max_profit) * 100
                    st.write(f"**% du max profit:** {format_percentage(pct)}")
                
                st.subheader("📊 Greeks - Exposition")
                st.write("**Total Stratégie:**")
                st.write(f"  • Delta: {winner.total_delta:.4f}")
                st.write(f"  • Gamma: {winner.total_gamma:.4f}")
                st.write(f"  • Vega: {winner.total_vega:.4f}")
                st.write(f"  • Theta: {winner.total_theta:.4f}")
                
                # Détail Calls vs Puts
                with st.expander("📈 Détail Calls / Puts"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write("**Calls:**")
                        st.write(f"  • Delta: {winner.total_delta_calls:.4f}")
                        st.write(f"  • Gamma: {winner.total_gamma_calls:.4f}")
                        st.write(f"  • Vega: {winner.total_vega_calls:.4f}")
                        st.write(f"  • Theta: {winner.total_theta_calls:.4f}")
                    with col_b:
                        st.write("**Puts:**")
                        st.write(f"  • Delta: {winner.total_delta_puts:.4f}")
                        st.write(f"  • Gamma: {winner.total_gamma_puts:.4f}")
                        st.write(f"  • Vega: {winner.total_vega_puts:.4f}")
                        st.write(f"  • Theta: {winner.total_theta_puts:.4f}")
            
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
                best_target_price * 0.90,
                best_target_price * 0.95,
                best_target_price,
                best_target_price * 1.05,
                best_target_price * 1.10
            ]
            
            sim_data = []
            for comp in comparisons[:3]:  # Top 3
                row = {'Stratégie': comp.strategy_name}
                for price in price_scenarios:
                    pnl = comp.strategy.profit_at_expiry(price)
                    pct_change = ((price - best_target_price) / best_target_price) * 100
                    row[f"${price:.2f}\n({pct_change:+.0f}%)"] = format_currency(pnl)
                sim_data.append(row)
            
            st.dataframe(pd.DataFrame(sim_data), use_container_width=True, hide_index=True)
        
        # ----------------------------------------------------------------
        # TAB 4: TOUTES LES COMBINAISONS
        # ----------------------------------------------------------------
        with tab4:
            st.header("🎯 Toutes les Combinaisons Prix/Stratégie Testées")
            
            st.write(f"**Total de combinaisons:** {len(all_comparisons)}")
            st.write(f"**Prix testés:** {len(target_prices)} prix de ${min(target_prices):.2f} à ${max(target_prices):.2f}")
            
            # Créer un DataFrame complet
            all_data = []
            for comp in all_comparisons:
                all_data.append({
                    'Prix Cible': f"${comp.target_price:.2f}",
                    'Stratégie': comp.strategy_name,
                    'Score': f"{comp.score:.4f}",
                    'Crédit': format_currency(comp.net_credit),
                    'Max Profit': format_currency(comp.max_profit),
                    'Max Loss': format_currency(comp.max_loss) if comp.max_loss != float('inf') else 'Illimité',
                    'R/R': f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else '∞',
                    'P&L@Target': format_currency(comp.profit_at_target),
                    'Zone Profitable': format_currency(comp.profit_zone_width),
                    'Delta': f"{comp.total_delta:.3f}",
                    'Vega': f"{comp.total_vega:.3f}",
                    'Theta': f"{comp.total_theta:.3f}"
                })
            
            df_all = pd.DataFrame(all_data)
            
            # Filtres interactifs
            st.subheader("🔎 Filtrer les Résultats")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filter_strategies = st.multiselect(
                    "Stratégies:",
                    options=sorted(set([comp.strategy_name for comp in all_comparisons])),
                    default=None
                )
            
            with col2:
                filter_prices = st.multiselect(
                    "Prix Cibles:",
                    options=sorted(set([f"${comp.target_price:.2f}" for comp in all_comparisons])),
                    default=None
                )
            
            with col3:
                min_score = st.slider(
                    "Score minimum:",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.0,
                    step=0.05
                )
            
            # Appliquer les filtres
            df_filtered = df_all.copy()
            
            if filter_strategies:
                df_filtered = df_filtered[df_filtered['Stratégie'].isin(filter_strategies)]
            
            if filter_prices:
                df_filtered = df_filtered[df_filtered['Prix Cible'].isin(filter_prices)]
            
            if min_score > 0:
                df_filtered['Score_num'] = df_filtered['Score'].astype(float)
                df_filtered = df_filtered[df_filtered['Score_num'] >= min_score]
                df_filtered = df_filtered.drop('Score_num', axis=1)
            
            st.write(f"**{len(df_filtered)} / {len(df_all)} combinaisons affichées**")
            
            # Tableau avec tri
            st.dataframe(
                df_filtered,
                use_container_width=True,
                hide_index=True,
                height=500
            )
            
            # Graphiques d'analyse
            st.subheader("📊 Analyse Visuelle")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Heatmap: Score par prix et stratégie
                pivot_data = df_all.copy()
                pivot_data['Score_num'] = pivot_data['Score'].astype(float)
                pivot_table = pivot_data.pivot_table(
                    index='Stratégie',
                    columns='Prix Cible',
                    values='Score_num',
                    aggfunc='mean'
                )
                
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=pivot_table.values,
                    x=pivot_table.columns,
                    y=pivot_table.index,
                    colorscale='RdYlGn',
                    text=pivot_table.values,
                    texttemplate='%{text:.3f}',
                    textfont={"size":10},
                    colorbar=dict(title="Score")
                ))
                
                fig_heatmap.update_layout(
                    title="Heatmap des Scores",
                    xaxis_title="Prix Cible",
                    yaxis_title="Stratégie",
                    height=400
                )
                
                st.plotly_chart(fig_heatmap, use_container_width=True)
            
            with col2:
                # Top 10 des meilleures combinaisons
                top_10 = df_all.head(10)
                
                fig_top10 = px.bar(
                    top_10,
                    x='Score',
                    y=[f"{row['Stratégie']}\n@{row['Prix Cible']}" for _, row in top_10.iterrows()],
                    orientation='h',
                    title="Top 10 des Combinaisons",
                    labels={'y': 'Stratégie @ Prix'},
                    color='Score',
                    color_continuous_scale='viridis'
                )
                
                fig_top10.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_top10, use_container_width=True)
        
        # ----------------------------------------------------------------
        # TAB 5: DONNÉES BRUTES
        # ----------------------------------------------------------------
        with tab5:
            st.header("📋 Données Brutes")
            
            for idx, comp in enumerate(comparisons, 1):
                with st.expander(f"{idx}. {comp.strategy_name} (Score: {comp.score:.3f})"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.write("**Métriques Financières:**")
                        st.json({
                            "net_credit": comp.net_credit,
                            "max_profit": comp.max_profit if comp.max_profit != float('inf') else "Illimité",
                            "max_loss": comp.max_loss if comp.max_loss != float('inf') else "Illimité",
                            "risk_reward_ratio": comp.risk_reward_ratio if comp.risk_reward_ratio != float('inf') else "∞"
                        })
                    
                    with col2:
                        st.write("**Greeks - Total:**")
                        st.json({
                            "delta": round(comp.total_delta, 4),
                            "gamma": round(comp.total_gamma, 4),
                            "vega": round(comp.total_vega, 4),
                            "theta": round(comp.total_theta, 4)
                        })
                    
                    with col3:
                        st.write("**Greeks - Calls:**")
                        st.json({
                            "delta_calls": round(comp.total_delta_calls, 4),
                            "gamma_calls": round(comp.total_gamma_calls, 4),
                            "vega_calls": round(comp.total_vega_calls, 4),
                            "theta_calls": round(comp.total_theta_calls, 4)
                        })
                    
                    with col4:
                        st.write("**Greeks - Puts:**")
                        st.json({
                            "delta_puts": round(comp.total_delta_puts, 4),
                            "gamma_puts": round(comp.total_gamma_puts, 4),
                            "vega_puts": round(comp.total_vega_puts, 4),
                            "theta_puts": round(comp.total_theta_puts, 4)
                        })

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    main()
