"""
Streamlit Interface for Options Strategy Comparison
Description: Web user interface to compare options strategies
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from myproject.strategy.comparison_class import StrategyComparison
from myproject.app.main import process_bloomberg_to_strategies
from myproject.app.styles import inject_css
from myproject.app.widget import sidebar_params, scenario_params
from myproject.app.scoring_block import scoring_weights_block
from myproject.app.utils import (
    create_payoff_diagram,
    format_currency,
    create_comparison_table
)
from myproject.app.mixture_diagram import create_mixture_diagram


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
        
        # Widget de scénarios de marché
        st.markdown("---")
        scenarios = scenario_params()
        scoring_weights = scoring_weights_block()

    # ========================================================================
    # ZONE PRINCIPALE
    # ========================================================================
    
    compare_button = st.button("🚀 Lancer la Comparaison", type="primary", use_container_width=True)
    
    # Déterminer quelle source de stratégies utiliser
    all_comparisons = None
    best_target_price = None
    mixture = None  # Initialiser mixture
    
    # Utiliser les stratégies chargées si disponibles
        
    if compare_button:
        # ====================================================================
        # ÉTAPE 1 : Traitement complet via la fonction main
        # ====================================================================
        
        with st.spinner(f"🔄 Génération et comparaison des stratégies (max {params.max_legs} legs)..."):
            # Appeler la fonction principale qui fait TOUT
            best_strategies, stats, mixture = process_bloomberg_to_strategies(
                underlying=params.underlying,
                months=params.months,
                years=params.years,
                strikes=params.strikes,
                target_price=params.strike,
                price_min=params.price_min,
                price_max=params.price_max,
                max_legs=params.max_legs,
                top_n=200,
                scoring_weights=scoring_weights,
                verbose=False,
                scenarios = scenarios
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
        best_target_price = best_strategies[0].target_price if best_strategies else None
        
        if not all_comparisons:
            st.error("❌ Aucune stratégie disponible")
            return
        
        st.info(f"🎯 **Meilleur prix cible identifié : ${best_target_price:.2f}**")
        
        # Sauvegarder les stratégies dans session_state pour pouvoir les exporter
        st.session_state['current_strategies'] = all_comparisons
        st.session_state['current_params'] = {
            'underlying': params.underlying,
            'target_price': best_target_price,
            'months': params.months,
            'years': params.years,
            'strikes': params.strikes,
            'max_legs': params.max_legs,
            'price_min': params.price_min,
            'price_max': params.price_max
        }
    
    # Si on arrive ici sans stratégies, ne rien afficher
    if not all_comparisons:
        return
    
    # Filtrer les comparaisons pour le meilleur prix cible
    comparisons: list[StrategyComparison] = [c for c in all_comparisons if c.target_price == best_target_price]
    
    
    # ====================================================================
    # TABS POUR L'AFFICHAGE
    # ====================================================================
    
    tab1, tab2, tab3 , tab4= st.tabs([
        "Vue d'Ensemble", 
        "Diagramme P&L",
        "Mixture gaussienne",
        "test de tableau"
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
                "💰 Max Profit",
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

        
        st.dataframe(
            df.style,
            width='stretch',
            hide_index=True
        )
               
    # ----------------------------------------------------------------
    # TAB 2: DIAGRAMME P&L
    # ----------------------------------------------------------------
    with tab2:
        st.header("Diagramme de Profit/Perte à l'Expiration")
        fig_payoff = create_payoff_diagram(comparisons)
        st.plotly_chart(fig_payoff, use_container_width=True)
    
        
    with tab3: 
        st.header("Mixture Gaussienne")
        if mixture is not None:
            fig = create_mixture_diagram(mixture, target_price=best_target_price or 97.5)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Aucune mixture gaussienne disponible. Lancez une comparaison pour générer la mixture.")
    
# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    main()