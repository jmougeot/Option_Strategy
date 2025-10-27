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
from myproject.option.comparison_class import StrategyComparison
from myproject.option.main import process_bloomberg_to_strategies
from myproject.app.styles import inject_css
from myproject.app.widget import scoring_weights_block, sidebar_params
from myproject.app.utils import (
    create_payoff_diagram,
    load_options_from_bloomberg,
    format_currency,
    create_comparison_table
)

# ============================================================================
# CONFIGURATION DE LA PAGE
# ============================================================================

st.set_page_config(
    page_title="Options Strategy Comparator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

inject_css()



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
        params = sidebar_params()
        scoring_weights = scoring_weights_block()

    # ========================================================================
    # ZONE PRINCIPALE
    # ========================================================================
    
    compare_button = st.button("🚀 Lancer la Comparaison", type="primary", use_container_width=True)
    
    if compare_button:
        # ====================================================================
        # ÉTAPE 1 : Chargement des données depuis Bloomberg
        # ====================================================================
        with st.spinner("📥 Import depuis Bloomberg..."):
            # Convertir UIParams en dict pour load_options_from_bloomberg
            params_dict = {
                'underlying': params.underlying,
                'months': params.months,
                'years': params.years,
                'strikes': params.strikes,
                'price_min': params.price_min,
                'price_max': params.price_max
            }
            options = load_options_from_bloomberg(params_dict)
            
            nb_options = len(options)
            st.success(f"✅ {nb_options} options chargées depuis Bloomberg")
            
            # Optionnellement sauvegarder
            save_data = st.checkbox("Sauvegarder les données importées en JSON", value=False)
            if save_data and options:
                from myproject.bloomberg.bloomberg_data_importer import save_to_json
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_filename = f"bloomberg_import_{timestamp}.json"
                save_to_json(options, save_filename)
                st.success(f"💾 Données sauvegardées dans {save_filename}")
        
        # Validation
        if nb_options == 0:
            st.error("❌ Aucune option trouvée dans les données Bloomberg")
            return
        
        # Validation de l'intervalle de prix
        if params.price_min >= params.price_max:
            st.error("❌ Le prix minimum doit être inférieur au prix maximum")
            return
        
        # ====================================================================
        # ÉTAPE 2-3 : Traitement complet via la fonction main
        # ====================================================================
        
        with st.spinner(f"🔄 Génération et comparaison des stratégies (max {params.max_legs} legs)..."):
            # Appeler la fonction principale qui fait TOUT
            best_strategies, stats = process_bloomberg_to_strategies(
                underlying=params.underlying,
                months=params.months,
                years=params.years,
                strikes=params.strikes,
                target_price=params.strike,
                price_min=params.price_min,
                price_max=params.price_max,
                max_legs=params.max_legs,
                top_n=params.top_n,
                scoring_weights=scoring_weights,
                verbose=False
            )
            
            # Vérifier les résultats
            if not best_strategies:
                st.error("❌ Aucune stratégie générée")
                st.info(f"📊 Statistiques : {stats.get('nb_options', 0)} options converties")
                return
            
            # Afficher les statistiques
            st.success(f"""✅ Traitement terminé avec succès !
            • {stats.get('nb_options', 0)} options converties
            • {stats.get('nb_strategies_totales', 0)} stratégies générées
            • {stats.get('nb_strategies_classees', 0)} meilleures stratégies identifiées
            """)
        
        # Utiliser best_strategies pour l'affichage
        all_comparisons = best_strategies
        comparisons = best_strategies
        best_comparison = best_strategies[0] if best_strategies else None
        
        if not best_comparison:
            st.error("❌ Aucune stratégie disponible")
            return
        
        # Pour l'affichage, on utilise la meilleure stratégie
        best_comparison = all_comparisons[0]
        best_target_price = best_comparison.target_price
        
        # Filtrer les comparaisons pour ce prix optimal
        comparisons = [c for c in all_comparisons if c.target_price == best_target_price]
        st.info(f"🎯 **Meilleur prix cible identifié : ${best_target_price:.2f}**")
        
        # ====================================================================
        # AFFICHAGE DES POIDS UTILISÉS - COMPLET
        # ====================================================================
        
        with st.expander("📊 Poids de scoring utilisés (TOUS LES ATTRIBUTS)", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("**💰 Métriques Financières**")
                st.write(f"• Max Profit: **{scoring_weights.get('max_profit', 0)*100:.0f}%**")
                st.write(f"• Risque/Rendement: **{scoring_weights.get('risk_reward', 0)*100:.0f}%**")
                st.write(f"• Zone Profitable: **{scoring_weights.get('profit_zone', 0)*100:.0f}%**")
                st.write(f"• Performance Cible: **{scoring_weights.get('target_performance', 0)*100:.0f}%**")
            
            with col2:
                st.markdown("**📐 Surfaces**")
                st.write(f"• Surface Profit: **{scoring_weights.get('surface_profit', 0)*100:.0f}%**")
                st.write(f"• Surface Loss: **{scoring_weights.get('surface_loss', 0)*100:.0f}%**")
                st.write(f"• Ratio P/L: **{scoring_weights.get('profit_loss_ratio', 0)*100:.0f}%**")
            
            with col3:
                st.markdown("**🔢 Greeks**")
                st.write(f"• Delta Neutral: **{scoring_weights.get('delta_neutral', 0)*100:.0f}%**")
                st.write(f"• Gamma: **{scoring_weights.get('gamma_exposure', 0)*100:.0f}%**")
                st.write(f"• Vega: **{scoring_weights.get('vega_exposure', 0)*100:.0f}%**")
                st.write(f"• Theta: **{scoring_weights.get('theta_positive', 0)*100:.0f}%**")
            
            with col4:
                st.markdown("**📊 Autres**")
                st.write(f"• Volatilité: **{scoring_weights.get('implied_vol', 0)*100:.0f}%**")
                st.write(f"• BE Count: **{scoring_weights.get('breakeven_count', 0)*100:.0f}%**")
                st.write(f"• BE Spread: **{scoring_weights.get('breakeven_spread', 0)*100:.0f}%**")
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
