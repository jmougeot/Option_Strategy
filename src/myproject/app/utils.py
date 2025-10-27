# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from typing import Dict, List
from myproject.option.comparison_class import StrategyComparison
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

def create_comparison_table(comparisons: List[StrategyComparison]) -> pd.DataFrame:
    """Crée un DataFrame pour l'affichage des comparaisons avec TOUS les critères de scoring."""
    
    data = []
    for idx, comp in enumerate(comparisons, 1):
        # Calculs additionnels
        be_count = len(comp.breakeven_points)
        be_spread = (max(comp.breakeven_points) - min(comp.breakeven_points)) if len(comp.breakeven_points) >= 2 else 0
        
        data.append({
            'Rang': idx,
            'Stratégie': comp.strategy_name,
            'Expiration': format_expiration_date(comp.expiration_month, comp.expiration_year),
            'Premium': format_currency(comp.premium),
            'Score': f"{comp.score:.3f}",
            
            # 💰 MÉTRIQUES FINANCIÈRES
            'Max Profit': format_currency(comp.max_profit),
            'Max Loss': format_currency(comp.max_loss) if comp.max_loss != float('inf') else 'Illimité',
            'R/R': f"{comp.risk_reward_ratio:.2f}" if comp.risk_reward_ratio != float('inf') else '∞',
            'Zone ±': format_currency(comp.profit_zone_width),
            'P&L@Target': format_currency(comp.profit_at_target),
            'Target %': f"{comp.profit_at_target_pct:.1f}%",
            
            # 📐 SURFACES
            'Surf. Profit': f"{comp.surface_profit:.2f}",
            'Surf. Loss': f"{comp.surface_loss:.2f}",
            'P/L Ratio': f"{(comp.surface_profit/comp.surface_loss):.2f}" if comp.surface_loss > 0 else '∞',
            
            # 🔢 GREEKS
            'Delta': f"{comp.total_delta:.3f}",
            'Gamma': f"{comp.total_gamma:.3f}",
            'Vega': f"{comp.total_vega:.3f}",
            'Theta': f"{comp.total_theta:.3f}",
            
            # 📊 VOLATILITÉ & BREAKEVENS
            'IV': f"{comp.avg_implied_volatility:.2%}",
            'BE Count': be_count,
            'BE Spread': f"${be_spread:.2f}" if be_spread > 0 else '-',
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

def strike_list(strike_min: float, strike_max : float, step:float)->List[float]:
    strike_list = []
    strike = strike_min
    while strike<=strike_max:
        strike_list.append(strike)
        strike+=step
    return strike_list
