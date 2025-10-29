import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from typing import Dict, List
from myproject.strategy.comparison_class import StrategyComparison
from myproject.option.option_class import Option


def prepare_options_data(options: List[Option]) -> Dict[str, List[Option]]:
    """Sépare les calls et puts."""
    calls = [opt for opt in options if opt.option_type == 'call']
    puts = [opt for opt in options if opt.option_type == 'put']
    
    return {'calls': calls, 'puts': puts}

def format_currency(value: float) -> str:
    """Formats a value as currency."""
    if value == float('inf'):
        return "Unlimited"
    return f"${value:.2f}"

def format_percentage(value: float) -> str:
    """Formats a percentage."""
    return f"{value:.1f}%"

def format_expiration_date(month: str, year: int) -> str:
    """
    Formate la date d'expiration à partir du mois Bloomberg et de l'année.
    
    Args:
        month: Code du mois Bloomberg (F, G, H, K, M, N, Q, U, V, X, Z)
        year: Année (6 = 2026)
        
    Returns:
        Date formatée (ex: "Jun 2026")
    """
    month_names = {
        'F': 'Jan', 'G': 'Feb', 'H': 'Mar', 'K': 'Apr',
        'M': 'Jun', 'N': 'Jul', 'Q': 'Aug', 'U': 'Sep',
        'V': 'Oct', 'X': 'Nov', 'Z': 'Dec'
    }
    
    month_name = month_names.get(month, month)
    full_year = 2020 + year
    
    return f"{month_name} {full_year}"

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


def create_single_strategy_payoff(strategy: StrategyComparison, target_price: float) -> go.Figure:
    """
    Crée un diagramme P&L pour une seule stratégie.
    
    Args:
        strategy: Stratégie à afficher
        target_price: Prix cible pour la référence verticale
        
    Returns:
        Figure Plotly avec la courbe P&L
    """
    # Générer la plage de prix (±20% autour du prix cible)
    price_range = [target_price * (1 + i/100) for i in range(-20, 21, 1)]
    
    fig = go.Figure()
    
    # Lignes de référence
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=target_price, line_dash="dot", line_color="red", 
                  annotation_text="Target", opacity=0.7)
    
    # Calculer P&L
    if strategy.strategy is not None:
        pnl_values = [strategy.strategy.profit_at_expiry(price) for price in price_range]
        
        # Courbe P&L
        fig.add_trace(go.Scatter(
            x=price_range,
            y=pnl_values,
            mode='lines',
            name=strategy.strategy_name,
            line=dict(color='#1f77b4', width=3),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)',
            hovertemplate='Prix: $%{x:.2f}<br>P&L: $%{y:.2f}<extra></extra>'
        ))
        
        # Markers de breakeven
        if strategy.breakeven_points:
            fig.add_trace(go.Scatter(
                x=strategy.breakeven_points,
                y=[0] * len(strategy.breakeven_points),
                mode='markers',
                marker=dict(size=12, color='red', symbol='circle-open', line=dict(width=3)),
                name='Breakeven',
                hovertemplate='Breakeven: $%{x:.2f}<extra></extra>'
            ))
        
        # Marker au prix cible
        profit_at_target = strategy.strategy.profit_at_expiry(target_price)
        fig.add_trace(go.Scatter(
            x=[target_price],
            y=[profit_at_target],
            mode='markers',
            marker=dict(size=15, color='green', symbol='star'),
            name='Prix Cible',
            hovertemplate=f'Target: ${target_price:.2f}<br>P&L: ${profit_at_target:.2f}<extra></extra>'
        ))
    
    # Configuration du layout
    fig.update_layout(
        title=f"P&L - {strategy.strategy_name}",
        xaxis_title="Prix du Sous-Jacent ($)",
        yaxis_title="Profit / Perte ($)",
        height=400,
        hovermode='x unified',
        showlegend=True,
        plot_bgcolor='white',
        xaxis=dict(gridcolor='lightgray'),
        yaxis=dict(gridcolor='lightgray', zeroline=True, zerolinecolor='gray')
    )
    
    return fig


def display_interactive_strategy_table(
    strategies: List[StrategyComparison],
    target_price: float,
    key_prefix: str = "strategy_table"
) -> None:
    """
    Affiche un tableau interactif des stratégies avec sélection.
    Lorsqu'on clique sur une stratégie, son diagramme de payoff apparaît.
    
    Args:
        strategies: Liste des stratégies à afficher
        target_price: Prix cible pour les diagrammes
        key_prefix: Préfixe pour les clés Streamlit (évite les conflits)
    """
    if not strategies:
        st.warning("Aucune stratégie à afficher")
        return
    
    # Créer le DataFrame pour le tableau
    data = []
    for idx, strat in enumerate(strategies):
        data.append({
            'Sélection': idx,
            'Rang': strat.rank if strat.rank > 0 else idx + 1,
            'Stratégie': strat.strategy_name,
            'Score': f"{strat.score:.3f}",
            'Premium': format_currency(strat.premium),
            'Max Profit': format_currency(strat.max_profit),
            'Max Loss': format_currency(strat.max_loss) if strat.max_loss != float('inf') else 'Illimité',
            'R/R': f"{strat.risk_reward_ratio:.2f}" if strat.risk_reward_ratio != float('inf') else '∞',
            'P&L@Target': format_currency(strat.profit_at_target),
        })
    
    df = pd.DataFrame(data)
    
    # Configuration de l'affichage avec st.data_editor pour la sélection
    st.subheader("📊 Tableau des Stratégies - Cliquez pour voir le Payoff")
    
    # Utiliser un selectbox pour choisir la stratégie
    strategy_options = [f"{strat.rank if strat.rank > 0 else idx+1}. {strat.strategy_name}" 
                       for idx, strat in enumerate(strategies)]
    
    selected_strategy_name = st.selectbox(
        "Sélectionnez une stratégie pour voir son payoff :",
        options=strategy_options,
        key=f"{key_prefix}_selectbox"
    )
    
    # Afficher le tableau complet
    st.dataframe(
        df.drop('Sélection', axis=1),
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Trouver l'index de la stratégie sélectionnée
    selected_idx = strategy_options.index(selected_strategy_name)
    selected_strategy = strategies[selected_idx]
    
    # Afficher le diagramme de payoff de la stratégie sélectionnée
    st.divider()
    st.subheader(f"📈 Diagramme de Payoff - {selected_strategy.strategy_name}")
    
    # Créer deux colonnes pour les métriques et le graphique
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.metric("Score", f"{selected_strategy.score:.3f}")
        st.metric("Premium", format_currency(selected_strategy.premium))
        st.metric("Max Profit", format_currency(selected_strategy.max_profit))
        st.metric("Max Loss", format_currency(selected_strategy.max_loss) if selected_strategy.max_loss != float('inf') else 'Illimité')
        st.metric("R/R Ratio", f"{selected_strategy.risk_reward_ratio:.2f}" if selected_strategy.risk_reward_ratio != float('inf') else '∞')
        
        if selected_strategy.average_pnl is not None:
            st.metric("Avg P&L (Mixture)", format_currency(selected_strategy.average_pnl))
        if selected_strategy.sigma_pnl is not None:
            st.metric("σ P&L (Mixture)", format_currency(selected_strategy.sigma_pnl))
    
    with col2:
        # Créer et afficher le diagramme
        fig = create_single_strategy_payoff(selected_strategy, target_price)
        st.plotly_chart(fig, use_container_width=True)
    
    # Afficher les détails des options de la stratégie
    with st.expander("📋 Détails des Options"):
        if selected_strategy.all_options:
            options_data = []
            for opt in selected_strategy.all_options:
                options_data.append({
                    'Type': opt.option_type.upper(),
                    'Strike': f"${opt.strike:.2f}",
                    'Position': opt.position.upper(),
                    'Premium': format_currency(opt.premium),
                    'Delta': f"{opt.delta:.3f}" if opt.delta is not None else '-',
                    'Gamma': f"{opt.gamma:.3f}" if opt.gamma is not None else '-',
                    'Vega': f"{opt.vega:.3f}" if opt.vega is not None else '-',
                    'IV': f"{opt.implied_volatility:.2%}" if opt.implied_volatility is not None else '-',
                })
            
            options_df = pd.DataFrame(options_data)
            st.dataframe(options_df, use_container_width=True, hide_index=True)

